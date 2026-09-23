"""Tests for the bounded agent loop and mock mode."""

from __future__ import annotations

from opspilot.agent.runtime import OpsPilotAgent
from opspilot.config import Settings
from opspilot.simulator.store import FaultStore


def test_mock_agent_discovers_tools_and_produces_diagnosis() -> None:
    store = FaultStore()
    store.activate("bad_deployment", {"service": "checkout-api", "latency_ms": 750})
    settings = Settings(_env_file=None, environment="test", mock_llm=True)

    diagnosis, events = OpsPilotAgent(settings, store).investigate("bad_deployment")

    assert diagnosis.incident_id == "bad_deployment"
    assert "checkout version" in diagnosis.suspected_root_cause
    assert diagnosis.requires_approval is True
    assert diagnosis.tool_calls >= 5
    assert any(event.name == "get_service_metrics" for event in events)


def test_agent_is_bounded_by_max_steps() -> None:
    store = FaultStore()
    settings = Settings(
        _env_file=None, environment="test", mock_llm=True, max_investigation_steps=1
    )

    try:
        OpsPilotAgent(settings, store).investigate("bad_deployment")
    except RuntimeError as exc:
        assert "MAX_INVESTIGATION_STEPS" in str(exc)
    else:
        raise AssertionError("investigation should stop at the configured step limit")
