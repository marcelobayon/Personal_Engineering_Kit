import pytest

from mbkit import Err, Ok, Result
from mbkit.result import UnwrapError


def parse_port(raw: str) -> Result[int, str]:
    if not raw.isdigit():
        return Err(f"not a number: {raw!r}")
    return Ok(int(raw))


def test_ok_basics():
    r = parse_port("8080")
    assert r.is_ok() and not r.is_err()
    assert r.unwrap() == 8080
    assert r.unwrap_or(1) == 8080


def test_err_basics():
    r = parse_port("nope")
    assert r.is_err() and not r.is_ok()
    assert r.unwrap_or(5432) == 5432
    assert r.unwrap_err().startswith("not a number")


def test_map_only_runs_on_ok():
    assert parse_port("10").map(lambda p: p + 1).unwrap() == 11
    # map on Err is a no-op and keeps the error
    assert parse_port("x").map(lambda p: p + 1).unwrap_err()


def test_and_then_short_circuits():
    def ensure_high(p: int) -> Result[int, str]:
        return Ok(p) if p >= 1024 else Err("privileged port")

    assert parse_port("8080").and_then(ensure_high).unwrap() == 8080
    assert parse_port("80").and_then(ensure_high).unwrap_err() == "privileged port"
    assert parse_port("x").and_then(ensure_high).is_err()


def test_map_err():
    assert parse_port("x").map_err(str.upper).unwrap_err().startswith("NOT A NUMBER")


def test_unwrap_raises_on_err():
    with pytest.raises(UnwrapError):
        parse_port("x").unwrap()
    with pytest.raises(UnwrapError):
        parse_port("8080").unwrap_err()
