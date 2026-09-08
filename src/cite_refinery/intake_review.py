from __future__ import annotations

from typing import Any

from .problem_commons import ProblemPacket
from .problem_intake import OwnerIntake


def build_intake_owner_review_pack(
    intake: OwnerIntake,
    packet: ProblemPacket,
    *,
    rubrics: dict[str, Any],
) -> dict[str, Any]:
    if packet.id != f"problem:{intake.id.split(':', 1)[1]}":
        raise ValueError("packet does not align to intake")
    if rubrics.get("schema") != "problem-commons-rubrics/v0.1":
        raise ValueError(f"unsupported rubric schema: {rubrics.get('schema')}")
    rubric = rubrics.get("owner_agreement")
    if not isinstance(rubric, dict):
        raise ValueError("owner_agreement rubric is required")

    return {
        "schema": "problem-owner-intake-review/v0.1",
        "intake_id": intake.id,
        "problem_id": packet.id,
        "potential_owner": intake.owner_org,
        "source_ref": intake.source_ref,
        "instructions": [
            "Review this as a representation of your current real need, not as a proposed solution you are expected to accept.",
            "Correct anything stale, inaccurate, missing, unsafe, infeasible, or outside your authority/supervision capacity.",
            "Mark which proposed work paths are acceptable to explore and which should not proceed.",
            "Do not place participant/minor identities or sensitive records in this review response.",
            "Confirmation means the Problem formulation is usable for further curation; it does not authorize live work or guarantee a solver/funder.",
        ],
        "problem": {
            "title": packet.title,
            "observed_condition": packet.observed_condition,
            "unresolved_core": packet.unresolved_core,
            "geography": packet.geography,
            "reported_schedule": intake.schedule,
            "affected_actors": list(packet.affected_actors),
            "beneficiaries": list(packet.beneficiaries),
            "uncertainties": list(packet.disputes_uncertainty),
            "constraints": list(packet.constraints),
            "available_resources_reported": list(intake.available_resources),
            "requested_support_reported": list(intake.requested_support),
            "authority_boundary": packet.authority_boundary,
            "candidate_work": [
                {
                    "subproblem_id": item.id,
                    "title": item.title,
                    "description": item.description,
                    "kind": item.kind,
                    "status": item.status,
                    "effort": item.effort,
                    "expected_outputs": list(item.expected_outputs),
                    "required_credentials": list(item.required_credentials),
                }
                for item in packet.subproblems
            ],
        },
        "rubric": {
            "name": "owner_agreement",
            "items": list(rubric.get("items") or []),
            "scoring": str(rubric.get("scoring") or ""),
        },
        "response": {
            "source_still_current": None,
            "owner_identity_and_role_correct": None,
            "item_scores": [None for _ in rubric.get("items", [])],
            "factual_corrections": [],
            "missing_constraints": [],
            "desired_outcome_or_priority": "",
            "acceptable_work_subproblem_ids": [],
            "unacceptable_work_subproblem_ids": [],
            "access_or_safeguarding_corrections": [],
            "funding_or_resource_notes": [],
            "reframe_required": False,
            "disposition": "undecided",
            "owner_notes": "",
        },
        "allowed_dispositions": ["confirm", "reframe", "stale", "already-resolved", "decline", "undecided"],
        "privacy_note": "Return minimum-necessary corrections only. Sensitive participant, child, operational or personal data should be handled through an owner-approved private channel, not copied into this review pack.",
    }


def validate_owner_review_response(pack: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if pack.get("schema") != "problem-owner-intake-review/v0.1":
        errors.append("unsupported owner-review schema")
        return errors
    response = pack.get("response")
    if not isinstance(response, dict):
        errors.append("response object is required")
        return errors
    disposition = response.get("disposition")
    allowed = set(pack.get("allowed_dispositions") or [])
    if disposition not in allowed:
        errors.append("response disposition is invalid")
    scores = response.get("item_scores")
    items = ((pack.get("rubric") or {}).get("items") or [])
    if not isinstance(scores, list) or len(scores) != len(items):
        errors.append("item_scores must align to owner_agreement rubric items")
    if disposition in {"confirm", "reframe", "stale", "already-resolved", "decline"}:
        if response.get("source_still_current") is None:
            errors.append("completed owner review requires source_still_current")
        if response.get("owner_identity_and_role_correct") is None:
            errors.append("completed owner review requires owner_identity_and_role_correct")
    return errors
