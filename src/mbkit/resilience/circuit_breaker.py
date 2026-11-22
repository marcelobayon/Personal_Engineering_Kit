"""A thread-safe circuit breaker (closed / open / half-open).

From the biology-computing doc this is *homeostasis + protection*: when a
dependency keeps failing, stop calling it for a cooling-off period instead of
piling on load and timing out every request. After the window, let a single
trial request through (half-open); success closes the circuit, failure re-opens
it.

The teaching sketch in the theory doc was single-threaded; this version adds a
lock, an explicit half-open trial state, and a guard so only one trial runs at a
time.

Example
-------
>>> breaker = CircuitBreaker(failure_threshold=2, reset_timeout=0.05)
>>> def boom(): raise ConnectionError("down")
>>> for _ in range(2):
...     try: breaker.call(boom)
...     except ConnectionError: pass
>>> breaker.state
'open'
>>> try:
...     breaker.call(lambda: "x")
... except CircuitOpenError:
...     "blocked"
'blocked'
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

__all__ = ["CircuitBreaker", "CircuitOpenError", "CircuitState"]

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"      # normal: calls pass through
    OPEN = "open"          # tripped: calls are rejected fast
    HALF_OPEN = "half_open"  # trial: one call allowed to test recovery


class CircuitOpenError(RuntimeError):
    """Raised when a call is attempted while the breaker is open."""


class CircuitBreaker:
    """Protect a callable behind a failure-counting circuit.

    Parameters
    ----------
    failure_threshold:
        Consecutive failures that trip the breaker from closed to open.
    reset_timeout:
        Seconds to stay open before allowing a half-open trial request.
    exceptions:
        Which exception types count as failures. Others pass through and do not
        affect the breaker (a validation error is not an outage).
    """

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        reset_timeout: float = 30.0,
        exceptions: tuple[type[BaseException], ...] = (Exception,),
        clock: Callable[[], float] = time.monotonic,
    ):
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.exceptions = exceptions
        self._clock = clock

        self._lock = threading.RLock()
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at = 0.0

    @property
    def state(self) -> str:
        """Current state as a string, re-evaluating the open->half-open timer."""
        with self._lock:
            self._maybe_half_open()
            return self._state.value

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failures

    def _maybe_half_open(self) -> None:
        if (
            self._state is CircuitState.OPEN
            and self._clock() - self._opened_at >= self.reset_timeout
        ):
            self._state = CircuitState.HALF_OPEN

    def _on_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if (
                self._state is CircuitState.HALF_OPEN
                or self._failures >= self.failure_threshold
            ):
                self._state = CircuitState.OPEN
                self._opened_at = self._clock()

    def call(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Invoke ``fn`` through the breaker.

        Raises :class:`CircuitOpenError` immediately if the circuit is open.
        On an allowed call, a failure (one of ``exceptions``) is recorded and
        re-raised; a success resets the breaker.
        """
        with self._lock:
            self._maybe_half_open()
            if self._state is CircuitState.OPEN:
                raise CircuitOpenError(
                    f"circuit open; retry in "
                    f"{self.reset_timeout - (self._clock() - self._opened_at):.1f}s"
                )

        try:
            result = fn(*args, **kwargs)
        except self.exceptions:
            self._on_failure()
            raise
        else:
            self._on_success()
            return result

    def __call__(self, fn: Callable[..., T]) -> Callable[..., T]:
        """Use the breaker as a decorator."""
        import functools

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return self.call(fn, *args, **kwargs)

        return wrapper
