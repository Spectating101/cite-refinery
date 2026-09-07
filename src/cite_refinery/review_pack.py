from __future__ import annotations

from typing import Any

from .problem_case import ProblemCaseWorkspace


AUDIENCE_RUBRIC = {
    "owner": "owner_agreement",
    "reviewer": "reviewer_quality",
    "solver": "solver_comprehension",
}


def build_review_pack(
    workspace: ProblemCaseWorkspace,
    problem_id: str,
    *,
    audience: str,
    rubrics: dict[str, Any],
) -> dict[str, Any]:
    """Build a minimum-necessary pack for external pilot review.

    The pack always starts from the Problem Packet public snapshot so restricted
    locators/provenance are not exported merely because an external reviewer is
    participating in a pilot. Additional access should be granted separately by
    the owning institution when genuinely required.
    """

    audience = audience.strip().lower()
    if audience not in AUDIENCE_RUBRIC:
        raise ValueError("audience must be owner, reviewer, or solver")
    if rubrics.get("schema") != "problem-commons-rubrics/v0.1":
        raise ValueError(f"unsupported rubric schema: {rubrics.get('schema')}")

    problem = workspace.commons.get(problem_id)
    stages = workspace.stages.list(problem_id=problem_id)
    envelopes = workspace.governance.for_problem(problem_id)
    rubric_key = AUDIENCE_RUBRIC[audience]
    rubric = rubrics.get(rubric_key)
    if not isinstance(rubric, dict):
        raise ValueError(f"missing rubric: {rubric_key}")

    return {
        "schema": "problem-review-pack/v0.1",
        "audience": audience,
        "problem_id": problem_id,
        "instructions": _instructions(audience),
        "problem": problem.public_snapshot(),
        "stage_profiles": [_safe_stage(item.to_dict()) for item in stages],
        "governance": [_safe_governance(item.to_dict()) for item in envelopes],
        "rubric": {
            "name": rubric_key,
            "items": list(rubric.get("items") or []),
            "scoring": str(rubric.get("scoring") or ""),
        },
        "response": {
            "item_scores": [None for _ in rubric.get("items", [])],
            "disagreement_notes": [],
            "material_errors": [],
            "coaching_received": False,
        },
        "privacy_note": "This pack is generated from the public/redacted Problem Packet projection. Restricted evidence access, if needed, must be granted separately by the owning institution.",
    }


def _safe_stage(raw: dict[str, Any]) -> dict[str, Any]:
    keys = {
        "problem_id", "subproblem_id", "stage", "question", "epistemic_type",
        "uncertainty", "method_maturity", "expected_outputs", "evaluation_method",
        "authority_level", "authority_requirement", "required_credentials",
        "work_mode", "reuse_target",
    }
    return {key: raw[key] for key in keys if key in raw}


def _safe_governance(raw: dict[str, Any]) -> dict[str, Any]:
    gates = [
        {
            "kind": gate.get("kind"),
            "status": gate.get("status"),
            "requirement": gate.get("requirement", ""),
            "notes": gate.get("notes", ""),
        }
        for gate in raw.get("gates", [])
    ]
    tests = [
        {
            "passed": item.get("passed"),
            "scope": item.get("scope", ""),
            "summary": item.get("summary", ""),
            "guardrail_breaches": list(item.get("guardrail_breaches") or []),
        }
        for item in raw.get("tests", [])
    ]
    handoffs = [
        {
            "decision": item.get("decision"),
            "authority_scope": item.get("authority_scope", ""),
            "notes": item.get("notes", ""),
        }
        for item in raw.get("handoffs", [])
    ]
    return {
        "problem_id": raw.get("problem_id"),
        "subproblem_id": raw.get("subproblem_id"),
        "title": raw.get("title"),
        "target_transition": raw.get("target_transition"),
        "diagnosis_hypothesis": raw.get("diagnosis_hypothesis"),
        "intervention_class": raw.get("intervention_class"),
        "smallest_feasible_change": raw.get("smallest_feasible_change"),
        "expected_mechanism": raw.get("expected_mechanism"),
        "reversibility": raw.get("reversibility"),
        "rollback_plan": raw.get("rollback_plan"),
        "preconditions": list(raw.get("preconditions") or []),
        "constraints": list(raw.get("constraints") or []),
        "rights_impacts": list(raw.get("rights_impacts") or []),
        "safety_risks": list(raw.get("safety_risks") or []),
        "integrity_risks": list(raw.get("integrity_risks") or []),
        "outcome_metrics": list(raw.get("outcome_metrics") or []),
        "monitoring_plan": raw.get("monitoring_plan", ""),
        "state": raw.get("state"),
        "gates": gates,
        "tests": tests,
        "handoffs": handoffs,
    }


def _instructions(audience: str) -> list[str]:
    if audience == "owner":
        return [
            "Judge whether the packet represents your real operational problem rather than our preferred solution.",
            "Mark any missing constraint, wrong authority boundary, misleading uncertainty, or unusable success criterion.",
            "Do not disclose restricted operational data in this response pack.",
        ]
    if audience == "reviewer":
        return [
            "Review the problem formulation independently before discussing preferred interventions.",
            "Flag unsupported scope, hidden diagnosis assumptions, already-solved framing, unsafe contribution paths, or invalid authority transitions.",
            "Score only what is supported by the packet presented here.",
        ]
    return [
        "Read the packet without curator coaching first.",
        "Explain the observed condition, one important uncertainty, one contribution path you could attempt, a concrete useful output, and one material constraint or authority boundary.",
        "Do not score yourself; the observer should score the rubric after your unaided explanation.",
    ]
