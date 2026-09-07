from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import json
from pathlib import Path
import re
from typing import Any, Iterable
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


class Visibility(StrEnum):
    PRIVATE = "private"
    RESTRICTED = "restricted"
    PUBLIC = "public"


class AttemptStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    COMPLETED = "completed"


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

PUBLIC_STATES = {
    ProblemStatus.VERIFIED,
    ProblemStatus.OPEN,
    ProblemStatus.PARTIALLY_RESOLVED,
    ProblemStatus.PILOTING,
    ProblemStatus.DEPLOYED,
    ProblemStatus.MONITORING,
    ProblemStatus.RESOLVED,
}


@dataclass(slots=True)
class ExternalRef:
    id: str
    system: str
    ref: str
    relation: str
    visibility: Visibility = Visibility.RESTRICTED
    label: str = ""
    notes: str = ""


@dataclass(slots=True)
class EvidenceRef:
    id: str
    source: str
    locator: str
    summary: str
    confidence: str = "unreviewed"
    observed_at: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    visibility: Visibility = Visibility.RESTRICTED
    rights: str = ""
    disputes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DataResource:
    id: str
    title: str
    access: str
    uri: str | None = None
    license: str = ""
    sensitivity: str = "none"
    visibility: Visibility = Visibility.RESTRICTED
    notes: str = ""


@dataclass(slots=True)
class CapabilityNeed:
    id: str
    name: str
    state: str = "needed"
    description: str = ""
    capability_refs: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SuccessCriterion:
    id: str
    metric: str
    target: str
    measurement: str
    falsification: str = ""
    baseline: str = ""
    guardrails: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Subproblem:
    id: str
    title: str
    description: str
    kind: str
    status: str = "open"
    prerequisites: list[str] = field(default_factory=list)
    capability_refs: list[str] = field(default_factory=list)
    skill_tags: list[str] = field(default_factory=list)
    interest_tags: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    effort: str = "unspecified"
    participation_modes: list[str] = field(default_factory=lambda: ["individual", "team"])
    required_credentials: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Attempt:
    id: str
    problem_id: str
    title: str
    contributor: str
    subproblem_ids: list[str] = field(default_factory=list)
    status: AttemptStatus = AttemptStatus.ACTIVE
    capability_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    experiment_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    notes: str = ""
    credit: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utcnow)
    updated_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class AttemptReview:
    id: str
    problem_id: str
    attempt_id: str
    reviewer: str
    verdict: str
    notes: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class AuthorityDecision:
    id: str
    problem_id: str
    actor: str
    scope: str
    decision: str
    rationale: str = ""
    receipt_ref: str | None = None
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class Outcome:
    id: str
    problem_id: str
    summary: str
    observed_change: str
    evidence_refs: list[str] = field(default_factory=list)
    disposition: str = "observed"
    attribution: str = "not_established"
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
class StewardReview:
    id: str
    problem_id: str
    reviewer: str
    verdict: str
    notes: str = ""
    checklist: dict[str, bool] = field(default_factory=dict)
    created_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class PublishabilityReport:
    publishable: bool
    missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)

    @property
    def completeness(self) -> float:
        return (sum(self.checks.values()) / len(self.checks)) if self.checks else 0.0


@dataclass(slots=True)
class Match:
    subproblem_id: str
    title: str
    kind: str
    score: float
    matched_skills: list[str] = field(default_factory=list)
    matched_interests: list[str] = field(default_factory=list)
    missing_credentials: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass(slots=True)
class ProblemSignal:
    id: str
    source_system: str
    source_ref: str
    title: str
    observed_condition: str
    domain: str = "general"
    geography: str | None = None
    observed_at: str | None = None
    visibility: Visibility = Visibility.RESTRICTED
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProblemPacket:
    id: str
    title: str
    observed_condition: str
    unresolved_core: str
    steward: str
    status: ProblemStatus = ProblemStatus.CANDIDATE
    visibility: Visibility = Visibility.RESTRICTED
    domain: str = "general"
    geography: str | None = None
    time_scope: str | None = None
    summary: str = ""
    problem_owner: str = ""
    sponsor: str = ""
    affected_actors: list[str] = field(default_factory=list)
    beneficiaries: list[str] = field(default_factory=list)
    evidence: list[EvidenceRef] = field(default_factory=list)
    disputes_uncertainty: list[str] = field(default_factory=list)
    diagnosis: list[str] = field(default_factory=list)
    prior_attempts: list[str] = field(default_factory=list)
    knowledge_frontier: list[str] = field(default_factory=list)
    capability_frontier: list[str] = field(default_factory=list)
    capability_needs: list[CapabilityNeed] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    authority_boundary: str = ""
    implementation_pathway: list[str] = field(default_factory=list)
    data_access: list[str] = field(default_factory=list)
    data_resources: list[DataResource] = field(default_factory=list)
    success_criteria: list[SuccessCriterion] = field(default_factory=list)
    subproblems: list[Subproblem] = field(default_factory=list)
    attempts: list[Attempt] = field(default_factory=list)
    attempt_reviews: list[AttemptReview] = field(default_factory=list)
    authority_decisions: list[AuthorityDecision] = field(default_factory=list)
    outcomes: list[Outcome] = field(default_factory=list)
    revisions: list[Revision] = field(default_factory=list)
    steward_reviews: list[StewardReview] = field(default_factory=list)
    external_refs: list[ExternalRef] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    rights_notes: str = ""
    funding_notes: str = ""
    contribution_license: str = ""
    created_at: str = field(default_factory=utcnow)
    updated_at: str = field(default_factory=utcnow)

    def publishability(self, *, require_decomposition: bool = False) -> PublishabilityReport:
        reviewed_evidence = any(item.confidence in {"reviewed", "corroborated", "verified"} for item in self.evidence)
        checks = {
            "title": bool(self.title.strip()),
            "observed_condition": bool(self.observed_condition.strip()),
            "unresolved_core": bool(self.unresolved_core.strip()),
            "steward": bool(self.steward.strip()),
            "authority_boundary": bool(self.authority_boundary.strip()),
            "evidence": bool(self.evidence),
            "reviewed_evidence": reviewed_evidence,
            "success_criteria": bool(self.success_criteria),
            "affected_actors": bool(self.affected_actors),
            "constraints": bool(self.constraints),
            "knowledge_frontier": bool(self.knowledge_frontier),
            "capability_frontier": bool(self.capability_frontier or self.capability_needs),
            "decomposition": bool(self.subproblems),
        }
        required = ["title", "observed_condition", "unresolved_core", "steward", "authority_boundary", "evidence", "reviewed_evidence", "success_criteria"]
        if require_decomposition:
            required.append("decomposition")
        missing = [name for name in required if not checks[name]]
        warnings = [f"{name} is incomplete" for name in checks if not checks[name] and name not in required]
        if any(not item.falsification.strip() for item in self.success_criteria):
            warnings.append("one or more success criteria lack falsification conditions")
        if any(item.visibility != Visibility.PUBLIC for item in self.evidence):
            warnings.append("restricted/private evidence will be redacted from public snapshots")
        if not self.problem_owner:
            warnings.append("problem_owner is unspecified; implementation handoff may fail")
        if not self.implementation_pathway:
            warnings.append("implementation_pathway is empty; prototype-to-adoption risk is high")
        return PublishabilityReport(not missing, missing, warnings, checks)

    def transition(self, new_status: ProblemStatus, *, actor: str, reason: str) -> Revision:
        if new_status == self.status:
            raise ValueError(f"problem already has status {new_status}")
        if new_status not in ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(f"invalid transition {self.status} -> {new_status}")
        if new_status == ProblemStatus.VERIFIED:
            report = self.publishability(require_decomposition=False)
            if not report.publishable:
                raise ValueError(f"problem is not publishable; missing: {', '.join(report.missing)}")
        if new_status == ProblemStatus.OPEN:
            report = self.publishability(require_decomposition=True)
            if not report.publishable:
                raise ValueError(f"problem is not open-ready; missing: {', '.join(report.missing)}")
        if new_status == ProblemStatus.PILOTING and not any(attempt.status in {AttemptStatus.ACCEPTED, AttemptStatus.COMPLETED} for attempt in self.attempts):
            raise ValueError("piloting requires at least one accepted or completed attempt")
        if new_status == ProblemStatus.DEPLOYED and not any(decision.decision == "authorized" for decision in self.authority_decisions):
            raise ValueError("deployment requires an explicit authorized authority decision")
        revision = Revision(id=object_id("prev"), problem_id=self.id, reason=reason, from_status=self.status.value, to_status=new_status.value, actor=actor)
        self.status = new_status
        if new_status in PUBLIC_STATES:
            self.visibility = Visibility.PUBLIC
        self.updated_at = utcnow()
        self.revisions.append(revision)
        return revision

    def add_evidence(self, *, source: str, locator: str, summary: str, confidence: str = "unreviewed", visibility: Visibility = Visibility.RESTRICTED, observed_at: str | None = None, rights: str = "", provenance: dict[str, Any] | None = None) -> EvidenceRef:
        item = EvidenceRef(id=object_id("pevidence"), source=source, locator=locator, summary=summary, confidence=confidence, visibility=visibility, observed_at=observed_at, rights=rights, provenance=dict(provenance or {}))
        self.evidence.append(item)
        self.updated_at = utcnow()
        return item

    def add_subproblem(self, title: str, description: str, kind: str, *, prerequisites: list[str] | None = None, capability_refs: list[str] | None = None, skill_tags: list[str] | None = None, interest_tags: list[str] | None = None, expected_outputs: list[str] | None = None, effort: str = "unspecified", participation_modes: list[str] | None = None, required_credentials: list[str] | None = None) -> Subproblem:
        item = Subproblem(id=object_id("psub"), title=title, description=description, kind=kind, prerequisites=list(prerequisites or []), capability_refs=list(capability_refs or []), skill_tags=_norm_tags(skill_tags or []), interest_tags=_norm_tags(interest_tags or []), expected_outputs=list(expected_outputs or []), effort=effort, participation_modes=list(participation_modes or ["individual", "team"]), required_credentials=list(required_credentials or []))
        self.subproblems.append(item)
        self.updated_at = utcnow()
        return item

    def start_attempt(self, *, title: str, contributor: str, subproblem_ids: list[str] | None = None, notes: str = "", credit: list[str] | None = None) -> Attempt:
        if self.status not in {ProblemStatus.OPEN, ProblemStatus.PARTIALLY_RESOLVED, ProblemStatus.PILOTING}:
            raise ValueError("attempts require an open, partially resolved, or piloting problem")
        requested = list(subproblem_ids or [])
        known = {item.id for item in self.subproblems}
        unknown = sorted(set(requested) - known)
        if unknown:
            raise ValueError(f"unknown subproblem ids: {', '.join(unknown)}")
        if not requested:
            raise ValueError("attempt must attach to at least one explicit subproblem")
        attempt = Attempt(id=object_id("pattempt"), problem_id=self.id, title=title, contributor=contributor, subproblem_ids=requested, notes=notes, credit=list(credit or []))
        self.attempts.append(attempt)
        self.updated_at = utcnow()
        return attempt

    def update_attempt_status(self, attempt_id: str, status: AttemptStatus) -> Attempt:
        attempt = self._attempt(attempt_id)
        allowed = {
            AttemptStatus.DRAFT: {AttemptStatus.ACTIVE, AttemptStatus.WITHDRAWN},
            AttemptStatus.ACTIVE: {AttemptStatus.SUBMITTED, AttemptStatus.WITHDRAWN},
            AttemptStatus.SUBMITTED: {AttemptStatus.ACCEPTED, AttemptStatus.REJECTED, AttemptStatus.ACTIVE},
            AttemptStatus.ACCEPTED: {AttemptStatus.COMPLETED, AttemptStatus.ACTIVE},
            AttemptStatus.REJECTED: {AttemptStatus.ACTIVE, AttemptStatus.WITHDRAWN},
            AttemptStatus.WITHDRAWN: {AttemptStatus.ACTIVE},
            AttemptStatus.COMPLETED: set(),
        }
        if status not in allowed[attempt.status]:
            raise ValueError(f"invalid attempt transition {attempt.status} -> {status}")
        attempt.status = status
        attempt.updated_at = utcnow()
        self.updated_at = utcnow()
        return attempt

    def review_attempt(self, attempt_id: str, *, reviewer: str, verdict: str, notes: str = "", evidence_refs: list[str] | None = None) -> AttemptReview:
        attempt = self._attempt(attempt_id)
        if attempt.status != AttemptStatus.SUBMITTED:
            raise ValueError("attempt must be submitted before review")
        normalized = verdict.lower().strip()
        if normalized not in {"accept", "reject", "revise"}:
            raise ValueError("verdict must be accept, reject, or revise")
        attempt.status = AttemptStatus.ACCEPTED if normalized == "accept" else AttemptStatus.REJECTED if normalized == "reject" else AttemptStatus.ACTIVE
        attempt.updated_at = utcnow()
        review = AttemptReview(id=object_id("pareview"), problem_id=self.id, attempt_id=attempt.id, reviewer=reviewer, verdict=normalized, notes=notes, evidence_refs=list(evidence_refs or []))
        self.attempt_reviews.append(review)
        self.updated_at = utcnow()
        return review

    def authorize(self, *, actor: str, scope: str, decision: str, rationale: str = "", receipt_ref: str | None = None) -> AuthorityDecision:
        normalized = decision.lower().strip()
        if normalized not in {"authorized", "denied", "conditional"}:
            raise ValueError("decision must be authorized, denied, or conditional")
        item = AuthorityDecision(id=object_id("pauth"), problem_id=self.id, actor=actor, scope=scope, decision=normalized, rationale=rationale, receipt_ref=receipt_ref)
        self.authority_decisions.append(item)
        self.updated_at = utcnow()
        return item

    def record_outcome(self, *, summary: str, observed_change: str, evidence_refs: list[str] | None = None, disposition: str = "observed", attribution: str = "not_established") -> Outcome:
        outcome = Outcome(id=object_id("poutcome"), problem_id=self.id, summary=summary, observed_change=observed_change, evidence_refs=list(evidence_refs or []), disposition=disposition, attribution=attribution)
        self.outcomes.append(outcome)
        self.updated_at = utcnow()
        return outcome

    def attach_external_ref(self, *, system: str, ref: str, relation: str, visibility: Visibility = Visibility.RESTRICTED, label: str = "", notes: str = "") -> ExternalRef:
        item = ExternalRef(id=object_id("pref"), system=system, ref=ref, relation=relation, visibility=visibility, label=label, notes=notes)
        self.external_refs.append(item)
        self.updated_at = utcnow()
        return item

    def match_contributions(self, *, skills: Iterable[str] = (), interests: Iterable[str] = (), credentials: Iterable[str] = (), kinds: Iterable[str] = ()) -> list[Match]:
        skills_set, interests_set = set(_norm_tags(skills)), set(_norm_tags(interests))
        credentials_set = {item.strip().lower() for item in credentials if item.strip()}
        kinds_set = {item.strip().lower() for item in kinds if item.strip()}
        matches: list[Match] = []
        for sub in self.subproblems:
            if sub.status != "open":
                continue
            skill_hits = sorted(skills_set & set(sub.skill_tags))
            interest_hits = sorted(interests_set & set(sub.interest_tags))
            required = {item.strip().lower() for item in sub.required_credentials}
            missing_credentials = sorted(required - credentials_set)
            score = 2.0 * len(skill_hits) + 1.0 * len(interest_hits)
            if kinds_set and sub.kind.lower() in kinds_set:
                score += 1.25
            if not sub.skill_tags:
                score += 0.25
            if missing_credentials:
                score -= 4.0 * len(missing_credentials)
            rationale_bits = []
            if skill_hits:
                rationale_bits.append("skills: " + ", ".join(skill_hits))
            if interest_hits:
                rationale_bits.append("interests: " + ", ".join(interest_hits))
            if missing_credentials:
                rationale_bits.append("credential gate: " + ", ".join(missing_credentials))
            matches.append(Match(subproblem_id=sub.id, title=sub.title, kind=sub.kind, score=round(score, 2), matched_skills=skill_hits, matched_interests=interest_hits, missing_credentials=missing_credentials, rationale="; ".join(rationale_bits) or "open contribution path"))
        return sorted(matches, key=lambda item: (-item.score, item.title.lower()))

    def public_snapshot(self) -> dict[str, Any]:
        data = self.to_dict()
        data["evidence"] = [{**{k: v for k, v in asdict(item).items() if k not in {"locator", "provenance"}}, "locator": item.locator if item.visibility == Visibility.PUBLIC else None, "provenance": item.provenance if item.visibility == Visibility.PUBLIC else {}, "redacted": item.visibility != Visibility.PUBLIC} for item in self.evidence]
        data["data_resources"] = [{**asdict(item), "uri": item.uri if item.visibility == Visibility.PUBLIC else None, "redacted": item.visibility != Visibility.PUBLIC} for item in self.data_resources]
        data["external_refs"] = [asdict(item) for item in self.external_refs if item.visibility == Visibility.PUBLIC]
        data["steward_reviews"] = []
        data["authority_decisions"] = [{"id": item.id, "actor": item.actor, "scope": item.scope, "decision": item.decision, "created_at": item.created_at, "receipt_ref": item.receipt_ref if item.receipt_ref and item.receipt_ref.startswith("public:") else None} for item in self.authority_decisions]
        return data

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["visibility"] = self.visibility.value
        for item in data["evidence"]:
            item["visibility"] = str(item["visibility"])
        for item in data["data_resources"]:
            item["visibility"] = str(item["visibility"])
        for item in data["external_refs"]:
            item["visibility"] = str(item["visibility"])
        for item in data["attempts"]:
            item["status"] = str(item["status"])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProblemPacket:
        raw = dict(data)
        raw["status"] = ProblemStatus(raw.get("status", ProblemStatus.CANDIDATE))
        raw["visibility"] = Visibility(raw.get("visibility", Visibility.RESTRICTED))
        raw["evidence"] = [EvidenceRef(**{**item, "visibility": Visibility(item.get("visibility", Visibility.RESTRICTED))}) for item in raw.get("evidence", [])]
        raw["data_resources"] = [DataResource(**{**item, "visibility": Visibility(item.get("visibility", Visibility.RESTRICTED))}) for item in raw.get("data_resources", [])]
        raw["capability_needs"] = [CapabilityNeed(**item) for item in raw.get("capability_needs", [])]
        raw["success_criteria"] = [SuccessCriterion(**item) for item in raw.get("success_criteria", [])]
        raw["subproblems"] = [Subproblem(**item) for item in raw.get("subproblems", [])]
        raw["attempts"] = [Attempt(**{**item, "status": AttemptStatus(item.get("status", AttemptStatus.ACTIVE))}) for item in raw.get("attempts", [])]
        raw["attempt_reviews"] = [AttemptReview(**item) for item in raw.get("attempt_reviews", [])]
        raw["authority_decisions"] = [AuthorityDecision(**item) for item in raw.get("authority_decisions", [])]
        raw["outcomes"] = [Outcome(**item) for item in raw.get("outcomes", [])]
        raw["revisions"] = [Revision(**item) for item in raw.get("revisions", [])]
        raw["steward_reviews"] = [StewardReview(**item) for item in raw.get("steward_reviews", [])]
        raw["external_refs"] = [ExternalRef(**{**item, "visibility": Visibility(item.get("visibility", Visibility.RESTRICTED))}) for item in raw.get("external_refs", [])]
        return cls(**raw)

    def _attempt(self, attempt_id: str) -> Attempt:
        for attempt in self.attempts:
            if attempt.id == attempt_id:
                return attempt
        raise KeyError(f"unknown attempt: {attempt_id}")


class ProblemCommons:
    """Living, evidence-bounded problem registry.

    It owns problem identity, curation state, decomposition, attempts, authority
    receipts and outcome relationships. Domain engines remain authoritative for
    their own evidence, research, capability and decision state.
    """

    def __init__(self) -> None:
        self.problems: dict[str, ProblemPacket] = {}

    def create_problem(self, *, title: str, observed_condition: str, unresolved_core: str, steward: str, domain: str = "general", geography: str | None = None, problem_owner: str = "") -> ProblemPacket:
        packet = ProblemPacket(id=problem_id(), title=title, observed_condition=observed_condition, unresolved_core=unresolved_core, steward=steward, domain=domain, geography=geography, problem_owner=problem_owner)
        self.problems[packet.id] = packet
        return packet

    def create_from_signal(self, signal: ProblemSignal, *, steward: str, unresolved_core: str = "") -> ProblemPacket:
        packet = self.create_problem(title=signal.title, observed_condition=signal.observed_condition, unresolved_core=unresolved_core, steward=steward, domain=signal.domain, geography=signal.geography)
        packet.attach_external_ref(system=signal.source_system, ref=signal.source_ref, relation="problem_candidate", visibility=signal.visibility, label="origin signal")
        return packet

    def get(self, problem_id_value: str) -> ProblemPacket:
        try:
            return self.problems[problem_id_value]
        except KeyError as exc:
            raise KeyError(f"unknown problem: {problem_id_value}") from exc

    def list_public(self) -> list[ProblemPacket]:
        return sorted((problem for problem in self.problems.values() if problem.status in PUBLIC_STATES), key=lambda item: item.updated_at, reverse=True)

    def public_catalog(self) -> list[dict[str, Any]]:
        return [problem.public_snapshot() for problem in self.list_public()]

    def search(self, query: str, *, public_only: bool = False) -> list[ProblemPacket]:
        tokens = set(_tokenize(query))
        source = self.list_public() if public_only else list(self.problems.values())
        if not tokens:
            return sorted(source, key=lambda item: item.updated_at, reverse=True)
        scored: list[tuple[int, ProblemPacket]] = []
        for problem in source:
            haystack = " ".join([problem.title, problem.summary, problem.observed_condition, problem.unresolved_core, problem.domain, problem.geography or "", " ".join(problem.tags), " ".join(problem.knowledge_frontier), " ".join(problem.capability_frontier)])
            score = len(tokens & set(_tokenize(haystack)))
            if score:
                scored.append((score, problem))
        return [item for _, item in sorted(scored, key=lambda pair: (-pair[0], pair[1].title.lower()))]

    def duplicate_candidates(self, packet: ProblemPacket, *, threshold: float = 0.42) -> list[tuple[str, float]]:
        left = set(_tokenize(" ".join([packet.title, packet.observed_condition, packet.unresolved_core])))
        if not left:
            return []
        results = []
        for other in self.problems.values():
            if other.id == packet.id:
                continue
            right = set(_tokenize(" ".join([other.title, other.observed_condition, other.unresolved_core])))
            if not right:
                continue
            score = len(left & right) / len(left | right)
            if score >= threshold:
                results.append((other.id, round(score, 3)))
        return sorted(results, key=lambda item: -item[1])

    def to_dict(self) -> dict[str, Any]:
        return {"schema": "problem-commons/v0.1", "exported_at": utcnow(), "problems": [problem.to_dict() for problem in self.problems.values()]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProblemCommons:
        commons = cls()
        for raw in data.get("problems", []):
            packet = ProblemPacket.from_dict(raw)
            commons.problems[packet.id] = packet
        return commons

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(target)
        return target

    @classmethod
    def load(cls, path: str | Path) -> ProblemCommons:
        target = Path(path)
        if not target.exists():
            return cls()
        return cls.from_dict(json.loads(target.read_text(encoding="utf-8")))


def _norm_tags(values: Iterable[str]) -> list[str]:
    return sorted({item.strip().lower().replace(" ", "-") for item in values if item and item.strip()})


def _tokenize(value: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]{3,}", value.lower()) if token not in {"the", "and", "for", "with", "from"}]
