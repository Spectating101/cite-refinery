from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .problem_commons import (
    CapabilityNeed,
    ProblemPacket,
    StewardReview,
    Visibility,
    object_id,
    utcnow,
)


class ContextKind(StrEnum):
    OBSERVATION = "observation"
    KNOWLEDGE = "knowledge"
    CAPABILITY = "capability"
    DIAGNOSIS = "diagnosis"
    OUTCOME = "outcome"
    CITATION = "citation"


@dataclass(slots=True)
class ContextUpdate:
    """Provider-neutral proposal to enrich one Problem Packet.

    Updates never mutate a packet merely because an engine produced them. A
    curator/reviewer must explicitly accept an update through ``apply_update``.
    """

    id: str
    source_system: str
    source_ref: str
    kind: ContextKind
    payload: dict[str, Any]
    confidence: str = "unreviewed"
    visibility: Visibility = Visibility.RESTRICTED
    created_at: str = field(default_factory=utcnow)


def apply_update(
    packet: ProblemPacket,
    update: ContextUpdate,
    *,
    accepted_by: str,
    notes: str = "",
) -> StewardReview:
    """Apply a reviewed external-engine update without transferring authority.

    The source system remains authoritative for its own state. Problem Commons
    stores only the accepted projection plus a reference back to the source.
    """

    packet.attach_external_ref(
        system=update.source_system,
        ref=update.source_ref,
        relation=f"context:{update.kind.value}",
        visibility=update.visibility,
        label=update.kind.value,
        notes=notes,
    )

    payload = update.payload
    if update.kind == ContextKind.OBSERVATION:
        summary = str(payload.get("summary") or payload.get("observed_condition") or "").strip()
        if summary:
            packet.add_evidence(
                source=update.source_system,
                locator=str(payload.get("locator") or update.source_ref),
                summary=summary,
                confidence=update.confidence,
                visibility=update.visibility,
                observed_at=payload.get("observed_at"),
                rights=str(payload.get("rights") or ""),
                provenance={"source_ref": update.source_ref},
            )
    elif update.kind == ContextKind.KNOWLEDGE:
        packet.knowledge_frontier = _merge(packet.knowledge_frontier, payload.get("frontier", []))
        packet.prior_attempts = _merge(packet.prior_attempts, payload.get("prior_attempts", []))
    elif update.kind == ContextKind.CAPABILITY:
        packet.capability_frontier = _merge(packet.capability_frontier, payload.get("frontier", []))
        for raw in payload.get("needs", []):
            if not isinstance(raw, dict) or not raw.get("name"):
                continue
            packet.capability_needs.append(
                CapabilityNeed(
                    id=str(raw.get("id") or object_id("pcap")),
                    name=str(raw["name"]),
                    state=str(raw.get("state") or "needed"),
                    description=str(raw.get("description") or ""),
                    capability_refs=list(raw.get("capability_refs") or []),
                    limitations=list(raw.get("limitations") or []),
                )
            )
    elif update.kind == ContextKind.DIAGNOSIS:
        packet.diagnosis = _merge(packet.diagnosis, payload.get("diagnosis", []))
        packet.constraints = _merge(packet.constraints, payload.get("constraints", []))
        if payload.get("authority_boundary"):
            packet.authority_boundary = str(payload["authority_boundary"])
        packet.implementation_pathway = _merge(
            packet.implementation_pathway, payload.get("implementation_pathway", [])
        )
    elif update.kind == ContextKind.OUTCOME:
        packet.record_outcome(
            summary=str(payload.get("summary") or "Observed outcome"),
            observed_change=str(payload.get("observed_change") or ""),
            evidence_refs=list(payload.get("evidence_refs") or []),
            disposition=str(payload.get("disposition") or "observed"),
            attribution=str(payload.get("attribution") or "not_established"),
        )
    elif update.kind == ContextKind.CITATION:
        pass

    review = StewardReview(
        id=object_id("preview"),
        problem_id=packet.id,
        reviewer=accepted_by,
        verdict="accepted_context_update",
        notes=notes,
        checklist={"source_reference_preserved": True, "human_acceptance_recorded": True},
    )
    packet.steward_reviews.append(review)
    packet.updated_at = utcnow()
    return review


def _merge(current: list[str], incoming: Any) -> list[str]:
    values = list(current)
    for item in incoming or []:
        text = str(item).strip()
        if text and text not in values:
            values.append(text)
    return values
