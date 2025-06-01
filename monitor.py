import logging
import time
from collections.abc import Callable
from typing import Any


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
        if self.start is None:
            return
        self.elapsed = time.perf_counter() - self.start
        logging.getLogger(__name__).info("[Timer] %s: %.3f sec", self.label, self.elapsed)


def timed_run(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[Any, float]:
    """Run ``fn`` and return its result along with elapsed seconds."""
    with Timer(fn.__name__) as t:
        result = fn(*args, **kwargs)
    assert t.elapsed is not None
    return result, t.elapsed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    def sample_task(duration: float) -> str:
        time.sleep(duration)
        return "done"

    res, seconds = timed_run(sample_task, 0.1)
    print(f"result={res}, elapsed={seconds:.3f} sec")
