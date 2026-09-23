"""Input, tool, and output guardrails for OpsPilot."""

from __future__ import annotations

import re
from typing import Any

from opspilot.agent.models import Diagnosis
from opspilot.agent.tool_registry import RegisteredTool


class GuardrailViolation(ValueError):
    """Raised when a request or tool call violates policy."""


_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?previous", re.IGNORECASE),
    re.compile(r"reveal\s+(the\s+)?system\s+prompt", re.IGNORECASE),
    re.compile(r"exfiltrat|send\s+secrets|steal\s+credentials", re.IGNORECASE),
    re.compile(r"execute\s+(a\s+)?shell|run\s+arbitrary\s+command", re.IGNORECASE),
)
ALLOWED_SERVICES = frozenset({"checkout-api", "payment-service", "inventory-service"})
MAX_TEXT_LENGTH = 4000


def validate_user_input(text: str) -> str:
    """Reject obvious injection and unbounded input before agent execution."""
    if not text.strip():
        raise GuardrailViolation("investigation request cannot be empty")
    if len(text) > MAX_TEXT_LENGTH:
        raise GuardrailViolation("investigation request exceeds the input limit")
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            raise GuardrailViolation(
                "input resembles a prompt-injection or data-exfiltration attempt"
            )
    return text.strip()


def validate_tool_call(tool: RegisteredTool, arguments: dict[str, Any]) -> None:
    """Apply server-side restrictions to model-selected tool arguments."""
    if len(arguments) > 12:
        raise GuardrailViolation("tool argument count exceeds the policy limit")
    for key, value in arguments.items():
        if isinstance(value, str):
            if len(value) > MAX_TEXT_LENGTH:
                raise GuardrailViolation(f"tool argument {key} exceeds the text limit")
            if any(token in value for token in ("../", "~/", "&&", ";", "|", "$(")):
                raise GuardrailViolation(f"tool argument {key} contains an unsafe token")
        if key == "service" and value not in ALLOWED_SERVICES:
            raise GuardrailViolation(f"unsupported service: {value}")
    if tool.name in {"rollback_deployment", "restart_service"} and not arguments.get("approval_id"):
        raise GuardrailViolation(f"{tool.name} requires an approval_id")


def validate_diagnosis(diagnosis: Diagnosis) -> Diagnosis:
    """Ensure final output is evidence-backed and policy-aware."""
    if not diagnosis.evidence:
        raise GuardrailViolation("diagnosis must cite at least one evidence item")
    if diagnosis.confidence > 0.8 and len(diagnosis.evidence) < 2:
        raise GuardrailViolation("high-confidence diagnosis requires at least two evidence items")
    action = diagnosis.recommended_action.lower()
    if any(word in action for word in ("rollback", "restart", "deploy", "delete", "notify")):
        diagnosis.requires_approval = True
    return diagnosis
