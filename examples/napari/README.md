# napari panel from a spec

    python run.py

- `ops.py` declares the op. It does not import napari.
- `panel.py` reads the spec: a role `image` parameter becomes a layer
  dropdown, everything else becomes a widget with the op's own default and
  range. The Run button gathers the values and calls the op.
- Outputs are added by role: `labels` makes a Labels layer.

Add a parameter to the op and the panel grows one. The panel names no
parameter.
