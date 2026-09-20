from typing import Annotated

import numpy as np

from opspec.op import Axes, op
from opspec.types import ImageOf, LabelsOf


@op(env="demo")
def threshold(
    image: Annotated[ImageOf[np.ndarray], Axes("y", "x")],
    level: Annotated[float, {"min": 0.0, "max": 1.0}] = 0.5,
) -> LabelsOf[np.ndarray]:
    """Everything brighter than level * max becomes 1."""
    return (image > level * image.max()).astype(np.uint16)
