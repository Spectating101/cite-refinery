from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import Any

from .problem_case import ProblemCaseWorkspace
from .review_pack import build_review_pack


CONTROL_ARM = "ordinary_brief"
TREATMENT_ARM = "problem_packet"
KNOWN_ARMS = {CONTROL_ARM, TREATMENT_ARM}


@dataclass(slots=True)
class ExperimentAssignment:
    problem_id: str
    participant_id: str
    sequence_index: int
    arm: str
    pair_position: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assign_arm(problem_id: str, participant_id: str, *, sequence_index: int = 0) -> ExperimentAssignment:
    """Deterministically counterbalance arm order without storing identity centrally.

    The stable hash chooses whether this participant sees treatment or control
    first for this problem. Incrementing sequence_index alternates arms. This is
    a pilot convenience, not a substitute for a preregistered randomization plan.
    """
    if sequence_index < 0:
        raise ValueError("sequence_index must be non-negative")
    if not problem_id.startswith("problem:"):
        raise ValueError("problem_id must begin with problem:")
    if not participant_id.strip():
        raise ValueError("participant_id is required")
    digest = hashlib.sha256(f"{problem_id}|{participant_id}".encode("utf-8")).digest()
    first = TREATMENT_ARM if digest[0] % 2 else CONTROL_ARM
    second = CONTROL_ARM if first == TREATMENT_ARM else TREATMENT_ARM
    pair_position = sequence_index % 2
    return ExperimentAssignment(problem_id, participant_id, sequence_index, first if pair_position == 0 else second, pair_position)


def build_experiment_pack(
    workspace: ProblemCaseWorkspace,
    problem_id: str,
    *,
    participant_id: str,
    rubrics: dict[str, Any],
    sequence_index: int = 0,
    forced_arm: str | None = None,
) -> dict[str, Any]:
    assignment = assign_arm(problem_id, participant_id, sequence_index=sequence_index)
    arm = forced_arm or assignment.arm
    if arm not in KNOWN_ARMS:
        raise ValueError("forced_arm must be ordinary_brief or problem_packet")

    pack = build_review_pack(workspace, problem_id, audience="solver", rubrics=rubrics)
    pack["experiment"] = {
        "schema": "problem-solver-experiment/v0.1",
        "participant_id": participant_id,
        "sequence_index": sequence_index,
        "pair_position": assignment.pair_position,
        "arm": arm,
        "comparison_note": "Both arms derive from the same current Problem Packet facts. The control intentionally omits Commons-specific enrichment rather than changing the underlying problem claim.",
    }
    pack["response"]["arm"] = arm

    if arm == CONTROL_ARM:
        pack["problem"] = ordinary_challenge_projection(workspace, problem_id)
        pack["stage_profiles"] = []
        pack["governance"] = []
        pack["instructions"] = [
            "Read this ordinary challenge brief without curator coaching first.",
            "Explain what is happening, what you think remains uncertain, one workstream you could attempt, a concrete useful output, and one material constraint or authority boundary.",
            "Record time-to-useful-edge before any curator explanation.",
            "Do not infer information that is absent from the brief; missing context is part of the experiment.",
        ]
    else:
        pack["instructions"] = [
            "Read this full Problem Packet without curator coaching first.",
            "Explain the observed condition without substituting a preferred solution, identify an explicit uncertainty, select a contribution path, name a useful output, and identify a material constraint or authority boundary.",
            "Record time-to-useful-edge before any curator explanation.",
            "Use only the information exposed in this minimum-necessary pack.",
        ]
    return pack


def ordinary_challenge_projection(workspace: ProblemCaseWorkspace, problem_id: str) -> dict[str, Any]:
    """Create a credible conventional brief from the same redacted facts.

    The control receives the same problem claim, scope, success criteria,
    authority boundary and workstream descriptions. It intentionally omits
    Commons-specific evidence/uncertainty/frontier/capability/stage/governance
    organization. This avoids manufacturing a deliberately bad control.
    """
    problem = workspace.commons.get(problem_id)
    public = problem.public_snapshot()
    return {
        "id": problem.id,
        "title": problem.title,
        "status": problem.status.value,
        "visibility": "public-experiment-projection",
        "summary": problem.summary,
        "observed_condition": problem.observed_condition,
        "unresolved_core": problem.unresolved_core,
        "domain": problem.domain,
        "geography": problem.geography,
        "time_scope": problem.time_scope,
        "affected_actors": list(problem.affected_actors),
        "constraints": list(problem.constraints),
        "authority_boundary": problem.authority_boundary,
        "success_criteria": list(public.get("success_criteria") or []),
        "subproblems": [
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "kind": item.kind,
                "status": item.status,
                "expected_outputs": list(item.expected_outputs),
            }
            for item in problem.subproblems
            if item.status == "open"
        ],
        # Required by the shared review UI. The ordinary brief does not supply an
        # explicit uncertainty register; the UI therefore truthfully shows none.
        "disputes_uncertainty": [],
    }


def summarize_experiment(solver_rows: list[Any], *, problem_id: str | None = None) -> dict[str, Any]:
    rows = [item for item in solver_rows if problem_id is None or item.problem_id == problem_id]
    result: dict[str, Any] = {"schema": "problem-solver-experiment-report/v0.1", "problem_id": problem_id, "arms": {}}
    for arm in (CONTROL_ARM, TREATMENT_ARM):
        arm_rows = [item for item in rows if item.arm == arm]
        comprehension = [item.comprehension_score for item in arm_rows if item.comprehension_score is not None]
        time_to_edge = [item.minutes_to_useful_edge for item in arm_rows if item.minutes_to_useful_edge is not None]
        usefulness = [item.usefulness_rating for item in arm_rows if item.usefulness_rating is not None]
        result["arms"][arm] = {
            "sessions": len(arm_rows),
            "mean_comprehension": _mean(comprehension),
            "mean_minutes_to_useful_edge": _mean(time_to_edge),
            "mean_usefulness": _mean(usefulness),
            "serious_attempt_rate": _rate(sum(item.serious_attempt for item in arm_rows), len(arm_rows)),
            "abandonment_rate": _rate(sum(item.abandoned for item in arm_rows), len(arm_rows)),
            "mean_coaching_minutes": _mean([item.coaching_minutes for item in arm_rows]),
        }
    control = result["arms"][CONTROL_ARM]
    treatment = result["arms"][TREATMENT_ARM]
    result["difference_treatment_minus_control"] = {
        "comprehension": _difference(treatment["mean_comprehension"], control["mean_comprehension"]),
        "minutes_to_useful_edge": _difference(treatment["mean_minutes_to_useful_edge"], control["mean_minutes_to_useful_edge"]),
        "usefulness": _difference(treatment["mean_usefulness"], control["mean_usefulness"]),
        "serious_attempt_rate": _difference(treatment["serious_attempt_rate"], control["serious_attempt_rate"]),
        "abandonment_rate": _difference(treatment["abandonment_rate"], control["abandonment_rate"]),
        "coaching_minutes": _difference(treatment["mean_coaching_minutes"], control["mean_coaching_minutes"]),
    }
    result["warnings"] = []
    if min(control["sessions"], treatment["sessions"]) < 5:
        result["warnings"].append("fewer than five sessions in at least one arm; treat differences as exploratory")
    return result


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _difference(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right
