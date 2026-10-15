from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class CiteResearchResult:
    engine: str
    status: str
    raw: str
    structured: dict[str, Any] | None = None


class CiteResearchAdapter(Protocol):
    def deep(self, topic: str, *, target_count: int = 40, snowball_depth: int = 1) -> CiteResearchResult: ...


class UnavailableCiteResearchAdapter:
    def deep(self, topic: str, *, target_count: int = 40, snowball_depth: int = 1) -> CiteResearchResult:
        return CiteResearchResult(
            engine="unavailable",
            status="not_run",
            raw="Structured Cite deep-research command is not configured or installed; literature acquisition did not run.",
        )


class CiteAgentResearchCLIAdapter:
    """Deterministic adapter for `cite-agent-research deep`.

    This performs literature acquisition only. Cite-Refinery stores the receipt
    separately from later synthesis/claim grounding so finding papers cannot by
    itself mark an empirical observation or intervention claim as supported.
    """

    def __init__(self, command: str | None = None, timeout: int = 300) -> None:
        raw_command = command or os.environ.get("CITE_AGENT_RESEARCH_COMMAND", "cite-agent-research")
        self.command = shlex.split(raw_command)
        self.timeout = timeout

    def available(self) -> bool:
        if not self.command:
            return False
        first = self.command[0]
        if os.path.sep in first:
            return os.path.exists(first)
        return shutil.which(first) is not None

    def deep(self, topic: str, *, target_count: int = 40, snowball_depth: int = 1) -> CiteResearchResult:
        if not topic.strip():
            raise ValueError("topic must not be empty")
        if not 1 <= int(target_count) <= 200:
            raise ValueError("target_count must be between 1 and 200")
        if not 0 <= int(snowball_depth) <= 3:
            raise ValueError("snowball_depth must be between 0 and 3")
        if not self.available():
            return UnavailableCiteResearchAdapter().deep(
                topic,
                target_count=target_count,
                snowball_depth=snowball_depth,
            )
        proc = subprocess.run(
            [
                *self.command,
                "deep",
                topic,
                "--target-count",
                str(int(target_count)),
                "--snowball-depth",
                str(int(snowball_depth)),
            ],
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=False,
            shell=False,
        )
        raw = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()
        structured: dict[str, Any] | None = None
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    structured = parsed
            except json.JSONDecodeError:
                pass
        if proc.returncode != 0:
            return CiteResearchResult(
                engine="cite-agent:deep_research",
                status="error",
                raw=stderr or raw or f"cite-agent-research exited with code {proc.returncode}",
                structured=structured,
            )
        status = "completed"
        if isinstance(structured, dict) and structured.get("status") == "error":
            status = "error"
        return CiteResearchResult(
            engine="cite-agent:deep_research",
            status=status,
            raw=raw or "Cite deep research completed with no textual output.",
            structured=structured,
        )
