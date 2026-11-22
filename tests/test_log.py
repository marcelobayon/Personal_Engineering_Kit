import io
import json
import logging

from mbkit import get_logger
from mbkit.log import bind


def test_idempotent_no_duplicate_handlers():
    name = "mbkit.test.idem"
    a = get_logger(name)
    before = len(a.handlers)
    b = get_logger(name)
    assert a is b
    assert len(b.handlers) == before  # calling twice must not stack handlers


def test_human_format_writes_message():
    stream = io.StringIO()
    log = get_logger("mbkit.test.human", level="INFO", stream=stream)
    log.info("hello world")
    assert "hello world" in stream.getvalue()


def test_level_is_respected():
    stream = io.StringIO()
    log = get_logger("mbkit.test.level", level="WARNING", stream=stream)
    log.info("should not appear")
    log.warning("should appear")
    out = stream.getvalue()
    assert "should appear" in out
    assert "should not appear" not in out


def test_json_output_includes_extra():
    stream = io.StringIO()
    log = get_logger("mbkit.test.json", json=True, stream=stream)
    log.info("structured", extra={"request_id": "abc123"})
    record = json.loads(stream.getvalue().strip())
    assert record["message"] == "structured"
    assert record["level"] == "INFO"
    assert record["request_id"] == "abc123"


def test_bind_attaches_context():
    stream = io.StringIO()
    base = get_logger("mbkit.test.bind", json=True, stream=stream)
    scoped = bind(base, request_id="xyz")
    scoped.info("processing")
    record = json.loads(stream.getvalue().strip())
    assert record["request_id"] == "xyz"


def test_can_relevel_existing_logger():
    stream = io.StringIO()
    get_logger("mbkit.test.relevel", level="ERROR", stream=stream)
    log = get_logger("mbkit.test.relevel", level="DEBUG")
    assert log.level == logging.DEBUG
