import java.nio.ByteBuffer;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.apposed.appose.Appose;
import org.apposed.appose.Environment;
import org.apposed.appose.NDArray;
import org.apposed.appose.Service;

/** Read an op's spec from Python, then run the op. */
public class Demo {

	static final String PIXI =
		"[workspace]\n" +
		"name = \"opspec-demo\"\n" +
		"version = \"0.1.0\"\n" +
		"channels = [\"conda-forge\"]\n" +
		"platforms = [\"linux-64\", \"osx-64\", \"osx-arm64\", \"win-64\"]\n" +
		"[dependencies]\n" +
		"python = \"3.11.*\"\n" +
		"numpy = \"*\"\n" +
		"[pypi-dependencies]\n" +
		"appose = \"*\"\n";

	public static void main(String[] args) throws Exception {
		String opspecSrc = Paths.get("../../src").toAbsolutePath().normalize().toString();
		String opDir = Paths.get("python").toAbsolutePath().normalize().toString();

		Environment env = Appose.pixi().content(PIXI).name("opspec-demo")
			.subscribeOutput(System.out::print)
			.subscribeError(System.err::print)
			.build();

		try (Service python = env.python()) {
			python.debug(s -> {});
			python.init(
				"import sys\n" +
				"sys.path.insert(0, r'" + opspecSrc + "')\n" +
				"sys.path.insert(0, r'" + opDir + "')\n" +
				"import numpy as np\n" +
				"import demo_op\n" +
				"from opspec.op import OpSpec\n" +
				"the_op = demo_op.threshold\n");

			// 1. use the opspec converted to a dict to find out what the op takes
			Map<String, Object> spec = task(python, "OpSpec.from_op(the_op).to_dict()", Map.of());
			System.out.println("op: " + spec.get("name") + "  env: " + spec.get("env"));
			for (Object p : (List<?>) spec.get("params")) {
				Map<?, ?> param = (Map<?, ?>) p;
				System.out.println("  param " + param.get("name")
					+ " type=" + ((Map<?, ?>) param.get("type")).get("name")
					+ " default=" + param.get("default")
					+ " ui=" + param.get("ui")
					+ (param.get("axes") == null ? "" : " axes=" + axes(param.get("axes"))));
			}
			for (Object o : (List<?>) spec.get("outputs")) {
				Map<?, ?> out = (Map<?, ?>) o;
				System.out.println("  output " + out.get("name") + " role=" + out.get("role"));
			}

			// 2. inputs: a gradient image, and an output buffer of the same shape
			int h = 64, w = 64;
			NDArray image = new NDArray(NDArray.DType.FLOAT32,
				new NDArray.Shape(NDArray.Shape.Order.C_ORDER, h, w));
			ByteBuffer in = image.buffer();
			for (int y = 0; y < h; y++)
				for (int x = 0; x < w; x++) in.putFloat((float) x / w);

			NDArray labels = new NDArray(NDArray.DType.UINT16,
				new NDArray.Shape(NDArray.Shape.Order.C_ORDER, h, w));

			// 3. call it: names come from the spec, not from this file
			Map<String, Object> inputs = new LinkedHashMap<>();
			inputs.put("image", image);
			inputs.put("level", 0.75);
			inputs.put("labels", labels);
			task(python,
				"labels.ndarray()[:] = the_op(image=image.ndarray(), level=level)\n" +
				"{'set': int(labels.ndarray().sum())}",
				inputs);

			// 4. read the result back out of shared memory
			ByteBuffer out = labels.buffer();
			int set = 0;
			for (int i = 0; i < h * w; i++) if (out.getShort() != 0) set++;
			System.out.println("pixels labelled: " + set + " of " + (h * w));

			image.close();
			labels.close();
		}
	}

	/** "y, x, c?" or "y, x, ... " for a variadic op. */
	static String axes(Object spec) {
		Map<?, ?> a = (Map<?, ?>) spec;
		StringBuilder sb = new StringBuilder();
		for (Object s : (List<?>) a.get("slots")) {
			Map<?, ?> slot = (Map<?, ?>) s;
			Object name = slot.get("name");
			if (sb.length() > 0) sb.append(", ");
			sb.append(name == null ? "*" : name);
			if (Boolean.TRUE.equals(slot.get("optional"))) sb.append("?");
		}
		if (Boolean.TRUE.equals(a.get("variadic"))) sb.append(", ...");
		return sb.toString();
	}

	@SuppressWarnings("unchecked")
	static Map<String, Object> task(Service python, String script, Map<String, Object> inputs)
		throws Exception
	{
		Service.Task t = python.task(script, inputs);
		t.waitFor();
		if (t.status != Service.TaskStatus.COMPLETE) throw new RuntimeException(t.error);
		// a script evaluating to a dict has that dict *as* its outputs
		return t.outputs;
	}
}
