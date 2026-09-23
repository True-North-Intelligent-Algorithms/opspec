"""The widget: what npe2 calls for ``autogenerate: example-runner``.

Handed the op, it reads the spec for what to show, and calls the runner for
what to do. It names no parameter and knows no algorithm.
"""

from magicgui.widgets import Container, PushButton, create_widget

import napari

from opspec.op import OpSpec, Role

from .dialog import shout
from .runner import InProcessRunner

__all__ = ["build"]


def build(op, runner=None):
    """Return a factory that makes a panel calling *runner* for *op*."""
    spec = OpSpec.from_op(op)
    runner = runner or InProcessRunner()

    def factory() -> Container:
        widgets = _widgets_for(spec)

        def run() -> None:
            viewer = napari.current_viewer()
            values = _values(spec, widgets)

            result = runner.run(op, values)

            shout(f"{type(runner).__name__} ran {spec.name}.\nNot magicgui.")
            _show(viewer, spec, result)

        shout(f"example_runner built this panel from {spec.name}.")
        button = PushButton(text="Run")
        button.changed.connect(run)
        return Container(widgets=[*widgets.values(), button])

    return factory


def _widgets_for(spec: OpSpec) -> dict:
    """One widget per parameter, from what the op declared."""
    widgets = {}
    for param in spec.params:
        if param.role is Role.image:
            widgets[param.name] = create_widget(
                annotation=napari.layers.Image, label=param.name
            )
        else:
            widgets[param.name] = create_widget(
                value=param.default,
                annotation=param.type,
                options=dict(param.ui),
                label=param.name,
            )
    return widgets


def _values(spec: OpSpec, widgets: dict) -> dict:
    """What the widgets hold, as the op wants it: layers become arrays."""
    values = {name: w.value for name, w in widgets.items()}
    for param in spec.params:
        if param.role is Role.image:
            values[param.name] = values[param.name].data
    return values


def _show(viewer, spec: OpSpec, result) -> None:
    """Add each output as the layer its role calls for."""
    results = result if isinstance(result, tuple) else (result,)
    for output, value in zip(spec.outputs, results):
        add = viewer.add_labels if output.role is Role.labels else viewer.add_image
        add(value, name=f"{spec.function} {output.name}")
