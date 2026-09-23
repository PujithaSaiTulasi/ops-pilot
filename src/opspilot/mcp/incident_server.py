"""Incident record MCP server."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from opspilot.config import get_settings
from opspilot.mcp.incident_backend import IncidentBackend
from opspilot.mcp.server_utils import run_server


def create_server(backend: IncidentBackend | None = None) -> MCPServer:
    backend = backend or IncidentBackend()
    server = MCPServer("opspilot-incidents", description="Local incident record tools")

    @server.tool(description="Create a local incident record.")
    def create_incident(title: str, severity: str, summary: str) -> dict[str, Any]:
        return backend.create(title, severity, summary)

    @server.tool(description="Update a local incident status and optional comment.")
    def update_incident(
        incident_id: str, status: str, comment: str | None = None
    ) -> dict[str, Any]:
        return backend.update(incident_id, status, comment)

    @server.tool(description="Add a comment to a local incident.")
    def add_incident_comment(incident_id: str, comment: str) -> dict[str, Any]:
        return backend.update(incident_id, "open", comment)

    @server.tool(description="Get a local incident record.")
    def get_incident(incident_id: str) -> dict[str, Any]:
        return backend.get(incident_id)

    return server


server = create_server(IncidentBackend(get_settings().audit_log_path.with_name("incidents.json")))

if __name__ == "__main__":
    run_server(server)
