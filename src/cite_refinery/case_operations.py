from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import uuid4

from .pilot import PilotLedger, ProductionRecord
from .problem_case import ProblemCaseWorkspace
from .problem_commons import ProblemCommons, ProblemStatus, StewardReview, object_id, utcnow
from .problem_governance import GovernanceRegistry
from .problem_stages import StageRegistry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _op_id() -> str:
    return f"pop:{uuid4().hex[:12]}"


def _sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(slots=True)
class OperationReceipt:
    id: str
    problem_id: str
    action: str
    actor: str
    summary: str
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    problem_sha256: str = ""
    pilot_sha256: str = ""
    created_at: str = field(default_factory=_now)


class OperationLedger:
    """Append-only receipts for explicit cross-registry operator actions.

    This ledger is an audit trail, not a source of domain truth. Problem state
    remains in Problem Commons; pilot measurements remain in PilotLedger.
    """

    schema = "problem-operations/v0.1"

    def __init__(self) -> None:
        self.receipts: list[OperationReceipt] = []

    def append(self, receipt: OperationReceipt) -> OperationReceipt:
        self.receipts.append(receipt)
        return receipt

    def for_problem(self, problem_id: str) -> list[OperationReceipt]:
        return [item for item in self.receipts if item.problem_id == problem_id]

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, "receipts": [asdict(item) for item in self.receipts]}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "OperationLedger":
        if payload.get("schema") != cls.schema:
            raise ValueError(f"unsupported operations schema: {payload.get('schema')}")
        ledger = cls()
        ledger.receipts = [OperationReceipt(**item) for item in payload.get("receipts", [])]
        return ledger

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(target)
        return target

    @classmethod
    def load(cls, path: str | Path) -> "OperationLedger":
        target = Path(path)
        if not target.exists():
            return cls()
        return cls.from_dict(json.loads(target.read_text(encoding="utf-8")))


@dataclass(slots=True)
class ReviewIngestResult:
    problem_id: str
    audience: str
    score: float
    record_id: str
    receipt_id: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OperationsAssessment:
    problem_id: str
    status: str
    phase: str
    eligible_for_verification: bool
    eligible_for_open: bool
    owner_agreement: float | None
    reviewer_score: float | None
    solver_sessions: int
    mean_solver_comprehension: float | None
    serious_attempt_rate: float | None
    stage_coverage_rate: float | None
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CaseOperations:
    """Explicit mutation service for running a Problem Commons pilot.

    CaseWorkspace stays read-only. This service performs only explicit,
    actor-attributed writes to Problem Commons/PilotLedger and emits an
    append-only receipt after each mutation. It never creates external
    authority, test success, or outcome evidence on behalf of a user.
    """

    def __init__(
        self,
        *,
        commons: ProblemCommons | None = None,
        stages: StageRegistry | None = None,
        governance: GovernanceRegistry | None = None,
        pilot: PilotLedger | None = None,
        operations: OperationLedger | None = None,
    ) -> None:
        self.commons = commons or ProblemCommons()
        self.stages = stages or StageRegistry()
        self.governance = governance or GovernanceRegistry()
        self.pilot = pilot or PilotLedger()
        self.operations = operations or OperationLedger()

    @property
    def workspace(self) -> ProblemCaseWorkspace:
        return ProblemCaseWorkspace(
            commons=self.commons,
            stages=self.stages,
            governance=self.governance,
            pilot=self.pilot,
        )

    @classmethod
    def load(
        cls,
        *,
        commons_path: str | Path,
        stages_path: str | Path,
        governance_path: str | Path,
        pilot_path: str | Path,
        operations_path: str | Path,
    ) -> "CaseOperations":
        return cls(
            commons=ProblemCommons.load(commons_path),
            stages=StageRegistry.load(stages_path),
            governance=GovernanceRegistry.load(governance_path),
            pilot=PilotLedger.load(pilot_path),
            operations=OperationLedger.load(operations_path),
        )

    def save(self, *, commons_path: str | Path, pilot_path: str | Path, operations_path: str | Path) -> None:
        # V0.1 is intentionally single-writer. Each individual store uses a
        # temp-file replace; the operation receipt captures the resulting state.
        self.commons.save(commons_path)
        self.pilot.save(pilot_path)
        self.operations.save(operations_path)

    def start_production(
        self,
        problem_id: str,
        *,
        actor: str,
        curator_minutes: float,
        source_count: int = 0,
        correction_count: int = 0,
        reframing_count: int = 0,
        publishable: bool = False,
        blocker_codes: list[str] | None = None,
        notes: str = "",
    ) -> ProductionRecord:
        self.commons.get(problem_id)
        record = self.pilot.record_production(
            problem_id=problem_id,
            curator_minutes=curator_minutes,
            source_count=source_count,
            correction_count=correction_count,
            reframing_count=reframing_count,
            publishable=publishable,
            blocker_codes=list(blocker_codes or []),
            notes=notes,
        )
        self._receipt(
            problem_id,
            action="production-start",
            actor=actor,
            summary="Recorded curation cost/quality baseline for a candidate problem.",
            outputs={"production_record_id": record.id},
        )
        return record

    def ingest_review_pack(
        self,
        pack: dict[str, Any],
        *,
        participant_id: str,
        coaching_minutes: float = 0.0,
        serious_attempt: bool | None = None,
        usefulness_rating: float | None = None,
        selected_subproblem_id: str | None = None,
        abandoned: bool | None = None,
        abandonment_reason: str | None = None,
        notes: str = "",
    ) -> ReviewIngestResult:
        if pack.get("schema") != "problem-review-pack/v0.1":
            raise ValueError(f"unsupported review-pack schema: {pack.get('schema')}")
        audience = str(pack.get("audience", "")).strip().lower()
        if audience not in {"owner", "reviewer", "solver"}:
            raise ValueError("review-pack audience must be owner, reviewer, or solver")
        problem_id = str(pack.get("problem_id", ""))
        problem = self.commons.get(problem_id)
        embedded_problem_id = str((pack.get("problem") or {}).get("id", ""))
        if embedded_problem_id and embedded_problem_id != problem_id:
            raise ValueError("review-pack embedded problem does not match problem_id")

        rubric = pack.get("rubric") or {}
        items = list(rubric.get("items") or [])
        response = pack.get("response") or {}
        scores = list(response.get("item_scores") or [])
        if not items or len(scores) != len(items):
            raise ValueError("review response must contain one score for every rubric item")
        normalized_scores: list[int] = []
        for score in scores:
            if isinstance(score, bool):
                normalized_scores.append(int(score))
            elif isinstance(score, int) and score in {0, 1}:
                normalized_scores.append(score)
            else:
                raise ValueError("review item_scores must be completed with only 0 or 1")
        score_value = sum(normalized_scores) / len(normalized_scores)
        material_errors = [str(item) for item in response.get("material_errors", []) if str(item).strip()]
        disagreements = [str(item) for item in response.get("disagreement_notes", []) if str(item).strip()]
        combined_notes = _join_notes(notes, disagreements, material_errors)

        if audience in {"owner", "reviewer"}:
            production = self._latest_production(problem_id)
            if production is None:
                raise ValueError("owner/reviewer feedback requires a production record; run production-start first")
            if audience == "owner":
                production.owner_agreement = score_value
            else:
                production.reviewer_score = score_value
                production.correction_count += len(material_errors)
            if bool(response.get("reframe_required")):
                production.reframing_count += 1
            production.notes = _append_note(production.notes, combined_notes)
            record_id = production.id
        else:
            selected = selected_subproblem_id or response.get("selected_subproblem_id")
            if selected is not None:
                selected = str(selected)
                if selected not in {item.id for item in problem.subproblems}:
                    raise ValueError(f"solver selected unknown subproblem: {selected}")
            serious = bool(response.get("serious_attempt")) if serious_attempt is None else bool(serious_attempt)
            if serious and not selected:
                raise ValueError("serious solver attempt requires selected_subproblem_id")
            abandoned_value = bool(response.get("abandoned")) if abandoned is None else bool(abandoned)
            reason = abandonment_reason if abandonment_reason is not None else str(response.get("abandonment_reason") or "")
            usefulness = usefulness_rating if usefulness_rating is not None else response.get("usefulness_rating")
            if usefulness is not None:
                usefulness = float(usefulness)
            solver_record = self.pilot.record_solver(
                problem_id=problem_id,
                participant_id=participant_id,
                arm=str(response.get("arm") or "problem_packet"),
                comprehension_score=score_value,
                minutes_to_useful_edge=_optional_float(response.get("minutes_to_useful_edge")),
                coaching_minutes=float(coaching_minutes),
                selected_subproblem_id=selected,
                serious_attempt=serious,
                abandoned=abandoned_value,
                abandonment_reason=reason,
                usefulness_rating=usefulness,
                notes=_append_note(str(response.get("observer_notes") or ""), combined_notes),
            )
            record_id = solver_record.id

        receipt = self._receipt(
            problem_id,
            action=f"review-ingest:{audience}",
            actor=participant_id,
            summary=f"Ingested completed {audience} pilot rubric without changing problem lifecycle automatically.",
            inputs={"rubric": rubric.get("name"), "items": len(items)},
            outputs={"score": score_value, "record_id": record_id},
        )
        return ReviewIngestResult(problem_id, audience, score_value, record_id, receipt.id, disagreements + material_errors)

    def assess(self, problem_id: str, *, policy: dict[str, Any]) -> OperationsAssessment:
        if policy.get("schema") != "problem-operations-policy/v0.1":
            raise ValueError(f"unsupported operations policy: {policy.get('schema')}")
        problem = self.commons.get(problem_id)
        snapshot = self.workspace.snapshot(problem_id)
        production = self._latest_production(problem_id)
        owner_min = float(policy.get("owner_agreement_min", 0.8))
        reviewer_min = float(policy.get("reviewer_score_min", 0.8))
        solver_min = float(policy.get("solver_comprehension_min", 0.8))
        require_owner = bool(policy.get("require_owner_for_verification", True))
        require_reviewer = bool(policy.get("require_reviewer_for_verification", True))

        owner = production.owner_agreement if production else None
        reviewer = production.reviewer_score if production else None
        solver_rows = [item for item in self.pilot.solvers if item.problem_id == problem_id]
        solver_scores = [item.comprehension_score for item in solver_rows if item.comprehension_score is not None]
        mean_solver = mean(solver_scores) if solver_scores else None
        serious_rate = (sum(item.serious_attempt for item in solver_rows) / len(solver_rows)) if solver_rows else None

        blockers: list[str] = []
        warnings: list[str] = list(snapshot.warnings)
        next_actions: list[str] = []

        publishability = problem.publishability(require_decomposition=False)
        open_readiness = problem.publishability(require_decomposition=True)
        if production is None:
            blockers.append("missing production/curation measurement record")
            next_actions.append("record curator effort and source/correction counts with production-start")
        else:
            if require_owner and (owner is None or owner < owner_min):
                blockers.append(f"owner agreement below pilot threshold {owner_min:.2f}" if owner is not None else "owner review not recorded")
                next_actions.append("obtain independent problem-owner review and correct material disagreements")
            if require_reviewer and (reviewer is None or reviewer < reviewer_min):
                blockers.append(f"domain reviewer score below pilot threshold {reviewer_min:.2f}" if reviewer is not None else "domain reviewer review not recorded")
                next_actions.append("obtain independent domain review and revise unsupported framing")
            if production.blocker_codes:
                blockers.extend(f"production blocker: {item}" for item in production.blocker_codes)

        if not publishability.publishable:
            blockers.extend(f"publishability: {item}" for item in publishability.missing)
            next_actions.append("complete canonical Problem Packet publication requirements")

        eligible_verification = not blockers and publishability.publishable
        eligible_open = eligible_verification and open_readiness.publishable and problem.status == ProblemStatus.VERIFIED

        if problem.status in {ProblemStatus.CANDIDATE, ProblemStatus.RESEARCHING, ProblemStatus.REFRAMED}:
            phase = "eligible_for_verification" if eligible_verification else "curation"
            if eligible_verification:
                next_actions.append("a curator may explicitly record stewardship review and transition to VERIFIED")
        elif problem.status == ProblemStatus.VERIFIED:
            phase = "eligible_for_open" if eligible_open else "verified"
            if not open_readiness.publishable:
                next_actions.append("decompose the verified problem before opening it to solvers")
            elif eligible_open:
                next_actions.append("a curator may explicitly open the verified packet")
        elif problem.status in {ProblemStatus.OPEN, ProblemStatus.PARTIALLY_RESOLVED}:
            if not solver_rows:
                phase = "solver_validation"
                next_actions.append("run independent solver comprehension sessions without curator coaching")
            elif mean_solver is not None and mean_solver < solver_min:
                phase = "solver_validation"
                blockers.append(f"mean solver comprehension below pilot threshold {solver_min:.2f}")
                next_actions.append("improve decomposition/packet clarity before scaling solver recruitment")
            elif serious_rate is not None and serious_rate == 0:
                phase = "solver_conversion"
                warnings.append("solver comprehension is recorded but no serious attempt converted")
                next_actions.append("investigate why understandable contribution paths are not converting into serious attempts")
            else:
                phase = "active_problem"
        else:
            phase = problem.status.value

        if snapshot.stage_coverage_rate is not None and snapshot.stage_coverage_rate < 1:
            warnings.append("not all contribution paths have experimental stage profiles; stage semantics remain incomplete")

        return OperationsAssessment(
            problem_id=problem_id,
            status=problem.status.value,
            phase=phase,
            eligible_for_verification=eligible_verification,
            eligible_for_open=eligible_open,
            owner_agreement=owner,
            reviewer_score=reviewer,
            solver_sessions=len(solver_rows),
            mean_solver_comprehension=mean_solver,
            serious_attempt_rate=serious_rate,
            stage_coverage_rate=snapshot.stage_coverage_rate,
            blockers=_dedupe(blockers),
            warnings=_dedupe(warnings),
            next_actions=_dedupe(next_actions + snapshot.next_actions),
        )

    def promote(
        self,
        problem_id: str,
        *,
        target: str,
        actor: str,
        reason: str,
        policy: dict[str, Any],
    ) -> OperationReceipt:
        problem = self.commons.get(problem_id)
        assessment = self.assess(problem_id, policy=policy)
        normalized = target.strip().lower()
        if normalized == "verified":
            if problem.status not in {ProblemStatus.RESEARCHING, ProblemStatus.REFRAMED}:
                raise ValueError("verification promotion requires a researching or reframed problem")
            if not assessment.eligible_for_verification:
                raise ValueError("problem is not eligible for verification: " + "; ".join(assessment.blockers))
            checklist = {
                "publishability": True,
                "owner_review": assessment.owner_agreement is not None,
                "domain_review": assessment.reviewer_score is not None,
            }
            problem.steward_reviews.append(
                StewardReview(
                    id=object_id("psteward"), problem_id=problem_id, reviewer=actor,
                    verdict="accept", notes=reason, checklist=checklist,
                )
            )
            problem.transition(ProblemStatus.VERIFIED, actor=actor, reason=reason)
        elif normalized == "open":
            if problem.status != ProblemStatus.VERIFIED:
                raise ValueError("open promotion requires a VERIFIED problem")
            if not assessment.eligible_for_open:
                detail = assessment.blockers or problem.publishability(require_decomposition=True).missing
                raise ValueError("problem is not eligible to open: " + "; ".join(detail))
            problem.transition(ProblemStatus.OPEN, actor=actor, reason=reason)
        else:
            raise ValueError("promotion target must be verified or open")

        return self._receipt(
            problem_id,
            action=f"promote:{normalized}",
            actor=actor,
            summary=f"Explicit curator promotion to {normalized}; no external authority was created.",
            inputs={"reason": reason},
            outputs={"status": problem.status.value},
        )

    def queue(self, *, policy: dict[str, Any], public_only: bool = False) -> list[dict[str, Any]]:
        rows = self.commons.list_public() if public_only else list(self.commons.problems.values())
        result = []
        for problem in rows:
            assessment = self.assess(problem.id, policy=policy)
            result.append({
                "problem_id": problem.id,
                "title": problem.title,
                "status": problem.status.value,
                "phase": assessment.phase,
                "blockers": len(assessment.blockers),
                "owner_agreement": assessment.owner_agreement,
                "reviewer_score": assessment.reviewer_score,
                "solver_sessions": assessment.solver_sessions,
                "next_action": assessment.next_actions[0] if assessment.next_actions else None,
            })
        return sorted(result, key=lambda item: (item["blockers"], item["phase"], item["title"].lower()))

    def _latest_production(self, problem_id: str) -> ProductionRecord | None:
        rows = [item for item in self.pilot.production if item.problem_id == problem_id]
        return rows[-1] if rows else None

    def _receipt(
        self,
        problem_id: str,
        *,
        action: str,
        actor: str,
        summary: str,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
    ) -> OperationReceipt:
        problem = self.commons.get(problem_id)
        receipt = OperationReceipt(
            id=_op_id(), problem_id=problem_id, action=action, actor=actor, summary=summary,
            inputs=dict(inputs or {}), outputs=dict(outputs or {}),
            problem_sha256=_sha256(problem.to_dict()), pilot_sha256=_sha256(self.pilot.to_dict()),
        )
        self.operations.append(receipt)
        return receipt


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _append_note(existing: str, addition: str) -> str:
    addition = addition.strip()
    if not addition:
        return existing
    if not existing.strip():
        return addition
    return existing.rstrip() + "\n" + addition


def _join_notes(prefix: str, disagreements: list[str], errors: list[str]) -> str:
    parts = [prefix.strip()] if prefix.strip() else []
    if disagreements:
        parts.append("Disagreements: " + " | ".join(disagreements))
    if errors:
        parts.append("Material errors: " + " | ".join(errors))
    return "\n".join(parts)


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in values if item))
