"""JSON structured logging for OpsPilot.

Every log line is a single JSON object so logs are greppable and machine
parseable. Extra structured fields passed to log calls (``incident_id``,
``trace_id``, ...) are emitted verbatim.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

#: LogRecord attributes that are part of the logging protocol, not user data.
_RESERVED_FIELDS: frozenset[str] = frozenset(
    logging.LogRecord(
        name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
    ).__dict__
) | {"message", "asctime"}

_CONSOLE_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


class JsonFormatter(logging.Formatter):
    """Render log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in _RESERVED_FIELDS:
                continue
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


class _OpspilotHandler(logging.StreamHandler):
    """Marker handler so reconfiguration replaces ours, never someone else's."""

    _opspilot_handler = True


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    """Install (or reconfigure) the OpsPilot root log handler.

    Safe to call multiple times: the handler is replaced, never duplicated.
    """
    root = logging.getLogger()
    root.setLevel(level)

    for handler in list(root.handlers):
        if getattr(handler, "_opspilot_handler", False):
            root.removeHandler(handler)

    handler = _OpspilotHandler(sys.stdout)
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(_CONSOLE_FORMAT))
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger (``opspilot.*`` by convention)."""
    return logging.getLogger(name)
