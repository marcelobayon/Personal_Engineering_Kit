"""Approved-fallback chains: try reviewed alternatives in order.

From the biology-computing doc (*opportunism + redundancy*): when the preferred
provider is unavailable, switch to a **pre-approved** alternative — never an
arbitrary substitute. Each option is tried in order; the first that both
succeeds *and* passes an optional validity check wins. If all fail, every error
is reported together so you can see why.

Example
-------
>>> def primary(): raise ConnectionError("down")
>>> def secondary(): return "from-secondary"
>>> chain = FallbackChain([("primary", primary), ("secondary", secondary)])
>>> value, source = chain.run()
>>> (value, source)
('from-secondary', 'secondary')
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Generic, TypeVar

__all__ = ["FallbackChain", "AllFallbacksFailed", "fallback"]

T = TypeVar("T")

Option = tuple[str, Callable[[], T]]


class AllFallbacksFailed(RuntimeError):
    """Raised when no option in the chain produced a valid result."""

    def __init__(self, failures: Sequence[tuple[str, BaseException]]):
        self.failures = list(failures)
        detail = "; ".join(f"{name}: {err!r}" for name, err in failures)
        super().__init__(f"all fallbacks failed: {detail}")


class FallbackChain(Generic[T]):
    """An ordered set of named, reviewed alternatives for one capability."""

    def __init__(
        self,
        options: Sequence[Option[T]],
        *,
        validate: Callable[[T], bool] | None = None,
        exceptions: tuple[type, ...] = (Exception,),
    ):
        if not options:
            raise ValueError("FallbackChain needs at least one option")
        self._options: list[Option[T]] = list(options)
        self._validate = validate
        self._exceptions = exceptions

    def run(self) -> tuple[T, str]:
        """Return ``(value, source_name)`` from the first option that works."""
        failures: list[tuple[str, BaseException]] = []
        for name, fn in self._options:
            try:
                result = fn()
            except self._exceptions as exc:  # type: ignore[misc]
                failures.append((name, exc))
                continue
            if self._validate is not None and not self._validate(result):
                failures.append((name, ValueError("failed validation")))
                continue
            return result, name
        raise AllFallbacksFailed(failures)


def fallback(
    *options: Option[T] | Callable[[], T],
    validate: Callable[[T], bool] | None = None,
    exceptions: tuple[type, ...] = (Exception,),
) -> tuple[T, str]:
    """Convenience wrapper: run a chain from inline callables.

    Accepts either ``(name, callable)`` pairs or bare callables (auto-named
    ``option-1``, ``option-2`` ...).

    >>> fallback(lambda: 1/0, lambda: "safe")
    ('safe', 'option-2')
    """
    normalized: list[Option[T]] = []
    for i, opt in enumerate(options, start=1):
        if isinstance(opt, tuple):
            normalized.append(opt)
        else:
            normalized.append((f"option-{i}", opt))
    return FallbackChain(normalized, validate=validate, exceptions=exceptions).run()
