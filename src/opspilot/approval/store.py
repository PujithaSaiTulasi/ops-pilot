"""File-backed human approval store for the local simulator."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from opspilot.approval.models import ApprovalRequest


class ApprovalStore:
    """Persist approvals in a local JSON file with safe defaults."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data/approvals.json")

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text())

    def _write(self, records: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(records, indent=2))

    def create(self, action: str, arguments: dict[str, Any], reason: str) -> ApprovalRequest:
        request = ApprovalRequest(
            approval_id=f"APR-{uuid4().hex[:10]}", action=action, arguments=arguments, reason=reason
        )
        records = self._read()
        records.append(request.model_dump(mode="json"))
        self._write(records)
        return request

    def get(self, approval_id: str) -> ApprovalRequest:
        for record in self._read():
            if record["approval_id"] == approval_id:
                return ApprovalRequest.model_validate(record)
        raise KeyError(f"unknown approval: {approval_id}")

    def decide(
        self, approval_id: str, approved: bool, decided_by: str = "local-user"
    ) -> ApprovalRequest:
        records = self._read()
        for record in records:
            if record["approval_id"] == approval_id:
                if record["status"] != "pending":
                    raise ValueError(f"approval is already {record['status']}")
                record["status"] = "approved" if approved else "rejected"
                record["decided_at"] = datetime.now(UTC).isoformat()
                record["decided_by"] = decided_by
                self._write(records)
                return ApprovalRequest.model_validate(record)
        raise KeyError(f"unknown approval: {approval_id}")
