# 0001 — opspec

**Status:** living. Grows one entry at a time.

## Background  

scikit-ops grew a description of ops that nothing outside scikit-ops can
use without installing scikit-ops. The description itself is small and
needs no dependencies, so it can live on its own, where any host or
backend can read it.

## What an `OpSpec` is

`OpSpec` is a frozen dataclass holding what was read from an op's
signature: its name, its parameters and annotations with their types,
roles and defaults, its return.

```python
a = OpSpec.from_op(threshold)
type(a)        # <class 'opspec.OpSpec'>
a.params[0]    # ParamSpec(name='input1', type=np.ndarray, role=Role.image, ...)
a.env          # 'cupy'
```

Reading a signature needs only `inspect` and `typing`, so opspec ships
this reader itself, so every host does not have to write its own. The
class also converts to a plain dict, so a spec can cross to another
process where the function cannot.

## Op decorators, types, and annotations

**`@op`** — the decorator a plugin author puts on a function to say "this
is an op"

**`Role`** — what an input or output *means*: image, labels, masks,
points, boxes. A host maps a role to its own representations (ie bounding
boxes to napari.layers.Shapes).

**`ImageOf`** — allows image to be templated: `ImageOf[np.ndarray]` says numpy
only, `ImageOf[Array]` says any array. What the data means (the role) and
which array type holds it are separate.

Everything an op declares is visible in one line:

```python
def threshold(input1: ImageOf[np.ndarray]) -> LabelsOf[np.ndarray]: ...
#             ^name   ^role   ^array type     ^role   ^array type
```

`input1` is the name a host shows the user. `ImageOf` and `LabelsOf` are
roles: this one is an image, that one is labels. `np.ndarray` is the array
type, on both sides: this op takes numpy and returns numpy.

**`env`** — which environment the op runs in, given to the decorator:
`@op(env="cupy")`. It names the environment, it does not build it; making
that environment exist is a runner's job.

**`Axes`** — the shape of input the op consumes: `Axes("z", "y", "x")`
says it works on one volume at a time, so a caller holding a 4D stack
knows to loop rather then passing the entire array.  `Axes("z?", "y", "x", "t")`
indicates the op can handle a time series of frames, and optionally volumes (? indicates z is optional) 

**`PeakMemory`** — peak memory use of the op expressed as a multiple of
image size, `PeakMemory(scale=8, dtype=np.float32)`

An example with env, role, array type, axes, and peak memory (memory use)
all added.

```python
@op(env="cupy")
def richardson_lucy(
    input1: Annotated[
        ImageOf[cp.ndarray],
        Axes("z", "y", "x"),
        PeakMemory(scale=8, dtype=np.float32),
    ],
    psf: ImageOf[cp.ndarray],
    num_iters: int = 10,
) -> ImageOf[cp.ndarray]: ...
```

The above indicates run me in the `cupy` environment; hand me one ZYX volume at a
time; expect about 8x that volume as float32 while I work. `psf` carries a
role and an array type only — it is small, it is not tiled.  The op returns a numpy Array. 
