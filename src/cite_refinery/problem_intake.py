from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import json
from pathlib import Path
from typing import Any

from .problem_commons import (
    EvidenceRef,
    ExternalRef,
    ProblemPacket,
    ProblemStatus,
    Subproblem,
    SuccessCriterion,
    Visibility,
)


class IntakeMode(StrEnum):
    OWNER_SUBMITTED = "owner-submitted"
    CURATOR_INTERVIEW = "curator-interview"
    PUBLIC_LISTING = "public-listing"


class OwnerConfirmation(StrEnum):
    NOT_CONTACTED = "not-contacted"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REFRAMED = "reframed"
    DISPUTED = "disputed"


@dataclass(slots=True)
class SuggestedWork:
    title: str
    description: str
    kind: str
    expected_outputs: list[str] = field(default_factory=list)
    skill_tags: list[str] = field(default_factory=list)
    effort: str = "unspecified"
    required_credentials: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OwnerIntake:
    id: str
    source_system: str
    source_ref: str
    title: str
    owner_org: str
    owner_statement: str
    geography: str
    intake_mode: IntakeMode = IntakeMode.PUBLIC_LISTING
    owner_confirmation: OwnerConfirmation = OwnerConfirmation.NOT_CONTACTED
    source_observed_at: str | None = None
    owner_confirmation_ref: str = ""
    owner_confirmed_at: str | None = None
    schedule: str = ""
    affected_actors: list[str] = field(default_factory=list)
    beneficiaries: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    available_resources: list[str] = field(default_factory=list)
    requested_support: list[str] = field(default_factory=list)
    proposed_modes: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    safeguarding_notes: list[str] = field(default_factory=list)
    data_access_notes: list[str] = field(default_factory=list)
    suggested_work: list[SuggestedWork] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        self.intake_mode = IntakeMode(self.intake_mode)
        self.owner_confirmation = OwnerConfirmation(self.owner_confirmation)
        self.suggested_work = [
            item if isinstance(item, SuggestedWork) else SuggestedWork(**item)
            for item in self.suggested_work
        ]

    def validation(self) -> "IntakeValidation":
        errors: list[str] = []
        warnings: list[str] = []
        if not self.id.startswith("intake:"):
            errors.append("id must begin with intake:")
        for name, value in (
            ("source_system", self.source_system),
            ("source_ref", self.source_ref),
            ("title", self.title),
            ("owner_org", self.owner_org),
            ("owner_statement", self.owner_statement),
            ("geography", self.geography),
        ):
            if not value.strip():
                errors.append(f"{name} is required")
        if self.owner_confirmation in {OwnerConfirmation.CONFIRMED, OwnerConfirmation.REFRAMED}:
            if not self.owner_confirmation_ref.strip():
                errors.append("confirmed/reframed owner intake requires owner_confirmation_ref")
            if not self.owner_confirmed_at:
                errors.append("confirmed/reframed owner intake requires owner_confirmed_at")
        if self.intake_mode == IntakeMode.PUBLIC_LISTING and self.owner_confirmation == OwnerConfirmation.NOT_CONTACTED:
            warnings.append("public listing has not been confirmed by the potential problem owner")
        actor_text = " ".join(self.affected_actors + self.beneficiaries).lower()
        if any(term in actor_text for term in ("child", "children", "minor", "student", "pupil")) and not self.safeguarding_notes:
            warnings.append("child/minor-related intake has no safeguarding notes")
        if not self.suggested_work:
            warnings.append("no candidate work paths supplied; curation must create decomposition before opening")
        return IntakeValidation(valid=not errors, errors=errors, warnings=warnings)

    @property
    def owner_is_confirmed(self) -> bool:
        return self.owner_confirmation in {OwnerConfirmation.CONFIRMED, OwnerConfirmation.REFRAMED}

    def to_problem_packet(self, *, steward: str) -> ProblemPacket:
        report = self.validation()
        if not report.valid:
            raise ValueError("invalid owner intake: " + "; ".join(report.errors))
        if not steward.strip():
            raise ValueError("steward is required")

        suffix = self.id.split(":", 1)[1]
        uncertainty = list(self.uncertainties)
        if not self.owner_is_confirmed:
            uncertainty.insert(0, "Potential problem owner has not yet confirmed this Commons formulation or that the source listing remains current.")
        if self.source_observed_at is None:
            uncertainty.append("Source freshness is not timestamped in the intake; current need must be re-verified.")

        constraints = list(self.constraints)
        constraints.extend(note for note in self.safeguarding_notes if note not in constraints)
        if self.schedule:
            constraints.append(f"Reported operating schedule: {self.schedule}")

        packet = ProblemPacket(
            id=f"problem:{suffix}",
            title=self.title,
            observed_condition=f"Owner-reported/publicly listed condition: {self.owner_statement}",
            unresolved_core=(
                "Determine whether the reported condition remains current, what bounded contribution would materially help, "
                "and what access, safeguarding, resources, review, and authority are required before any work begins."
            ),
            steward=steward,
            status=ProblemStatus.CANDIDATE,
            visibility=Visibility.RESTRICTED,
            domain="community-support",
            geography=self.geography,
            time_scope=self.schedule or None,
            summary="Candidate generated from an external problem-owner intake/feed. Owner statements are preserved as reported context, not verified diagnosis.",
            problem_owner=self.owner_org if self.owner_is_confirmed else "",
            affected_actors=list(self.affected_actors),
            beneficiaries=list(self.beneficiaries),
            evidence=[
                EvidenceRef(
                    id=f"pevidence:{suffix}:source",
                    source=self.source_system,
                    locator=self.source_ref,
                    summary=f"Public/owner intake source reports the stated need on behalf of {self.owner_org}.",
                    confidence="reported",
                    observed_at=self.source_observed_at,
                    provenance={"intake_id": self.id, "intake_mode": self.intake_mode.value},
                    visibility=Visibility.PUBLIC,
                    rights="source-linked; no private contact details copied into the packet",
                    disputes=[],
                )
            ],
            disputes_uncertainty=uncertainty,
            diagnosis=["No causal diagnosis or preferred intervention is accepted at intake stage."],
            knowledge_frontier=[
                "Confirm with the potential problem owner that the need is current and accurately framed.",
                "Clarify the target outcome, current baseline/capacity, and what would count as useful support.",
                "Verify access, safeguarding, supervision, and participant eligibility before any direct service activity.",
            ],
            capability_frontier=list(self.requested_support),
            constraints=constraints,
            authority_boundary=(
                "This candidate authorizes no direct service, participant contact, data access, or intervention. "
                "Any real activity requires the problem owner's explicit agreement plus applicable institutional, safeguarding, professional, and legal requirements."
            ),
            implementation_pathway=[
                "Obtain owner confirmation or reframe/retire the candidate.",
                "Freeze the current need, baseline, access and safeguarding constraints.",
                "Convert only owner-approved work into solver-ready Project Briefs.",
                "Match appropriate people/resources and run bounded work under named review.",
                "Return outputs to the owner and record whether the condition or next decision materially changed.",
            ],
            data_access=list(self.data_access_notes),
            success_criteria=[
                SuccessCriterion(
                    id=f"criterion:{suffix}:owner-review",
                    metric="problem-owner formulation agreement",
                    target="Potential owner confirms the need and bounded work frontier, or explicitly reframes/rejects it.",
                    measurement="Owner review receipt against the generated candidate packet.",
                    falsification="Owner says the need is stale, materially misframed, already resolved, or unsuitable for external contribution.",
                    baseline="Unconfirmed public/owner intake.",
                    guardrails=["No direct participant contact before approval", "No owner endorsement inferred from a public listing"],
                )
            ],
            subproblems=[
                Subproblem(
                    id=f"psub:{suffix}:{index:02d}",
                    title=work.title,
                    description=work.description,
                    kind=work.kind,
                    status="proposed_pending_owner_review",
                    skill_tags=list(work.skill_tags),
                    expected_outputs=list(work.expected_outputs),
                    effort=work.effort,
                    required_credentials=list(work.required_credentials),
                )
                for index, work in enumerate(self.suggested_work, start=1)
            ],
            external_refs=[
                ExternalRef(
                    id=f"pref:{suffix}:source",
                    system=self.source_system,
                    ref=self.source_ref,
                    relation="owner_intake_source",
                    visibility=Visibility.PUBLIC,
                    label=self.owner_org,
                    notes="Source establishes a reported need, not Commons owner confirmation or endorsement.",
                )
            ],
            tags=["owner-intake", "candidate", "do-not-publish-before-owner-review"],
            rights_notes="Preserve minimum-necessary information. Do not copy participant/minor identities or private contact data into public exports.",
            funding_notes="No funding, stipend, volunteer availability, or sponsor commitment is inferred from the intake source.",
        )
        return packet

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["intake_mode"] = self.intake_mode.value
        data["owner_confirmation"] = self.owner_confirmation.value
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "OwnerIntake":
        return cls(**dict(raw))

    @classmethod
    def load(cls, path: str | Path) -> "OwnerIntake":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass(slots=True)
class IntakeValidation:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
