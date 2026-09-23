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
        service = {
            "bad_deployment": "checkout-api",
            "payment_timeout": "payment-service",
            "inventory_errors": "inventory-service",
            "database_connection_exhaustion": "checkout-api",
            "memory_pressure": "checkout-api",
            "dependency_failure": "checkout-api",
        }.get(self.incident_id, "checkout-api")
        plan: list[ToolCall] = [
            ToolCall(name="get_recent_alerts"),
            ToolCall(name="get_service_metrics", arguments={"service": service}),
            ToolCall(name="compare_service_baseline", arguments={"service": service}),
            ToolCall(name="search_logs", arguments={"query": self.incident_id, "service": service}),
            ToolCall(name="search_runbooks", arguments={"query": service}),
        ]
        if self.incident_id == "bad_deployment":
            plan.extend(
                [
                    ToolCall(name="list_recent_deployments"),
                    ToolCall(name="get_changed_files", arguments={"deployment_id": "deploy-001"}),
                    ToolCall(
                        name="create_rollback_plan", arguments={"deployment_id": "deploy-001"}
                    ),
                ]
            )
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
