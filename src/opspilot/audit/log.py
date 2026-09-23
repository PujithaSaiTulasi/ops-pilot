"""Append-only audit logging with conservative redaction."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

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
    """Write redacted, hash-chained JSON events for local auditability.

    This is intentionally still a file-backed portfolio implementation. The
    hash chain makes accidental edits and out-of-order records detectable while
    keeping the interface ready for a database or append-only log backend.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data/audit.jsonl")

    def record(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        previous = self._last_hash()
        record = {
            "event_id": f"EVT-{uuid4().hex[:12]}",
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "payload": redact(payload),
            "prev_hash": previous,
        }
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
        record["record_hash"] = hashlib.sha256(canonical.encode()).hexdigest()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
        return record

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]

    def _last_hash(self) -> str | None:
        records = self.read()
        return records[-1].get("record_hash") if records else None

    def verify_chain(self) -> bool:
        """Return whether every event links to the previous event correctly."""
        previous: str | None = None
        for record in self.read():
            if record.get("prev_hash") != previous:
                return False
            supplied_hash = record.get("record_hash")
            unsigned = {key: value for key, value in record.items() if key != "record_hash"}
            canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), default=str)
            if supplied_hash != hashlib.sha256(canonical.encode()).hexdigest():
                return False
            previous = supplied_hash
        return True
