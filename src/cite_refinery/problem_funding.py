from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import json
from pathlib import Path
from typing import Any

from .problem_commons import ProblemPacket
from .problem_stages import ProblemStage, StageProfile, WorkMode


class FundingStatus(StrEnum):
    UNKNOWN = "unknown"
    NOT_REQUIRED = "not-required"
    UNFUNDED = "unfunded"
    SEEKING = "seeking"
    PARTIAL = "partial"
    FUNDED = "funded"
    IN_KIND = "in-kind"


class CompensationMode(StrEnum):
    VOLUNTEER = "volunteer"
    STIPEND = "stipend"
    GRANT = "grant"
    PAID_PROJECT = "paid-project"
    PRIZE = "prize"
    EMPLOYMENT = "employment"
    IN_KIND = "in-kind"
    MIXED = "mixed"
    UNSPECIFIED = "unspecified"


class FundingReadiness(StrEnum):
    UNKNOWN = "unknown"
    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    NOT_REQUIRED = "not-required"


@dataclass(slots=True)
class FundingNeed:
    problem_id: str
    subproblem_id: str
    stage: ProblemStage
    status: FundingStatus = FundingStatus.UNKNOWN
    compensation_mode: CompensationMode = CompensationMode.UNSPECIFIED
    volunteer_compatible: bool = False
    currency: str = "TWD"
    minimum_amount: float | None = None
    target_amount: float | None = None
    committed_amount: float = 0.0
    eligible_instruments: list[str] = field(default_factory=list)
    in_kind_needs: list[str] = field(default_factory=list)
    restrictions: list[str] = field(default_factory=list)
    expense_categories: list[str] = field(default_factory=list)
    funding_source_refs: list[str] = field(default_factory=list)
    implementation_budget_owner: str = ""
    maintenance_budget_owner: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        self.stage = ProblemStage(self.stage)
        self.status = FundingStatus(self.status)
        self.compensation_mode = CompensationMode(self.compensation_mode)
        self.currency = self.currency.strip().upper() or "TWD"
        self.eligible_instruments = _clean(self.eligible_instruments)
        self.in_kind_needs = _clean(self.in_kind_needs)
        self.restrictions = _clean(self.restrictions)
        self.expense_categories = _clean(self.expense_categories)
        self.funding_source_refs = _clean(self.funding_source_refs)

    @property
    def id(self) -> str:
        return f"funding:{self.problem_id}:{self.subproblem_id}"

    @property
    def funding_gap(self) -> float | None:
        if self.target_amount is None:
            return None
        return max(float(self.target_amount) - float(self.committed_amount), 0.0)

    @property
    def minimum_gap(self) -> float | None:
        if self.minimum_amount is None:
            return None
        return max(float(self.minimum_amount) - float(self.committed_amount), 0.0)

    @property
    def readiness(self) -> FundingReadiness:
        if self.status == FundingStatus.NOT_REQUIRED:
            return FundingReadiness.NOT_REQUIRED
        if self.status == FundingStatus.UNKNOWN:
            return FundingReadiness.UNKNOWN
        if self.volunteer_compatible and (self.minimum_amount in {None, 0, 0.0}):
            return FundingReadiness.READY
        if self.minimum_amount is not None and self.committed_amount >= self.minimum_amount:
            return FundingReadiness.READY
        if self.status in {FundingStatus.FUNDED, FundingStatus.IN_KIND} and self.minimum_amount is None:
            return FundingReadiness.READY
        if self.committed_amount > 0 or self.status == FundingStatus.PARTIAL:
            return FundingReadiness.PARTIAL
        if not self.volunteer_compatible and self.status in {FundingStatus.UNFUNDED, FundingStatus.SEEKING}:
            return FundingReadiness.BLOCKED
        return FundingReadiness.UNKNOWN

    def validation(self) -> "FundingValidation":
        errors: list[str] = []
        warnings: list[str] = []

        if not self.problem_id.startswith("problem:"):
            errors.append("problem_id must begin with problem:")
        if not self.subproblem_id.strip():
            errors.append("subproblem_id is required")
        if self.minimum_amount is not None and self.minimum_amount < 0:
            errors.append("minimum_amount cannot be negative")
        if self.target_amount is not None and self.target_amount < 0:
            errors.append("target_amount cannot be negative")
        if self.committed_amount < 0:
            errors.append("committed_amount cannot be negative")
        if self.minimum_amount is not None and self.target_amount is not None and self.minimum_amount > self.target_amount:
            errors.append("minimum_amount cannot exceed target_amount")
        if self.target_amount is not None and self.committed_amount > self.target_amount:
            warnings.append("committed_amount exceeds target_amount; verify whether the target should be revised")
        if self.status == FundingStatus.FUNDED and self.minimum_amount is not None and self.committed_amount < self.minimum_amount:
            errors.append("funded status requires committed_amount to meet minimum_amount")
        if not self.volunteer_compatible and self.compensation_mode == CompensationMode.VOLUNTEER:
            errors.append("volunteer compensation mode conflicts with volunteer_compatible=false")
        if self.status == FundingStatus.NOT_REQUIRED and any(
            value not in {None, 0, 0.0} for value in (self.minimum_amount, self.target_amount)
        ):
            warnings.append("not-required funding plan carries a non-zero budget estimate")
        if self.stage in {ProblemStage.DEPLOY, ProblemStage.MONITOR} and not self.implementation_budget_owner:
            warnings.append("deployment/monitoring work has no implementation budget owner")
        if self.stage == ProblemStage.MONITOR and not self.maintenance_budget_owner:
            warnings.append("monitoring work has no maintenance budget owner")
        if self.readiness == FundingReadiness.UNKNOWN:
            warnings.append("funding readiness is unknown; do not assume unpaid labor is available")

        return FundingValidation(valid=not errors, errors=errors, warnings=warnings)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["id"] = self.id
        data["stage"] = self.stage.value
        data["status"] = self.status.value
        data["compensation_mode"] = self.compensation_mode.value
        data["funding_gap"] = self.funding_gap
        data["minimum_gap"] = self.minimum_gap
        data["readiness"] = self.readiness.value
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "FundingNeed":
        data = dict(raw)
        for derived in ("id", "funding_gap", "minimum_gap", "readiness"):
            data.pop(derived, None)
        return cls(**data)


@dataclass(slots=True)
class FundingValidation:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProjectBrief:
    problem_id: str
    subproblem_id: str
    title: str
    problem_title: str
    description: str
    stage: str
    work_mode: str
    effort: str
    skill_tags: list[str]
    required_credentials: list[str]
    expected_outputs: list[str]
    authority_requirement: str
    compensation_mode: str
    volunteer_compatible: bool
    funding_status: str
    funding_readiness: str
    currency: str
    minimum_amount: float | None
    target_amount: float | None
    committed_amount: float
    funding_gap: float | None
    eligible_instruments: list[str]
    in_kind_needs: list[str]
    expense_categories: list[str]
    funding_restrictions: list[str]
    implementation_budget_owner: str
    maintenance_budget_owner: str
    warnings: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"project:{self.problem_id}:{self.subproblem_id}"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, **asdict(self)}


class FundingRegistry:
    """Minimal funding extension for Problem Commons contributions.

    This layer records resource requirements and compensation expectations. It
    does not move money, award grants, infer eligibility, or grant authority.
    """

    schema = "problem-funding/v0.1"

    def __init__(self) -> None:
        self.needs: dict[tuple[str, str], FundingNeed] = {}

    def upsert(self, need: FundingNeed, *, validate: bool = True) -> FundingNeed:
        report = need.validation()
        if validate and not report.valid:
            raise ValueError("invalid funding need: " + "; ".join(report.errors))
        self.needs[(need.problem_id, need.subproblem_id)] = need
        return need

    def get(self, problem_id: str, subproblem_id: str) -> FundingNeed:
        try:
            return self.needs[(problem_id, subproblem_id)]
        except KeyError as exc:
            raise KeyError(f"unknown funding need: {problem_id}/{subproblem_id}") from exc

    def list(self, *, problem_id: str | None = None) -> list[FundingNeed]:
        rows = list(self.needs.values())
        if problem_id is not None:
            rows = [row for row in rows if row.problem_id == problem_id]
        return sorted(rows, key=lambda row: (row.problem_id, row.stage.value, row.subproblem_id))

    def coverage(self, problem_id: str) -> dict[str, Any]:
        rows = self.list(problem_id=problem_id)
        readiness_counts = {item.value: 0 for item in FundingReadiness}
        total_target = 0.0
        total_committed = 0.0
        unknown_target_count = 0
        for row in rows:
            readiness_counts[row.readiness.value] += 1
            total_committed += row.committed_amount
            if row.target_amount is None:
                unknown_target_count += 1
            else:
                total_target += row.target_amount
        return {
            "problem_id": problem_id,
            "plans": len(rows),
            "readiness": readiness_counts,
            "known_target_total": round(total_target, 2),
            "committed_total": round(total_committed, 2),
            "unknown_target_count": unknown_target_count,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, "needs": [row.to_dict() for row in self.list()]}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "FundingRegistry":
        registry = cls()
        schema = raw.get("schema")
        if schema not in {None, cls.schema}:
            raise ValueError(f"unsupported funding schema: {schema}")
        for item in raw.get("needs", []):
            registry.upsert(FundingNeed.from_dict(item))
        return registry

    @classmethod
    def load(cls, path: str | Path) -> "FundingRegistry":
        p = Path(path)
        if not p.exists():
            return cls()
        return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))

    def dump(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_project_brief(
    packet: ProblemPacket,
    subproblem_id: str,
    *,
    stage_profile: StageProfile | None = None,
    funding_need: FundingNeed | None = None,
) -> ProjectBrief:
    subproblem = next((item for item in packet.subproblems if item.id == subproblem_id), None)
    if subproblem is None:
        raise KeyError(f"unknown subproblem: {packet.id}/{subproblem_id}")

    warnings: list[str] = []
    if stage_profile is not None:
        if stage_profile.problem_id != packet.id or stage_profile.subproblem_id != subproblem_id:
            raise ValueError("stage profile does not align to requested problem/subproblem")
        stage = stage_profile.stage.value
        work_mode = stage_profile.work_mode.value
        authority_requirement = stage_profile.authority_requirement
    else:
        stage = "unclassified"
        work_mode = "unclassified"
        authority_requirement = ""
        warnings.append("stage profile missing; work mode and authority routing are unclassified")

    if funding_need is not None:
        if funding_need.problem_id != packet.id or funding_need.subproblem_id != subproblem_id:
            raise ValueError("funding need does not align to requested problem/subproblem")
        if stage_profile is not None and funding_need.stage != stage_profile.stage:
            warnings.append("funding stage does not match contribution stage")
        funding_report = funding_need.validation()
        warnings.extend(funding_report.warnings)
        compensation_mode = funding_need.compensation_mode.value
        volunteer_compatible = funding_need.volunteer_compatible
        funding_status = funding_need.status.value
        funding_readiness = funding_need.readiness.value
        currency = funding_need.currency
        minimum_amount = funding_need.minimum_amount
        target_amount = funding_need.target_amount
        committed_amount = funding_need.committed_amount
        funding_gap = funding_need.funding_gap
        eligible_instruments = list(funding_need.eligible_instruments)
        in_kind_needs = list(funding_need.in_kind_needs)
        expense_categories = list(funding_need.expense_categories)
        restrictions = list(funding_need.restrictions)
        implementation_owner = funding_need.implementation_budget_owner
        maintenance_owner = funding_need.maintenance_budget_owner
    else:
        compensation_mode = CompensationMode.UNSPECIFIED.value
        volunteer_compatible = False
        funding_status = FundingStatus.UNKNOWN.value
        funding_readiness = FundingReadiness.UNKNOWN.value
        currency = "TWD"
        minimum_amount = None
        target_amount = None
        committed_amount = 0.0
        funding_gap = None
        eligible_instruments = []
        in_kind_needs = []
        expense_categories = []
        restrictions = []
        implementation_owner = ""
        maintenance_owner = ""
        warnings.append("funding plan missing; do not assume the contribution will be performed for free")

    return ProjectBrief(
        problem_id=packet.id,
        subproblem_id=subproblem_id,
        title=subproblem.title,
        problem_title=packet.title,
        description=subproblem.description,
        stage=stage,
        work_mode=work_mode,
        effort=subproblem.effort,
        skill_tags=list(subproblem.skill_tags),
        required_credentials=list(subproblem.required_credentials),
        expected_outputs=list(subproblem.expected_outputs),
        authority_requirement=authority_requirement,
        compensation_mode=compensation_mode,
        volunteer_compatible=volunteer_compatible,
        funding_status=funding_status,
        funding_readiness=funding_readiness,
        currency=currency,
        minimum_amount=minimum_amount,
        target_amount=target_amount,
        committed_amount=committed_amount,
        funding_gap=funding_gap,
        eligible_instruments=eligible_instruments,
        in_kind_needs=in_kind_needs,
        expense_categories=expense_categories,
        funding_restrictions=restrictions,
        implementation_budget_owner=implementation_owner,
        maintenance_budget_owner=maintenance_owner,
        warnings=warnings,
    )


def _clean(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw).strip()
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            out.append(value)
    return out
