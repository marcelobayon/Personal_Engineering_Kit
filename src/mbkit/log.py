"""Configurable, idempotent logger factory with optional JSON output.

The README that seeded this repo called out a "reusable singleton logger" that
takes "thread safety, configurability, and ease of integration" seriously. This
is that utility, kept small:

- :func:`get_logger` returns a ``logging.Logger`` configured once. Calling it
  again with the same name never stacks duplicate handlers (the classic cause
  of every line being printed two or three times).
- Configuration is guarded by a lock, so wiring up logging from multiple
  threads at startup is safe.
- Pass ``json=True`` for one-line structured logs that a log aggregator can
  parse, or leave it off for human-readable console output.

Example
-------
>>> log = get_logger("mbkit.demo", level="INFO")
>>> log.info("hello")                      # -> 2026-... INFO mbkit.demo: hello
>>> get_logger("mbkit.demo") is log        # same logger, no extra handlers
True
"""

from __future__ import annotations

import json as _json
import logging
import sys
import threading
from collections.abc import MutableMapping
from typing import Any

__all__ = ["get_logger", "JsonFormatter", "DEFAULT_FORMAT"]

DEFAULT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"

_LOCK = threading.Lock()
# Names we have already configured, so repeat calls are cheap and idempotent.
_CONFIGURED: set[str] = set()

LevelLike = int | str


class JsonFormatter(logging.Formatter):
    """Render each record as a single JSON object.

    Extra fields attached via ``logger.info("msg", extra={"request_id": ...})``
    are included automatically, which is handy for request-scoped tracing.
    """

    _RESERVED = frozenset(
        vars(logging.makeLogRecord({})).keys()
        | {"message", "asctime", "taskName"}
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Merge any user-supplied `extra=` keys.
        for key, value in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith("_"):
                payload[key] = value
        return _json.dumps(payload, default=str)


def _coerce_level(level: LevelLike) -> int:
    if isinstance(level, int):
        return level
    resolved = logging.getLevelName(str(level).upper())
    if isinstance(resolved, int):
        return resolved
    raise ValueError(f"unknown log level: {level!r}")


def get_logger(
    name: str = "mbkit",
    *,
    level: LevelLike = logging.INFO,
    json: bool = False,
    stream: Any = None,
    fmt: str = DEFAULT_FORMAT,
    propagate: bool = False,
) -> logging.Logger:
    """Return a logger configured exactly once for ``name``.

    Parameters
    ----------
    name:
        Logger name. Use a dotted path (``"myapp.worker"``) to inherit config.
    level:
        Minimum level, as an int (``logging.DEBUG``) or name (``"DEBUG"``).
    json:
        Emit structured JSON instead of the human-readable ``fmt``.
    stream:
        Output stream; defaults to ``sys.stderr``.
    fmt:
        ``logging``-style format string, used when ``json`` is ``False``.
    propagate:
        Whether to also bubble records to ancestor loggers. Off by default so a
        configured logger does not double-print through the root logger.
    """
    logger = logging.getLogger(name)
    resolved_level = _coerce_level(level)

    with _LOCK:
        if name not in _CONFIGURED:
            handler = logging.StreamHandler(stream or sys.stderr)
            handler.setFormatter(
                JsonFormatter() if json else logging.Formatter(fmt)
            )
            logger.addHandler(handler)
            _CONFIGURED.add(name)
        # Level/propagate are always refreshed so later calls can adjust them.
        logger.setLevel(resolved_level)
        logger.propagate = propagate

    return logger


def bind(logger: logging.Logger, **context: Any) -> logging.LoggerAdapter[logging.Logger]:
    """Attach fixed context (e.g. a request id) to every message from ``logger``.

    >>> base = get_logger("mbkit.req")
    >>> scoped = bind(base, request_id="abc123")
    >>> scoped.info("processing")   # json mode -> includes request_id=abc123
    """
    return _ContextAdapter(logger, dict(context))


class _ContextAdapter(logging.LoggerAdapter):  # type: ignore[type-arg]
    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[Any, MutableMapping[str, Any]]:
        merged = {**(self.extra or {}), **kwargs.get("extra", {})}
        new_kwargs = dict(kwargs)
        new_kwargs["extra"] = merged
        return msg, new_kwargs


__all__.append("bind")
