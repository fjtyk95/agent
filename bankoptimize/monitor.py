from __future__ import annotations

import logging
import time
from typing import Callable, Any, Tuple

__all__ = ["Timer", "timed_run"]


class Timer:
    """Context manager for measuring execution time."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.start: float | None = None
        self.elapsed: float | None = None

    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.elapsed = time.perf_counter() - (self.start or 0)
        logging.info("[Timer] %s: %.3f sec", self.label, self.elapsed)


def timed_run(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Tuple[Any, float]:
    """Run ``fn`` and return its result and runtime in seconds."""
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed = time.perf_counter() - start
    logging.info("[Timer] %s: %.3f sec", getattr(fn, "__name__", "func"), elapsed)
    return result, elapsed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    def _demo() -> None:
        time.sleep(0.1)

    with Timer("demo block"):
        _demo()

    timed_run(_demo)
