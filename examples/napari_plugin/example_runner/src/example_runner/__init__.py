"""A runner for opspec ops, and a napari widget wired to it."""

from .runner import InProcessRunner
from .widget import build

__all__ = ["InProcessRunner", "build"]
