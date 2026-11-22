"""mbkit — Marcelo Bayon's personal engineering kit.

A small, dependency-free toolkit of the patterns you reach for in every
project, so you stop re-writing them:

- ``log``        configurable, idempotent logging (human or JSON)
- ``config``     layered config: defaults < file < environment
- ``resilience`` retry, circuit breaker, approved-fallback chains
- ``result``     railway-oriented ``Result[T, E]`` for expected failures
- ``timing``     ``Timer`` and ``@timed`` for measuring what you run

Everything is standard-library only and importable from the top level::

    from mbkit import get_logger, load_config, retry, CircuitBreaker, Result, Ok, Err

Design philosophy and the biology-to-software thinking behind the resilience
module live in ``docs/BIOLOGICAL_COMPUTING_THEORY.md``.
"""

from __future__ import annotations

from .config import Config, ConfigError, load_config
from .log import bind, get_logger
from .resilience import (
    AllFallbacksFailed,
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    FallbackChain,
    RetryError,
    fallback,
    retry,
)
from .result import Err, Ok, Result, UnwrapError
from .timing import Timer, timed

__version__ = "0.2.0"

__all__ = [
    "__version__",
    # logging
    "get_logger",
    "bind",
    # config
    "load_config",
    "Config",
    "ConfigError",
    # resilience
    "retry",
    "RetryError",
    "CircuitBreaker",
    "CircuitOpenError",
    "CircuitState",
    "FallbackChain",
    "AllFallbacksFailed",
    "fallback",
    # result
    "Result",
    "Ok",
    "Err",
    "UnwrapError",
    # timing
    "Timer",
    "timed",
]
