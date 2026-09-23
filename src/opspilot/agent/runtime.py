"""OpsPilot investigation loop."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from opspilot.agent.models import Diagnosis, Evidence, InvestigationEvent
from opspilot.agent.tool_registry import MCPToolRegistry
from opspilot.approval.store import ApprovalStore
from opspilot.audit.log import AuditLogger
from opspilot.config import Settings
from opspilot.guardrails.policy import validate_diagnosis, validate_tool_call, validate_user_input
from opspilot.llm.mock import MockModel
from opspilot.llm.responses import ResponsesModel
from opspilot.simulator.catalog import load_scenario
from opspilot.simulator.store import FaultStore


class OpsPilotAgent:
    """Run a bounded incident investigation using discovered MCP tools."""

    def __init__(self, settings: Settings | None = None, store: FaultStore | None = None) -> None:
        self.settings = settings or Settings()
        self.store = store or FaultStore(self.settings.redis_url)
        self.registry = MCPToolRegistry(self.store)
        self.approvals = ApprovalStore(self.settings.approval_store_path)
        self.audit = AuditLogger(self.settings.audit_log_path)

    async def investigate_async(
        self, incident_id: str, request: str | None = None
    ) -> tuple[Diagnosis, list[InvestigationEvent]]:
        scenario = load_scenario(incident_id, self.settings.scenario_dir)
        await self.registry.discover_async()
        events: list[InvestigationEvent] = []
        observations: list[dict[str, Any]] = []
        mock = MockModel(incident_id) if self.settings.mock_llm else None
        live = None
        if not self.settings.mock_llm:
            if not self.settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when MOCK_LLM=false")
            live = ResponsesModel(
                self.settings.openai_api_key.get_secret_value(), self.settings.openai_model
            )
        request_text = validate_user_input(request or f"Investigate incident {incident_id}.")
        self.audit.record(
            "investigation_started", {"incident_id": incident_id, "request": request_text}
        )
        input_items: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": request_text,
            }
        ]
        for _step in range(self.settings.max_investigation_steps):
            if mock is not None:
                decision = mock.next(observations)
                response = None
            else:
                assert live is not None
                decision, response = await live.next_async(
                    input_items, self.registry.openai_tools()
                )
            events.append(
                InvestigationEvent(kind="model", name=decision.kind, payload=decision.model_dump())
            )
            if decision.kind == "final":
                diagnosis = validate_diagnosis(
                    self._diagnosis(
                        scenario, observations, len([e for e in events if e.kind == "tool"])
                    )
                )
                self.audit.record("diagnosis_produced", diagnosis.model_dump(mode="json"))
                events.append(
                    InvestigationEvent(
                        kind="final", name="diagnosis", payload=diagnosis.model_dump(mode="json")
                    )
                )
                return diagnosis, events
            assert decision.tool_call is not None
            call = decision.tool_call
            metadata = self.registry.metadata(call.name)
            validate_tool_call(metadata, call.arguments)
            self.audit.record(
                "tool_requested",
                {
                    "tool": call.name,
                    "arguments": call.arguments,
                    "approval_required": metadata.approval_required,
                },
            )
            if metadata.approval_required:
                approval = self.approvals.create(
                    call.name,
                    call.arguments,
                    f"Agent requested {call.name} during {incident_id}",
                )
                result = {
                    "status": "approval_required",
                    "approval_id": approval.approval_id,
                    "tool": call.name,
                }
                self.audit.record("approval_requested", approval.model_dump(mode="json"))
            else:
                result = await self.registry.call_async(call.name, call.arguments)
                self.audit.record("tool_completed", {"tool": call.name, "result": result})
            observations.append({"tool": call.name, "arguments": call.arguments, "result": result})
            events.append(
                InvestigationEvent(
                    kind="tool",
                    name=call.name,
                    payload={"arguments": call.arguments, "result": result},
                )
            )
            if live is not None:
                if response is not None:
                    input_items.extend(
                        [
                            item.model_dump() if hasattr(item, "model_dump") else item
                            for item in response.output
                        ]
                    )
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result, default=str),
                    }
                )
        raise RuntimeError("investigation exceeded MAX_INVESTIGATION_STEPS")

    def investigate(
        self, incident_id: str, request: str | None = None
    ) -> tuple[Diagnosis, list[InvestigationEvent]]:
        return asyncio.run(self.investigate_async(incident_id, request))

    @staticmethod
    def _diagnosis(scenario: Any, observations: list[dict[str, Any]], tool_calls: int) -> Diagnosis:
        evidence = [
            Evidence(
                source=item["tool"],
                detail=f"{item['tool']} returned simulator evidence",
                data=item["result"],
            )
            for item in observations
        ]
        return Diagnosis(
            incident_id=scenario.scenario_id,
            severity="critical"
            if scenario.scenario_id in {"payment_timeout", "database_connection_exhaustion"}
            else "warning",
            summary=scenario.title,
            suspected_root_cause=scenario.root_cause,
            confidence=0.91 if tool_calls >= 5 else 0.65,
            affected_services=scenario.affected_services,
            evidence=evidence,
            recommended_action=scenario.safe_remediation,
            requires_approval=True,
            unresolved_questions=[],
            tool_calls=tool_calls,
        )
