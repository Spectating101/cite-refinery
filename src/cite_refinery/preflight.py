from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .cite import CiteAgentCLIAdapter
from .cite_research import CiteAgentResearchCLIAdapter
from .solution import CanonicalRefineryCLIAdapter, ReviewedMarketCLIAdapter


def _check(name: str, *, available: bool, required: bool, detail: str, recovery: str | None = None) -> dict[str, Any]:
    status = "ready" if available else ("missing" if required else "degraded")
    row = {
        "name": name,
        "status": status,
        "required": required,
        "available": bool(available),
        "detail": detail,
    }
    if not available and recovery:
        row["recovery"] = recovery
    return row


def build_preflight(
    workspace: str | Path = ".cite-refinery",
    *,
    cite: CiteAgentCLIAdapter | None = None,
    cite_research: CiteAgentResearchCLIAdapter | None = None,
    canonical_refinery: CanonicalRefineryCLIAdapter | None = None,
    reviewed_market: ReviewedMarketCLIAdapter | None = None,
) -> dict[str, Any]:
    """Inspect local orchestration prerequisites without doing network research."""

    cite = cite or CiteAgentCLIAdapter()
    cite_research = cite_research or CiteAgentResearchCLIAdapter()
    canonical_refinery = canonical_refinery or CanonicalRefineryCLIAdapter()
    reviewed_market = reviewed_market or ReviewedMarketCLIAdapter()

    workspace_path = Path(workspace).expanduser().resolve()
    workspace_error = None
    try:
        workspace_path.mkdir(parents=True, exist_ok=True)
        workspace_available = workspace_path.is_dir() and os.access(workspace_path, os.R_OK | os.W_OK)
    except OSError as exc:
        workspace_available = False
        workspace_error = str(exc)

    market_db = getattr(reviewed_market, "db_path", None)
    market_db_exists = bool(market_db) and Path(str(market_db)).is_file()
    market_command_available = bool(getattr(reviewed_market, "command", [])) and reviewed_market.available() if market_db_exists else False

    checks = [
        _check(
            "workspace",
            available=workspace_available,
            required=True,
            detail=str(workspace_path) if not workspace_error else f"{workspace_path}: {workspace_error}",
            recovery="Choose a writable --workspace path.",
        ),
        _check(
            "cite_grounding",
            available=cite.available(),
            required=True,
            detail=" ".join(cite.command),
            recovery="Install Cite-Agent or set CITE_AGENT_COMMAND to its executable.",
        ),
        _check(
            "cite_deep_research",
            available=cite_research.available(),
            required=True,
            detail=" ".join(cite_research.command),
            recovery="Install current Cite-Agent with cite-agent-research or set CITE_AGENT_RESEARCH_COMMAND.",
        ),
        _check(
            "refinery_canonical",
            available=canonical_refinery.available(),
            required=True,
            detail=" ".join(canonical_refinery.command),
            recovery="Install current Refinery or set REFINERY_COMMAND to its executable.",
        ),
        _check(
            "refinery_reviewed_market_database",
            available=market_db_exists,
            required=False,
            detail=(
                f"{market_db} ({getattr(reviewed_market, 'db_source', 'unknown')})"
                if market_db
                else "no reviewed-market database configured or restored"
            ),
            recovery=(
                "Run `refinery-market-snapshot restore --input <reviewed-market-search-v1.json>` "
                "or set REFINERY_MARKET_DB."
            ),
        ),
        _check(
            "refinery_reviewed_market_search",
            available=market_command_available,
            required=False,
            detail=" ".join(getattr(reviewed_market, "command", [])) or "refinery-market-search",
            recovery="Install current Refinery so refinery-market-search is available.",
        ),
    ]

    required_failures = [row["name"] for row in checks if row["required"] and not row["available"]]
    broad_supply_failures = [
        row["name"]
        for row in checks
        if row["name"] in {"refinery_reviewed_market_database", "refinery_reviewed_market_search"}
        and not row["available"]
    ]
    return {
        "schema_version": 1,
        "kind": "cite-refinery-preflight-v1",
        "workspace": str(workspace_path),
        "core_ready": not required_failures,
        "full_broad_supply_ready": not required_failures and not broad_supply_failures,
        "feedback_protocol_ready": True,
        "required_failures": required_failures,
        "broad_supply_degradations": broad_supply_failures,
        "checks": checks,
        "boundary": (
            "Preflight checks local commands, paths, and restored search state only. It does not make network calls, "
            "validate API credentials, prove source availability, or establish empirical/literature quality. A green "
            "preflight means the orchestration surfaces are locally present, not that a research project will succeed."
        ),
    }
