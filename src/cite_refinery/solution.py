from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Protocol


_DEFAULT_REVIEWED_MARKET_DB = "~/.local/share/refinery/reviewed-market-search.db"


@dataclass(slots=True)
class RefinerySearchResult:
    engine: str
    status: str
    raw: str
    structured: Any = None


class RefinerySearchAdapter(Protocol):
    def search(self, query: str, limit: int = 20) -> RefinerySearchResult: ...


class UnavailableRefineryAdapter:
    def search(self, query: str, limit: int = 20) -> RefinerySearchResult:
        return RefinerySearchResult(
            engine="unavailable",
            status="not_run",
            raw="Refinery search is not configured or installed; no external solution search ran.",
        )


def _command_available(command: list[str]) -> bool:
    if not command:
        return False
    first = command[0]
    if os.path.sep in first:
        return os.path.exists(first)
    return shutil.which(first) is not None


def _run_json_command(argv: list[str], *, timeout: int, engine: str) -> RefinerySearchResult:
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        shell=False,
    )
    raw = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return RefinerySearchResult(
            engine=engine,
            status="error",
            raw=stderr or raw or f"Refinery exited with code {proc.returncode}",
        )
    structured: Any = None
    if raw:
        try:
            structured = json.loads(raw)
        except json.JSONDecodeError:
            pass
    return RefinerySearchResult(
        engine=engine,
        status="completed",
        raw=raw or "Refinery completed with no textual output.",
        structured=structured,
    )


class CanonicalRefineryCLIAdapter:
    """Read-only adapter for canonical Refinery's reviewed Commons `search` command."""

    def __init__(self, command: str | None = None, timeout: int = 120) -> None:
        raw_command = command or os.environ.get("REFINERY_COMMAND", "refinery")
        self.command = shlex.split(raw_command)
        self.timeout = timeout

    def available(self) -> bool:
        return _command_available(self.command)

    def search(self, query: str, limit: int = 20) -> RefinerySearchResult:
        if not self.available():
            return UnavailableRefineryAdapter().search(query, limit)
        return _run_json_command(
            [*self.command, "search", query, "--limit", str(limit)],
            timeout=self.timeout,
            engine="refinery:canonical-search",
        )


class ReviewedMarketCLIAdapter:
    """Optional read-only adapter for Refinery's reviewed market graph search.

    Resolution order for the database is explicit `db_path`, then
    `REFINERY_MARKET_DB`, then the canonical path written by
    `refinery-market-snapshot restore`. The market graph remains descriptive
    supply evidence and never gains Commons/execution authority here.
    """

    def __init__(
        self,
        command: str | None = None,
        db_path: str | None = None,
        timeout: int = 120,
    ) -> None:
        raw_command = command or os.environ.get("REFINERY_MARKET_COMMAND", "refinery-market-search")
        self.command = shlex.split(raw_command)
        configured_db = db_path if db_path is not None else os.environ.get("REFINERY_MARKET_DB")
        if configured_db:
            self.db_path = os.path.abspath(os.path.expanduser(configured_db))
            self.db_source = "explicit" if db_path is not None else "environment"
        else:
            canonical = os.path.abspath(os.path.expanduser(_DEFAULT_REVIEWED_MARKET_DB))
            self.db_path = canonical if os.path.isfile(canonical) else None
            self.db_source = "canonical_restored_path" if self.db_path else "unconfigured"
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.db_path) and _command_available(self.command)

    def search(self, query: str, limit: int = 20) -> RefinerySearchResult:
        if not self.db_path:
            return RefinerySearchResult(
                engine="refinery:reviewed-market-search",
                status="not_run",
                raw=(
                    "No reviewed-market database is configured or restored. Set REFINERY_MARKET_DB or run "
                    "`refinery-market-snapshot restore --input <snapshot.json>` to create the canonical local database."
                ),
            )
        if not _command_available(self.command):
            return RefinerySearchResult(
                engine="refinery:reviewed-market-search",
                status="not_run",
                raw="refinery-market-search is not installed; reviewed market supply was not searched.",
            )
        result = _run_json_command(
            [*self.command, query, "--db", self.db_path, "--limit", str(limit)],
            timeout=self.timeout,
            engine="refinery:reviewed-market-search",
        )
        if isinstance(result.structured, dict):
            result.structured.setdefault("database", self.db_path)
            result.structured.setdefault("database_source", self.db_source)
        return result


class LayeredRefinerySearchAdapter:
    """Search canonical reusable supply plus optional reviewed market supply.

    The two layers are preserved separately in the result so descriptive market
    evidence is never mistaken for a validated reusable/executable capability.
    """

    def __init__(
        self,
        canonical: RefinerySearchAdapter | None = None,
        market: RefinerySearchAdapter | None = None,
    ) -> None:
        self.canonical = canonical or CanonicalRefineryCLIAdapter()
        self.market = market or ReviewedMarketCLIAdapter()

    @staticmethod
    def _canonical_lists(structured: Any) -> tuple[list[Any], list[Any]]:
        if not isinstance(structured, dict):
            return [], []
        commons = structured.get("commons") if isinstance(structured.get("commons"), list) else []
        operational = structured.get("operational") if isinstance(structured.get("operational"), list) else []
        return list(commons), list(operational)

    @staticmethod
    def _market_results(structured: Any) -> list[Any]:
        if not isinstance(structured, dict):
            return []
        value = structured.get("results")
        return list(value) if isinstance(value, list) else []

    def search(self, query: str, limit: int = 20) -> RefinerySearchResult:
        canonical = self.canonical.search(query, limit=limit)
        market = self.market.search(query, limit=limit)
        completed = [result for result in (canonical, market) if result.status == "completed"]
        errors = [result for result in (canonical, market) if result.status == "error"]
        if len(completed) == 2:
            status = "completed"
        elif completed:
            status = "partial" if errors else "completed"
        elif errors:
            status = "error"
        else:
            status = "not_run"

        commons, operational = self._canonical_lists(canonical.structured)
        reviewed_market = self._market_results(market.structured)
        structured = {
            "query": query,
            "commons": commons,
            "operational": operational,
            "reviewed_market": reviewed_market,
            "results": reviewed_market,
            "layers": {
                "canonical": {
                    "engine": canonical.engine,
                    "status": canonical.status,
                    "raw": canonical.raw,
                    "structured": canonical.structured,
                },
                "reviewed_market": {
                    "engine": market.engine,
                    "status": market.status,
                    "raw": market.raw,
                    "structured": market.structured,
                },
            },
            "boundary": (
                "Commons/operational matches retain their canonical Refinery authority. "
                "reviewed_market matches are descriptive reviewed directory evidence only and do not inherit "
                "Commons admission, rights clearance, validation, recommendation, or execution permission."
            ),
        }
        return RefinerySearchResult(
            engine="refinery:layered-search",
            status=status,
            raw=json.dumps(structured, ensure_ascii=False, sort_keys=True),
            structured=structured,
        )
