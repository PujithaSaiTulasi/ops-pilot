"""Read-only MCP server for simulated deployment history."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from opspilot.mcp.deployment_backend import DeploymentBackend
from opspilot.mcp.server_utils import run_server


def create_server(backend: DeploymentBackend | None = None) -> MCPServer:
    backend = backend or DeploymentBackend()
    server = MCPServer("opspilot-deployments", description="Read-only deployment metadata tools")

    @server.tool(description="List recent simulated deployments.")
    def list_recent_deployments() -> list[dict[str, Any]]:
        return backend.deployments()

    @server.tool(description="Get one deployment and its changed files.")
    def get_deployment_details(deployment_id: str) -> dict[str, Any]:
        return backend.details(deployment_id)

    @server.tool(description="Get changed files for a deployment.")
    def get_changed_files(deployment_id: str) -> list[str]:
        return backend.changed_files(deployment_id)

    @server.tool(description="Get the active version for a simulated service.")
    def get_active_version(service: str) -> dict[str, str]:
        return {"service": service, "version": backend.active_version(service)}

    return server


server = create_server()

if __name__ == "__main__":
    run_server(server)
