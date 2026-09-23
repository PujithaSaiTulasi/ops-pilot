"""Typed agent messages and investigation results."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """One model-requested tool call."""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    call_id: str = "mock-call"


class ModelDecision(BaseModel):
    """Model output normalized across live and mock implementations."""

    kind: Literal["tool_call", "final"]
    tool_call: ToolCall | None = None
    text: str | None = None


class Evidence(BaseModel):
    """Evidence returned by a tool during an investigation."""

    source: str
    detail: str
    data: Any = None


class Diagnosis(BaseModel):
    """Structured final output of an OpsPilot investigation."""

    incident_id: str
    severity: Literal["info", "warning", "critical"] = "warning"
    summary: str
    suspected_root_cause: str
    confidence: float = Field(ge=0, le=1)
    affected_services: list[str]
    evidence: list[Evidence]
    recommended_action: str
    requires_approval: bool
    unresolved_questions: list[str] = Field(default_factory=list)
    tool_calls: int = 0


class InvestigationEvent(BaseModel):
    """One observable step in an investigation trace."""

    kind: Literal["model", "tool", "final"]
    name: str
    payload: dict[str, Any] = Field(default_factory=dict)
