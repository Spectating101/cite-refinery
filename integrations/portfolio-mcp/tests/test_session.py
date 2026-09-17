"""Real stateful MCP fixture. Not evidence of a portfolio engine's functionality."""
import asyncio
import os
import sys
import pytest
pytest.importorskip('mcp')
from portfolio_mcp.client import PortfolioSession, StdioConnection


def test_one_connection_preserves_server_state_between_calls(tmp_path):
    server = tmp_path/'stateful_server.py'
    server.write_text('''from mcp.server import MCPServer
server = MCPServer("stateful transport fixture")
count = 0
@server.tool()
def next_count() -> dict:
    global count
    count += 1
    return {"count": count}
server.run()
''')
    connection = StdioConnection(sys.executable, (str(server),), dict(os.environ))
    async def exercise():
        async with asyncio.timeout(45):
            async with PortfolioSession(connection) as session:
                assert len((await session.inspect())['tools']) == 1
                first = await session.invoke('next_count', {})
                second = await session.invoke('next_count', {})
                assert not first['is_error'] and not second['is_error']
                assert first['structured_content']['count'] == 1
                assert second['structured_content']['count'] == 2
            with pytest.raises(RuntimeError):
                await session.inspect()
            async with PortfolioSession(connection) as fresh:
                assert (await fresh.invoke('next_count', {}))['structured_content']['count'] == 1
    asyncio.run(exercise())
