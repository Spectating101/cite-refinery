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
