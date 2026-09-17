"""Application-side client. Connection configuration is operator-owned.

Consumers receive the owning server's full result and must inspect domain status.
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


async def inspect_server(connection: StdioConnection) -> dict[str, Any]:
    from mcp import Client
    async with Client(connection.parameters()) as client:
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


async def invoke(connection: StdioConnection, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    from mcp import Client
    async with Client(connection.parameters()) as client:
        result = await client.call_tool(tool, arguments)
        return {"is_error": result.is_error,
                "structured_content": result.structured_content,
                "content": [item.model_dump(mode="json", by_alias=True) for item in result.content]}
