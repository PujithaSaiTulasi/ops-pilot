"""MCP tool discovery and dispatch for the agent runtime."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult

from opspilot.mcp.deployment_backend import DeploymentBackend
from opspilot.mcp.deployment_server import create_server as create_deployment_server
from opspilot.mcp.incident_server import create_server as create_incident_server
from opspilot.mcp.observability_backend import ObservabilityBackend
from opspilot.mcp.observability_server import create_server as create_observability_server
from opspilot.mcp.remediation_server import create_server as create_remediation_server
from opspilot.mcp.runbook_server import create_server as create_runbook_server
from opspilot.simulator.store import FaultStore


@dataclass(frozen=True)
class RegisteredTool:
    """Agent-facing metadata for one MCP tool."""

    name: str
    server_name: str
    description: str
    input_schema: dict[str, Any]
    read_only: bool
    approval_required: bool


class MCPToolRegistry:
    """Discover and call the local MCP server tools."""

    def __init__(self, store: FaultStore | None = None) -> None:
        shared_store = store or FaultStore()
        self.servers: dict[str, MCPServer] = {
            "observability": create_observability_server(ObservabilityBackend(shared_store)),
            "deployments": create_deployment_server(DeploymentBackend(shared_store)),
            "runbooks": create_runbook_server(),
            "remediation": create_remediation_server(shared_store),
            "incidents": create_incident_server(),
        }
        self._tool_server: dict[str, MCPServer] = {}
        self._metadata: dict[str, RegisteredTool] = {}

    async def discover_async(self) -> list[RegisteredTool]:
        self._tool_server.clear()
        self._metadata.clear()
        for server_name, server in self.servers.items():
            for tool in await server.list_tools():
                read_only = server_name in {"observability", "deployments", "runbooks"}
                registered = RegisteredTool(
                    name=tool.name,
                    server_name=server_name,
                    description=tool.description or tool.name,
                    input_schema=tool.input_schema,
                    read_only=read_only,
                    approval_required=not read_only,
                )
                self._tool_server[tool.name] = server
                self._metadata[tool.name] = registered
        return list(self._metadata.values())

    def discover(self) -> list[RegisteredTool]:
        return asyncio.run(self.discover_async())

    async def call_async(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self._tool_server:
            await self.discover_async()
        server = self._tool_server.get(name)
        if server is None:
            raise KeyError(f"unknown MCP tool: {name}")
        result = await server.call_tool(name, arguments)
        if not isinstance(result, CallToolResult):
            raise RuntimeError(f"MCP tool {name} requested additional input")
        if result.is_error:
            raise RuntimeError(f"MCP tool {name} failed: {result.content}")
        if result.structured_content and "result" in result.structured_content:
            return result.structured_content["result"]
        values = [getattr(item, "text", str(item)) for item in result.content]
        if len(values) == 1:
            try:
                return json.loads(values[0])
            except (TypeError, ValueError):
                return values[0]
        return values

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        return asyncio.run(self.call_async(name, arguments))

    def openai_tools(self) -> list[dict[str, Any]]:
        if not self._metadata:
            self.discover()
        return [
            {
                "type": "function",
                "name": item.name,
                "description": item.description,
                "parameters": item.input_schema,
            }
            for item in self._metadata.values()
        ]

    def metadata(self, name: str) -> RegisteredTool:
        if not self._metadata:
            self.discover()
        return self._metadata[name]
