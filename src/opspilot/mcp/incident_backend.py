"""Local incident record backend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4


class IncidentBackend:
    """Persist simple incident records in a local JSON file."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data/incidents.json")

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text())

    def _write(self, incidents: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(incidents, indent=2))

    def create(self, title: str, severity: str, summary: str) -> dict[str, Any]:
        incident = {
            "incident_id": f"INC-{uuid4().hex[:8]}",
            "title": title,
            "severity": severity,
            "summary": summary,
            "status": "open",
        }
        records = self._read()
        records.append(incident)
        self._write(records)
        return incident

    def update(self, incident_id: str, status: str, comment: str | None = None) -> dict[str, Any]:
        records = self._read()
        for incident in records:
            if incident["incident_id"] == incident_id:
                incident["status"] = status
                if comment:
                    incident.setdefault("comments", []).append(comment)
                self._write(records)
                return incident
        raise KeyError(f"unknown incident: {incident_id}")

    def get(self, incident_id: str) -> dict[str, Any]:
        for incident in self._read():
            if incident["incident_id"] == incident_id:
                return incident
        raise KeyError(f"unknown incident: {incident_id}")
