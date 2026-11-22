"""Lightweight timing: a ``Timer`` context manager and a ``@timed`` decorator.

Measuring "how long did that take?" is the first step toward the resource-aware
behaviour the biology-computing doc describes — you cannot throttle or budget
what you have not measured.

Example
-------
>>> with Timer("load") as t:
...     total = sum(range(1_000_00))
>>> t.elapsed >= 0
True

>>> @timed()
... def work():
...     return 42
>>> work()
42
"""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

__all__ = ["Timer", "timed"]

F = TypeVar("F", bound=Callable[..., Any])


class Timer:
    """Context manager that records wall-clock elapsed seconds.

    Uses :func:`time.perf_counter`, the right clock for measuring durations.
    Optionally logs the result on exit when given a ``logger``.
    """

    def __init__(self, label: str = "block", logger: logging.Logger | None = None):
        self.label = label
        self.logger = logger
        self.start: float = 0.0
        self.end: float | None = None

    @property
    def elapsed(self) -> float:
        """Seconds elapsed; valid during and after the ``with`` block."""
        end = self.end if self.end is not None else time.perf_counter()
        return end - self.start

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed * 1000.0

    def __enter__(self) -> Timer:
        self.start = time.perf_counter()
        self.end = None
        return self

    def __exit__(self, *exc: Any) -> None:
        self.end = time.perf_counter()
        if self.logger is not None:
            self.logger.info(
                "%s took %.2f ms", self.label, self.elapsed_ms,
                extra={"label": self.label, "elapsed_ms": round(self.elapsed_ms, 3)},
            )


def timed(
    logger: logging.Logger | None = None,
    *,
    label: str | None = None,
    level: int = logging.INFO,
) -> Callable[[F], F]:
    """Decorator that times a function call and logs its duration.

    >>> log = logging.getLogger("demo")
    >>> @timed(log, label="fetch")
    ... def fetch(): return "ok"
    >>> fetch()
    'ok'
    """

    def decorate(fn: F) -> F:
        name = label or fn.__qualname__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                if logger is not None:
                    logger.log(
                        level,
                        "%s took %.2f ms",
                        name,
                        elapsed_ms,
                        extra={"label": name, "elapsed_ms": round(elapsed_ms, 3)},
                    )

        return wrapper  # type: ignore[return-value]

    return decorate
