from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def problem_id() -> str:
    return f"problem:{uuid4().hex[:12]}"


def object_id(prefix: str) -> str:
    return f"{prefix}:{uuid4().hex[:12]}"


class ProblemStatus(StrEnum):
    CANDIDATE = "candidate"
    RESEARCHING = "researching"
    VERIFIED = "verified"
    OPEN = "open"
    PARTIALLY_RESOLVED = "partially_resolved"
    PILOTING = "piloting"
    DEPLOYED = "deployed"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    REFRAMED = "reframed"
    RETIRED = "retired"
    INVALIDATED = "invalidated"


ALLOWED_TRANSITIONS: dict[ProblemStatus, set[ProblemStatus]] = {
    ProblemStatus.CANDIDATE: {ProblemStatus.RESEARCHING, ProblemStatus.RETIRED, ProblemStatus.INVALIDATED},
    ProblemStatus.RESEARCHING: {ProblemStatus.VERIFIED, ProblemStatus.REFRAMED, ProblemStatus.RETIRED, ProblemStatus.INVALIDATED},
    ProblemStatus.REFRAMED: {ProblemStatus.RESEARCHING, ProblemStatus.VERIFIED, ProblemStatus.RETIRED, ProblemStatus.INVALIDATED},
    ProblemStatus.VERIFIED: {ProblemStatus.OPEN, ProblemStatus.REFRAMED, ProblemStatus.RETIRED},
    ProblemStatus.OPEN: {ProblemStatus.PARTIALLY_RESOLVED, ProblemStatus.PILOTING, ProblemStatus.REFRAMED, ProblemStatus.RETIRED},
    ProblemStatus.PARTIALLY_RESOLVED: {ProblemStatus.OPEN, ProblemStatus.PILOTING, ProblemStatus.REFRAMED, ProblemStatus.RESOLVED},
    ProblemStatus.PILOTING: {ProblemStatus.OPEN, ProblemStatus.PARTIALLY_RESOLVED, ProblemStatus.DEPLOYED, ProblemStatus.REFRAMED, ProblemStatus.RETIRED},
    ProblemStatus.DEPLOYED: {ProblemStatus.MONITORING, ProblemStatus.PARTIALLY_RESOLVED, ProblemStatus.OPEN},
    ProblemStatus.MONITORING: {ProblemStatus.RESOLVED, ProblemStatus.PARTIALLY_RESOLVED, ProblemStatus.OPEN, ProblemStatus.REFRAMED},
    ProblemStatus.RESOLVED: {ProblemStatus.OPEN, ProblemStatus.REFRAMED},
    ProblemStatus.RETIRED: {ProblemStatus.RESEARCHING},
    ProblemStatus.INVALIDATED: {ProblemStatus.RESEARCHING},
}


@dataclass(slots=True)
class EvidenceRef:
    id: str
    source: str
    locator: str
    summary: str
    confidence: str = "unreviewed"
    observed_at: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SuccessCriterion:
    id: str
    metric: str
    target: str
    measurement: str
    falsification: str = ""


@dataclass(slots=True)
class Subproblem:
    id: str
    title: str
    description: str
    kind: str
    status: str = "open"
    prerequisites: list[str] = field(default_factory=list)
    capability_refs: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Attempt:
    id: str
    problem_id: str
    title: str
    contributor: str
    subproblem_ids: list[str] = field(default_factory=list)
    status: str = "active"
    artifact_refs: list[str] = field(default_factory=list)
    experiment_refs: list[str] = field(default_factory=list)
    notes: str = ""
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class Outcome:
    id: str
    problem_id: str
    summary: str
    observed_change: str
    evidence_refs: list[str] = field(default_factory=list)
    disposition: str = "observed"
    observed_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class Revision:
    id: str
    problem_id: str
    reason: str
    from_status: str
    to_status: str
    actor: str
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class PublishabilityReport:
    publishable: bool
    missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProblemPacket:
    id: str
    title: str
    observed_condition: str
    unresolved_core: str
    steward: str
    status: ProblemStatus = ProblemStatus.CANDIDATE
    domain: str = "general"
    geography: str | None = None
    time_scope: str | None = None
    affected_actors: list[str] = field(default_factory=list)
    evidence: list[EvidenceRef] = field(default_factory=list)
    disputes_uncertainty: list[str] = field(default_factory=list)
    diagnosis: list[str] = field(default_factory=list)
    knowledge_frontier: list[str] = field(default_factory=list)
    capability_frontier: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    authority_boundary: str = ""
    data_access: list[str] = field(default_factory=list)
    success_criteria: list[SuccessCriterion] = field(default_factory=list)
    subproblems: list[Subproblem] = field(default_factory=list)
    attempts: list[Attempt] = field(default_factory=list)
    outcomes: list[Outcome] = field(default_factory=list)
    revisions: list[Revision] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utcnow)
    updated_at: str = field(default_factory=utcnow)

    def publishability(self) -> PublishabilityReport:
        missing: list[str] = []
        warnings: list[str] = []
        required_text = {
            "title": self.title,
            "observed_condition": self.observed_condition,
            "unresolved_core": self.unresolved_core,
            "steward": self.steward,
            "authority_boundary": self.authority_boundary,
        }
        missing.extend(name for name, value in required_text.items() if not value.strip())
        if not self.evidence:
            missing.append("evidence")
        if not self.success_criteria:
            missing.append("success_criteria")
        if not self.affected_actors:
            warnings.append("affected_actors is empty")
        if not self.constraints:
            warnings.append("constraints is empty")
        if not self.knowledge_frontier:
            warnings.append("knowledge_frontier is empty; verify the problem is not already solved")
        if not self.capability_frontier:
            warnings.append("capability_frontier is empty; reusable capabilities may be overlooked")
        if not self.subproblems:
            warnings.append("subproblems is empty; outsiders may not know where to contribute")
        unreviewed = [item.id for item in self.evidence if item.confidence == "unreviewed"]
        if unreviewed:
            warnings.append(f"unreviewed evidence: {', '.join(unreviewed)}")
        return PublishabilityReport(publishable=not missing, missing=missing, warnings=warnings)

    def transition(self, new_status: ProblemStatus, *, actor: str, reason: str) -> Revision:
        if new_status == self.status:
            raise ValueError(f"problem already has status {new_status}")
        allowed = ALLOWED_TRANSITIONS[self.status]
        if new_status not in allowed:
            raise ValueError(f"invalid transition {self.status} -> {new_status}")
        if new_status in {ProblemStatus.VERIFIED, ProblemStatus.OPEN}:
            report = self.publishability()
            if not report.publishable:
                raise ValueError(f"problem is not publishable; missing: {', '.join(report.missing)}")
        revision = Revision(
            id=object_id("prev"),
            problem_id=self.id,
            reason=reason,
            from_status=self.status.value,
            to_status=new_status.value,
            actor=actor,
        )
        self.status = new_status
        self.updated_at = utcnow()
        self.revisions.append(revision)
        return revision

    def add_subproblem(self, title: str, description: str, kind: str, *, prerequisites: list[str] | None = None) -> Subproblem:
        item = Subproblem(
            id=object_id("psub"),
            title=title,
            description=description,
            kind=kind,
            prerequisites=list(prerequisites or []),
        )
        self.subproblems.append(item)
        self.updated_at = utcnow()
        return item

    def start_attempt(self, *, title: str, contributor: str, subproblem_ids: list[str] | None = None, notes: str = "") -> Attempt:
        if self.status not in {ProblemStatus.OPEN, ProblemStatus.PARTIALLY_RESOLVED, ProblemStatus.PILOTING}:
            raise ValueError("attempts require an open, partially resolved, or piloting problem")
        requested = list(subproblem_ids or [])
        known = {item.id for item in self.subproblems}
        unknown = sorted(set(requested) - known)
        if unknown:
            raise ValueError(f"unknown subproblem ids: {', '.join(unknown)}")
        attempt = Attempt(
            id=object_id("pattempt"),
            problem_id=self.id,
            title=title,
            contributor=contributor,
            subproblem_ids=requested,
            notes=notes,
        )
        self.attempts.append(attempt)
        self.updated_at = utcnow()
        return attempt

    def record_outcome(self, *, summary: str, observed_change: str, evidence_refs: list[str] | None = None, disposition: str = "observed") -> Outcome:
        outcome = Outcome(
            id=object_id("poutcome"),
            problem_id=self.id,
            summary=summary,
            observed_change=observed_change,
            evidence_refs=list(evidence_refs or []),
            disposition=disposition,
        )
        self.outcomes.append(outcome)
        self.updated_at = utcnow()
        return outcome

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


class ProblemCommons:
    """V0 service for living, evidence-bounded problem objects.

    It intentionally does not absorb Nocturnal, Cite, Public-Good, or Refinery state.
    It stores references to those systems and owns only the problem lifecycle plus
    contribution/outcome relationships.
    """

    def __init__(self) -> None:
        self.problems: dict[str, ProblemPacket] = {}

    def create_problem(self, *, title: str, observed_condition: str, unresolved_core: str, steward: str, domain: str = "general") -> ProblemPacket:
        packet = ProblemPacket(
            id=problem_id(),
            title=title,
            observed_condition=observed_condition,
            unresolved_core=unresolved_core,
            steward=steward,
            domain=domain,
        )
        self.problems[packet.id] = packet
        return packet

    def get(self, problem_id_value: str) -> ProblemPacket:
        try:
            return self.problems[problem_id_value]
        except KeyError as exc:
            raise KeyError(f"unknown problem: {problem_id_value}") from exc

    def list_public(self) -> list[ProblemPacket]:
        public_states = {
            ProblemStatus.VERIFIED,
            ProblemStatus.OPEN,
            ProblemStatus.PARTIALLY_RESOLVED,
            ProblemStatus.PILOTING,
            ProblemStatus.DEPLOYED,
            ProblemStatus.MONITORING,
            ProblemStatus.RESOLVED,
        }
        return sorted(
            (problem for problem in self.problems.values() if problem.status in public_states),
            key=lambda item: item.updated_at,
            reverse=True,
        )
