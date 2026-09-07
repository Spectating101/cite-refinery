from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import json
from pathlib import Path
from typing import Any, Iterable


class ProblemStage(StrEnum):
    OBSERVE = "observe"
    MEASURE = "measure"
    EXPLAIN = "explain"
    DESIGN = "design"
    BUILD = "build"
    TEST = "test"
    DEPLOY = "deploy"
    MONITOR = "monitor"
    GENERALIZE = "generalize"


STAGE_ORDER = [
    ProblemStage.OBSERVE,
    ProblemStage.MEASURE,
    ProblemStage.EXPLAIN,
    ProblemStage.DESIGN,
    ProblemStage.BUILD,
    ProblemStage.TEST,
    ProblemStage.DEPLOY,
    ProblemStage.MONITOR,
    ProblemStage.GENERALIZE,
]


class UncertaintyLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FRONTIER = "frontier"


class MethodMaturity(StrEnum):
    ESTABLISHED = "established"
    ADAPTABLE = "adaptable"
    EXPERIMENTAL = "experimental"
    NOVEL = "novel"


class AuthorityLevel(StrEnum):
    NONE = "none"
    REVIEW = "review"
    QUALIFIED = "qualified"
    INSTITUTIONAL = "institutional"


class WorkMode(StrEnum):
    KNOWN_PRACTICE = "known-practice"
    ADAPTIVE_PRACTICE = "adaptive-practice"
    EMPIRICAL_INQUIRY = "empirical-inquiry"
    RESEARCH_FRONTIER = "research-frontier"


SYSTEM_NOCTURNAL = "nocturnal"
SYSTEM_CITE = "cite"
SYSTEM_REFINERY = "refinery"
SYSTEM_PUBLIC_GOOD = "public-good"
SYSTEM_PROBLEM_COMMONS = "problem-commons"
SYSTEM_EXTERNAL_AUTHORITY = "external-authority"

KNOWN_SYSTEMS = {
    SYSTEM_NOCTURNAL,
    SYSTEM_CITE,
    SYSTEM_REFINERY,
    SYSTEM_PUBLIC_GOOD,
    SYSTEM_PROBLEM_COMMONS,
    SYSTEM_EXTERNAL_AUTHORITY,
}


DEFAULT_STAGE_ROUTES: dict[ProblemStage, tuple[str, ...]] = {
    ProblemStage.OBSERVE: (SYSTEM_NOCTURNAL, SYSTEM_PROBLEM_COMMONS),
    ProblemStage.MEASURE: (SYSTEM_CITE, SYSTEM_REFINERY),
    ProblemStage.EXPLAIN: (SYSTEM_CITE,),
    ProblemStage.DESIGN: (SYSTEM_PUBLIC_GOOD, SYSTEM_CITE, SYSTEM_REFINERY),
    ProblemStage.BUILD: (SYSTEM_REFINERY,),
    ProblemStage.TEST: (SYSTEM_CITE, SYSTEM_REFINERY, SYSTEM_PUBLIC_GOOD),
    ProblemStage.DEPLOY: (SYSTEM_PUBLIC_GOOD, SYSTEM_EXTERNAL_AUTHORITY),
    ProblemStage.MONITOR: (SYSTEM_NOCTURNAL, SYSTEM_CITE),
    ProblemStage.GENERALIZE: (SYSTEM_REFINERY, SYSTEM_CITE),
}


@dataclass(slots=True)
class StageProfile:
    problem_id: str
    subproblem_id: str
    stage: ProblemStage
    question: str
    epistemic_type: str
    uncertainty: UncertaintyLevel
    method_maturity: MethodMaturity
    expected_outputs: list[str] = field(default_factory=list)
    evaluation_method: str = ""
    authority_level: AuthorityLevel = AuthorityLevel.NONE
    authority_requirement: str = ""
    required_credentials: list[str] = field(default_factory=list)
    system_routes: list[str] = field(default_factory=list)
    reuse_target: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        self.stage = ProblemStage(self.stage)
        self.uncertainty = UncertaintyLevel(self.uncertainty)
        self.method_maturity = MethodMaturity(self.method_maturity)
        self.authority_level = AuthorityLevel(self.authority_level)
        self.system_routes = _normalized_routes(self.system_routes or DEFAULT_STAGE_ROUTES[self.stage])
        self.expected_outputs = _clean(self.expected_outputs)
        self.required_credentials = _clean(self.required_credentials)

    @property
    def id(self) -> str:
        return f"stage:{self.problem_id}:{self.subproblem_id}"

    @property
    def work_mode(self) -> WorkMode:
        if self.uncertainty == UncertaintyLevel.FRONTIER or self.method_maturity == MethodMaturity.NOVEL:
            return WorkMode.RESEARCH_FRONTIER
        if self.stage in {ProblemStage.MEASURE, ProblemStage.EXPLAIN, ProblemStage.TEST} and self.uncertainty in {UncertaintyLevel.HIGH, UncertaintyLevel.FRONTIER}:
            return WorkMode.EMPIRICAL_INQUIRY
        if self.method_maturity in {MethodMaturity.ADAPTABLE, MethodMaturity.EXPERIMENTAL} or self.uncertainty == UncertaintyLevel.MEDIUM:
            return WorkMode.ADAPTIVE_PRACTICE
        return WorkMode.KNOWN_PRACTICE

    @property
    def requires_professional_authority(self) -> bool:
        return self.authority_level in {AuthorityLevel.QUALIFIED, AuthorityLevel.INSTITUTIONAL}

    def validation(self) -> "StageValidation":
        errors: list[str] = []
        warnings: list[str] = []

        if not self.problem_id.startswith("problem:"):
            errors.append("problem_id must begin with problem:")
        if not self.subproblem_id.strip():
            errors.append("subproblem_id is required")
        if not self.question.strip():
            errors.append("question is required")
        if not self.epistemic_type.strip():
            errors.append("epistemic_type is required")
        if not self.expected_outputs:
            errors.append("at least one expected output is required")
        if not self.evaluation_method.strip():
            errors.append("evaluation_method is required")

        if self.stage == ProblemStage.DEPLOY:
            if self.authority_level != AuthorityLevel.INSTITUTIONAL:
                errors.append("deploy stage requires institutional authority")
            if not self.authority_requirement.strip():
                errors.append("deploy stage requires an explicit authority requirement")
            if SYSTEM_EXTERNAL_AUTHORITY not in self.system_routes:
                errors.append("deploy stage must route to external-authority")

        if self.requires_professional_authority and not self.authority_requirement.strip():
            errors.append("qualified/institutional work requires authority_requirement")

        if self.method_maturity == MethodMaturity.NOVEL and self.uncertainty == UncertaintyLevel.LOW:
            warnings.append("novel method with low uncertainty is unusual; verify the classification")

        if self.stage == ProblemStage.GENERALIZE:
            if SYSTEM_REFINERY not in self.system_routes:
                errors.append("generalize stage must route to Refinery")
            if not self.reuse_target.strip():
                warnings.append("generalize stage has no reuse_target; compounding value may be lost")

        if self.stage == ProblemStage.MONITOR and SYSTEM_NOCTURNAL not in self.system_routes:
            warnings.append("monitor stage does not route to Nocturnal")

        if self.stage == ProblemStage.EXPLAIN and self.uncertainty in {UncertaintyLevel.HIGH, UncertaintyLevel.FRONTIER} and SYSTEM_CITE not in self.system_routes:
            warnings.append("high-uncertainty explanation work does not route to Cite")

        if self.stage == ProblemStage.BUILD and SYSTEM_REFINERY not in self.system_routes:
            warnings.append("build stage does not route to Refinery")

        return StageValidation(valid=not errors, errors=errors, warnings=warnings)

    def route_plan(self) -> list[dict[str, str]]:
        roles = {
            SYSTEM_NOCTURNAL: "observe longitudinal reality, recurrence, corrections, and later outcomes",
            SYSTEM_CITE: "establish evidence, prior knowledge, uncertainty, and empirical support",
            SYSTEM_REFINERY: "find, build, execute, validate, and preserve reusable capability",
            SYSTEM_PUBLIC_GOOD: "reason about bottlenecks, constraints, intervention classes, and authority boundaries",
            SYSTEM_PROBLEM_COMMONS: "preserve the living problem, decomposition, attempts, and contribution state",
            SYSTEM_EXTERNAL_AUTHORITY: "authorize or execute consequential real-world action",
        }
        return [{"system": system, "role": roles[system]} for system in self.system_routes]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["id"] = self.id
        data["stage"] = self.stage.value
        data["uncertainty"] = self.uncertainty.value
        data["method_maturity"] = self.method_maturity.value
        data["authority_level"] = self.authority_level.value
        data["work_mode"] = self.work_mode.value
        data["requires_professional_authority"] = self.requires_professional_authority
        data["route_plan"] = self.route_plan()
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "StageProfile":
        data = dict(raw)
        for derived in ("id", "work_mode", "requires_professional_authority", "route_plan"):
            data.pop(derived, None)
        return cls(**data)


@dataclass(slots=True)
class StageValidation:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class StageRegistry:
    """Versioned extension layer for contribution-stage semantics.

    Profiles are keyed to existing Problem Commons subproblem IDs. The extension
    deliberately does not grant authority or mutate Problem Packets by itself.
    """

    schema = "problem-stages/v0.1"

    def __init__(self) -> None:
        self.profiles: dict[tuple[str, str], StageProfile] = {}

    def upsert(self, profile: StageProfile, *, validate: bool = True) -> StageProfile:
        report = profile.validation()
        if validate and not report.valid:
            raise ValueError("invalid stage profile: " + "; ".join(report.errors))
        self.profiles[(profile.problem_id, profile.subproblem_id)] = profile
        return profile

    def get(self, problem_id: str, subproblem_id: str) -> StageProfile:
        try:
            return self.profiles[(problem_id, subproblem_id)]
        except KeyError as exc:
            raise KeyError(f"unknown stage profile: {problem_id}/{subproblem_id}") from exc

    def list(self, *, problem_id: str | None = None, stage: ProblemStage | None = None) -> list[StageProfile]:
        rows = list(self.profiles.values())
        if problem_id is not None:
            rows = [row for row in rows if row.problem_id == problem_id]
        if stage is not None:
            rows = [row for row in rows if row.stage == ProblemStage(stage)]
        order = {item: index for index, item in enumerate(STAGE_ORDER)}
        return sorted(rows, key=lambda row: (row.problem_id, order[row.stage], row.subproblem_id))

    def coverage(self, problem_id: str) -> dict[str, Any]:
        rows = self.list(problem_id=problem_id)
        counts = {stage.value: 0 for stage in STAGE_ORDER}
        for row in rows:
            counts[row.stage.value] += 1
        return {
            "problem_id": problem_id,
            "profiles": len(rows),
            "stages_present": [stage for stage, count in counts.items() if count],
            "stage_counts": counts,
            "work_modes": _counts(row.work_mode.value for row in rows),
            "systems": _counts(system for row in rows for system in row.system_routes),
            "authority_gated": sum(row.requires_professional_authority for row in rows),
        }

    def validate_all(self) -> dict[str, Any]:
        rows = []
        valid = True
        for profile in self.list():
            report = profile.validation()
            rows.append({"problem_id": profile.problem_id, "subproblem_id": profile.subproblem_id, "valid": report.valid, "errors": report.errors, "warnings": report.warnings})
            valid = valid and report.valid
        return {"valid": valid, "profiles": rows}

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, "profiles": [profile.to_dict() for profile in self.list()]}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StageRegistry":
        if payload.get("schema") != cls.schema:
            raise ValueError(f"unsupported stage schema: {payload.get('schema')}")
        registry = cls()
        for raw in payload.get("profiles", []):
            registry.upsert(StageProfile.from_dict(raw), validate=False)
        return registry

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> "StageRegistry":
        target = Path(path)
        if not target.exists():
            return cls()
        return cls.from_dict(json.loads(target.read_text(encoding="utf-8")))


def _clean(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in values if item and item.strip()))


def _normalized_routes(values: Iterable[str]) -> list[str]:
    rows = _clean(item.lower() for item in values)
    unknown = sorted(set(rows) - KNOWN_SYSTEMS)
    if unknown:
        raise ValueError("unknown system routes: " + ", ".join(unknown))
    return rows


def _counts(values: Iterable[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items()))
