"""One op. It knows nothing about napari, widgets or runners."""

from typing import Annotated

import numpy as np
from skimage import filters, measure

from opspec.op import op
from opspec.types import ImageOf, LabelsOf


@op
def label_objects(
    image: ImageOf[np.ndarray],
    sigma: Annotated[float, {"min": 0.1, "max": 10.0, "step": 0.1}] = 2.0,
) -> LabelsOf[np.ndarray]:
    """Blur, threshold, then number each connected object."""
    blurred = filters.gaussian(image, sigma=sigma)
    return measure.label(blurred > filters.threshold_otsu(blurred))
