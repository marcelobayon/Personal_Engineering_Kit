"""Runnable tour of mbkit. Run with: python examples/quickstart.py"""

from mbkit import (
    CircuitBreaker,
    Err,
    Ok,
    Result,
    Timer,
    fallback,
    get_logger,
    load_config,
    retry,
)

log = get_logger("quickstart", level="INFO")


# 1. Config: defaults < file < environment (env_prefix strips "DEMO_")
cfg = load_config(defaults={"port": 8080, "debug": False}, env_prefix="DEMO_")
log.info("config loaded: port=%s debug=%s", cfg.get_int("port"), cfg.get_bool("debug"))


# 2. Result: expected failures as values, not exceptions
def parse_port(raw: str) -> Result[int, str]:
    return Ok(int(raw)) if raw.isdigit() else Err(f"bad port: {raw!r}")


log.info("parsed: %s", parse_port("9000").map(lambda p: p + 1).unwrap_or(-1))
log.info("parsed bad: %s", parse_port("xx").unwrap_or(5432))


# 3. Retry: bounded backoff on transient errors
attempts = {"n": 0}


@retry(attempts=3, base_delay=0.0, exceptions=(ConnectionError,))
def flaky_call() -> str:
    attempts["n"] += 1
    if attempts["n"] < 3:
        raise ConnectionError("temporary blip")
    return "connected"


log.info("retry result: %s after %d tries", flaky_call(), attempts["n"])


# 4. Fallback: approved alternatives in order
def primary() -> str:
    raise ConnectionError("primary down")


value, source = fallback(("primary", primary), ("secondary", lambda: "cached-value"))
log.info("fallback served %r from %s", value, source)


# 5. Circuit breaker: stop hammering a failing dependency
breaker = CircuitBreaker(failure_threshold=2, reset_timeout=30)
for _ in range(2):
    try:
        breaker.call(lambda: (_ for _ in ()).throw(ConnectionError()))
    except ConnectionError:
        pass
log.info("breaker state after 2 failures: %s", breaker.state)


# 6. Timing
with Timer("crunch", logger=log):
    sum(range(1_000_000))
