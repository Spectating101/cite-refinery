"""Local read-only MCP surface for the Cite-Refinery headless change inbox.

STDIO transport only. The MCP server does not fetch, execute vendor tools, or
write to the semantic graph. Run under a trusted local account; do not expose
the process or its private database to an untrusted network.
"""
from __future__ import annotations

import os
from pathlib import Path

from .headless_intelligence import status


def create_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install optional MCP support: pip install -e '.[headless]'") from exc

    app = FastMCP("cite-refinery-headless")
    db = Path(os.environ.get("CITE_REFINERY_HEADLESS_DB", ".cite-refinery/private/headless.sqlite"))

    @app.tool()
    def feed_status() -> dict:
        """List locally configured source checkpoints and candidate-only counts."""
        return {"feeds": status(db)["feeds"], "authority": "read_only"}

    @app.tool()
    def recent_changes(limit: int = 25) -> dict:
        """Return recent content-digest changes without raw private source payloads."""
        snapshot = status(db, event_limit=limit)
        return {"events": snapshot["events"], "authority": "read_only"}

    return app


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
