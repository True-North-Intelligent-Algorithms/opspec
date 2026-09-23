"""The runner: what it means to call an op.

``InProcessRunner`` satisfies opspec's ``Runner`` protocol and calls the op
here, in this process. A runner that builds an environment, slices a stack
or tiles for memory would replace this class and nothing else.
"""

from typing import Any

__all__ = ["InProcessRunner"]


class InProcessRunner:
    def run(self, fn, args: dict | None = None, **kwargs: Any) -> Any:
        return fn(**{**(args or {}), **kwargs})

    def close(self) -> None:
        pass
