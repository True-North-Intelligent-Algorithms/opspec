# A different widget generator

Three parts, deliberately separate:

- `label_op/` — one op and a manifest. The author writes
  `autogenerate: example-runner` and nothing else. No napari code, no
  widget code, no runner.
- `example_runner/` — a runner, and a napari widget wired to it. The
  runner is the point; the widget exists because napari's own path wires
  the call into magicgui.
- npe2 — a small patch so `autogenerate` may name a generator instead of
  only being true or false:
  https://github.com/napari/npe2/compare/main...bnorthan:npe2:pluggable-widget-generators

## Install

    pip install -e <npe2 checkout, branch pluggable-widget-generators>
    pip install -e example_runner
    pip install -e label_op

## Run

    napari

Open an image, then Plugins > Label objects. A dialog says which generator
built the panel, and another says which runner ran the op.

The panel has a layer dropdown and a sigma slider from 0.1 to 10, both read
from the op's signature.

## Where the run logic lives

`example_runner/src/example_runner/widget.py`:

    result = runner.run(op, values)

`InProcessRunner` calls the op here. Swap it for one that builds an
environment, slices a stack or tiles for memory, and neither the op nor the
manifest changes.
