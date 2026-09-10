from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


WORKSPACE_SCHEMA = "problem-contribution-workspace/v0.1"
SUBMISSION_SCHEMA = "problem-contribution-submission/v0.1"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + sha256(payload.encode("utf-8")).hexdigest()


class ContributionState(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUBMITTED = "submitted"
    WITHDRAWN = "withdrawn"


class ParticipationBasis(StrEnum):
    NOT_ESTABLISHED = "not-established"
    COMPENSATED = "compensated"
    VOLUNTEER = "volunteer"
    ACADEMIC_CREDIT = "academic-credit"
    IN_KIND = "in-kind"
    MIXED = "mixed"


@dataclass(slots=True)
class ArtifactRef:
    id: str
    title: str
    kind: str
    locator: str
    sha256: str = ""
    notes: str = ""

    def validation_errors(self) -> list[str]:
        errors: list[str] = []
        if not self.id.strip():
            errors.append("artifact id is required")
        if not self.title.strip():
            errors.append("artifact title is required")
        if not self.kind.strip():
            errors.append("artifact kind is required")
        if not self.locator.strip():
            errors.append("artifact locator is required")
        if self.sha256:
            digest = self.sha256.removeprefix("sha256:")
            if len(digest) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in digest):
                errors.append("artifact sha256 must contain 64 hexadecimal characters")
        return errors


@dataclass(slots=True)
class ContributionValidation:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ContributorWorkspace:
    id: str
    project_id: str
    problem_id: str
    subproblem_id: str
    contributor_ref: str
    project_brief: dict[str, Any]
    project_brief_hash: str
    state: ContributionState = ContributionState.DRAFT
    participation_basis: ParticipationBasis = ParticipationBasis.NOT_ESTABLISHED
    participation_note: str = ""
    method_scope: str = ""
    produced_outputs: list[str] = field(default_factory=list)
    artifacts: list[ArtifactRef] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    notes: str = ""
    created_at: str = field(default_factory=utcnow)
    updated_at: str = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        self.state = ContributionState(self.state)
        self.participation_basis = ParticipationBasis(self.participation_basis)
        self.project_brief = dict(self.project_brief)
        self.produced_outputs = _clean(self.produced_outputs)
        self.blockers = _clean(self.blockers)
        self.artifacts = [item if isinstance(item, ArtifactRef) else ArtifactRef(**item) for item in self.artifacts]

    @classmethod
    def from_project_brief(
        cls,
        brief: dict[str, Any],
        *,
        contributor_ref: str,
        workspace_id: str | None = None,
    ) -> "ContributorWorkspace":
        brief = dict(brief)
        errors = validate_project_brief(brief)
        if errors:
            raise ValueError("invalid project brief: " + "; ".join(errors))
        if not contributor_ref.strip():
            raise ValueError("contributor_ref is required")
        return cls(
            id=workspace_id or f"contribution:{uuid4().hex[:12]}",
            project_id=str(brief["id"]),
            problem_id=str(brief["problem_id"]),
            subproblem_id=str(brief["subproblem_id"]),
            contributor_ref=contributor_ref.strip(),
            project_brief=brief,
            project_brief_hash=canonical_hash(brief),
        )

    def validation(self, *, require_submittable: bool = False) -> ContributionValidation:
        errors: list[str] = []
        warnings: list[str] = []
        errors.extend(validate_project_brief(self.project_brief))

        if not self.id.startswith("contribution:") or not self.id.split(":", 1)[1].strip():
            errors.append("workspace id must begin with contribution:")
        if self.project_id != self.project_brief.get("id"):
            errors.append("workspace project_id does not match embedded Project Brief")
        if self.problem_id != self.project_brief.get("problem_id"):
            errors.append("workspace problem_id does not match embedded Project Brief")
        if self.subproblem_id != self.project_brief.get("subproblem_id"):
            errors.append("workspace subproblem_id does not match embedded Project Brief")
        if self.project_brief_hash != canonical_hash(self.project_brief):
            errors.append("embedded Project Brief no longer matches the issued brief hash")
        if not self.contributor_ref.strip():
            errors.append("contributor_ref is required")

        complete_work = require_submittable or self.state == ContributionState.SUBMITTED
        if self.state in {ContributionState.ACTIVE, ContributionState.SUBMITTED}:
            if self.participation_basis == ParticipationBasis.NOT_ESTABLISHED:
                errors.append("active/submitted work requires an explicit participation basis")
            errors.extend(self._participation_errors())
        if complete_work:
            if self.state == ContributionState.DRAFT:
                errors.append("draft workspace cannot be submitted")
            if not self.method_scope.strip():
                errors.append("submission requires a method/scope statement")
            if not self.produced_outputs:
                errors.append("submission requires at least one produced output")
            if not self.artifacts:
                errors.append("submission requires at least one material artifact reference")

        seen_artifacts: set[str] = set()
        for artifact in self.artifacts:
            errors.extend(artifact.validation_errors())
            if artifact.id in seen_artifacts:
                errors.append(f"duplicate artifact id: {artifact.id}")
            seen_artifacts.add(artifact.id)

        expected = _clean(list(self.project_brief.get("expected_outputs") or []))
        if expected and self.produced_outputs:
            warnings.append("produced_outputs are contributor claims until independent review; expected-output satisfaction is not inferred")
        if self.blockers:
            warnings.append("submission carries unresolved blockers; reviewer must determine whether the work is still useful")
        if self.project_brief.get("funding_readiness") in {"unknown", "blocked", "partial"}:
            warnings.append("Project Brief funding is not fully ready; workspace does not infer unpaid labor or funding commitment")

        return ContributionValidation(valid=not errors, errors=_clean(errors), warnings=_clean(warnings))

    def _participation_errors(self) -> list[str]:
        brief = self.project_brief
        basis = self.participation_basis
        errors: list[str] = []
        if basis == ParticipationBasis.VOLUNTEER and not bool(brief.get("volunteer_compatible")):
            errors.append("Project Brief does not permit volunteer participation")
        if basis == ParticipationBasis.COMPENSATED and brief.get("funding_readiness") != "ready":
            errors.append("compensated participation requires Project Brief funding_readiness=ready")
        if basis in {ParticipationBasis.ACADEMIC_CREDIT, ParticipationBasis.IN_KIND, ParticipationBasis.MIXED} and not self.participation_note.strip():
            errors.append(f"{basis.value} participation requires a note describing the established arrangement")
        return errors

    def activate(self, *, basis: ParticipationBasis | str, participation_note: str = "") -> None:
        if self.state not in {ContributionState.DRAFT, ContributionState.ACTIVE}:
            raise ValueError(f"cannot activate workspace from state {self.state.value}")
        previous = (self.state, self.participation_basis, self.participation_note)
        self.state = ContributionState.ACTIVE
        self.participation_basis = ParticipationBasis(basis)
        self.participation_note = participation_note.strip()
        report = self.validation()
        if not report.valid:
            self.state, self.participation_basis, self.participation_note = previous
            raise ValueError("cannot activate contribution: " + "; ".join(report.errors))
        self.updated_at = utcnow()

    def set_work(
        self,
        *,
        method_scope: str | None = None,
        produced_outputs: list[str] | None = None,
        blockers: list[str] | None = None,
        notes: str | None = None,
    ) -> None:
        if self.state == ContributionState.SUBMITTED:
            raise ValueError("submitted workspace is immutable; revise through the later review/revision workflow")
        if self.state == ContributionState.WITHDRAWN:
            raise ValueError("withdrawn workspace cannot be edited")
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
        if self.state not in {ContributionState.DRAFT, ContributionState.ACTIVE}:
            raise ValueError("artifacts can only be added before submission/withdrawal")
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

    def submit(self) -> dict[str, Any]:
        if self.state != ContributionState.ACTIVE:
            raise ValueError("only an active workspace can be submitted")
        report = self.validation(require_submittable=True)
        if not report.valid:
            raise ValueError("contribution is not submittable: " + "; ".join(report.errors))
        self.state = ContributionState.SUBMITTED
        self.updated_at = utcnow()
        return self.submission_snapshot()

    def withdraw(self, *, reason: str) -> None:
        if self.state == ContributionState.SUBMITTED:
            raise ValueError("submitted work must be handled through review; it cannot be silently withdrawn")
        if self.state == ContributionState.WITHDRAWN:
            raise ValueError("workspace is already withdrawn")
        if not reason.strip():
            raise ValueError("withdrawal reason is required")
        self.notes = (self.notes + "\n" if self.notes else "") + f"Withdrawal: {reason.strip()}"
        self.state = ContributionState.WITHDRAWN
        self.updated_at = utcnow()

    def submission_snapshot(self) -> dict[str, Any]:
        if self.state != ContributionState.SUBMITTED:
            raise ValueError("submission snapshot requires submitted state")
        payload = {
            "schema": SUBMISSION_SCHEMA,
            "workspace_id": self.id,
            "project_id": self.project_id,
            "problem_id": self.problem_id,
            "subproblem_id": self.subproblem_id,
            "contributor_ref": self.contributor_ref,
            "project_brief_hash": self.project_brief_hash,
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
                "Submission records contributor-supplied work for independent review. It does not establish correctness, "
                "acceptance, problem resolution, funding, external authority, deployment permission, or outcome attribution."
            ),
        }
        payload["workspace_hash"] = canonical_hash(self.to_dict())
        return payload

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema"] = WORKSPACE_SCHEMA
        data["state"] = self.state.value
        data["participation_basis"] = self.participation_basis.value
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ContributorWorkspace":
        data = dict(raw)
        schema = data.pop("schema", None)
        if schema not in {None, WORKSPACE_SCHEMA}:
            raise ValueError(f"unsupported contribution workspace schema: {schema}")
        return cls(**data)

    @classmethod
    def load(cls, path: str | Path) -> "ContributorWorkspace":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def dump(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_project_brief(brief: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_text = ["id", "problem_id", "subproblem_id", "title", "description", "funding_readiness", "compensation_mode"]
    for key in required_text:
        if not isinstance(brief.get(key), str) or not str(brief.get(key)).strip():
            errors.append(f"Project Brief {key} is required")
    if isinstance(brief.get("problem_id"), str) and not brief["problem_id"].startswith("problem:"):
        errors.append("Project Brief problem_id must begin with problem:")
    if all(isinstance(brief.get(key), str) and brief.get(key) for key in ("id", "problem_id", "subproblem_id")):
        expected_id = f"project:{brief['problem_id']}:{brief['subproblem_id']}"
        if brief["id"] != expected_id:
            errors.append("Project Brief id does not match problem_id/subproblem_id")
    for key in ("expected_outputs", "required_credentials", "warnings"):
        value = brief.get(key, [])
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            errors.append(f"Project Brief {key} must be a list of text")
    if not isinstance(brief.get("volunteer_compatible"), bool):
        errors.append("Project Brief volunteer_compatible must be boolean")
    if "authority_requirement" in brief and not isinstance(brief.get("authority_requirement"), str):
        errors.append("Project Brief authority_requirement must be text")
    return _clean(errors)


def hash_file(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _clean(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw).strip()
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out
