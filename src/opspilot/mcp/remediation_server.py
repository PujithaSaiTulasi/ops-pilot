"""Approval-gated remediation MCP server for the simulator."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from opspilot.approval.store import ApprovalStore
from opspilot.config import get_settings
from opspilot.mcp.deployment_backend import DeploymentBackend
from opspilot.mcp.server_utils import run_server
from opspilot.simulator.store import FaultStore


def create_server(
    store: FaultStore | None = None, approvals: ApprovalStore | None = None
) -> MCPServer:
    store = store or FaultStore()
    approvals = approvals or ApprovalStore(get_settings().approval_store_path)
    deployment_backend = DeploymentBackend(store)
    server = MCPServer("opspilot-remediation", description="Side-effecting simulator tools")

    @server.tool(description="Create a rollback plan without executing it.")
    def create_rollback_plan(deployment_id: str) -> dict[str, Any]:
        deployment = deployment_backend.details(deployment_id)
        return {
            "deployment_id": deployment_id,
            "service": deployment["service"],
            "from_version": deployment["version"],
            "to_version": deployment["previous_version"],
            "requires_approval": True,
        }

    @server.tool(description="Rollback a simulated deployment after external approval.")
    def rollback_deployment(deployment_id: str, approval_id: str) -> dict[str, Any]:
        if not approval_id.strip():
            raise ToolError("approval_id is required for rollback")
        try:
            approvals.validate_for_action(
                approval_id,
                "rollback_deployment",
                {"deployment_id": deployment_id},
                consume=True,
            )
            deployment = deployment_backend.details(deployment_id)
        except (KeyError, ValueError) as exc:
            raise ToolError(str(exc)) from exc
        if deployment["service"] == "checkout-api":
            store.clear("bad_deployment")
        return {"status": "rolled_back", "deployment_id": deployment_id, "approval_id": approval_id}

    @server.tool(description="Restart a simulated service after external approval.")
    def restart_service(service: str, approval_id: str) -> dict[str, Any]:
        if not approval_id.strip():
            raise ToolError("approval_id is required for restart")
        try:
            approvals.validate_for_action(
                approval_id,
                "restart_service",
                {"service": service},
                consume=True,
            )
        except (KeyError, ValueError) as exc:
            raise ToolError(str(exc)) from exc
        if service == "checkout-api":
            store.clear("memory_pressure")
        return {"status": "restarted", "service": service, "approval_id": approval_id}

    @server.tool(description="Verify that a simulated incident has recovered.")
    def verify_recovery(service: str) -> dict[str, Any]:
        active = [fault.scenario for fault in store.active()]
        return {"service": service, "recovered": not active, "active_faults": active}

    return server


server = create_server(
    FaultStore(get_settings().redis_url, get_settings().simulator_state_path),
    ApprovalStore(get_settings().approval_store_path),
)

if __name__ == "__main__":
    run_server(server)
