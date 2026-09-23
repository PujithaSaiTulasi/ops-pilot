"""MCP server discovery and tool behavior tests."""

from __future__ import annotations

import asyncio

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from opspilot.approval.store import ApprovalStore
from opspilot.mcp.deployment_server import create_server as create_deployment_server
from opspilot.mcp.incident_backend import IncidentBackend
from opspilot.mcp.incident_server import create_server as create_incident_server
from opspilot.mcp.observability_server import create_server as create_observability_server
from opspilot.mcp.remediation_server import create_server as create_remediation_server
from opspilot.mcp.runbook_server import create_server as create_runbook_server
from opspilot.simulator.store import FaultStore


def _tool_names(server: object) -> list[str]:
    async def collect() -> list[str]:
        tools = await server.list_tools()  # type: ignore[attr-defined]
        return [tool.name for tool in tools]

    return asyncio.run(collect())


def test_observability_server_exposes_read_only_tools() -> None:
    names = _tool_names(create_observability_server(FaultStore()))
    assert names == [
        "get_service_metrics",
        "search_logs",
        "get_recent_alerts",
        "get_trace_summary",
        "compare_service_baseline",
    ]


def test_deployment_server_returns_changed_files() -> None:
    server = create_deployment_server()

    async def call() -> object:
        return await server.call_tool("get_changed_files", {"deployment_id": "deploy-001"})

    result = asyncio.run(call())
    assert "services/checkout/latency.py" in str(result)


def test_runbook_server_is_discoverable() -> None:
    names = _tool_names(create_runbook_server())
    assert "search_runbooks" in names
    assert "get_runbook" in names


def test_remediation_requires_approval_id() -> None:
    server = create_remediation_server(FaultStore())

    async def call() -> object:
        return await server.call_tool(
            "restart_service", {"service": "checkout-api", "approval_id": ""}
        )

    with pytest.raises(ToolError, match="approval_id is required"):
        asyncio.run(call())


def test_remediation_rejects_approval_for_a_different_deployment(tmp_path) -> None:
    approvals = ApprovalStore(tmp_path / "approvals.json")
    request = approvals.create("rollback_deployment", {"deployment_id": "deploy-001"}, "test")
    approvals.decide(request.approval_id, True)
    server = create_remediation_server(FaultStore(), approvals)

    async def call() -> object:
        return await server.call_tool(
            "rollback_deployment",
            {"deployment_id": "deploy-000", "approval_id": request.approval_id},
        )

    with pytest.raises(ToolError, match="approval arguments do not match"):
        asyncio.run(call())


def test_incident_server_persists_records(tmp_path) -> None:
    server = create_incident_server(IncidentBackend(tmp_path / "incidents.json"))

    async def call() -> object:
        return await server.call_tool(
            "create_incident",
            {"title": "Checkout slow", "severity": "warning", "summary": "latency elevated"},
        )

    result = asyncio.run(call())
    assert result.is_error is False  # type: ignore[attr-defined]
