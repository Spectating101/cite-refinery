from __future__ import annotations

from typing import Any

from .case_operations import CaseOperations, OperationReceipt
from .problem_commons import ProblemPacket, ProblemStatus, Visibility


ALLOWED_DRAFT_STATES = {
    ProblemStatus.CANDIDATE,
    ProblemStatus.RESEARCHING,
    ProblemStatus.REFRAMED,
}


def admit_draft_packet(
    operations: CaseOperations,
    payload: dict[str, Any],
    *,
    actor: str,
    allow_duplicate: bool = False,
) -> tuple[ProblemPacket, OperationReceipt, list[tuple[str, float]]]:
    """Admit a standalone curated draft without bypassing publication gates.

    Draft admission is intentionally stricter than normal persistence loading:
    public lifecycle state, public packet visibility, attempts, authority decisions,
    and outcomes are rejected. The imported object remains candidate/researching
    work until later explicit review and promotion.
    """

    packet = ProblemPacket.from_dict(payload)
    if not packet.id.startswith("problem:"):
        raise ValueError("draft problem id must begin with problem:")
    if packet.id in operations.commons.problems:
        raise ValueError(f"problem already exists: {packet.id}")
    if packet.status not in ALLOWED_DRAFT_STATES:
        raise ValueError(f"draft admission rejects lifecycle state: {packet.status.value}")
    if packet.visibility == Visibility.PUBLIC:
        raise ValueError("draft admission rejects public packet visibility")
    if packet.attempts:
        raise ValueError("draft admission rejects embedded attempts; import attempts through their reviewed workflow")
    if packet.authority_decisions:
        raise ValueError("draft admission rejects embedded authority decisions")
    if packet.outcomes:
        raise ValueError("draft admission rejects embedded outcomes")
    if not packet.steward.strip():
        raise ValueError("draft admission requires an explicit steward")

    duplicates = operations.commons.duplicate_candidates(packet)
    if duplicates and not allow_duplicate:
        rendered = ", ".join(f"{problem_id} ({score:.3f})" for problem_id, score in duplicates)
        raise ValueError("possible duplicate draft; inspect before admission: " + rendered)

    if "draft-admission" not in packet.tags:
        packet.tags.append("draft-admission")
    if "do-not-publish-before-curation" not in packet.tags:
        packet.tags.append("do-not-publish-before-curation")
    operations.commons.problems[packet.id] = packet
    receipt = operations._receipt(
        packet.id,
        action="draft-import",
        actor=actor,
        summary="Admitted a non-public standalone draft for reviewed curation; no publication or authority state was inherited.",
        inputs={"original_status": packet.status.value, "allow_duplicate": allow_duplicate},
        outputs={"status": packet.status.value, "visibility": packet.visibility.value, "duplicate_candidates": duplicates},
    )
    return packet, receipt, duplicates
