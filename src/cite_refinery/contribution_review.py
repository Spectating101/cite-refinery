from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4

from .contribution_handoff import (
    SUBMISSION_SCHEMA,
    ArtifactRef,
    ContributorWorkspace,
    canonical_hash,
    utcnow,
)
from .contribution_revision import (
    REVISION_SUBMISSION_SCHEMA,
    ContributionRevisionWorkspace,
    validate_revision_submission,
)
from .problem_commons import AttemptStatus, ProblemCommons


REVIEW_SCHEMA = "problem-contribution-review/v0.1"
PROJECTION_SCHEMA = "problem-contribution-projection/v0.1"
REVISION_PROJECTION_SCHEMA = "problem-contribution-revision-projection/v0.1"


class ContributionVerdict(StrEnum):
    ACCEPT = "accept"
    REVISE = "revise"
    REJECT = "reject"


@dataclass(slots=True)
class ReviewValidation:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ContributionReview:
    id: str
    submission_hash: str
    workspace_id: str
    project_id: str
    problem_id: str
    subproblem_id: str
    contributor_ref: str
    reviewer_ref: str
    verdict: ContributionVerdict
    summary: str
    strengths: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    revision_requirements: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        self.verdict = ContributionVerdict(self.verdict)
        self.strengths = _clean(self.strengths)
        self.limitations = _clean(self.limitations)
        self.revision_requirements = _clean(self.revision_requirements)
        self.evidence_refs = _clean(self.evidence_refs)

    @classmethod
    def from_submission(
        cls,
        submission: dict[str, Any],
        *,
        reviewer_ref: str,
        verdict: ContributionVerdict | str,
        summary: str,
        strengths: list[str] | None = None,
        limitations: list[str] | None = None,
        revision_requirements: list[str] | None = None,
        evidence_refs: list[str] | None = None,
        review_id: str | None = None,
    ) -> "ContributionReview":
        errors = validate_reviewable_submission(submission)
        if errors:
            raise ValueError("invalid contribution submission: " + "; ".join(errors))
        return cls(
            id=review_id or f"contribreview:{uuid4().hex[:12]}",
            submission_hash=canonical_hash(submission),
            workspace_id=str(submission["workspace_id"]),
            project_id=str(submission["project_id"]),
            problem_id=str(submission["problem_id"]),
            subproblem_id=str(submission["subproblem_id"]),
            contributor_ref=str(submission["contributor_ref"]),
            reviewer_ref=reviewer_ref.strip(),
            verdict=ContributionVerdict(verdict),
            summary=summary.strip(),
            strengths=list(strengths or []),
            limitations=list(limitations or []),
            revision_requirements=list(revision_requirements or []),
            evidence_refs=list(evidence_refs or []),
        )

    def validation(self, submission: dict[str, Any]) -> ReviewValidation:
        errors = validate_reviewable_submission(submission)
        warnings: list[str] = []
        if not self.id.startswith("contribreview:") or not self.id.split(":", 1)[1].strip():
            errors.append("review id must begin with contribreview:")
        if self.submission_hash != canonical_hash(submission):
            errors.append("review is not bound to this exact submission")
        for key in ("workspace_id", "project_id", "problem_id", "subproblem_id", "contributor_ref"):
            if getattr(self, key) != submission.get(key):
                errors.append(f"review {key} does not match submission")
        if not self.reviewer_ref.strip():
            errors.append("reviewer_ref is required")
        if self.reviewer_ref.strip() == self.contributor_ref.strip():
            errors.append("independent review requires reviewer_ref to differ from contributor_ref")
        if not self.summary.strip():
            errors.append("review summary is required")
        if self.verdict == ContributionVerdict.REVISE and not self.revision_requirements:
            errors.append("revise verdict requires at least one revision requirement")
        if self.verdict == ContributionVerdict.REJECT and not self.limitations:
            warnings.append("reject verdict has no explicit limitations; preserve enough rationale for the contributor")
        warnings.append("review verdict evaluates the submitted contribution only; it does not establish problem resolution, deployment authority, funding, or real-world outcome")
        return ReviewValidation(valid=not errors, errors=_clean(errors), warnings=_clean(warnings))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": REVIEW_SCHEMA,
            **asdict(self),
            "verdict": self.verdict.value,
            "claims_boundary": (
                "This is an independent review of a submitted contribution. Acceptance is not a finding that the Problem is resolved, "
                "that an intervention is authorized, that funding exists, or that any real-world outcome occurred."
            ),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ContributionReview":
        data = dict(raw)
        schema = data.pop("schema", None)
        data.pop("claims_boundary", None)
        if schema != REVIEW_SCHEMA:
            raise ValueError(f"unsupported contribution review schema: {schema}")
        return cls(**data)


def validate_reviewable_submission(submission: dict[str, Any]) -> list[str]:
    if not isinstance(submission, dict):
        return ["submission must be an object"]
    schema = submission.get("schema")
    if schema == SUBMISSION_SCHEMA:
        return validate_submission_snapshot(submission)
    if schema == REVISION_SUBMISSION_SCHEMA:
        return validate_revision_submission(submission)
    return ["unsupported contribution submission schema"]


def validate_submission_snapshot(
    submission: dict[str, Any],
    *,
    workspace: ContributorWorkspace | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(submission, dict):
        return ["submission must be an object"]
    if submission.get("schema") != SUBMISSION_SCHEMA:
        errors.append("unsupported contribution submission schema")
    required_text = (
        "workspace_id", "project_id", "problem_id", "subproblem_id", "contributor_ref",
        "project_brief_hash", "workspace_hash", "participation_basis", "method_scope", "submitted_at", "claims_boundary",
    )
    for key in required_text:
        if not isinstance(submission.get(key), str) or not str(submission.get(key)).strip():
            errors.append(f"submission {key} is required")
    if isinstance(submission.get("problem_id"), str) and not submission["problem_id"].startswith("problem:"):
        errors.append("submission problem_id must begin with problem:")
    if not isinstance(submission.get("produced_outputs"), list) or not submission.get("produced_outputs"):
        errors.append("submission requires at least one produced output")
    elif any(not isinstance(item, str) or not item.strip() for item in submission["produced_outputs"]):
        errors.append("submission produced_outputs must contain non-empty text")
    if not isinstance(submission.get("artifacts"), list) or not submission.get("artifacts"):
        errors.append("submission requires at least one material artifact")
    else:
        seen: set[str] = set()
        for raw in submission["artifacts"]:
            if not isinstance(raw, dict):
                errors.append("submission artifacts must be objects")
                continue
            try:
                artifact = ArtifactRef(**raw)
            except TypeError as exc:
                errors.append(f"invalid submission artifact: {exc}")
                continue
            errors.extend(artifact.validation_errors())
            if artifact.id in seen:
                errors.append(f"duplicate submission artifact id: {artifact.id}")
            seen.add(artifact.id)
    for key in ("blockers",):
        value = submission.get(key, [])
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            errors.append(f"submission {key} must be a list of text")
    if workspace is not None:
        report = workspace.validation(require_submittable=True)
        if not report.valid:
            errors.extend(f"workspace: {item}" for item in report.errors)
        if workspace.state.value != "submitted":
            errors.append("canonical projection requires a submitted Contributor Workspace")
        else:
            expected = workspace.submission_snapshot()
            if canonical_hash(expected) != canonical_hash(submission):
                errors.append("submission does not match the retained submitted Contributor Workspace")
    return _clean(errors)


def project_review_into_commons(
    commons: ProblemCommons,
    workspace: ContributorWorkspace,
    submission: dict[str, Any],
    review: ContributionReview,
) -> dict[str, Any]:
    submission_errors = validate_submission_snapshot(submission, workspace=workspace)
    if submission_errors:
        raise ValueError("submission/workspace validation failed: " + "; ".join(submission_errors))
    review_report = review.validation(submission)
    if not review_report.valid:
        raise ValueError("contribution review is invalid: " + "; ".join(review_report.errors))

    packet = commons.get(workspace.problem_id)
    if not any(item.id == workspace.subproblem_id for item in packet.subproblems):
        raise ValueError("canonical Problem no longer contains the reviewed subproblem")

    suffix = workspace.id.split(":", 1)[1]
    attempt_id = f"pattempt:{suffix}"
    canonical_review_id = f"pareview:{suffix}"
    submission_hash = canonical_hash(submission)
    review_hash = canonical_hash(review.to_dict())
    artifact_refs = [item["id"] for item in submission["artifacts"]]
    submission_marker = f"contribution_submission={submission_hash}"
    review_marker = f"contribution_review={review_hash}"

    existing = next((item for item in packet.attempts if item.id == attempt_id), None)
    existing_reviews = [item for item in packet.attempt_reviews if item.attempt_id == attempt_id]

    if existing is not None:
        if existing.contributor != workspace.contributor_ref:
            raise ValueError("existing canonical Attempt has a conflicting contributor")
        if existing.subproblem_ids != [workspace.subproblem_id]:
            raise ValueError("existing canonical Attempt has conflicting subproblem linkage")
        if existing.artifact_refs != artifact_refs or submission_marker not in existing.notes:
            raise ValueError("existing canonical Attempt does not match this contribution submission")
        if existing_reviews:
            if len(existing_reviews) != 1:
                raise ValueError("canonical Attempt has multiple reviews; automatic replay is unsafe")
            prior = existing_reviews[0]
            expected_status = _attempt_status_for_verdict(review.verdict)
            if (
                prior.id != canonical_review_id
                or prior.reviewer != review.reviewer_ref
                or prior.verdict != review.verdict.value
                or review.submission_hash not in prior.notes
                or review_marker not in prior.notes
                or existing.status != expected_status
            ):
                raise ValueError("a different review has already been projected for this contribution")
            return _projection_receipt(packet.id, workspace, review, attempt_id, canonical_review_id, review_hash, changed=False)
        if existing.status != AttemptStatus.SUBMITTED:
            raise ValueError("existing canonical Attempt is not awaiting review")
    else:
        attempt = packet.start_attempt(
            title=workspace.project_brief.get("title", workspace.project_id),
            contributor=workspace.contributor_ref,
            subproblem_ids=[workspace.subproblem_id],
            notes=(
                f"Projected from Contributor Workspace {workspace.id}. {submission_marker}. "
                "Projection records submitted work; it does not establish correctness, funding, authority, outcome, or problem resolution."
            ),
        )
        attempt.id = attempt_id
        attempt.artifact_refs = artifact_refs
        packet.update_attempt_status(attempt.id, AttemptStatus.SUBMITTED)

    note_parts = [
        f"Independent contribution review {review.id}.",
        f"submission_hash={review.submission_hash}.",
        f"{review_marker}.",
        review.summary,
    ]
    if review.revision_requirements:
        note_parts.append("Revision requirements: " + " | ".join(review.revision_requirements))
    if review.limitations:
        note_parts.append("Limitations: " + " | ".join(review.limitations))
    canonical_review = packet.review_attempt(
        attempt_id,
        reviewer=review.reviewer_ref,
        verdict=review.verdict.value,
        notes=" ".join(note_parts),
        evidence_refs=review.evidence_refs,
    )
    canonical_review.id = canonical_review_id

    return _projection_receipt(packet.id, workspace, review, attempt_id, canonical_review_id, review_hash, changed=True)


def project_revision_review_into_commons(
    commons: ProblemCommons,
    workspace: ContributionRevisionWorkspace,
    submission: dict[str, Any],
    review: ContributionReview,
    *,
    parent_submission: dict[str, Any],
    trigger_review: dict[str, Any],
) -> dict[str, Any]:
    submission_errors = validate_revision_submission(
        submission,
        workspace=workspace,
        parent_submission=parent_submission,
        trigger_review=trigger_review,
    )
    if submission_errors:
        raise ValueError("revision submission/workspace validation failed: " + "; ".join(submission_errors))
    review_report = review.validation(submission)
    if not review_report.valid:
        raise ValueError("contribution revision review is invalid: " + "; ".join(review_report.errors))

    packet = commons.get(workspace.problem_id)
    if not any(item.id == workspace.subproblem_id for item in packet.subproblems):
        raise ValueError("canonical Problem no longer contains the reviewed subproblem")

    suffix = workspace.root_workspace_id.split(":", 1)[1]
    attempt_id = f"pattempt:{suffix}"
    canonical_review_id = f"pareview:{suffix}:r{workspace.revision_number}"
    prior_review_id = f"pareview:{suffix}" if workspace.revision_number == 1 else f"pareview:{suffix}:r{workspace.revision_number - 1}"
    submission_hash = canonical_hash(submission)
    review_hash = canonical_hash(review.to_dict())
    artifact_refs = [item["id"] for item in submission["artifacts"]]
    submission_marker = f"contribution_submission={submission_hash}"
    parent_marker = f"submission_hash={workspace.parent_submission_hash}"
    trigger_marker = f"contribution_review={workspace.trigger_review_hash}"
    review_marker = f"contribution_review={review_hash}"

    attempt = next((item for item in packet.attempts if item.id == attempt_id), None)
    if attempt is None:
        raise ValueError("canonical Attempt for the revision root does not exist")
    if attempt.contributor != workspace.contributor_ref:
        raise ValueError("existing canonical Attempt has a conflicting contributor")
    if attempt.subproblem_ids != [workspace.subproblem_id]:
        raise ValueError("existing canonical Attempt has conflicting subproblem linkage")

    reviews = [item for item in packet.attempt_reviews if item.attempt_id == attempt_id]
    review_ids = [item.id for item in reviews]
    if len(review_ids) != len(set(review_ids)):
        raise ValueError("canonical Attempt has duplicate review ids; automatic revision projection is unsafe")
    prior = next((item for item in reviews if item.id == prior_review_id), None)
    if prior is None:
        raise ValueError("revision lineage is missing the immediately preceding canonical review")
    if prior.verdict != ContributionVerdict.REVISE.value:
        raise ValueError("immediately preceding canonical review is not REVISE")
    if parent_marker not in prior.notes or trigger_marker not in prior.notes:
        raise ValueError("preceding canonical review does not match the revision parent/review hashes")
    if f"contribution_submission={workspace.parent_submission_hash}" not in attempt.notes:
        raise ValueError("canonical Attempt does not retain the parent submission hash for this revision")

    expected_prior_ids = {f"pareview:{suffix}"}
    expected_prior_ids.update(f"pareview:{suffix}:r{index}" for index in range(1, workspace.revision_number))
    current = next((item for item in reviews if item.id == canonical_review_id), None)
    actual_ids = set(review_ids)

    if current is not None:
        if actual_ids != expected_prior_ids | {canonical_review_id}:
            raise ValueError("later or conflicting canonical revision reviews make this replay unsafe")
        expected_status = _attempt_status_for_verdict(review.verdict)
        if (
            current.reviewer != review.reviewer_ref
            or current.verdict != review.verdict.value
            or review.submission_hash not in current.notes
            or review_marker not in current.notes
            or attempt.status != expected_status
            or attempt.artifact_refs != artifact_refs
            or submission_marker not in attempt.notes
        ):
            raise ValueError("a different review has already been projected for this revision")
        return _revision_projection_receipt(
            packet.id,
            workspace,
            review,
            attempt_id,
            canonical_review_id,
            review_hash,
            changed=False,
        )

    if actual_ids != expected_prior_ids:
        raise ValueError("canonical Attempt review history does not match the expected revision sequence")
    if attempt.status != AttemptStatus.ACTIVE:
        raise ValueError("canonical Attempt must be active after REVISE before a revision can be resubmitted")

    attempt.artifact_refs = artifact_refs
    attempt.notes = (
        attempt.notes
        + " "
        + f"Revision r{workspace.revision_number} submitted from {workspace.id}. {submission_marker}. "
        + f"trigger_review={workspace.trigger_review_hash}. "
        + "Revision projection preserves prior review history and does not establish correctness, funding, authority, outcome, or problem resolution."
    )
    packet.update_attempt_status(attempt_id, AttemptStatus.SUBMITTED)

    note_parts = [
        f"Independent contribution revision review {review.id} for revision r{workspace.revision_number}.",
        f"submission_hash={review.submission_hash}.",
        f"{review_marker}.",
        review.summary,
    ]
    if review.revision_requirements:
        note_parts.append("Revision requirements: " + " | ".join(review.revision_requirements))
    if review.limitations:
        note_parts.append("Limitations: " + " | ".join(review.limitations))
    canonical_review = packet.review_attempt(
        attempt_id,
        reviewer=review.reviewer_ref,
        verdict=review.verdict.value,
        notes=" ".join(note_parts),
        evidence_refs=review.evidence_refs,
    )
    canonical_review.id = canonical_review_id

    return _revision_projection_receipt(
        packet.id,
        workspace,
        review,
        attempt_id,
        canonical_review_id,
        review_hash,
        changed=True,
    )


def _projection_receipt(
    problem_id: str,
    workspace: ContributorWorkspace,
    review: ContributionReview,
    attempt_id: str,
    canonical_review_id: str,
    review_hash: str,
    *,
    changed: bool,
) -> dict[str, Any]:
    return {
        "schema": PROJECTION_SCHEMA,
        "problem_id": problem_id,
        "workspace_id": workspace.id,
        "submission_hash": review.submission_hash,
        "review_hash": review_hash,
        "attempt_id": attempt_id,
        "attempt_review_id": canonical_review_id,
        "verdict": review.verdict.value,
        "attempt_status": _attempt_status_for_verdict(review.verdict).value,
        "changed": changed,
        "next_action": _next_action_for_verdict(review.verdict),
        "claims_boundary": (
            "Canonical projection records an independently reviewed Attempt only. It does not transition the Problem, create an Outcome, "
            "assert funding, authorize deployment, or establish causal impact."
        ),
    }


def _revision_projection_receipt(
    problem_id: str,
    workspace: ContributionRevisionWorkspace,
    review: ContributionReview,
    attempt_id: str,
    canonical_review_id: str,
    review_hash: str,
    *,
    changed: bool,
) -> dict[str, Any]:
    return {
        "schema": REVISION_PROJECTION_SCHEMA,
        "problem_id": problem_id,
        "workspace_id": workspace.id,
        "root_workspace_id": workspace.root_workspace_id,
        "parent_workspace_id": workspace.parent_workspace_id,
        "revision_number": workspace.revision_number,
        "parent_submission_hash": workspace.parent_submission_hash,
        "trigger_review_hash": workspace.trigger_review_hash,
        "submission_hash": review.submission_hash,
        "review_hash": review_hash,
        "attempt_id": attempt_id,
        "attempt_review_id": canonical_review_id,
        "verdict": review.verdict.value,
        "attempt_status": _attempt_status_for_verdict(review.verdict).value,
        "changed": changed,
        "next_action": _next_action_for_verdict(review.verdict),
        "claims_boundary": (
            "Revision projection appends one independently reviewed round to the same canonical Attempt. It preserves prior review history and "
            "does not transition the Problem, create an Outcome, assert funding, authorize deployment, or establish causal impact."
        ),
    }


def _attempt_status_for_verdict(verdict: ContributionVerdict) -> AttemptStatus:
    return {
        ContributionVerdict.ACCEPT: AttemptStatus.ACCEPTED,
        ContributionVerdict.REVISE: AttemptStatus.ACTIVE,
        ContributionVerdict.REJECT: AttemptStatus.REJECTED,
    }[verdict]


def _next_action_for_verdict(verdict: ContributionVerdict) -> str:
    return {
        ContributionVerdict.ACCEPT: "attempt-accepted-await-separate-problem-or-outcome-decision",
        ContributionVerdict.REVISE: "revision-required-create-explicit-revision-workspace",
        ContributionVerdict.REJECT: "attempt-rejected-preserve-record-no-outcome-inferred",
    }[verdict]


def _clean(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw).strip()
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out
