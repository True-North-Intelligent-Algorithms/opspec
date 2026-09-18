# 0002 — Runner

## Background

A runner is what actually calls ops.  

## What a runner does

- (Optionally) **Provides the environment** the op asked for with `env=`.
- (Optionally) **Slices** — the op declared `Axes("z", "y", "x")` and the
  caller has ZYXT, so the runner loops over T and gathers the results.
- (Optionally) **Chunks** — the op declared a `WorkingSet`, so the runner
  divides the input into tiles that fit the memory it has.
- **Calls the op** with the caller's arguments.
- **Returns the result**, or an error.

opspec does the arithmetic for the two optional ones: how many slices,
which tile size fits the budget. That is shape and byte counting, so it
stays in opspec. Carrying it out — slicing the array, calling the op once
per tile, putting the pieces back — touches pixels, so it belongs to the
runner.

## What a runner is

A Protocol. opspec says what methods a runner has; it ships no runner.
The simplest one calls the function in this process. Others start a
worker, a conda environment, or a machine with a GPU.
