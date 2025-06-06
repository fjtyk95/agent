from __future__ import annotations

import logging
import time
from typing import Callable, Any, Tuple

__all__ = ["Timer", "timed_run"]


class Timer:
    """Context manager to measure elapsed time."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.start = 0.0
        self.elapsed = 0.0

    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        self.elapsed = time.perf_counter() - self.start
        logging.info("[Timer] %s: %.3f sec", self.label, self.elapsed)


def timed_run(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Tuple[Any, float]:
    """Execute ``fn`` and return its result and elapsed seconds."""
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed = time.perf_counter() - start
    logging.info("[Timer] %s: %.3f sec", getattr(fn, "__name__", "<func>"), elapsed)
    return result, elapsed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    def sample(n: int) -> int:
        s = 0
        for i in range(n):
            s += i
        return s

    with Timer("sample-loop"):
        sample(1000000)

    timed_run(sample, 1000000)
