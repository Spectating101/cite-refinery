from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Protocol


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
            raw="Canonical Refinery is not configured or installed; no external solution search ran.",
        )


class CanonicalRefineryCLIAdapter:
    """Read-only adapter for canonical Refinery's `search` command."""

    def __init__(self, command: str | None = None, timeout: int = 120) -> None:
        raw_command = command or os.environ.get("REFINERY_COMMAND", "refinery")
        self.command = shlex.split(raw_command)
        self.timeout = timeout

    def available(self) -> bool:
        first = self.command[0]
        if os.path.sep in first:
            return os.path.exists(first)
        return shutil.which(first) is not None

    def search(self, query: str, limit: int = 20) -> RefinerySearchResult:
        if not self.available():
            return UnavailableRefineryAdapter().search(query, limit)
        proc = subprocess.run(
            [*self.command, "search", query, "--limit", str(limit)],
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=False,
            shell=False,
        )
        raw = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        if proc.returncode != 0:
            return RefinerySearchResult(
                engine="refinery:canonical-search",
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
            engine="refinery:canonical-search",
            status="completed",
            raw=raw or "Refinery completed with no textual output.",
            structured=structured,
        )
