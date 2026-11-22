import pytest

from mbkit import CircuitBreaker, FallbackChain, fallback, retry
from mbkit.resilience import AllFallbacksFailed, CircuitOpenError, RetryError


# -- retry -----------------------------------------------------------------
def test_retry_succeeds_after_transient_failures():
    calls = {"n": 0}

    @retry(attempts=3, base_delay=0, jitter=False, exceptions=(ValueError,))
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3


def test_retry_gives_up_and_wraps():
    @retry(attempts=2, base_delay=0, jitter=False, exceptions=(ValueError,))
    def always_fails():
        raise ValueError("nope")

    with pytest.raises(RetryError) as exc:
        always_fails()
    assert exc.value.attempts == 2
    assert isinstance(exc.value.last, ValueError)


def test_retry_does_not_catch_unlisted_exceptions():
    @retry(attempts=3, base_delay=0, exceptions=(ValueError,))
    def wrong_error():
        raise KeyError("not retried")

    with pytest.raises(KeyError):
        wrong_error()


def test_retry_calls_on_retry_hook():
    seen = []
    state = {"n": 0}

    @retry(attempts=3, base_delay=0, jitter=False, on_retry=lambda n, e: seen.append(n))
    def fail_twice():
        state["n"] += 1
        if state["n"] < 3:
            raise RuntimeError("x")
        return "done"

    assert fail_twice() == "done"
    assert seen == [1, 2]


# -- circuit breaker -------------------------------------------------------
def test_breaker_opens_after_threshold():
    clock = {"t": 0.0}
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=10, clock=lambda: clock["t"])

    def boom():
        raise ConnectionError("down")

    for _ in range(2):
        with pytest.raises(ConnectionError):
            cb.call(boom)
    assert cb.state == "open"
    with pytest.raises(CircuitOpenError):
        cb.call(lambda: "blocked")


def test_breaker_half_opens_then_closes_on_success():
    clock = {"t": 0.0}
    cb = CircuitBreaker(failure_threshold=1, reset_timeout=5, clock=lambda: clock["t"])

    with pytest.raises(ConnectionError):
        cb.call(lambda: (_ for _ in ()).throw(ConnectionError()))
    assert cb.state == "open"

    clock["t"] = 6.0  # past the reset window
    assert cb.state == "half_open"
    assert cb.call(lambda: "recovered") == "recovered"
    assert cb.state == "closed"


def test_breaker_ignores_unlisted_exceptions():
    cb = CircuitBreaker(failure_threshold=1, exceptions=(ConnectionError,))
    with pytest.raises(ValueError):
        cb.call(lambda: (_ for _ in ()).throw(ValueError()))
    assert cb.state == "closed"  # a validation error is not an outage


# -- fallback --------------------------------------------------------------
def test_fallback_chain_uses_first_working_option():
    def primary():
        raise ConnectionError("down")

    def secondary():
        return "from-secondary"

    value, source = FallbackChain(
        [("primary", primary), ("secondary", secondary)]
    ).run()
    assert value == "from-secondary"
    assert source == "secondary"


def test_fallback_validate_rejects_bad_result():
    value, source = fallback(
        lambda: "",            # empty -> fails validation
        lambda: "good",
        validate=lambda s: bool(s.strip()),
    )
    assert value == "good"
    assert source == "option-2"


def test_fallback_all_fail():
    with pytest.raises(AllFallbacksFailed) as exc:
        fallback(lambda: 1 / 0, lambda: [][0])
    assert len(exc.value.failures) == 2
