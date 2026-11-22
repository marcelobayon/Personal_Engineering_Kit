"""Resilience patterns: retry, circuit breaker, and approved-fallback chains.

These are the "survive partial failure" utilities, translated from the
biological-computing theory doc into bounded, verifiable code. Nothing here
heals a system on its own — each pattern is an *explicit, policy-bounded*
behaviour you opt into.
"""

from .circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState
from .fallback import AllFallbacksFailed, FallbackChain, fallback
from .retry import RetryError, retry

__all__ = [
    "retry",
    "RetryError",
    "CircuitBreaker",
    "CircuitOpenError",
    "CircuitState",
    "FallbackChain",
    "AllFallbacksFailed",
    "fallback",
]
