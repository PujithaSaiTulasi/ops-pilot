"""Small local alert store used by the simulator and MCP tools."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class AlertStore:
    """Keep received alert payloads in process memory for local demos."""

    def __init__(self) -> None:
        self._alerts: list[dict[str, Any]] = []

    def record(self, payload: dict[str, Any]) -> dict[str, Any]:
        stored = dict(payload)
        stored.setdefault("received_at", datetime.now(UTC).isoformat())
        self._alerts.append(stored)
        return stored

    def recent(self) -> list[dict[str, Any]]:
        return list(reversed(self._alerts[-50:]))

    def clear(self) -> None:
        self._alerts.clear()
