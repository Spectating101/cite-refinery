from __future__ import annotations

from typing import Any

from .problem_commons import ProblemPacket
from .problem_intake import OwnerIntake
from .owner_review_contract import validate_owner_review_response
from urllib.parse import urlsplit


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
        "source_ref": _public_source_ref(intake, packet),
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



def _public_source_ref(intake: OwnerIntake, packet: ProblemPacket) -> str:
    """Do not forward private source locators just because this is a review pack."""
    from .problem_commons import Visibility
    if not any(item.locator == intake.source_ref and item.visibility == Visibility.PUBLIC for item in packet.evidence):
        return ""
    try:
        url = urlsplit(intake.source_ref)
        if url.scheme in {"http", "https"} and url.hostname and not url.username and not url.password:
            return intake.source_ref
    except ValueError:
        pass
    return ""
