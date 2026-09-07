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


class CiteAgentCLIAdapter:
    """Adapter for Cite-Agent's real `tool ground` command.

    Set CITE_AGENT_COMMAND to override the executable, e.g.
    `python -m cite_agent.cli`. The claim is passed as one argv element, never via
    a shell, so project text cannot become shell syntax.
    """

    def __init__(self, command: str | None = None, timeout: int = 180) -> None:
        raw_command = command or os.environ.get("CITE_AGENT_COMMAND", "cite-agent")
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
        proc = subprocess.run(
            [*self.command, "tool", "ground", text],
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=False,
        )
        raw = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        if proc.returncode != 0:
            return CiteAuditResult(
                engine="cite-agent:ground_claims",
                status="error",
                raw=stderr or raw or f"Cite-Agent exited with code {proc.returncode}",
            )
        structured: dict[str, Any] | list[Any] | None = None
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, (dict, list)):
                    structured = parsed
            except json.JSONDecodeError:
                pass
        return CiteAuditResult(
            engine="cite-agent:ground_claims",
            status="completed",
            raw=raw or "Cite-Agent completed with no textual output.",
            structured=structured,
        )
