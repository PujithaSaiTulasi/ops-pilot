"""Shared helpers for the local MCP server processes."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TypeVar

from mcp.server.mcpserver import MCPServer

T = TypeVar("T")


def run_server(server: MCPServer) -> None:
    """Run an MCP server over stdio when invoked as a module."""
    asyncio.run(server.run_stdio_async())


def tool_names(server: MCPServer) -> Awaitable[list[str]]:
    """Return a server's discoverable tool names."""

    async def _names() -> list[str]:
        return [tool.name for tool in await server.list_tools()]

    return _names()
