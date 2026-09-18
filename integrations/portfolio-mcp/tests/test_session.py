"""Real stateful MCP fixtures, not evidence of a portfolio engine's functionality."""
import asyncio
import json
import os
import sys

import pytest

pytest.importorskip("mcp")
from portfolio_mcp.client import PortfolioSession, StdioConnection


@pytest.mark.parametrize("structured", [True, False])
def test_one_connection_preserves_server_state_between_calls(tmp_path, structured):
    server = tmp_path / "stateful_server.py"
    # The original bare `-> dict` fixture did not supply structured_content.
    # Declare structured output explicitly and also test text-only preservation;
    # never make the client silently fabricate a structured server response.
    return_annotation = "CounterValue" if structured else "str"
    return_expression = "CounterValue(count=count)" if structured else 'json.dumps({"count": count})'
    decorator = "@server.tool()" if structured else "@server.tool(structured_output=False)"
    server.write_text(
        "import json\n"
        "from pydantic import BaseModel\n"
        "from mcp.server import MCPServer\n"
        'server = MCPServer("stateful transport fixture")\n'
        "class CounterValue(BaseModel):\n"
        "    count: int\n"
        "count = 0\n"
        f"{decorator}\n"
        f"def next_count() -> {return_annotation}:\n"
        "    global count\n"
        "    count += 1\n"
        f"    return {return_expression}\n"
        "server.run()\n",
        encoding="utf-8",
    )
    connection = StdioConnection(sys.executable, (str(server),), dict(os.environ))

    def count_value(response):
        assert not response["is_error"], response
        if structured:
            assert response["structured_content"] is not None, response
            return response["structured_content"]["count"]
        assert response["structured_content"] is None, response
        blocks = response["content"]
        assert len(blocks) == 1 and blocks[0]["type"] == "text", response
        return json.loads(blocks[0]["text"])["count"]

    async def exercise():
        async with asyncio.timeout(45):
            async with PortfolioSession(connection) as session:
                tools = (await session.inspect())["tools"]
                assert len(tools) == 1
                assert (tools[0].get("outputSchema") is not None) == structured
                first = await session.invoke("next_count", {})
                second = await session.invoke("next_count", {})
                assert count_value(first) == 1
                assert count_value(second) == 2
            with pytest.raises(RuntimeError):
                await session.inspect()
            async with PortfolioSession(connection) as fresh:
                assert count_value(await fresh.invoke("next_count", {})) == 1

    asyncio.run(exercise())
