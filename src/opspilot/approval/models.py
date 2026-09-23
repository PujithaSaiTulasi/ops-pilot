"""Approval record models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    """Human decision record for a side-effecting action."""

    approval_id: str
    action: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str
    status: Literal["pending", "approved", "rejected"] = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decided_at: datetime | None = None
    decided_by: str | None = None
