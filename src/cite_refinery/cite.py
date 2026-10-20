from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class CiteAuditResult:
    engine: str
    status: str
    raw: str
    structured: dict[str, Any] | list[Any] | None = None


class CiteAdapter(Protocol):
    def ground(self, text: str) -> CiteAuditResult: ...


class UnavailableCiteAdapter:
    """Safe fallback: records that grounding did not run; never fabricates support."""

    def ground(self, text: str) -> CiteAuditResult:
        return CiteAuditResult(
            engine="unavailable",
            status="not_run",
            raw="Cite-Agent is not configured or installed; claim remains unverified.",
        )


_STATUSES = {"completed", "not_run", "error"}


def _summary(parsed: dict[str, Any]) -> str:
    claims = parsed.get("claims") or []
    counts: dict[str, int] = {}
    for claim in claims:
        verdict = str(claim.get("verdict") or "unknown")
        counts[verdict] = counts.get(verdict, 0) + 1
    detail = ", ".join(f"{n} {verdict}" for verdict, n in sorted(counts.items()))
    return f"{len(claims)} claim(s): {detail}" if claims else str(parsed.get("error") or "no claims judged")


class CiteAgentCLIAdapter:
    """Adapter for Cite-Agent's JSON literature layer: `cite-agent-research ground <text>`.

    Set CITE_AGENT_RESEARCH_COMMAND to override the executable, e.g.
    `/path/to/Cite-Agent/.venv/bin/python -m cite_agent.research_cli`. The text is passed as one argv
    element, never via a shell. The command prints JSON only and exits 0 (completed), 3 (not run) or
    2 (error); a verdict other than not_found always carries a quote found verbatim in a paper abstract.
    """

    engine = "cite-agent-research:ground"

    def __init__(self, command: str | None = None, timeout: int = 900) -> None:
        raw_command = command or os.environ.get("CITE_AGENT_RESEARCH_COMMAND", "cite-agent-research")
        self.command = shlex.split(raw_command)
        self.timeout = timeout

    def available(self) -> bool:
        first = self.command[0]
        if os.path.sep in first:
            return os.path.exists(first)
        return shutil.which(first) is not None

    def ground(self, text: str) -> CiteAuditResult:
        if not self.available():
            return UnavailableCiteAdapter().ground(text)
        try:
            proc = subprocess.run(
                [*self.command, "ground", text],
                capture_output=True, text=True, timeout=self.timeout, check=False,
            )
        except subprocess.TimeoutExpired:
            return CiteAuditResult(engine=self.engine, status="error", raw=f"Cite-Agent timed out after {self.timeout}s")
        try:
            parsed = json.loads(proc.stdout or "")
        except json.JSONDecodeError:
            parsed = None
        if not isinstance(parsed, dict):
            detail = (proc.stderr or proc.stdout or "").strip()[-500:]
            return CiteAuditResult(engine=self.engine, status="error",
                                   raw=f"Cite-Agent returned no JSON (exit {proc.returncode}). {detail}".strip())
        status = parsed.get("status") if parsed.get("status") in _STATUSES else "error"
        if status == "completed" and proc.returncode != 0:
            status = "error"
        return CiteAuditResult(engine=self.engine, status=status, raw=_summary(parsed), structured=parsed)
