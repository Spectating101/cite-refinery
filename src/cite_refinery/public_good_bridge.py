from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from .problem_funding import FundingNeed, FundingStatus


class ResourceMatchStatus(StrEnum):
    QUALIFIED_CANDIDATE = "qualified_candidate"
    REQUIRES_VERIFICATION = "requires_verification"
    BLOCKED = "blocked"


@dataclass(slots=True)
class PublicGoodNeedProjection:
    """Projection of a Commons resource need into Public-Good coordination.

    This object is deliberately weaker than a grant/application object. It says
    only that a Commons project has an evidenced resource demand that Public-Good
    may try to match against external resource programs.
    """

    problem_id: str
    subproblem_id: str
    need_id: str
    kind: str = "funding"
    priority: str = "watch"
    amount: float | None = None
    currency: str | None = None
    notes: str = ""
    source_refs: list[str] = field(default_factory=list)
    claim_boundary: str = (
        "Projected resource demand only; this does not establish eligibility, "
        "application readiness, award, commitment, procurement, or authority."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FundingOpportunityProjection:
    """Reviewed projection of a Public-Good CoordinationMatch into Commons.

    A qualified candidate remains a candidate. This projection can never mutate
    FundingNeed.committed_amount or FundingNeed.status to funded.
    """

    problem_id: str
    subproblem_id: str
    resource_id: str
    status: ResourceMatchStatus
    matched_dimensions: list[str] = field(default_factory=list)
    unresolved_dimensions: list[str] = field(default_factory=list)
    blocking_dimensions: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    funding_commitment: bool = False
    application_submitted: bool = False
    authority_granted: bool = False
    claim_boundary: str = (
        "Resource-match projection only; qualified_candidate is not eligibility "
        "approval, an application, an award, a funding commitment, or authority."
    )

    def __post_init__(self) -> None:
        self.status = ResourceMatchStatus(self.status)
        if self.funding_commitment or self.application_submitted or self.authority_granted:
            raise ValueError("bridge projections cannot assert commitment, submission, or authority")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(slots=True)
class CandidateWorkProjection:
    """Candidate Commons work derived from a Public-Good normalized finding.

    Public-Good control stages and Commons work stages are orthogonal. The bridge
    therefore preserves the Public-Good stage and does not invent an Observe →
    Generalize classification. A curator must decide whether/how to create a real
    Commons Subproblem and StageProfile.
    """

    problem_id: str
    source_case_id: str
    public_good_stage: str
    problem_class: str
    priority: str
    recommended_action: str
    evidence_refs: list[str] = field(default_factory=list)
    human_authority_required: bool = True
    structural_candidate: bool = False
    domain_detail: dict[str, Any] = field(default_factory=dict)
    commons_stage: str | None = None
    commons_subproblem_created: bool = False
    authority_granted: bool = False
    claim_boundary: str = (
        "Candidate work projection only; a Public-Good finding does not create a "
        "Commons Subproblem, classify a Commons work stage, accept an attempt, or grant authority."
    )

    def __post_init__(self) -> None:
        if self.commons_stage is not None:
            raise ValueError("bridge must not auto-map Public-Good control stage to Commons work stage")
        if self.commons_subproblem_created or self.authority_granted:
            raise ValueError("bridge projections cannot create Commons work or grant authority")

    @property
    def suggested_title(self) -> str:
        label = self.problem_class.replace("_", " ").strip()
        return f"Investigate {label}" if label else "Investigate Public-Good finding"

    def to_dict(self) -> dict[str, Any]:
        return {"suggested_title": self.suggested_title, **asdict(self)}


def funding_need_to_public_good(need: FundingNeed) -> PublicGoodNeedProjection:
    """Project a Commons FundingNeed into the Public-Good resource-matching plane."""

    if need.status == FundingStatus.NOT_REQUIRED:
        raise ValueError("funding marked not-required should not be projected as a funding need")

    amount = need.target_amount if need.target_amount is not None else need.minimum_amount
    notes = [
        f"Commons funding status={need.status.value}",
        f"funding readiness={need.readiness.value}",
        f"compensation mode={need.compensation_mode.value}",
        f"volunteer compatible={str(need.volunteer_compatible).lower()}",
    ]
    if need.expense_categories:
        notes.append("expense categories=" + ", ".join(need.expense_categories))
    if need.in_kind_needs:
        notes.append("in-kind needs=" + ", ".join(need.in_kind_needs))
    if need.restrictions:
        notes.append("restrictions=" + " | ".join(need.restrictions))
    if need.notes:
        notes.append(need.notes)

    return PublicGoodNeedProjection(
        problem_id=need.problem_id,
        subproblem_id=need.subproblem_id,
        need_id=f"commons:{need.problem_id}:{need.subproblem_id}:funding",
        amount=amount,
        currency=need.currency,
        notes="; ".join(notes),
        source_refs=list(need.funding_source_refs),
    )


def coordination_match_to_commons(
    *,
    problem_id: str,
    subproblem_id: str,
    raw_match: dict[str, Any],
) -> FundingOpportunityProjection:
    """Convert a Public-Good CoordinationMatch payload to a non-escalating Commons projection."""

    return FundingOpportunityProjection(
        problem_id=problem_id,
        subproblem_id=subproblem_id,
        resource_id=str(raw_match.get("resource_id", "")).strip(),
        status=ResourceMatchStatus(str(raw_match.get("status", "requires_verification"))),
        matched_dimensions=_clean(raw_match.get("matched_dimensions", [])),
        unresolved_dimensions=_clean(raw_match.get("unresolved_dimensions", [])),
        blocking_dimensions=_clean(raw_match.get("blocking_dimensions", [])),
        evidence_refs=_clean(raw_match.get("evidence_refs", [])),
        reasons=_clean(raw_match.get("reasons", [])),
    )


def normalized_finding_to_candidate_work(
    *,
    problem_id: str,
    source_case_id: str,
    raw_finding: dict[str, Any],
) -> CandidateWorkProjection:
    """Convert a Public-Good NormalizedFinding to curator-reviewable candidate work."""

    return CandidateWorkProjection(
        problem_id=problem_id,
        source_case_id=source_case_id,
        public_good_stage=str(raw_finding.get("stage", "evidence")).strip() or "evidence",
        problem_class=str(raw_finding.get("problem_class", "")).strip(),
        priority=str(raw_finding.get("priority", "watch")).strip() or "watch",
        recommended_action=str(raw_finding.get("recommended_action", "")).strip(),
        evidence_refs=_clean(raw_finding.get("evidence_refs", [])),
        human_authority_required=bool(raw_finding.get("human_authority_required", True)),
        structural_candidate=bool(raw_finding.get("structural_candidate", False)),
        domain_detail=dict(raw_finding.get("domain_detail", {}) or {}),
    )


def freeze_invariants() -> list[str]:
    return [
        "Commons Problem status is not Public-Good diagnosis certainty.",
        "Commons work stage is not Public-Good control stage.",
        "FundingNeed is not eligibility or funding commitment.",
        "Public-Good qualified_candidate is not an award or application submission.",
        "Public-Good finding is not a Commons Subproblem until curator review.",
        "Successful attempt or test is not authority.",
        "Neither bridge direction may grant external authority.",
        "Domain constitutions remain authoritative in Public-Good and are not copied into Commons.",
    ]


def _clean(values: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        value = str(raw).strip()
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            out.append(value)
    return out
