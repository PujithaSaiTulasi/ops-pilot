"""LangGraph-powered, bounded incident investigation runtime."""

from __future__ import annotations

import asyncio
import json
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from opspilot.agent.models import Diagnosis, Evidence, InvestigationEvent, ModelDecision
from opspilot.agent.tool_registry import MCPToolRegistry
from opspilot.approval.store import ApprovalStore
from opspilot.audit.log import AuditLogger
from opspilot.config import Settings
from opspilot.guardrails.policy import validate_diagnosis, validate_tool_call, validate_user_input
from opspilot.llm.mock import MockModel
from opspilot.llm.responses import ResponsesModel
from opspilot.simulator.catalog import load_scenario
from opspilot.simulator.store import FaultStore


class InvestigationState(TypedDict, total=False):
    """State carried between the explicit LangGraph nodes."""

    incident_id: str
    request: str
    observations: list[dict[str, Any]]
    events: list[InvestigationEvent]
    input_items: list[dict[str, Any]]
    decision: ModelDecision
    response: Any
    steps: int
    diagnosis: Diagnosis


class OpsPilotAgent:
    """Run a bounded evidence-gathering graph using discovered MCP tools."""

    def __init__(self, settings: Settings | None = None, store: FaultStore | None = None) -> None:
        self.settings = settings or Settings()
        self.store = store or FaultStore(
            self.settings.redis_url, self.settings.simulator_state_path
        )
        self.approvals = ApprovalStore(self.settings.approval_store_path)
        self.audit = AuditLogger(self.settings.audit_log_path)
        self.registry = MCPToolRegistry(self.store, self.settings, self.approvals)

    async def investigate_async(
        self, incident_id: str, request: str | None = None
    ) -> tuple[Diagnosis, list[InvestigationEvent]]:
        scenario = load_scenario(incident_id, self.settings.scenario_dir)
        request_text = validate_user_input(request or f"Investigate incident {incident_id}.")
        self.audit.record(
            "investigation_started", {"incident_id": incident_id, "request": request_text}
        )
        mock = MockModel(incident_id) if self.settings.mock_llm else None
        live = None
        if not self.settings.mock_llm:
            if not self.settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when MOCK_LLM=false")
            live = ResponsesModel(
                self.settings.openai_api_key.get_secret_value(), self.settings.openai_model
            )

        async def model_node(state: InvestigationState) -> dict[str, Any]:
            steps = state.get("steps", 0) + 1
            if steps > self.settings.max_investigation_steps:
                raise RuntimeError("investigation exceeded MAX_INVESTIGATION_STEPS")
            if mock is not None:
                decision = mock.next(state.get("observations", []))
                response = None
            else:
                assert live is not None
                decision, response = await live.next_async(
                    state["input_items"], await self.registry.openai_tools_async()
                )
            event = InvestigationEvent(
                kind="model", name=decision.kind, payload=decision.model_dump()
            )
            return {
                "decision": decision,
                "response": response,
                "steps": steps,
                "events": [*state["events"], event],
            }

        async def tool_node(state: InvestigationState) -> dict[str, Any]:
            decision = state["decision"]
            if decision.tool_call is None:
                raise RuntimeError("tool node received a decision without a tool call")
            call = decision.tool_call
            metadata = await self.registry.metadata_async(call.name)
            validate_tool_call(metadata, call.arguments)
            self.audit.record(
                "tool_requested",
                {
                    "tool": call.name,
                    "server": metadata.server_name,
                    "arguments": call.arguments,
                    "approval_required": metadata.approval_required,
                },
            )
            if metadata.approval_required:
                approval = self.approvals.create(
                    call.name,
                    call.arguments,
                    f"Agent requested {call.name} during {incident_id}",
                    ttl_seconds=self.settings.approval_timeout_seconds,
                    context={"incident_id": incident_id},
                )
                result: Any = {
                    "status": "approval_required",
                    "approval_id": approval.approval_id,
                    "tool": call.name,
                }
                self.audit.record("approval_requested", approval.model_dump(mode="json"))
            else:
                result = await asyncio.wait_for(
                    self.registry.call_async(call.name, call.arguments),
                    timeout=self.settings.tool_timeout_seconds,
                )
                self.audit.record("tool_completed", {"tool": call.name, "result": result})
            observation = {"tool": call.name, "arguments": call.arguments, "result": result}
            event = InvestigationEvent(
                kind="tool", name=call.name, payload={"arguments": call.arguments, "result": result}
            )
            input_items = list(state["input_items"])
            response = state.get("response")
            if live is not None and response is not None:
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
            return {
                "observations": [*state["observations"], observation],
                "events": [*state["events"], event],
                "input_items": input_items,
            }

        def route_after_model(state: InvestigationState) -> str:
            return "finalize" if state["decision"].kind == "final" else "tool"

        def finalize_node(state: InvestigationState) -> dict[str, Any]:
            diagnosis = validate_diagnosis(
                self._diagnosis(incident_id, scenario, state["observations"])
            )
            self.audit.record("diagnosis_produced", diagnosis.model_dump(mode="json"))
            final_event = InvestigationEvent(
                kind="final", name="diagnosis", payload=diagnosis.model_dump(mode="json")
            )
            return {"diagnosis": diagnosis, "events": [*state["events"], final_event]}

        graph = StateGraph(InvestigationState)
        graph.add_node("model", model_node)
        graph.add_node("tool", tool_node)
        graph.add_node("finalize", finalize_node)
        graph.add_edge(START, "model")
        graph.add_conditional_edges(
            "model", route_after_model, {"tool": "tool", "finalize": "finalize"}
        )
        graph.add_edge("tool", "model")
        graph.add_edge("finalize", END)
        compiled = graph.compile()
        initial: InvestigationState = {
            "incident_id": incident_id,
            "request": request_text,
            "observations": [],
            "events": [],
            "input_items": [{"role": "user", "content": request_text}],
            "steps": 0,
        }
        try:
            # Start MCP sessions in the caller task. AnyIO's stdio transport
            # owns cancel scopes, so entering and closing them must happen in
            # the same task even though LangGraph runs nodes as tasks.
            await self.registry.discover_async()
            result = await compiled.ainvoke(initial)
            return result["diagnosis"], result["events"]
        finally:
            await self.registry.aclose()

    def investigate(
        self, incident_id: str, request: str | None = None
    ) -> tuple[Diagnosis, list[InvestigationEvent]]:
        return asyncio.run(self.investigate_async(incident_id, request))

    @staticmethod
    def _diagnosis(
        incident_id: str, scenario: Any, observations: list[dict[str, Any]]
    ) -> Diagnosis:
        """Build a guarded diagnosis from collected evidence, not fixture root cause."""
        evidence = [
            Evidence(
                source=item["tool"],
                detail=f"{item['tool']} returned evidence for the incident",
                data=item["result"],
            )
            for item in observations
        ]
        results = [item["result"] for item in observations]
        metrics = [value for value in results if isinstance(value, dict) and "error_rate" in value]
        deployments = [
            value
            for value in results
            if isinstance(value, list)
            and any(isinstance(item, dict) and "deployment_id" in item for item in value)
        ]
        deployment = next(
            (
                item
                for collection in deployments
                for item in collection
                if item.get("status") == "active"
            ),
            None,
        )
        current_metrics = next(iter(metrics), {})
        affected = sorted(
            {
                str(value.get("service"))
                for value in results
                if isinstance(value, dict)
                and value.get("service")
                in {
                    "checkout-api",
                    "payment-service",
                    "inventory-service",
                }
            }
        ) or list(scenario.affected_services)

        if deployment:
            version = deployment.get("version", "unknown")
            service = deployment.get("service", affected[0])
            service_label = str(service).removesuffix("-api")
            root_cause = f"{service_label} version {version} introduced a latency regression"
            action = (
                f"rollback {service} to version {deployment.get('previous_version', 'previous')}"
            )
        elif current_metrics.get("database_pool_usage") == 1.0:
            root_cause = "checkout database connection pool exhausted"
            action = "restore database connection capacity"
        elif current_metrics.get("memory_usage", 0) >= 0.9:
            root_cause = "checkout-api memory pressure"
            action = "restart checkout-api after approval"
        elif current_metrics.get("error_rate", 0) >= 1.0:
            service = current_metrics.get("service", affected[0])
            root_cause = f"{service} dependency is returning errors or timing out"
            action = f"restore {service} responses"
        else:
            root_cause = "downstream dependency unavailable"
            action = "restore downstream dependency"
        return Diagnosis(
            incident_id=incident_id,
            severity="critical" if current_metrics.get("error_rate", 0) >= 1.0 else "warning",
            summary=f"Evidence-backed investigation for {incident_id.replace('_', ' ')}",
            suspected_root_cause=root_cause,
            confidence=min(0.95, 0.55 + (0.06 * len(evidence))),
            affected_services=affected,
            evidence=evidence,
            recommended_action=action,
            requires_approval=True,
            unresolved_questions=[],
            tool_calls=len(observations),
        )
