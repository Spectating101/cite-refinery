"""Application-side client. Connection configuration is operator-owned.

Use PortfolioSession for multi-step workflows; invoke is a stateless convenience.
Consumers receive native results and must inspect both transport and domain status.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StdioConnection:
    command: str
    args: tuple[str, ...] = ()
    env: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None

    def parameters(self):
        from mcp import StdioServerParameters
        return StdioServerParameters(command=self.command, args=list(self.args), env=self.env or None, cwd=self.cwd)


class PortfolioSession:
    """One MCP connection/process for a complete application workflow.

    Keep this context manager in one asyncio task. A session neither grants
    permission nor persists state after shutdown; those remain server concerns.
    """
    def __init__(self, connection: StdioConnection):
        self.connection = connection
        self._context = None
        self._client = None

    async def __aenter__(self):
        from mcp import Client
        if self._context is not None:
            raise RuntimeError("The session is already entered")
        self._context = Client(self.connection.parameters())
        try:
            self._client = await self._context.__aenter__()
        except BaseException:
            self._context = None
            raise
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        if self._context is None:
            raise RuntimeError("The session is not entered")
        try:
            return await self._context.__aexit__(exc_type, exc, traceback)
        finally:
            self._client = None
            self._context = None

    def _connected(self):
        if self._client is None:
            raise RuntimeError("Use the session inside 'async with'")
        return self._client

    async def inspect(self) -> dict[str, Any]:
        client = self._connected()
        tools, cursor, seen = [], None, set()
        for _ in range(100):
            page = await client.list_tools(cursor=cursor)
            tools.extend(tool.model_dump(mode="json", by_alias=True) for tool in page.tools)
            cursor = page.next_cursor
            if cursor is None:
                return {"protocol_version": client.protocol_version, "tools": tools}
            if cursor in seen:
                raise RuntimeError("Server repeated a pagination cursor")
            seen.add(cursor)
        raise RuntimeError("Tool catalog exceeded the configured page limit")

    async def invoke(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await self._connected().call_tool(tool, arguments)
        return {"is_error": result.is_error,
                "structured_content": result.structured_content,
                "content": [item.model_dump(mode="json", by_alias=True) for item in result.content]}


async def inspect_server(connection: StdioConnection) -> dict[str, Any]:
    async with PortfolioSession(connection) as session:
        return await session.inspect()


async def invoke(connection: StdioConnection, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """One-shot invocation. Use PortfolioSession when subsequent calls need state."""
    async with PortfolioSession(connection) as session:
        return await session.invoke(tool, arguments)
