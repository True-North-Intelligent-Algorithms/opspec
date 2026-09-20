# Java demo

Java reads an op's spec from Python, then calls the op.

    mvn compile exec:java -Dexec.mainClass=Demo

First run builds a small pixi environment (python, numpy, appose).

- `python/demo_op.py` — the op: `@op def threshold(image, level=0.5)`
- `src/main/java/Demo.java` — describe, then call

Output:

    op: demo_op:threshold  env: demo
      param image type=ndarray default=null ui=null
      param level type=float default=0.5 ui={min=0.0, max=1.0}
      output result role=labels
    pixels labelled: 1024 of 4096
