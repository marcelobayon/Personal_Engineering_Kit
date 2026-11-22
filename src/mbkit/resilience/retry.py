"""Bounded retry with exponential backoff and optional jitter.

From the biology-computing doc: *"Retry with bounded backoff for transient
errors."* The emphasis is on **bounded** — you declare which exceptions are
worth retrying, how many attempts, and a ceiling on the wait, so a transient
blip gets a second chance without turning into an infinite hammer on a
struggling dependency.

Example
-------
>>> calls = {"n": 0}
>>> @retry(attempts=3, base_delay=0, exceptions=(ValueError,))
... def flaky():
...     calls["n"] += 1
...     if calls["n"] < 3:
...         raise ValueError("not yet")
...     return "ok"
>>> flaky()
'ok'
>>> calls["n"]
3
"""

from __future__ import annotations

import functools
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

__all__ = ["retry", "RetryError"]

F = TypeVar("F", bound=Callable[..., Any])


class RetryError(RuntimeError):
    """Raised when every retry attempt has failed.

    The final underlying exception is attached as ``__cause__`` and ``last``.
    """

    def __init__(self, attempts: int, last: BaseException):
        super().__init__(f"all {attempts} attempt(s) failed: {last!r}")
        self.attempts = attempts
        self.last = last


def _compute_delay(
    attempt: int, base_delay: float, factor: float, max_delay: float, jitter: bool
) -> float:
    # attempt is 1-based; first retry waits base_delay.
    raw = base_delay * (factor ** (attempt - 1))
    raw = min(raw, max_delay)
    if jitter and raw > 0:
        # Full jitter: pick uniformly in [0, raw] to de-correlate retries.
        return random.uniform(0, raw)
    return raw


def retry(
    attempts: int = 3,
    *,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    base_delay: float = 0.1,
    factor: float = 2.0,
    max_delay: float = 10.0,
    jitter: bool = True,
    on_retry: Callable[[int, BaseException], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[F], F]:
    """Retry a function call on the listed ``exceptions``.

    Parameters
    ----------
    attempts:
        Total tries, including the first. ``attempts=3`` means up to 2 retries.
    exceptions:
        Only these exception types trigger a retry; anything else propagates
        immediately (do not retry a bug).
    base_delay, factor, max_delay:
        Backoff grows as ``base_delay * factor**(n-1)``, capped at ``max_delay``.
    jitter:
        Spread retries randomly within the computed delay to avoid thundering
        herds when many clients retry at once.
    on_retry:
        Optional callback ``(attempt, exception)`` for logging or metrics.
    sleep:
        Injectable sleep, so tests can run with ``base_delay=0`` and no waiting.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    def decorate(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    last = exc
                    if attempt == attempts:
                        break
                    if on_retry is not None:
                        on_retry(attempt, exc)
                    delay = _compute_delay(attempt, base_delay, factor, max_delay, jitter)
                    if delay > 0:
                        sleep(delay)
            assert last is not None
            raise RetryError(attempts, last) from last

        return wrapper  # type: ignore[return-value]

    return decorate
