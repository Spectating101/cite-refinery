from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

from .pilot import PilotLedger
from .problem_commons import AttemptStatus, ProblemCommons, ProblemStatus
from .problem_governance import GovernanceRegistry
from .problem_stage_governance import align_stage_and_governance
from .problem_stages import ProblemStage, StageRegistry


@dataclass(slots=True)
class CaseValidation:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CaseSnapshot:
    problem_id: str
    title: str
    status: str
    public: bool
    publishable: bool
    completeness: float
    subproblems: int
    staged_subproblems: int
    stage_coverage_rate: float | None
    governance_envelopes: int
    attempts: int
    accepted_attempts: int
    tests: int
    authorized_handoffs: int
    outcomes: int
    inbound_reuse: int
    outbound_reuse: int
    milestones: dict[str, bool]
    next_actions: list[str]
    blockers: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProblemCaseWorkspace:
    """Read-only orchestration view across Problem Commons V0.1 registries.

    This class deliberately does not become a fifth source of truth. It joins the
    existing Problem Packet, stage, governance and pilot ledgers by stable IDs,
    validates that they agree, and emits an inspectable case snapshot/bundle.
    """

    schema = "problem-case/v0.1"

    def __init__(
        self,
        *,
        commons: ProblemCommons | None = None,
        stages: StageRegistry | None = None,
        governance: GovernanceRegistry | None = None,
        pilot: PilotLedger | None = None,
    ) -> None:
        self.commons = commons or ProblemCommons()
        self.stages = stages or StageRegistry()
        self.governance = governance or GovernanceRegistry()
        self.pilot = pilot or PilotLedger()

    @classmethod
    def load(
        cls,
        *,
        commons_path: str | Path,
        stages_path: str | Path,
        governance_path: str | Path,
        pilot_path: str | Path,
    ) -> "ProblemCaseWorkspace":
        return cls(
            commons=ProblemCommons.load(commons_path),
            stages=StageRegistry.load(stages_path),
            governance=GovernanceRegistry.load(governance_path),
            pilot=PilotLedger.load(pilot_path),
        )

    def validate(self, problem_id: str) -> CaseValidation:
        problem = self.commons.get(problem_id)
        subproblem_ids = {item.id for item in problem.subproblems}
        profiles = self.stages.list(problem_id=problem_id)
        envelopes = self.governance.for_problem(problem_id)
        profile_by_subproblem = {item.subproblem_id: item for item in profiles}
        envelope_by_subproblem = {item.subproblem_id: item for item in envelopes}

        errors: list[str] = []
        warnings: list[str] = []

        for profile in profiles:
            report = profile.validation()
            errors.extend(f"stage {profile.subproblem_id}: {item}" for item in report.errors)
            warnings.extend(f"stage {profile.subproblem_id}: {item}" for item in report.warnings)
            if profile.subproblem_id not in subproblem_ids:
                errors.append(f"stage profile references unknown subproblem {profile.subproblem_id}")

        for envelope in envelopes:
            if envelope.subproblem_id not in subproblem_ids:
                errors.append(f"governance envelope references unknown subproblem {envelope.subproblem_id}")
                continue
            profile = profile_by_subproblem.get(envelope.subproblem_id)
            if profile is None:
                warnings.append(f"governance envelope {envelope.subproblem_id} has no stage profile")
                continue
            alignment = align_stage_and_governance(profile, envelope)
            errors.extend(f"alignment {envelope.subproblem_id}: {item}" for item in alignment.errors)
            warnings.extend(f"alignment {envelope.subproblem_id}: {item}" for item in alignment.warnings)

        for attempt in problem.attempts:
            unknown = sorted(set(attempt.subproblem_ids) - subproblem_ids)
            if unknown:
                errors.append(f"attempt {attempt.id} references unknown subproblems: {', '.join(unknown)}")

        if problem.subproblems and len(profiles) < len(problem.subproblems):
            missing = sorted(subproblem_ids - set(profile_by_subproblem))
            warnings.append("unstaged contribution paths: " + ", ".join(missing))

        # Intervention-oriented stage profiles should not silently jump from a
        # stage label to real-world action without a governance envelope.
        for subproblem_id, profile in profile_by_subproblem.items():
            if profile.stage == ProblemStage.DEPLOY and subproblem_id not in envelope_by_subproblem:
                errors.append(f"deploy stage {subproblem_id} requires a governance envelope")
            elif profile.stage == ProblemStage.TEST and subproblem_id not in envelope_by_subproblem:
                warnings.append(f"test stage {subproblem_id} has no governance envelope")

        if problem.status in {ProblemStatus.DEPLOYED, ProblemStatus.MONITORING, ProblemStatus.RESOLVED}:
            if not any(item.decision == "authorized" for item in problem.authority_decisions):
                errors.append("deployed/monitoring/resolved problem lacks an authorized Problem Packet authority decision")

        return CaseValidation(valid=not errors, errors=errors, warnings=_dedupe(warnings))

    def snapshot(self, problem_id: str) -> CaseSnapshot:
        problem = self.commons.get(problem_id)
        validation = self.validate(problem_id)
        publishability = problem.publishability(require_decomposition=problem.status == ProblemStatus.OPEN)
        profiles = self.stages.list(problem_id=problem_id)
        envelopes = self.governance.for_problem(problem_id)

        accepted_attempts = [
            item for item in problem.attempts
            if item.status in {AttemptStatus.ACCEPTED, AttemptStatus.COMPLETED}
        ]
        submitted_attempts = [item for item in problem.attempts if item.status == AttemptStatus.SUBMITTED]
        tests = [test for envelope in envelopes for test in envelope.tests]
        authorized_handoffs = [
            handoff for envelope in envelopes for handoff in envelope.handoffs
            if handoff.decision == "authorized"
        ]
        inbound_reuse = [item for item in self.pilot.reuse if item.target_problem_id == problem_id]
        outbound_reuse = [item for item in self.pilot.reuse if item.source_problem_id == problem_id]

        public = problem.status in {
            ProblemStatus.VERIFIED,
            ProblemStatus.OPEN,
            ProblemStatus.PARTIALLY_RESOLVED,
            ProblemStatus.PILOTING,
            ProblemStatus.DEPLOYED,
            ProblemStatus.MONITORING,
            ProblemStatus.RESOLVED,
        }
        stage_rate = len(profiles) / len(problem.subproblems) if problem.subproblems else None

        milestones = {
            "problem_formulated": publishability.publishable,
            "problem_public": public,
            "work_decomposed": bool(problem.subproblems),
            "work_staged": bool(problem.subproblems) and len(profiles) >= len(problem.subproblems),
            "attempt_started": bool(problem.attempts),
            "attempt_accepted": bool(accepted_attempts),
            "intervention_governed": bool(envelopes),
            "test_recorded": bool(tests),
            "authority_recorded": bool(authorized_handoffs) or any(x.decision == "authorized" for x in problem.authority_decisions),
            "deployed": problem.status in {ProblemStatus.DEPLOYED, ProblemStatus.MONITORING, ProblemStatus.RESOLVED},
            "outcome_observed": bool(problem.outcomes),
            "reuse_observed": bool(inbound_reuse or outbound_reuse),
        }

        blockers: list[str] = list(validation.errors)
        next_actions: list[str] = []

        if problem.status in {ProblemStatus.CANDIDATE, ProblemStatus.RESEARCHING, ProblemStatus.REFRAMED}:
            if not publishability.publishable:
                blockers.extend(f"publishability: {item}" for item in publishability.missing)
                next_actions.append("complete evidence-bounded curation before verification/publication")
            else:
                next_actions.append("record steward/domain review and move the packet toward VERIFIED")
        elif problem.status == ProblemStatus.VERIFIED:
            if not problem.subproblems:
                next_actions.append("decompose the verified problem into explicit contribution paths")
            else:
                next_actions.append("open the verified packet for attempts when steward review is satisfied")
        else:
            unstaged = [item.id for item in problem.subproblems if (problem_id, item.id) not in self.stages.profiles]
            if unstaged:
                next_actions.append("classify remaining contribution paths: " + ", ".join(unstaged))
            if not problem.attempts and problem.status in {ProblemStatus.OPEN, ProblemStatus.PARTIALLY_RESOLVED}:
                next_actions.append("match or recruit an independent solver and start a bounded attempt")
            if submitted_attempts:
                next_actions.append("review submitted attempts: " + ", ".join(item.id for item in submitted_attempts))
            if accepted_attempts and problem.status in {ProblemStatus.OPEN, ProblemStatus.PARTIALLY_RESOLVED}:
                next_actions.append("evaluate whether an accepted attempt justifies a bounded shadow/pilot transition")

        for envelope in envelopes:
            if not envelope.tests:
                readiness = envelope.readiness("test")
                if readiness.ready:
                    next_actions.append(f"run a bounded test for {envelope.subproblem_id} and record a receipt")
                else:
                    blockers.extend(f"governance {envelope.subproblem_id}: {item}" for item in readiness.blockers)
            deploy = envelope.readiness("deploy")
            if not deploy.ready:
                blockers.extend(f"deploy {envelope.subproblem_id}: {item}" for item in deploy.blockers)

        if problem.status in {ProblemStatus.DEPLOYED, ProblemStatus.MONITORING} and not problem.outcomes:
            next_actions.append("monitor the external condition and attach outcome evidence; do not infer impact from activity")
        if problem.outcomes and not outbound_reuse:
            next_actions.append("identify which validated evidence/method/capability can be generalized and test cross-problem reuse")

        if not next_actions:
            next_actions.append("continue longitudinal monitoring and look for a valid cross-problem reuse opportunity")

        warnings = _dedupe(validation.warnings + publishability.warnings)
        blockers = _dedupe(blockers)

        return CaseSnapshot(
            problem_id=problem.id,
            title=problem.title,
            status=problem.status.value,
            public=public,
            publishable=publishability.publishable,
            completeness=round(publishability.completeness, 3),
            subproblems=len(problem.subproblems),
            staged_subproblems=len(profiles),
            stage_coverage_rate=round(stage_rate, 3) if stage_rate is not None else None,
            governance_envelopes=len(envelopes),
            attempts=len(problem.attempts),
            accepted_attempts=len(accepted_attempts),
            tests=len(tests),
            authorized_handoffs=len(authorized_handoffs),
            outcomes=len(problem.outcomes),
            inbound_reuse=len(inbound_reuse),
            outbound_reuse=len(outbound_reuse),
            milestones=milestones,
            next_actions=_dedupe(next_actions),
            blockers=blockers,
            warnings=warnings,
        )

    def bundle(self, problem_id: str) -> dict[str, Any]:
        problem = self.commons.get(problem_id)
        profiles = self.stages.list(problem_id=problem_id)
        envelopes = self.governance.for_problem(problem_id)
        pilot_records = {
            "production": [asdict(x) for x in self.pilot.production if x.problem_id == problem_id],
            "solvers": [asdict(x) for x in self.pilot.solvers if x.problem_id == problem_id],
            "adoption": [asdict(x) for x in self.pilot.adoption if x.problem_id == problem_id],
            "reuse_inbound": [asdict(x) | {"net_minutes_saved": x.net_minutes_saved} for x in self.pilot.reuse if x.target_problem_id == problem_id],
            "reuse_outbound": [asdict(x) | {"net_minutes_saved": x.net_minutes_saved} for x in self.pilot.reuse if x.source_problem_id == problem_id],
        }
        validation = self.validate(problem_id)
        return {
            "schema": self.schema,
            "problem_id": problem_id,
            "validation": asdict(validation),
            "snapshot": self.snapshot(problem_id).to_dict(),
            "problem": problem.to_dict(),
            "stages": [item.to_dict() for item in profiles],
            "governance": [item.to_dict() for item in envelopes],
            "pilot": pilot_records,
        }

    def save_bundle(self, problem_id: str, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.bundle(problem_id), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return target


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in values if item))
