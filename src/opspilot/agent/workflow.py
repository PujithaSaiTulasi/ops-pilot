"""Approval-gated remediation workflow."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from opspilot.agent.runtime import OpsPilotAgent
from opspilot.approval.store import ApprovalStore
from opspilot.audit.log import AuditLogger
from opspilot.config import Settings
from opspilot.simulator.store import FaultStore


class RemediationResult(BaseModel):
    """State returned by preparation or completion of remediation."""

    incident_id: str
    status: str
    diagnosis: dict[str, Any]
    approval_id: str | None = None
    action_result: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)


class RemediationWorkflow:
    """Coordinate investigation, approval, remediation, and verification."""

    def __init__(self, settings: Settings | None = None, store: FaultStore | None = None) -> None:
        self.settings = settings or Settings()
        self.store = store or FaultStore(self.settings.redis_url)
        self.agent = OpsPilotAgent(self.settings, self.store)
        self.approvals = ApprovalStore(self.settings.approval_store_path)
        self.audit = AuditLogger(self.settings.audit_log_path)

    def prepare(self, incident_id: str) -> RemediationResult:
        diagnosis, _events = self.agent.investigate(incident_id)
        plan = self.agent.registry.call("create_rollback_plan", {"deployment_id": "deploy-001"})
        approval = self.approvals.create(
            "rollback_deployment",
            {"deployment_id": "deploy-001", "incident_id": incident_id},
            f"Rollback plan for {incident_id}: {diagnosis.suspected_root_cause}",
        )
        self.audit.record(
            "remediation_prepared", {"approval": approval.model_dump(mode="json"), "plan": plan}
        )
        return RemediationResult(
            incident_id=incident_id,
            status="pending_approval",
            diagnosis=diagnosis.model_dump(mode="json"),
            approval_id=approval.approval_id,
        )

    def resume(self, approval_id: str) -> RemediationResult:
        approval = self.approvals.get(approval_id)
        incident_id = str(approval.arguments.get("incident_id", "bad_deployment"))
        diagnosis = {"incident_id": incident_id, "recommended_action": approval.action}
        if approval.status != "approved":
            return RemediationResult(
                incident_id=incident_id,
                status=f"approval_{approval.status}",
                diagnosis=diagnosis,
                approval_id=approval_id,
            )
        action_result = self.agent.registry.call(
            "rollback_deployment",
            {
                "deployment_id": approval.arguments.get("deployment_id", "deploy-001"),
                "approval_id": approval_id,
            },
        )
        verification = self.agent.registry.call("verify_recovery", {"service": "checkout-api"})
        status = "resolved" if verification.get("recovered") else "verification_failed"
        self.audit.record(
            "remediation_completed",
            {
                "approval_id": approval_id,
                "action_result": action_result,
                "verification": verification,
            },
        )
        return RemediationResult(
            incident_id=incident_id,
            status=status,
            diagnosis=diagnosis,
            approval_id=approval_id,
            action_result=action_result,
            verification=verification,
        )
