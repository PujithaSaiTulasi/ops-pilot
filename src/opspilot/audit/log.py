"""Append-only audit logging with conservative redaction."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SENSITIVE_KEYS = {"api_key", "authorization", "token", "password", "secret"}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if key.lower() in SENSITIVE_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class AuditLogger:
    """Write one immutable JSON event per line."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data/audit.jsonl")

    def record(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "payload": redact(payload),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
        return record

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]
