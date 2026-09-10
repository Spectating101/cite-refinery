from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .contribution_handoff import (
    SUBMISSION_SCHEMA,
    ArtifactRef,
    ContributionState,
    ParticipationBasis,
    canonical_hash,
    utcnow,
)


REVISION_WORKSPACE_SCHEMA = "problem-contribution-revision-workspace/v0.1"
REVISION_SUBMISSION_SCHEMA = "problem-contribution-revision-submission/v0.1"
REVIEW_SCHEMA = "problem-contribution-review/v0.1"


@dataclass(slots=True)
class RevisionValidation:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ContributionRevisionWorkspace:
    id: str
    root_workspace_id: str
    parent_workspace_id: str
    revision_number: int
    project_id: str
    problem_id: str
    subproblem_id: str
    contributor_ref: str
    parent_submission_hash: str
    trigger_review_id: str
    trigger_review_hash: str
    revision_requirements: list[str]
    base_work_hash: str
    participation_basis: ParticipationBasis
    participation_note: str = ""
    method_scope: str = ""
    produced_outputs: list[str] = field(default_factory=list)
    artifacts: list[ArtifactRef] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    notes: str = ""
    state: ContributionState = ContributionState.ACTIVE
    created_at: str = field(default_factory=utcnow)
    updated_at: str = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        self.state = ContributionState(self.state)
        self.participation_basis = ParticipationBasis(self.participation_basis)
        self.revision_requirements = _clean(self.revision_requirements)
        self.produced_outputs = _clean(self.produced_outputs)
        self.blockers = _clean(self.blockers)
        self.artifacts = [item if isinstance(item, ArtifactRef) else ArtifactRef(**item) for item in self.artifacts]

    @classmethod
    def from_revise(
        cls,
        parent_submission: dict[str, Any],
        trigger_review: dict[str, Any],
        *,
        workspace_id: str | None = None,
    ) -> "ContributionRevisionWorkspace":
        errors = validate_revision_trigger(parent_submission, trigger_review)
        if errors:
            raise ValueError("invalid revision trigger: " + "; ".join(errors))

        root_workspace_id = str(parent_submission.get("root_workspace_id") or parent_submission["workspace_id"])
        prior_revision = int(parent_submission.get("revision_number") or 0)
        revision_number = prior_revision + 1
        suffix = _root_suffix(root_workspace_id)
        artifacts = [ArtifactRef(**dict(item)) for item in parent_submission["artifacts"]]
        return cls(
            id=workspace_id or f"contributionrev:{suffix}:r{revision_number}",
            root_workspace_id=root_workspace_id,
            parent_workspace_id=str(parent_submission["workspace_id"]),
            revision_number=revision_number,
            project_id=str(parent_submission["project_id"]),
            problem_id=str(parent_submission["problem_id"]),
            subproblem_id=str(parent_submission["subproblem_id"]),
            contributor_ref=str(parent_submission["contributor_ref"]),
            parent_submission_hash=canonical_hash(parent_submission),
            trigger_review_id=str(trigger_review["id"]),
            trigger_review_hash=canonical_hash(trigger_review),
            revision_requirements=list(trigger_review.get("revision_requirements") or []),
            base_work_hash=submission_work_hash(parent_submission),
            participation_basis=ParticipationBasis(str(parent_submission["participation_basis"])),
            participation_note=str(parent_submission.get("participation_note") or ""),
            method_scope=str(parent_submission.get("method_scope") or ""),
            produced_outputs=list(parent_submission.get("produced_outputs") or []),
            artifacts=artifacts,
            blockers=list(parent_submission.get("blockers") or []),
            notes=str(parent_submission.get("notes") or ""),
        )

    def validation(
        self,
        *,
        parent_submission: dict[str, Any] | None = None,
        trigger_review: dict[str, Any] | None = None,
        require_submittable: bool = False,
    ) -> RevisionValidation:
        errors: list[str] = []
        warnings: list[str] = []

        if not self.id.startswith("contributionrev:") or not self.id.split(":", 1)[1].strip():
            errors.append("revision workspace id must begin with contributionrev:")
        if not self.root_workspace_id.startswith("contribution:"):
            errors.append("root_workspace_id must identify the original contribution workspace")
        if not self.parent_workspace_id.strip():
            errors.append("parent_workspace_id is required")
        if self.revision_number < 1:
            errors.append("revision_number must be at least 1")
        for key in ("project_id", "problem_id", "subproblem_id", "contributor_ref", "parent_submission_hash", "trigger_review_id", "trigger_review_hash", "base_work_hash"):
            if not str(getattr(self, key)).strip():
                errors.append(f"{key} is required")
        if not self.revision_requirements:
            errors.append("revision workspace requires at least one retained revision requirement")
        if self.state not in {ContributionState.ACTIVE, ContributionState.SUBMITTED, ContributionState.WITHDRAWN}:
            errors.append("revision workspace must be active, submitted, or withdrawn")
        if self.state in {ContributionState.ACTIVE, ContributionState.SUBMITTED} and self.participation_basis == ParticipationBasis.NOT_ESTABLISHED:
            errors.append("revision work requires the established participation basis from the parent submission")

        if (parent_submission is None) != (trigger_review is None):
            errors.append("parent_submission and trigger_review must be supplied together for lineage validation")
        if parent_submission is not None and trigger_review is not None:
            errors.extend(validate_revision_trigger(parent_submission, trigger_review))
            expected_root = str(parent_submission.get("root_workspace_id") or parent_submission.get("workspace_id") or "")
            expected_revision = int(parent_submission.get("revision_number") or 0) + 1
            bindings = {
                "root_workspace_id": expected_root,
                "parent_workspace_id": str(parent_submission.get("workspace_id") or ""),
                "project_id": str(parent_submission.get("project_id") or ""),
                "problem_id": str(parent_submission.get("problem_id") or ""),
                "subproblem_id": str(parent_submission.get("subproblem_id") or ""),
                "contributor_ref": str(parent_submission.get("contributor_ref") or ""),
                "parent_submission_hash": canonical_hash(parent_submission),
                "trigger_review_id": str(trigger_review.get("id") or ""),
                "trigger_review_hash": canonical_hash(trigger_review),
                "base_work_hash": submission_work_hash(parent_submission),
            }
            for key, expected in bindings.items():
                if getattr(self, key) != expected:
                    errors.append(f"revision workspace {key} does not match its exact parent/review lineage")
            if self.revision_number != expected_revision:
                errors.append("revision workspace revision_number does not continue the parent revision sequence")
            expected_requirements = _clean(list(trigger_review.get("revision_requirements") or []))
            if self.revision_requirements != expected_requirements:
                errors.append("revision requirements do not match the triggering review")

        complete_work = require_submittable or self.state == ContributionState.SUBMITTED
        if complete_work:
            if self.state == ContributionState.WITHDRAWN:
                errors.append("withdrawn revision workspace cannot be submitted")
            if not self.method_scope.strip():
                errors.append("revision submission requires a method/scope statement")
            if not self.produced_outputs:
                errors.append("revision submission requires at least one produced output")
            if not self.artifacts:
                errors.append("revision submission requires at least one material artifact reference")
            if self.current_work_hash() == self.base_work_hash:
                errors.append("revision must change contributor work before resubmission")

        seen_artifacts: set[str] = set()
        for artifact in self.artifacts:
            errors.extend(artifact.validation_errors())
            if artifact.id in seen_artifacts:
                errors.append(f"duplicate artifact id: {artifact.id}")
            seen_artifacts.add(artifact.id)

        warnings.append("revision lineage preserves the prior submission and triggering review by exact hash; it does not supersede or erase either record")
        warnings.append("revision review evaluates the revised contribution only; it does not establish problem resolution, funding, deployment authority, or real-world outcome")
        return RevisionValidation(valid=not errors, errors=_clean(errors), warnings=_clean(warnings))

    def set_work(
        self,
        *,
        method_scope: str | None = None,
        produced_outputs: list[str] | None = None,
        blockers: list[str] | None = None,
        notes: str | None = None,
    ) -> None:
        self._require_active()
        if method_scope is not None:
            self.method_scope = method_scope.strip()
        if produced_outputs is not None:
            self.produced_outputs = _clean(produced_outputs)
        if blockers is not None:
            self.blockers = _clean(blockers)
        if notes is not None:
            self.notes = notes.strip()
        self.updated_at = utcnow()

    def add_artifact(
        self,
        *,
        title: str,
        kind: str,
        locator: str,
        sha256_value: str = "",
        notes: str = "",
        artifact_id: str | None = None,
    ) -> ArtifactRef:
        self._require_active()
        artifact = ArtifactRef(
            id=artifact_id or f"artifact:{uuid4().hex[:12]}",
            title=title.strip(),
            kind=kind.strip(),
            locator=locator.strip(),
            sha256=sha256_value.strip(),
            notes=notes.strip(),
        )
        errors = artifact.validation_errors()
        if errors:
            raise ValueError("invalid artifact: " + "; ".join(errors))
        if any(item.id == artifact.id for item in self.artifacts):
            raise ValueError(f"duplicate artifact id: {artifact.id}")
        self.artifacts.append(artifact)
        self.updated_at = utcnow()
        return artifact

    def remove_artifact(self, artifact_id: str) -> ArtifactRef:
        self._require_active()
        for index, artifact in enumerate(self.artifacts):
            if artifact.id == artifact_id:
                removed = self.artifacts.pop(index)
                self.updated_at = utcnow()
                return removed
        raise ValueError(f"unknown artifact id: {artifact_id}")

    def submit(
        self,
        *,
        parent_submission: dict[str, Any],
        trigger_review: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_active()
        report = self.validation(
            parent_submission=parent_submission,
            trigger_review=trigger_review,
            require_submittable=True,
        )
        if not report.valid:
            raise ValueError("revision is not submittable: " + "; ".join(report.errors))
        self.state = ContributionState.SUBMITTED
        self.updated_at = utcnow()
        return self.submission_snapshot()

    def withdraw(self, *, reason: str) -> None:
        self._require_active()
        if not reason.strip():
            raise ValueError("withdrawal reason is required")
        self.notes = (self.notes + "\n" if self.notes else "") + f"Withdrawal: {reason.strip()}"
        self.state = ContributionState.WITHDRAWN
        self.updated_at = utcnow()

    def current_work_hash(self) -> str:
        return submission_work_hash(self.to_dict())

    def submission_snapshot(self) -> dict[str, Any]:
        if self.state != ContributionState.SUBMITTED:
            raise ValueError("revision submission snapshot requires submitted state")
        payload = {
            "schema": REVISION_SUBMISSION_SCHEMA,
            "workspace_id": self.id,
            "root_workspace_id": self.root_workspace_id,
            "parent_workspace_id": self.parent_workspace_id,
            "revision_number": self.revision_number,
            "project_id": self.project_id,
            "problem_id": self.problem_id,
            "subproblem_id": self.subproblem_id,
            "contributor_ref": self.contributor_ref,
            "parent_submission_hash": self.parent_submission_hash,
            "trigger_review_id": self.trigger_review_id,
            "trigger_review_hash": self.trigger_review_hash,
            "revision_requirements": list(self.revision_requirements),
            "base_work_hash": self.base_work_hash,
            "work_hash": self.current_work_hash(),
            "workspace_hash": "",
            "participation_basis": self.participation_basis.value,
            "participation_note": self.participation_note,
            "method_scope": self.method_scope,
            "produced_outputs": list(self.produced_outputs),
            "artifacts": [asdict(item) for item in self.artifacts],
            "blockers": list(self.blockers),
            "notes": self.notes,
            "submitted_at": self.updated_at,
            "claims_boundary": (
                "Revision submission preserves and responds to a prior reviewed submission. It does not erase prior review history, "
                "establish correctness, resolve the Problem, create an Outcome, establish funding, or grant deployment authority."
            ),
        }
        payload["workspace_hash"] = canonical_hash(self.to_dict())
        return payload

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = REVISION_WORKSPACE_SCHEMA
        data["state"] = self.state.value
        data["participation_basis"] = self.participation_basis.value
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ContributionRevisionWorkspace":
        data = dict(raw)
        schema = data.pop("schema", None)
        if schema != REVISION_WORKSPACE_SCHEMA:
            raise ValueError(f"unsupported contribution revision workspace schema: {schema}")
        return cls(**data)

    @classmethod
    def load(cls, path: str | Path) -> "ContributionRevisionWorkspace":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def dump(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def _require_active(self) -> None:
        if self.state != ContributionState.ACTIVE:
            raise ValueError(f"revision workspace must be active to edit; current state is {self.state.value}")


def validate_revision_trigger(parent_submission: dict[str, Any], trigger_review: dict[str, Any]) -> list[str]:
    errors = _validate_parent_submission_shape(parent_submission)
    if not isinstance(trigger_review, dict):
        return _clean(errors + ["trigger review must be an object"])
    if trigger_review.get("schema") != REVIEW_SCHEMA:
        errors.append("trigger review must use the contribution review schema")
    required = (
        "id", "submission_hash", "workspace_id", "project_id", "problem_id", "subproblem_id",
        "contributor_ref", "reviewer_ref", "verdict", "summary",
    )
    for key in required:
        if not isinstance(trigger_review.get(key), str) or not str(trigger_review.get(key)).strip():
            errors.append(f"trigger review {key} is required")
    if trigger_review.get("verdict") != "revise":
        errors.append("revision workspace requires a revise verdict")
    requirements = trigger_review.get("revision_requirements")
    if not isinstance(requirements, list) or not _clean([str(item) for item in requirements if isinstance(item, str)]):
        errors.append("triggering revise review requires at least one revision requirement")
    if trigger_review.get("submission_hash") != canonical_hash(parent_submission):
        errors.append("trigger review is not bound to the exact parent submission")
    for key in ("workspace_id", "project_id", "problem_id", "subproblem_id", "contributor_ref"):
        if trigger_review.get(key) != parent_submission.get(key):
            errors.append(f"trigger review {key} does not match parent submission")
    if str(trigger_review.get("reviewer_ref") or "").strip() == str(parent_submission.get("contributor_ref") or "").strip():
        errors.append("trigger review is not independent from the contributor")
    return _clean(errors)


def validate_revision_submission(
    submission: dict[str, Any],
    *,
    workspace: ContributionRevisionWorkspace | None = None,
    parent_submission: dict[str, Any] | None = None,
    trigger_review: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(submission, dict):
        return ["revision submission must be an object"]
    if submission.get("schema") != REVISION_SUBMISSION_SCHEMA:
        errors.append("unsupported contribution revision submission schema")
    required_text = (
        "workspace_id", "root_workspace_id", "parent_workspace_id", "project_id", "problem_id", "subproblem_id",
        "contributor_ref", "parent_submission_hash", "trigger_review_id", "trigger_review_hash", "base_work_hash",
        "work_hash", "workspace_hash", "participation_basis", "method_scope", "submitted_at", "claims_boundary",
    )
    for key in required_text:
        if not isinstance(submission.get(key), str) or not str(submission.get(key)).strip():
            errors.append(f"revision submission {key} is required")
    if not str(submission.get("workspace_id") or "").startswith("contributionrev:"):
        errors.append("revision submission workspace_id must begin with contributionrev:")
    if not str(submission.get("root_workspace_id") or "").startswith("contribution:"):
        errors.append("revision submission root_workspace_id must identify the original contribution workspace")
    if not isinstance(submission.get("revision_number"), int) or int(submission.get("revision_number") or 0) < 1:
        errors.append("revision submission revision_number must be an integer of at least 1")
    for key in ("revision_requirements", "produced_outputs", "blockers"):
        value = submission.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            errors.append(f"revision submission {key} must be a list of text")
    if isinstance(submission.get("revision_requirements"), list) and not _clean(submission["revision_requirements"]):
        errors.append("revision submission requires at least one revision requirement")
    if not isinstance(submission.get("artifacts"), list) or not submission.get("artifacts"):
        errors.append("revision submission requires at least one material artifact")
    else:
        seen: set[str] = set()
        for raw in submission["artifacts"]:
            if not isinstance(raw, dict):
                errors.append("revision submission artifacts must be objects")
                continue
            try:
                artifact = ArtifactRef(**raw)
            except TypeError as exc:
                errors.append(f"invalid revision submission artifact: {exc}")
                continue
            errors.extend(artifact.validation_errors())
            if artifact.id in seen:
                errors.append(f"duplicate revision submission artifact id: {artifact.id}")
            seen.add(artifact.id)
    if submission.get("work_hash") != submission_work_hash(submission):
        errors.append("revision submission work_hash does not match its work payload")
    if submission.get("base_work_hash") == submission.get("work_hash"):
        errors.append("revision submission does not change contributor work from its parent")

    if (parent_submission is None) != (trigger_review is None):
        errors.append("parent_submission and trigger_review must be supplied together for lineage validation")
    if parent_submission is not None and trigger_review is not None:
        errors.extend(validate_revision_trigger(parent_submission, trigger_review))
        expected_root = str(parent_submission.get("root_workspace_id") or parent_submission.get("workspace_id") or "")
        expected_revision = int(parent_submission.get("revision_number") or 0) + 1
        bindings = {
            "root_workspace_id": expected_root,
            "parent_workspace_id": str(parent_submission.get("workspace_id") or ""),
            "revision_number": expected_revision,
            "project_id": str(parent_submission.get("project_id") or ""),
            "problem_id": str(parent_submission.get("problem_id") or ""),
            "subproblem_id": str(parent_submission.get("subproblem_id") or ""),
            "contributor_ref": str(parent_submission.get("contributor_ref") or ""),
            "parent_submission_hash": canonical_hash(parent_submission),
            "trigger_review_id": str(trigger_review.get("id") or ""),
            "trigger_review_hash": canonical_hash(trigger_review),
            "base_work_hash": submission_work_hash(parent_submission),
        }
        for key, expected in bindings.items():
            if submission.get(key) != expected:
                errors.append(f"revision submission {key} does not match its exact parent/review lineage")
        expected_requirements = _clean(list(trigger_review.get("revision_requirements") or []))
        if submission.get("revision_requirements") != expected_requirements:
            errors.append("revision submission requirements do not match the triggering review")

    if workspace is not None:
        report = workspace.validation(
            parent_submission=parent_submission,
            trigger_review=trigger_review,
            require_submittable=True,
        )
        if not report.valid:
            errors.extend(f"workspace: {item}" for item in report.errors)
        if workspace.state != ContributionState.SUBMITTED:
            errors.append("canonical revision projection requires a submitted revision workspace")
        else:
            expected = workspace.submission_snapshot()
            if canonical_hash(expected) != canonical_hash(submission):
                errors.append("revision submission does not match the retained submitted revision workspace")
    return _clean(errors)


def submission_work_hash(value: dict[str, Any]) -> str:
    payload = {
        "participation_basis": str(value.get("participation_basis") or ""),
        "participation_note": str(value.get("participation_note") or ""),
        "method_scope": str(value.get("method_scope") or ""),
        "produced_outputs": list(value.get("produced_outputs") or []),
        "artifacts": [dict(item) for item in value.get("artifacts") or [] if isinstance(item, dict)],
        "blockers": list(value.get("blockers") or []),
        "notes": str(value.get("notes") or ""),
    }
    return canonical_hash(payload)


def _validate_parent_submission_shape(submission: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(submission, dict):
        return ["parent submission must be an object"]
    schema = submission.get("schema")
    if schema not in {SUBMISSION_SCHEMA, REVISION_SUBMISSION_SCHEMA}:
        errors.append("parent submission must be an original or revision contribution submission")
    required_text = (
        "workspace_id", "project_id", "problem_id", "subproblem_id", "contributor_ref",
        "participation_basis", "method_scope", "submitted_at",
    )
    for key in required_text:
        if not isinstance(submission.get(key), str) or not str(submission.get(key)).strip():
            errors.append(f"parent submission {key} is required")
    if not isinstance(submission.get("produced_outputs"), list) or not submission.get("produced_outputs"):
        errors.append("parent submission requires at least one produced output")
    if not isinstance(submission.get("artifacts"), list) or not submission.get("artifacts"):
        errors.append("parent submission requires at least one material artifact")
    if schema == REVISION_SUBMISSION_SCHEMA:
        if not isinstance(submission.get("revision_number"), int) or int(submission.get("revision_number") or 0) < 1:
            errors.append("parent revision submission revision_number is invalid")
        if not str(submission.get("root_workspace_id") or "").startswith("contribution:"):
            errors.append("parent revision submission root_workspace_id is invalid")
    return _clean(errors)


def _root_suffix(root_workspace_id: str) -> str:
    if not root_workspace_id.startswith("contribution:") or not root_workspace_id.split(":", 1)[1].strip():
        raise ValueError("root contribution workspace id is invalid")
    return root_workspace_id.split(":", 1)[1]


def _clean(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw).strip()
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out
