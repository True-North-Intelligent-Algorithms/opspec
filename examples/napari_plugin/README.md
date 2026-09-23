# A custom widget generator for ops

This project is an example of how we could override the current magicgui
widget generator to use a custom generator hooked to custom run logic.

There are three parts:

- `label_op/` — an op and a manifest. In the manifest we add
  `autogenerate: example-runner` to indicate we want to use a custom
  generator (`autogenerate: true` works as before).
- `example_runner/` — a runner, and a widget generator. We want custom run
  logic, but napari wires the call into magicgui. So to override the run,
  we need to override the widget generator. We still use magicgui to make
  the widget, but wire it to a different run. In addition, napari and
  magicgui don't support the ops annotations, but since we route widget
  generation to our own code we can handle this ourselves.
- npe2 — a small patch so `autogenerate` may name a generator instead of
  only being true or false:
  https://github.com/napari/npe2/compare/main...bnorthan:npe2:pluggable-widget-generators

## Install

    pip install -e <npe2 checkout, branch pluggable-widget-generators>
    pip install -e example_runner
    pip install -e label_op

## Run

    napari

Open an image, then Plugins > Label objects. You should see dialogs pop up
to let you know you are running via a different runner.

The panel has a layer dropdown and a sigma slider from 0.1 to 10, both read
from the op's signature.

## Where the run logic lives

`example_runner/src/example_runner/widget.py`:

    result = runner.run(op, values)

`InProcessRunner` calls the op here. Swap it for one that builds an
environment, slices a stack or tiles for memory, and neither the op nor the
manifest changes.
