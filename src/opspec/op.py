"""Op declaration and signature introspection.

Standard library only: this module is imported inside every worker
environment, so it must depend on nothing heavier.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Any, get_args, get_origin, get_type_hints


class Role(Enum):
    """What a value *means*

    Attach with ``Annotated[T, Role.<name>]``::

        @op
        def threshold(
            image: Annotated[np.ndarray, Role.image],
        ) -> Annotated[np.ndarray, Role.labels]: ...

    A host reads ``Role.labels`` and shows the result as a segmentation
    rather than a grey picture.
    """

    boxes = "boxes"
    image = "image"
    labels = "labels"
    masks = "masks"
    points = "points"
    shapes = "shapes"
    surface = "surface"
    tracks = "tracks"
    vectors = "vectors"


def role_of(annotation: Any) -> Role | None:
    """Read the role off an annotation, or ``None`` if it declares no role."""
    if get_origin(annotation) is Annotated:
        for meta in get_args(annotation)[1:]:
            if isinstance(meta, Role):
                return meta
    return None


#: Axis names a viewer can map onto display semantics. Privileged, not
#: exclusive: any string is a valid axis label.
CANONICAL = ("x", "y", "z", "c", "t")

#: Synonyms, resolved by lookup rather than guessed: ``row`` *is* ``y``.
#: From scikit-image, ImageJ, Bio-Formats, CZI and OME-NGFF. Labels with
#: no canonical equivalent (``lifetime``, ``batch``) pass through.
ALIASES = {
    "col": "x",
    "cols": "x",
    "column": "x",
    "columns": "x",
    "row": "y",
    "rows": "y",
    "pln": "z",
    "plane": "z",
    "planes": "z",
    "slice": "z",
    "slices": "z",
    "ch": "c",
    "chan": "c",
    "channel": "c",
    "channels": "c",
    "frame": "t",
    "frames": "t",
    "time": "t",
    "timepoint": "t",
    "timepoints": "t",
}


def canonical(label: str) -> str:
    """One axis label, case ignored and resolved: ``ROW`` -> ``y``.

    Unrecognized labels pass through lowercased, so ``"lifetime"`` survives.
    """
    folded = label.strip().casefold()
    return ALIASES.get(folded, folded)


WILDCARD = "*"


@dataclass(frozen=True)
class Slot:
    """One axis an op consumes. ``name`` is a hint, not a requirement.

    ``name`` None is a wildcard: no preference at all.
    """

    name: str | None
    optional: bool = False

    def __str__(self) -> str:
        return (self.name or WILDCARD) + ("?" if self.optional else "")


@dataclass(frozen=True, init=False)
class Axes:
    """How many axes an op consumes, and what it likes to call them::

        Axes("y", "x")        # two axes, named y and x
        Axes(list("zyx"))     # three
        Axes("y", "x", "c?")  # two, plus a channel axis if there is one
        Axes("*", "*")        # two axes, no opinion which
        Axes(variadic=True)   # any number

    - Names are hints. A mismatch is reported in the plan, never refused.
    - Arity binds: how many axes the op consumes is what its indexing needs.
    - ``variadic`` means the op handles extra axes itself, so they need
      not be looped over.
    - Inert at runtime. Calling the op directly ignores all of this.
    """

    slots: tuple[Slot, ...]
    variadic: bool

    def __init__(self, *names: Any, variadic: bool = False) -> None:
        # Note: frozen blocks ordinary assignment, so a hand-written __init__
        # has to set fields the way dataclass itself does. Storing the parsed
        # slots rather than the raw text is what makes Axes("z", "y", "x") and
        # Axes("pln", "row", "col") compare equal, as they should.
        if len(names) == 1 and not isinstance(names[0], str):
            # A lone non-string is the sequence itself: Axes(list("zyx")).
            names = tuple(names[0])
        object.__setattr__(self, "slots", _parse_slots(names))
        object.__setattr__(self, "variadic", variadic)

    @property
    def names(self) -> tuple[str, ...]:
        """Each slot's preferred name, with ``"*"`` standing in for a wildcard."""
        return tuple(str(slot).removesuffix("?") for slot in self.slots)

    @property
    def optional(self) -> frozenset[str]:
        """Names of the slots that need not be filled."""
        return frozenset(
            slot.name for slot in self.slots if slot.optional and slot.name
        )

    @property
    def core(self) -> tuple[str, ...]:
        """Preferred names of the slots that must be filled."""
        return tuple(str(slot) for slot in self.slots if not slot.optional)

    def __repr__(self) -> str:
        shown = ", ".join(repr(str(slot)) for slot in self.slots)
        if self.variadic:
            shown = f"{shown}, variadic=True" if shown else "variadic=True"
        return f"Axes({shown})"


def _parse_slots(names: tuple[Any, ...]) -> tuple[Slot, ...]:
    """Validate slot spellings, resolving names and splitting off the '?'."""
    slots: list[Slot] = []
    seen: set[str] = set()
    for label in names:
        if label == "?":
            raise ValueError(
                "A lone '?' is not an axis. Mark the axis it belongs to, as 'c?'."
            )
        if not isinstance(label, str) or not label.strip("?"):
            raise ValueError(f"Axis label {label!r} is not a non-empty string")
        if any(char.isspace() or char == "," for char in label.strip()):
            raise ValueError(
                f"Axis label {label!r} has a separator in it; pass one label "
                "per argument, as Axes('z', 'y', 'x')."
            )
        optional = label.endswith("?")
        text = label.removesuffix("?")
        if text == WILDCARD:
            if optional:
                # A wildcard has no name, and an optional slot is filled only
                # by a name match, so '*?' could never be filled by anything.
                raise ValueError(
                    "'*?' is not a usable slot: a wildcard has no name to match "
                    "on, and an optional slot is filled only by name. Use '*' "
                    "for an axis the op always takes, or variadic=True for a "
                    "tail of axes it may or may not be given."
                )
            # Wildcards are exempt from the repeat check: Axes('*', '*') is
            # two axes the op has no opinion about, which is the whole point.
            slots.append(Slot(None, False))
            continue
        name = canonical(text)
        if name in seen:
            raise ValueError(f"Repeated axis {name!r} in {names}")
        seen.add(name)
        slots.append(Slot(name, optional))
    return tuple(slots)


def axes_of(annotation: Any) -> Axes | None:
    if get_origin(annotation) is Annotated:
        for meta in get_args(annotation)[1:]:
            if isinstance(meta, Axes):
                return meta
    return None


@dataclass(frozen=True)
class _OpConfig:
    env: str | None


def op(fn: Callable | None = None, *, env: str | None = None) -> Callable:
    """Declare a function as an op.

    Sets an attribute on the function and returns the same function, so
    calling it directly is unaffected. Bare or called, like ``@dataclass``::

        @op
        def smooth(image: ImageOf[np.ndarray]) -> ImageOf[np.ndarray]: ...

        @op(env="cupy")
        def deconvolve(image: ImageOf[cp.ndarray]) -> ImageOf[cp.ndarray]: ...

    Args:
        env: Environment the op runs in. Omit it and the op runs wherever
            the caller is.
    """

    def decorate(f: Callable) -> Callable:
        f.__opspec__ = _OpConfig(env=env)
        return f

    return decorate(fn) if fn is not None else decorate


def is_op(obj: Any) -> bool:
    """Whether ``obj`` carries the ``@op`` decorator."""
    return callable(obj) and isinstance(getattr(obj, "__opspec__", None), _OpConfig)


def ui_hints_of(annotation: Any) -> dict:
    """Collect dict metadata off an annotation: widget hints for a host::

        sigma: Annotated[float, {"min": 0.1, "max": 10.0}] = 2.0

    Several dicts merge, left to right. opspec does not interpret the keys;
    a host reads the ones it knows.
    """
    hints: dict = {}
    if get_origin(annotation) is Annotated:
        for meta in get_args(annotation)[1:]:
            if isinstance(meta, dict):
                hints.update(meta)
    return hints


def _strip(annotation: Any) -> Any:
    """The underlying type of a possibly-``Annotated`` annotation."""
    if get_origin(annotation) is Annotated:
        return get_args(annotation)[0]
    return annotation


@dataclass(frozen=True)
class ParamSpec:
    """One parameter of an op, as declared."""

    name: str
    type: Any
    default: Any
    role: Role | None = None
    axes: Axes | None = None
    ui: dict = field(default_factory=dict)


@dataclass(frozen=True)
class OpSpec:
    """A class to convert an op signature into data::

        spec = OpSpec.from_op(threshold)
        spec.return_role        # <Role.labels: 'labels'>
    """

    name: str
    module: str
    function: str
    env: str | None
    params: tuple[ParamSpec, ...]
    return_type: Any
    return_role: Role | None
    doc: str | None

    @classmethod
    def from_op(cls, fn: Callable) -> OpSpec:
        """Read the spec off a decorated op.

        Annotations are resolved here rather than at decoration time, so an
        op may refer to types defined later in its own module.
        """
        config = getattr(fn, "__opspec__", None)
        if not isinstance(config, _OpConfig):
            raise TypeError(f"Not an op: {fn!r} (missing @op decorator)")

        signature = inspect.signature(fn)
        hints = get_type_hints(fn, include_extras=True)

        params = []
        for name, param in signature.parameters.items():
            annotation = hints.get(name, param.annotation)
            params.append(
                ParamSpec(
                    name=name,
                    type=_strip(annotation),
                    default=param.default,
                    role=role_of(annotation),
                    axes=axes_of(annotation),
                    ui=ui_hints_of(annotation),
                )
            )

        returns = hints.get("return", signature.return_annotation)
        return cls(
            name=f"{fn.__module__}:{fn.__name__}",
            module=fn.__module__,
            function=fn.__name__,
            env=config.env,
            params=tuple(params),
            return_type=_strip(returns),
            return_role=role_of(returns),
            doc=inspect.getdoc(fn),
        )
