"""Op declaration and signature introspection.

Standard library only: this module is imported inside every worker
environment, so it must depend on nothing heavier.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, get_args, get_origin


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
