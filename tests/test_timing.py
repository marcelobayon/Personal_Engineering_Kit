import io
import logging

from mbkit import Timer, timed


def test_timer_measures_elapsed():
    with Timer("work") as t:
        sum(range(10000))
    assert t.elapsed >= 0
    assert t.elapsed_ms == t.elapsed * 1000.0
    assert t.end is not None


def test_timer_logs_on_exit():
    stream = io.StringIO()
    logger = logging.getLogger("mbkit.test.timer")
    logger.handlers.clear()
    logger.addHandler(logging.StreamHandler(stream))
    logger.setLevel(logging.INFO)
    logger.propagate = False

    with Timer("load", logger=logger):
        pass
    assert "load took" in stream.getvalue()


def test_timed_decorator_returns_value_and_logs():
    stream = io.StringIO()
    logger = logging.getLogger("mbkit.test.timed")
    logger.handlers.clear()
    logger.addHandler(logging.StreamHandler(stream))
    logger.setLevel(logging.INFO)
    logger.propagate = False

    @timed(logger, label="fetch")
    def fetch():
        return "ok"

    assert fetch() == "ok"
    assert "fetch took" in stream.getvalue()


def test_timed_still_times_on_exception():
    stream = io.StringIO()
    logger = logging.getLogger("mbkit.test.timed.exc")
    logger.handlers.clear()
    logger.addHandler(logging.StreamHandler(stream))
    logger.setLevel(logging.INFO)
    logger.propagate = False

    @timed(logger)
    def boom():
        raise RuntimeError("x")

    try:
        boom()
    except RuntimeError:
        pass
    assert "took" in stream.getvalue()
