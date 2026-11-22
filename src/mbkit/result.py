"""Railway-oriented result type: ``Result[T, E]`` as ``Ok`` or ``Err``.

A small, dependency-free alternative to raising exceptions for *expected*
failures. You return a value *or* an error, and the caller is forced by the
type checker to handle both. Chain transformations with :meth:`Result.map` and
:meth:`Result.and_then` so a failure short-circuits the rest of the pipeline
instead of blowing up.

This mirrors the "verified recovery, not silent failure" idea from the
biology-computing theory doc: an operation's outcome is explicit and carries a
reason, never a bare ``None``.

Example
-------
>>> def parse_port(raw: str) -> Result[int, str]:
...     if not raw.isdigit():
...         return Err(f"not a number: {raw!r}")
...     return Ok(int(raw))
>>> parse_port("8080").map(lambda p: p + 1).unwrap()
8081
>>> parse_port("oops").unwrap_or(5432)
5432
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Generic, NoReturn, TypeVar

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")
F = TypeVar("F")

__all__ = ["Result", "Ok", "Err", "UnwrapError"]


class UnwrapError(Exception):
    """Raised when :meth:`Result.unwrap` is called on an ``Err`` (or the mirror)."""


@dataclass(frozen=True)
class Ok(Generic[T]):
    """A successful result wrapping a value."""

    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        """Transform the contained value, leaving an ``Err`` untouched."""
        return Ok(fn(self.value))

    def map_err(self, fn: Callable[[E], F]) -> Result[T, F]:
        return self

    def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Chain another fallible step; the step runs only on ``Ok``."""
        return fn(self.value)

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: T) -> T:
        return self.value

    def unwrap_err(self) -> NoReturn:
        raise UnwrapError(f"called unwrap_err on an Ok: {self.value!r}")

    def __iter__(self) -> Iterator[T]:
        yield self.value


@dataclass(frozen=True)
class Err(Generic[E]):
    """A failed result wrapping an error value (often a string or exception)."""

    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        return self

    def map_err(self, fn: Callable[[E], F]) -> Result[T, F]:
        return Err(fn(self.error))

    def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return self

    def unwrap(self) -> NoReturn:
        raise UnwrapError(f"called unwrap on an Err: {self.error!r}")

    def unwrap_or(self, default: T) -> T:
        return default

    def unwrap_err(self) -> E:
        return self.error

    def __iter__(self) -> Iterator[object]:
        return iter(())


# A Result is either an Ok carrying T or an Err carrying E.
Result = Ok[T] | Err[E]
