"""Read-only MCP server for incident runbooks."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from opspilot.mcp.runbook_backend import RunbookBackend
from opspilot.mcp.server_utils import run_server


def create_server(backend: RunbookBackend | None = None) -> MCPServer:
    backend = backend or RunbookBackend()
    server = MCPServer("opspilot-runbooks", description="Read-only incident runbook tools")

    @server.tool(description="Search local incident runbooks and past operating guidance.")
    def search_runbooks(query: str) -> list[dict[str, object]]:
        return backend.search(query)

    @server.tool(description="Read one local incident runbook.")
    def get_runbook(runbook_id: str) -> dict[str, str]:
        return backend.get(runbook_id)

    @server.tool(description="Search past incident notes in local runbooks.")
    def search_past_incidents(query: str) -> list[dict[str, object]]:
        return backend.search(query)

    return server


server = create_server()

if __name__ == "__main__":
    run_server(server)
