import logging
import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class Timer:
    """Context manager for measuring execution time."""

    def __init__(self, label: str) -> None:
        self.label = label
        self._start = 0.0
        self.elapsed = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.elapsed = time.perf_counter() - self._start
        logging.info("[Timer] %s: %.3f sec", self.label, self.elapsed)


def timed_run(fn: Callable[..., T], *args: Any, **kwargs: Any) -> tuple[T, float]:
    """Execute ``fn`` and return its result along with elapsed seconds."""
    with Timer(fn.__name__) as timer:
        result = fn(*args, **kwargs)
    return result, timer.elapsed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    def _demo_task(seconds: float) -> str:
        time.sleep(seconds)
        return "done"

    with Timer("context demo"):
        _demo_task(0.2)

    result, secs = timed_run(_demo_task, 0.3)
    print(f"timed_run: {result} in {secs:.3f} sec")
