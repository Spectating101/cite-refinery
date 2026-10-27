"""Local read-only MCP surface for the Cite-Refinery headless change inbox.

STDIO transport only. The MCP server does not fetch, execute vendor tools, or
write to the semantic graph. Run under a trusted local account; do not expose
the process or its private database to an untrusted network.
"""
from __future__ import annotations

import os
from pathlib import Path

from .headless_intelligence import status
from .development_steering import project_brief as read_project_brief, load_registry


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

    @app.tool()
    def development_brief(project_id: str, limit: int = 20) -> dict:
        """Retrieve candidate development steering changes and next checks."""
        return read_project_brief(db, project_id, limit=limit)

    @app.tool()
    def registered_projects() -> dict:
        """List projects explicitly opted into local monitoring, without checkout paths."""
        raw = os.environ.get("CITE_REFINERY_DEVELOPMENT_REGISTRY")
        if not raw:
            return {"status": "not_configured", "projects": []}
        try:
            projects = load_registry(Path(raw))
        except (OSError, ValueError):
            return {"status": "invalid_registry", "projects": []}
        return {"status": "configured", "projects": [
            {"id": p["id"], "repository": p["repository"], "state": p["state"],
             "goals": p["goals"], "current_priorities": p["current_priorities"]}
            for p in projects
        ], "authority": "local_read_only"}

    return app


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
