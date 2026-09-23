"""Deterministic model used for tests, demos, and CI."""

from __future__ import annotations

from typing import Any

from opspilot.agent.models import ModelDecision, ToolCall


class MockModel:
    """Produce a repeatable evidence-gathering sequence for each scenario."""

    def __init__(self, incident_id: str) -> None:
        self.incident_id = incident_id
        self.index = 0

    def next(self, history: list[dict[str, Any]]) -> ModelDecision:
        plan: list[ToolCall] = [
            ToolCall(name="get_recent_alerts"),
            ToolCall(name="get_service_metrics", arguments={"service": "checkout-api"}),
            ToolCall(name="compare_service_baseline", arguments={"service": "checkout-api"}),
            ToolCall(name="search_logs", arguments={"query": self.incident_id}),
            ToolCall(name="list_recent_deployments"),
            ToolCall(name="get_changed_files", arguments={"deployment_id": "deploy-001"}),
            ToolCall(name="search_runbooks", arguments={"query": "checkout latency deployment"}),
            ToolCall(name="create_rollback_plan", arguments={"deployment_id": "deploy-001"}),
        ]
        if self.index < len(plan):
            call = plan[self.index]
            self.index += 1
            return ModelDecision(kind="tool_call", tool_call=call)
        return ModelDecision(
            kind="final",
            text=(
                "Checkout latency increased after deployment deploy-001. "
                "The evidence supports rolling back checkout-api to version 1.0.0."
            ),
        )
