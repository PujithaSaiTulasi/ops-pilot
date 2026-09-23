"""End-to-end approval-gated remediation tests."""

from __future__ import annotations

from pathlib import Path

from opspilot.agent.workflow import RemediationWorkflow
from opspilot.approval.store import ApprovalStore
from opspilot.config import Settings
from opspilot.simulator.store import FaultStore


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        mock_llm=True,
        approval_store_path=tmp_path / "approvals.json",
        audit_log_path=tmp_path / "audit.jsonl",
    )


def test_workflow_pauses_then_resolves_after_approval(tmp_path: Path) -> None:
    store = FaultStore()
    store.activate("bad_deployment", {"service": "checkout-api", "latency_ms": 1})
    workflow = RemediationWorkflow(_settings(tmp_path), store)

    prepared = workflow.prepare("bad_deployment")
    assert prepared.status == "pending_approval"
    assert prepared.approval_id
    assert store.get("bad_deployment") is not None

    ApprovalStore(_settings(tmp_path).approval_store_path).decide(prepared.approval_id, True)
    completed = workflow.resume(prepared.approval_id)

    assert completed.status == "resolved"
    assert completed.verification == {
        "service": "checkout-api",
        "recovered": True,
        "active_faults": [],
    }
    assert store.get("bad_deployment") is None


def test_workflow_does_not_execute_rejected_action(tmp_path: Path) -> None:
    store = FaultStore()
    store.activate("bad_deployment", {"service": "checkout-api", "latency_ms": 1})
    workflow = RemediationWorkflow(_settings(tmp_path), store)

    prepared = workflow.prepare("bad_deployment")
    assert prepared.approval_id
    ApprovalStore(_settings(tmp_path).approval_store_path).decide(prepared.approval_id, False)

    rejected = workflow.resume(prepared.approval_id)
    assert rejected.status == "approval_rejected"
    assert store.get("bad_deployment") is not None
