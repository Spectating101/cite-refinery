from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import uuid4


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def pilot_id(prefix: str) -> str:
    return f"{prefix}:{uuid4().hex[:12]}"


@dataclass(slots=True)
class ProductionRecord:
    """Cost/quality record for turning messy source material into a Problem Packet."""

    id: str
    problem_id: str
    curator_minutes: float
    source_count: int = 0
    correction_count: int = 0
    reframing_count: int = 0
    owner_agreement: float | None = None
    reviewer_score: float | None = None
    publishable: bool = False
    blocker_codes: list[str] = field(default_factory=list)
    notes: str = ""
    recorded_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class SolverSession:
    """Observation of whether an independent solver can understand and enter a problem."""

    id: str
    problem_id: str
    participant_id: str
    arm: str = "problem_packet"
    comprehension_score: float | None = None
    minutes_to_useful_edge: float | None = None
    coaching_minutes: float = 0.0
    selected_subproblem_id: str | None = None
    serious_attempt: bool = False
    abandoned: bool = False
    abandonment_reason: str = ""
    usefulness_rating: float | None = None
    notes: str = ""
    recorded_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class AdoptionRecord:
    """Tracks the prototype -> accepted -> pilot -> deployment -> outcome chain."""

    id: str
    problem_id: str
    attempt_id: str
    accepted_for_review: bool = False
    accepted_for_pilot: bool = False
    pilot_authorized: bool = False
    deployed: bool = False
    maintenance_owner_identified: bool = False
    outcome_observed: bool = False
    guardrail_violation: bool = False
    stop_reason: str = ""
    notes: str = ""
    recorded_at: str = field(default_factory=utcnow)


@dataclass(slots=True)
class ReuseRecord:
    """Measures net compounding after search/adaptation cost, not reuse count alone."""

    id: str
    source_problem_id: str
    target_problem_id: str
    asset_type: str
    asset_ref: str
    search_minutes: float
    adaptation_minutes: float
    estimated_rebuild_minutes: float
    successful: bool = True
    notes: str = ""
    recorded_at: str = field(default_factory=utcnow)

    @property
    def net_minutes_saved(self) -> float:
        if not self.successful:
            return -(self.search_minutes + self.adaptation_minutes)
        return self.estimated_rebuild_minutes - self.search_minutes - self.adaptation_minutes


@dataclass(slots=True)
class PilotReport:
    problem_records: int
    publishable_rate: float | None
    mean_curator_minutes: float | None
    mean_owner_agreement: float | None
    mean_reviewer_score: float | None
    solver_sessions: int
    mean_comprehension: float | None
    mean_coaching_minutes: float | None
    serious_attempt_rate: float | None
    adoption_records: int
    pilot_rate: float | None
    deployment_rate: float | None
    outcome_rate: float | None
    guardrail_violations: int
    reuse_records: int
    reuse_success_rate: float | None
    total_net_reuse_minutes_saved: float
    mean_net_reuse_minutes_saved: float | None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PilotLedger:
    """Small single-writer evidence ledger for Problem Commons V0.1 pilots.

    This intentionally stores operational measurements rather than claiming that
    pilot targets are validated benchmarks. Decision rules belong in the pilot
    protocol and can change without rewriting observed records.
    """

    schema = "problem-commons-pilot/v0.1"

    def __init__(self) -> None:
        self.production: list[ProductionRecord] = []
        self.solvers: list[SolverSession] = []
        self.adoption: list[AdoptionRecord] = []
        self.reuse: list[ReuseRecord] = []

    def record_production(self, *, problem_id: str, curator_minutes: float, **kwargs: Any) -> ProductionRecord:
        item = ProductionRecord(id=pilot_id("pprod"), problem_id=problem_id, curator_minutes=float(curator_minutes), **kwargs)
        self._validate_fraction(item.owner_agreement, "owner_agreement")
        self._validate_fraction(item.reviewer_score, "reviewer_score")
        self.production.append(item)
        return item

    def record_solver(self, *, problem_id: str, participant_id: str, **kwargs: Any) -> SolverSession:
        item = SolverSession(id=pilot_id("psolver"), problem_id=problem_id, participant_id=participant_id, **kwargs)
        self._validate_fraction(item.comprehension_score, "comprehension_score")
        self._validate_fraction(item.usefulness_rating, "usefulness_rating")
        self.solvers.append(item)
        return item

    def record_adoption(self, *, problem_id: str, attempt_id: str, **kwargs: Any) -> AdoptionRecord:
        item = AdoptionRecord(id=pilot_id("padopt"), problem_id=problem_id, attempt_id=attempt_id, **kwargs)
        if item.deployed and not item.pilot_authorized:
            raise ValueError("deployed adoption record requires pilot_authorized=true")
        if item.outcome_observed and not item.deployed:
            raise ValueError("outcome_observed requires deployed=true")
        self.adoption.append(item)
        return item

    def record_reuse(self, *, source_problem_id: str, target_problem_id: str, asset_type: str, asset_ref: str, search_minutes: float, adaptation_minutes: float, estimated_rebuild_minutes: float, **kwargs: Any) -> ReuseRecord:
        if source_problem_id == target_problem_id:
            raise ValueError("reuse must cross problem boundaries")
        item = ReuseRecord(
            id=pilot_id("preuse"),
            source_problem_id=source_problem_id,
            target_problem_id=target_problem_id,
            asset_type=asset_type,
            asset_ref=asset_ref,
            search_minutes=float(search_minutes),
            adaptation_minutes=float(adaptation_minutes),
            estimated_rebuild_minutes=float(estimated_rebuild_minutes),
            **kwargs,
        )
        if min(item.search_minutes, item.adaptation_minutes, item.estimated_rebuild_minutes) < 0:
            raise ValueError("reuse time values must be non-negative")
        self.reuse.append(item)
        return item

    def report(self) -> PilotReport:
        warnings: list[str] = []
        if len(self.production) < 5:
            warnings.append("problem-production sample is too small for a stable curation conclusion")
        if len(self.solvers) < 5:
            warnings.append("solver sample is too small for a stable comprehension/conversion conclusion")
        if not self.adoption:
            warnings.append("no adoption records; prototype-to-world conversion remains untested")
        if not self.reuse:
            warnings.append("no cross-problem reuse records; compounding remains untested")

        owners = [x.owner_agreement for x in self.production if x.owner_agreement is not None]
        reviewers = [x.reviewer_score for x in self.production if x.reviewer_score is not None]
        comprehension = [x.comprehension_score for x in self.solvers if x.comprehension_score is not None]
        net = [x.net_minutes_saved for x in self.reuse]

        return PilotReport(
            problem_records=len(self.production),
            publishable_rate=self._rate(sum(x.publishable for x in self.production), len(self.production)),
            mean_curator_minutes=self._mean([x.curator_minutes for x in self.production]),
            mean_owner_agreement=self._mean(owners),
            mean_reviewer_score=self._mean(reviewers),
            solver_sessions=len(self.solvers),
            mean_comprehension=self._mean(comprehension),
            mean_coaching_minutes=self._mean([x.coaching_minutes for x in self.solvers]),
            serious_attempt_rate=self._rate(sum(x.serious_attempt for x in self.solvers), len(self.solvers)),
            adoption_records=len(self.adoption),
            pilot_rate=self._rate(sum(x.accepted_for_pilot for x in self.adoption), len(self.adoption)),
            deployment_rate=self._rate(sum(x.deployed for x in self.adoption), len(self.adoption)),
            outcome_rate=self._rate(sum(x.outcome_observed for x in self.adoption), len(self.adoption)),
            guardrail_violations=sum(x.guardrail_violation for x in self.adoption),
            reuse_records=len(self.reuse),
            reuse_success_rate=self._rate(sum(x.successful for x in self.reuse), len(self.reuse)),
            total_net_reuse_minutes_saved=sum(net),
            mean_net_reuse_minutes_saved=self._mean(net),
            warnings=warnings,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "production": [asdict(x) for x in self.production],
            "solvers": [asdict(x) for x in self.solvers],
            "adoption": [asdict(x) for x in self.adoption],
            "reuse": [asdict(x) for x in self.reuse],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PilotLedger":
        if data.get("schema") != cls.schema:
            raise ValueError(f"unsupported pilot schema: {data.get('schema')}")
        ledger = cls()
        ledger.production = [ProductionRecord(**x) for x in data.get("production", [])]
        ledger.solvers = [SolverSession(**x) for x in data.get("solvers", [])]
        ledger.adoption = [AdoptionRecord(**x) for x in data.get("adoption", [])]
        ledger.reuse = [ReuseRecord(**x) for x in data.get("reuse", [])]
        return ledger

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(target)

    @classmethod
    def load(cls, path: str | Path) -> "PilotLedger":
        target = Path(path)
        if not target.exists():
            return cls()
        return cls.from_dict(json.loads(target.read_text(encoding="utf-8")))

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    @staticmethod
    def _mean(values: list[float]) -> float | None:
        return mean(values) if values else None

    @staticmethod
    def _validate_fraction(value: float | None, name: str) -> None:
        if value is not None and not 0 <= value <= 1:
            raise ValueError(f"{name} must be between 0 and 1")
