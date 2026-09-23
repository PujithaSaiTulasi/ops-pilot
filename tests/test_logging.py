"""Tests for JSON structured logging."""

from __future__ import annotations

import io
import json
import logging

from opspilot.logging import JsonFormatter, configure_logging, get_logger


def _capture_logger(name: str, level: int = logging.INFO) -> tuple[logging.Logger, io.StringIO]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger(name)
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False
    return logger, stream


def test_json_formatter_emits_one_valid_json_object() -> None:
    logger, stream = _capture_logger("opspilot.test.json")

    logger.info("incident detected")

    payload = json.loads(stream.getvalue().strip())
    assert payload["message"] == "incident detected"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "opspilot.test.json"
    assert "timestamp" in payload


def test_json_formatter_includes_structured_extra_fields() -> None:
    logger, stream = _capture_logger("opspilot.test.extra")

    logger.info(
        "tool call",
        extra={"incident_id": "inc-42", "tool": "get_recent_deployments", "duration_ms": 12},
    )

    payload = json.loads(stream.getvalue().strip())
    assert payload["incident_id"] == "inc-42"
    assert payload["tool"] == "get_recent_deployments"
    assert payload["duration_ms"] == 12


def test_json_formatter_includes_exception_details() -> None:
    logger, stream = _capture_logger("opspilot.test.error")

    try:
        msg = "boom"
        raise ValueError(msg)
    except ValueError:
        logger.exception("investigation failed")

    payload = json.loads(stream.getvalue().strip())
    assert payload["level"] == "ERROR"
    assert "ValueError: boom" in payload["exception"]


def test_configure_logging_is_idempotent() -> None:
    configure_logging(level="INFO", fmt="json")
    configure_logging(level="DEBUG", fmt="json")

    root = logging.getLogger()
    handlers = [
        handler for handler in root.handlers if getattr(handler, "_opspilot_handler", False)
    ]

    assert len(handlers) == 1
    assert root.level == logging.DEBUG
    assert isinstance(handlers[0].formatter, JsonFormatter)


def test_console_format_is_human_readable() -> None:
    configure_logging(level="INFO", fmt="console")

    handlers = [
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, "_opspilot_handler", False)
    ]

    assert handlers, "console handler was not installed"
    assert not isinstance(handlers[0].formatter, JsonFormatter)


def test_get_logger_returns_namespaced_logger() -> None:
    logger = get_logger("opspilot.agent")

    assert logger.name == "opspilot.agent"
