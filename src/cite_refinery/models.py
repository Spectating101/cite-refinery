from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def machine_id(prefix: str) -> str:
    return f"{prefix}:{uuid4().hex[:12]}"


@dataclass(slots=True)
class Project:
    id: str
    title: str
    problem: str
    branch: str
    status: str = "active"
    created_at: str = field(default_factory=utcnow)
    updated_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class ProblemObservation:
    id: str
    project_id: str
    source_system: str
    external_id: str
    matter_id: str | None
    event_id: str | None
    text: str
    observed_at: str | None = None
    status_stage: str | None = None
    frame: str | None = None
    sources: list[str] = field(default_factory=list)
    literature_queries: list[dict[str, Any]] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class ResearchBrief:
    id: str
    project_id: str
    title: str
    observation_ids: list[str] = field(default_factory=list)
    questions: list[dict[str, Any]] = field(default_factory=list)
    audit_ids: list[str] = field(default_factory=list)
    status: str = "prepared"
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class Claim:
    id: str
    project_id: str
    text: str
    status: str = "unverified"
    confidence: float | None = None
    evidence_ids: list[str] = field(default_factory=list)
    audit_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class Evidence:
    id: str
    project_id: str
    source: str
    locator: str | None = None
    summary: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class Audit:
    id: str
    project_id: str
    claim_ids: list[str]
    engine: str
    status: str
    raw: str
    structured: dict[str, Any] | list[Any] | None = None
    purpose: str = "claim_grounding"
    target_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class Requirement:
    id: str
    project_id: str
    text: str
    kind: str = "capability"
    tags: list[str] = field(default_factory=list)
    source_brief_id: str | None = None
    source_audit_id: str | None = None
    status: str = "open"
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class SolutionMap:
    id: str
    project_id: str
    requirement_ids: list[str]
    engine: str
    status: str
    results: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class Capability:
    id: str
    name: str
    description: str
    tags: list[str] = field(default_factory=list)
    scope: str = "global"
    project_id: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class Implementation:
    id: str
    capability_id: str
    provider: str
    invocation: dict[str, Any] = field(default_factory=dict)
    scope: str = "global"
    project_id: str | None = None
    validated: bool = False
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class Run:
    id: str
    project_id: str
    implementation_id: str
    capability_id: str
    provider: str
    input: Any = None
    status: str = "error"
    output: Any = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_ms: int = 0
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class Artifact:
    id: str
    project_id: str
    name: str
    kind: str
    uri: str | None = None
    description: str = ""
    reusable: bool = False
    capability_id: str | None = None
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class Experiment:
    id: str
    project_id: str
    name: str
    method: str
    result: str
    verdict: str = "inconclusive"
    metrics: dict[str, Any] = field(default_factory=dict)
    claim_ids: list[str] = field(default_factory=list)
    artifact_ids: list[str] = field(default_factory=list)
    run_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class Event:
    id: str
    project_id: str | None
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utcnow)


def dump_model(value: Any) -> dict[str, Any]:
    return asdict(value)
