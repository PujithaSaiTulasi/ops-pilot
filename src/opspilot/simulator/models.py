"""Typed models used by the local incident simulator."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class FaultState(BaseModel):
    """An active deterministic fault in the simulated environment."""

    scenario: str
    activated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = Field(default_factory=dict)


class ScenarioDefinition(BaseModel):
    """Ground-truth metadata for one simulator scenario."""

    scenario_id: str
    title: str
    description: str
    affected_services: list[str]
    symptoms: list[str]
    root_cause: str
    safe_remediation: str
    verification: list[str]
    fault_details: dict[str, Any] = Field(default_factory=dict)


class InjectRequest(BaseModel):
    """API payload for activating a scenario."""

    scenario: str
