"""File-backed human approval store for the local simulator."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
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

    def create(
        self,
        action: str,
        arguments: dict[str, Any],
        reason: str,
        *,
        ttl_seconds: int = 300,
        context: dict[str, Any] | None = None,
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            approval_id=f"APR-{uuid4().hex[:10]}",
            action=action,
            arguments=arguments,
            reason=reason,
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
            context=context or {},
        )
        records = self._read()
        records.append(request.model_dump(mode="json"))
        self._write(records)
        return request

    def get(self, approval_id: str) -> ApprovalRequest:
        records = self._read()
        for record in records:
            if record["approval_id"] == approval_id:
                request = ApprovalRequest.model_validate(record)
                if (
                    request.status == "pending"
                    and request.expires_at is not None
                    and request.expires_at <= datetime.now(UTC)
                ):
                    record["status"] = "expired"
                    self._write(records)
                    request = ApprovalRequest.model_validate(record)
                return request
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

    @staticmethod
    def _canonical_arguments(arguments: dict[str, Any]) -> str:
        return json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str)

    @classmethod
    def arguments_hash(cls, arguments: dict[str, Any]) -> str:
        return hashlib.sha256(cls._canonical_arguments(arguments).encode()).hexdigest()

    def validate_for_action(
        self,
        approval_id: str,
        action: str,
        arguments: dict[str, Any],
        *,
        consume: bool = False,
    ) -> ApprovalRequest:
        """Validate an approval against the exact mutating tool invocation."""
        request = self.get(approval_id)
        if request.status != "approved":
            raise ValueError(f"approval is {request.status}, not approved")
        if request.action != action:
            raise ValueError("approval action does not match requested action")
        if self.arguments_hash(request.arguments) != self.arguments_hash(arguments):
            raise ValueError("approval arguments do not match requested action")
        if consume:
            records = self._read()
            for record in records:
                if record["approval_id"] == approval_id:
                    if record.get("status") != "approved":
                        raise ValueError(f"approval is already {record.get('status')}")
                    record["status"] = "consumed"
                    record["consumed_at"] = datetime.now(UTC).isoformat()
                    self._write(records)
                    return ApprovalRequest.model_validate(record)
        return request
