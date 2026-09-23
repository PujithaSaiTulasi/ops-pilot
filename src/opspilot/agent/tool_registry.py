"""MCP tool discovery and dispatch for the agent runtime.

The registry supports two transports:

* ``in_process`` keeps unit tests fast and deterministic.
* ``stdio`` starts the declared MCP servers as separate child processes and
  talks to them through the official MCP client session.

The agent only sees discovered schemas and never receives arbitrary shell
access. This makes the transport boundary visible without making local demos
depend on a cloud environment.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult

from opspilot.approval.store import ApprovalStore
from opspilot.config import Settings
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
    """Discover and call MCP tools over an in-process or stdio transport."""

    def __init__(
        self,
        store: FaultStore | None = None,
        settings: Settings | None = None,
        approvals: ApprovalStore | None = None,
    ) -> None:
        self.settings = settings or Settings()
        shared_store = store or FaultStore(
            self.settings.redis_url, self.settings.simulator_state_path
        )
        approval_store = approvals or ApprovalStore(self.settings.approval_store_path)
        self.servers: dict[str, MCPServer] = {
            "observability": create_observability_server(ObservabilityBackend(shared_store)),
            "deployments": create_deployment_server(DeploymentBackend(shared_store)),
            "runbooks": create_runbook_server(),
            "remediation": create_remediation_server(shared_store, approval_store),
            "incidents": create_incident_server(),
        }
        self._tool_server: dict[str, MCPServer] = {}
        self._sessions: dict[str, ClientSession] = {}
        self._metadata: dict[str, RegisteredTool] = {}
        self._stack: AsyncExitStack | None = None

    @staticmethod
    def _tools(result: Any) -> list[Any]:
        return list(getattr(result, "tools", result))

    @staticmethod
    def _is_read_only(server_name: str, tool_name: str) -> bool:
        return server_name in {"observability", "deployments", "runbooks"} or tool_name in {
            "create_rollback_plan",
            "verify_recovery",
            "get_incident",
        }

    async def _start_stdio_servers(self) -> None:
        if self._sessions:
            return
        config = json.loads(Path(self.settings.mcp_servers_path).read_text())
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        child_env = os.environ.copy()
        child_env.update(
            {
                "REDIS_URL": self.settings.redis_url,
                "SIMULATOR_STATE_PATH": str(self.settings.simulator_state_path),
                "APPROVAL_STORE_PATH": str(self.settings.approval_store_path),
            }
        )
        for server_name, spec in config["servers"].items():
            command = str(spec["command"])
            if command == "python":
                command = sys.executable
            parameters = StdioServerParameters(
                command=command,
                args=[str(value) for value in spec.get("args", [])],
                env=child_env,
            )
            read_stream, write_stream = await self._stack.enter_async_context(
                stdio_client(parameters)
            )
            session = await self._stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()
            self._sessions[server_name] = session

    async def discover_async(self) -> list[RegisteredTool]:
        self._tool_server.clear()
        self._metadata.clear()
        if self.settings.mcp_transport == "stdio":
            await self._start_stdio_servers()
            for server_name, session in self._sessions.items():
                for tool in self._tools(await session.list_tools()):
                    self._register(server_name, tool)
        else:
            for server_name, server in self.servers.items():
                for tool in self._tools(await server.list_tools()):
                    self._register(server_name, tool)
        return list(self._metadata.values())

    def _register(self, server_name: str, tool: Any) -> None:
        read_only = self._is_read_only(server_name, tool.name)
        self._metadata[tool.name] = RegisteredTool(
            name=tool.name,
            server_name=server_name,
            description=tool.description or tool.name,
            input_schema=tool.input_schema,
            read_only=read_only,
            approval_required=not read_only,
        )
        if self.settings.mcp_transport == "in_process":
            self._tool_server[tool.name] = self.servers[server_name]

    def discover(self) -> list[RegisteredTool]:
        return asyncio.run(self.discover_async())

    async def call_async(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self._metadata:
            await self.discover_async()
        result: Any = None
        try:
            if self.settings.mcp_transport == "stdio":
                session = self._sessions[self._metadata[name].server_name]
                result = await session.call_tool(name, arguments)
            else:
                server = self._tool_server.get(name)
                if server is None:
                    raise KeyError(f"unknown MCP tool: {name}")
                result = await server.call_tool(name, arguments)
        except KeyError:
            raise
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
        if self.settings.mcp_transport == "stdio":

            async def call_and_close() -> Any:
                try:
                    return await self.call_async(name, arguments)
                finally:
                    await self.aclose()

            return asyncio.run(call_and_close())
        return asyncio.run(self.call_async(name, arguments))

    async def openai_tools_async(self) -> list[dict[str, Any]]:
        if not self._metadata:
            await self.discover_async()
        return self.openai_tools()

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

    async def metadata_async(self, name: str) -> RegisteredTool:
        if not self._metadata:
            await self.discover_async()
        return self._metadata[name]

    async def aclose(self) -> None:
        """Stop child MCP processes and release their stdio streams."""
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self._sessions.clear()
            self._tool_server.clear()
            self._metadata.clear()
