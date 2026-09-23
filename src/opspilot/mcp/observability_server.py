"""Read-only MCP server for simulated logs, metrics, traces, and alerts."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from opspilot.mcp.observability_backend import ObservabilityBackend
from opspilot.mcp.server_utils import run_server


def create_server(backend: ObservabilityBackend | None = None) -> MCPServer:
    backend = backend or ObservabilityBackend()
    server = MCPServer(
        "opspilot-observability", description="Read-only simulator observability tools"
    )

    @server.tool(description="Get recent metrics for a simulated service.")
    def get_service_metrics(service: str, window_minutes: int = 5) -> dict[str, Any]:
        return backend.metrics(service, window_minutes)

    @server.tool(description="Search simulated structured logs.")
    def search_logs(
        query: str = "", service: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        return backend.logs(query, service, limit)

    @server.tool(description="Get currently firing simulated alerts.")
    def get_recent_alerts() -> list[dict[str, Any]]:
        return backend.alerts()

    @server.tool(description="Get a trace summary for a simulated request.")
    def get_trace_summary(
        trace_id: str | None = None, service: str = "checkout-api"
    ) -> dict[str, Any]:
        return backend.trace_summary(trace_id, service)

    @server.tool(description="Compare current service metrics with the known baseline.")
    def compare_service_baseline(service: str) -> dict[str, Any]:
        return backend.baseline(service)

    return server


server = create_server()

if __name__ == "__main__":
    run_server(server)
