from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class NocturnalObservationRecord:
    external_id: str
    matter_id: str | None
    event_id: str | None
    text: str
    observed_at: str | None
    status_stage: str | None
    frame: str | None
    sources: list[str]
    literature_queries: list[dict[str, Any]]
    provenance: dict[str, Any]


def _claim_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [
        packet.get("claims"),
        packet.get("engine_diagnostics", {}).get("claims") if isinstance(packet.get("engine_diagnostics"), dict) else None,
        packet.get("evidence_history", {}).get("claims") if isinstance(packet.get("evidence_history"), dict) else None,
    ]
    for value in candidates:
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def _literature_queries(row: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[Any] = []
    direct = row.get("literature_queries")
    if isinstance(direct, list):
        values.extend(direct)
    posture = row.get("epistemic_posture")
    if isinstance(posture, dict) and isinstance(posture.get("literature_queries"), list):
        values.extend(posture["literature_queries"])

    seen: set[tuple[str, str, str]] = set()
    normalized: list[dict[str, Any]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        query = str(item.get("query") or "").strip()
        if not query:
            continue
        domain = str(item.get("domain") or "").strip()
        reason = str(item.get("reason") or "").strip()
        key = (domain.lower(), query.lower(), reason.lower())
        if key in seen:
            continue
        seen.add(key)
        normalized.append({
            "domain": domain or None,
            "query": query,
            "reason": reason or None,
            "claim_anchor": item.get("claim_anchor"),
        })
    return normalized


def parse_nocturnal_packet(packet: dict[str, Any]) -> list[NocturnalObservationRecord]:
    if not isinstance(packet, dict):
        raise ValueError("Nocturnal packet must be a JSON object")
    rows = _claim_rows(packet)
    if not rows:
        raise ValueError("Nocturnal packet contains no claim rows")

    artifact_kind = packet.get("artifact_kind")
    records: list[NocturnalObservationRecord] = []
    for row in rows:
        text = str(row.get("public_claim") or row.get("claim") or "").strip()
        if not text:
            continue
        matter_id = row.get("matter_id")
        event_id = row.get("event_id")
        claim_id = row.get("claim_id")
        if event_id:
            external_id = str(event_id)
        elif claim_id:
            external_id = str(claim_id)
        else:
            basis = f"{matter_id or ''}\n{text}".encode("utf-8")
            external_id = hashlib.sha256(basis).hexdigest()[:20]

        raw_sources = row.get("sources")
        sources = [str(value) for value in raw_sources] if isinstance(raw_sources, list) else []
        canonical_url = row.get("canonical_url")
        if canonical_url and str(canonical_url) not in sources:
            sources.append(str(canonical_url))

        provenance = {
            "artifact_kind": artifact_kind,
            "canonical_url": canonical_url,
            "source_tier": row.get("source_tier"),
            "source_domain": row.get("source_domain"),
            "custody_sha256": row.get("custody_sha256"),
            "dispute_state": row.get("dispute_state"),
            "correction_of": row.get("correction_of"),
            "article_title": row.get("article_title"),
            "risk_level": row.get("risk_level"),
            "review_required": row.get("review_required"),
        }
        provenance = {key: value for key, value in provenance.items() if value is not None}
        records.append(NocturnalObservationRecord(
            external_id=external_id,
            matter_id=str(matter_id) if matter_id is not None else None,
            event_id=str(event_id) if event_id is not None else None,
            text=text,
            observed_at=str(row.get("observed_at")) if row.get("observed_at") is not None else None,
            status_stage=str(row.get("status_stage")) if row.get("status_stage") is not None else None,
            frame=str(row.get("frame")) if row.get("frame") is not None else None,
            sources=sources,
            literature_queries=_literature_queries(row),
            provenance=provenance,
        ))

    if not records:
        raise ValueError("Nocturnal packet contains no usable claim text")
    return records
