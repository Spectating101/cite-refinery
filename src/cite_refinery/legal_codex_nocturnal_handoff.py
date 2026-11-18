"""Portable, source-custodied Legal Codex 020 candidates for native intake.

The packet contains the reviewed public XML bodies, their capture receipts,
re-extractions and the visible curated ledger. Its digest identifies a version;
it is not a signature, a legal review or authorization to publish. Importers
must preserve that distinction when projecting the candidates into native notes.
"""
from __future__ import annotations

import argparse
import base64
import binascii
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path

from .legal_codex_access_outcomes import SOURCE_PINS, _capture_module
from .legal_codex_remedy_sources import DUTCH, finlex_module, load_inputs
from .legal_codex_remedy_tracker import evaluate, _prepare

SCHEMA = "legal_codex.nocturnal_handoff_021.v1"
MAX_PACKET_BYTES = 4 * 1024 * 1024
MAX_SOURCE_BYTES = 1024 * 1024
BOUNDARIES = {
    "candidate_only": True,
    "review_state": "unreviewed_external_candidate",
    "source_material": "published_decisions",
    "original_claimant_record_custody": False,
    "independent_legal_interpretation_reviewed": False,
    "intervention_verdict": None,
    "causal_effect_established": False,
    "individual_responsibility_inferred": False,
    "operational_replay_allowed": False,
    "publication_authorized": False,
    "capture_receipts_are_cryptographic_attestations": False,
}
DUTCH_RECEIPT_SCHEMA = "legal_codex.cross_case_sources_019.v1"


def canonical_bytes(value):
    """Canonical JSON convention shared with the portable intake contract."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def packet_digest(packet):
    return digest(canonical_bytes({k: v for k, v in packet.items()
                                   if k not in {"packet_id", "packet_sha256"}}))


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_packet(path):
    """Read bounded JSON without silently accepting duplicate field names."""
    source = Path(path)
    if source.is_symlink():
        raise ValueError("packet symlink refused")
    raw = source.read_bytes()
    if len(raw) > MAX_PACKET_BYTES:
        raise ValueError("packet byte budget exceeded")
    value = json.loads(raw, object_pairs_hook=_unique_pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    if not isinstance(value, dict):
        raise ValueError("packet must be an object")
    return value


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("capture timestamp must be text")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid capture timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("capture timestamp must include timezone")
    return value


def _source_from_custody(sid, raw, receipt, receipt_schema):
    """Re-extract the known source version; never trust supplied parsed text."""
    if not isinstance(raw, bytes) or not 40 < len(raw) <= MAX_SOURCE_BYTES:
        raise ValueError("invalid raw source byte budget")
    if not isinstance(receipt, dict):
        raise ValueError("capture receipt must be an object")
    captured_at = _timestamp(receipt.get("attempted_at"))
    if sid in DUTCH:
        capture = _capture_module()
        url, fmt, identity = capture.SOURCES[sid]
        pin, decided, sector = SOURCE_PINS[sid]
        if receipt_schema != DUTCH_RECEIPT_SCHEMA:
            raise ValueError("wrong Dutch capture receipt schema")
        document = capture.extract(raw, fmt, identity)
        if decided not in document["metadata"]["decision_dates"]:
            raise ValueError("source decision date differs")
        runtime = {**document, "source_id": sid, "source_url": url,
                   "raw_sha256": pin, "date": decided, "date_kind": "decision_date",
                   "sector": sector, "captured_at": captured_at,
                   "historical_version_verified": False}
        scope = "Rechtspraak XML paragraph blocks, with original block IDs and exact normalized text."
    else:
        capture = finlex_module()
        if sid != capture.SOURCE_ID or receipt_schema != capture.SCHEMA:
            raise ValueError("unrecognized source or Finlex capture receipt schema")
        url, fmt, identity, pin = capture.SOURCE_URL, "xml", capture.IDENTITY, capture.PINNED_SHA256
        document = capture.extract(raw, captured_at=captured_at)
        runtime = document
        if (receipt.get("schema") != capture.SCHEMA or receipt.get("http_status") != 200
                or not capture._xml_content_type(receipt.get("content_type"))):
            raise ValueError("unaccepted Finlex capture metadata")
        scope = ("Numbered XML paragraph elements 1–67 and finality statement. "
                 "Unnumbered quotation/list continuations remain in the complete raw XML; "
                 "this is not a complete text edition.")
    expected = {"source_id": sid, "identity": identity, "format": fmt,
                "url": url, "final_url": url, "status": "captured_and_reextracted",
                "raw_sha256": pin, "raw_bytes": len(raw), "block_count": len(document["blocks"])}
    if digest(raw) != pin:
        raise ValueError("source differs from reviewed raw pin")
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError("capture receipt disagrees with reviewed source custody")
    if type(receipt.get("raw_bytes")) is not int or receipt.get("tls_hostname_verified") is not True:
        raise ValueError("capture receipt lacks byte count or verified TLS report")
    return runtime, document, scope


def _decode_source(row):
    if not isinstance(row, dict):
        raise ValueError("source entry must be an object")
    encoded = row.get("raw_content_base64")
    if not isinstance(encoded, str) or len(encoded) > ((MAX_SOURCE_BYTES + 2) // 3) * 4:
        raise ValueError("invalid encoded source byte budget")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid raw source base64") from exc
    runtime, document, scope = _source_from_custody(
        row.get("source_id"), raw, row.get("capture_receipt"), row.get("capture_receipt_schema"))
    if row.get("raw_bytes") != len(raw) or row.get("raw_sha256") != digest(raw):
        raise ValueError("source payload byte count or hash differs")
    if row.get("extracted_document") != document:
        raise ValueError("extracted document differs from raw source re-extraction")
    if row.get("extracted_sha256") != digest(canonical_bytes(document)):
        raise ValueError("extracted document hash differs")
    if row.get("capture_receipt_sha256") != digest(canonical_bytes(row["capture_receipt"])):
        raise ValueError("capture receipt hash differs")
    return runtime, document, scope, raw


def _visible_ledger(ledger, report, sources):
    """Do not carry future components, events or deadlines into an intake packet."""
    event_ids = {event["id"] for event in report["events"]}
    component_rows = {row["id"]: row for row in report["obligations"] if row["event_ids"]}
    if not event_ids:
        raise ValueError("no publicly visible events for an intake handoff at this cutoff")
    events = [deepcopy(event) for event in ledger["events"] if event["id"] in event_ids]
    selected = {event["source_id"] for event in events}
    obligations = []
    for original in ledger["obligations"]:
        if original["id"] not in component_rows:
            continue
        row = deepcopy(original)
        deadline = component_rows[row["id"]]["deadline"]
        if deadline is None:
            row.pop("deadline", None)
        else:
            row["deadline"] = deepcopy(deadline)
            selected.add(deadline["basis"]["source_id"])
        obligations.append(row)
    # A retained event may use an explicitly reviewed same-proceeding link.
    case_ids = {row["case_id"] for row in obligations}
    links = [deepcopy(link) for link in ledger.get("case_links", [])
             if link["source_id"] in selected and link["case_id"] in case_ids]
    result = {"schema": ledger["schema"], "description": ledger.get("description", "Curated public-source candidates."),
              "sources": {sid: deepcopy(ledger["sources"][sid]) for sid in sorted(selected)},
              "obligations": obligations, "events": events}
    if links:
        result["case_links"] = links
    # Re-evaluation also rejects dangling supersession/order references.
    evaluate(result, sources, report["as_of"])
    return result


def _assemble(ledger, custody, as_of):
    sources, documents, scopes, raws = {}, {}, {}, {}
    for sid, row in custody.items():
        runtime, document, scope, raw = _decode_source(row)
        if runtime["source_id"] != sid:
            raise ValueError("source registry key differs from source identity")
        sources[sid], documents[sid], scopes[sid], raws[sid] = runtime, document, scope, raw
    if set(sources) != set(ledger.get("sources", {})):
        raise ValueError("source custody set differs from visible ledger sources")
    report = evaluate(ledger, sources, as_of)
    visible_ids = {event["id"] for event in report["events"]}
    if not visible_ids or visible_ids != {event["id"] for event in ledger["events"]}:
        raise ValueError("handoff must contain only visible events at the cutoff")
    if any(not row["event_ids"] for row in report["obligations"]):
        raise ValueError("handoff cannot expose a future component without visible evidence")
    _, _, source_rows = _prepare(ledger, sources)
    source_packets = []
    for sid in sorted(sources):
        row = custody[sid]
        source_packets.append({**source_rows[sid], "format": "xml",
            "captured_at": sources[sid]["captured_at"], "raw_bytes": len(raws[sid]),
            "raw_content_base64": base64.b64encode(raws[sid]).decode("ascii"),
            "extracted_document": documents[sid],
            "extracted_sha256": digest(canonical_bytes(documents[sid])),
            "capture_receipt_schema": row["capture_receipt_schema"],
            "capture_receipt": deepcopy(row["capture_receipt"]),
            "capture_receipt_sha256": digest(canonical_bytes(row["capture_receipt"])),
            "extraction_scope": scopes[sid]})
    body = {"schema": SCHEMA, "as_of": as_of, "boundaries": deepcopy(BOUNDARIES),
            "input_ledger": deepcopy(ledger), "input_ledger_sha256": digest(canonical_bytes(ledger)),
            "sources": source_packets, "components": report["obligations"], "events": report["events"],
            "counts": {"sources": len(source_packets), "components": len(report["obligations"]),
                       "events": len(report["events"]),
                       "components_confirmed_by_public_source": report["confirmed_obligation_count"]}}
    value = packet_digest(body)
    result = {**body, "packet_id": "legal-codex-021-" + value[:24], "packet_sha256": value}
    if len(canonical_bytes(result)) > MAX_PACKET_BYTES:
        raise ValueError("packet byte budget exceeded")
    return result


def build_handoff(dutch_folder, finlex_folder, ledger_path, as_of):
    """Build from 020 inputs after receipt verification and raw re-extraction."""
    ledger, sources = load_inputs(dutch_folder, finlex_folder, ledger_path)
    report = evaluate(ledger, sources, as_of)
    visible = _visible_ledger(ledger, report, sources)
    dutch = Path(dutch_folder)
    finnish = Path(finlex_folder)
    receipts = json.loads((dutch / "receipt.json").read_text(encoding="utf-8"))
    rows = {row["source_id"]: row for row in receipts["sources"]}
    rows["finnish_tax_2026"] = json.loads((finnish / "receipt.json").read_text(encoding="utf-8"))
    custody = {}
    for sid in visible["sources"]:
        folder = dutch if sid in DUTCH else finnish
        for suffix in (".xml", ".json"):
            if (folder / (sid + suffix)).is_symlink():
                raise ValueError("source symlink refused")
        raw = (folder / (sid + ".xml")).read_bytes()
        document = json.loads((folder / (sid + ".json")).read_text(encoding="utf-8"))
        receipt_schema = receipts["schema"] if sid in DUTCH else rows[sid]["schema"]
        custody[sid] = {"source_id": sid, "raw_content_base64": base64.b64encode(raw).decode("ascii"),
            "raw_sha256": digest(raw), "raw_bytes": len(raw), "extracted_document": document,
            "extracted_sha256": digest(canonical_bytes(document)), "capture_receipt_schema": receipt_schema,
            "capture_receipt": rows[sid], "capture_receipt_sha256": digest(canonical_bytes(rows[sid]))}
    return _assemble(visible, custody, as_of)


def validate_handoff(packet, *, expected_packet_sha256=None):
    """Rebuild all candidates from embedded original sources and visible ledger.

    The optional expected digest binds a previously selected packet version.
    Hashes alone do not authenticate a person or establish legal meaning. A new
    correctly hashed analyst ledger remains a new unreviewed candidate version.
    """
    if not isinstance(packet, dict) or packet.get("schema") != SCHEMA:
        raise ValueError("wrong portable handoff schema")
    if len(canonical_bytes(packet)) > MAX_PACKET_BYTES:
        raise ValueError("packet byte budget exceeded")
    claimed = packet.get("packet_sha256")
    if claimed != packet_digest(packet):
        raise ValueError("packet digest differs")
    if expected_packet_sha256 is not None and claimed != expected_packet_sha256:
        raise ValueError("packet differs from selected expected digest")
    if packet.get("packet_id") != "legal-codex-021-" + claimed[:24]:
        raise ValueError("packet ID differs from packet digest")
    if packet.get("boundaries") != BOUNDARIES:
        raise ValueError("candidate boundaries changed")
    rows = packet.get("sources")
    if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError("source custody entries required")
    custody = {row.get("source_id"): row for row in rows}
    if len(custody) != len(rows):
        raise ValueError("duplicate source identity")
    ledger = packet.get("input_ledger")
    if not isinstance(ledger, dict) or packet.get("input_ledger_sha256") != digest(canonical_bytes(ledger)):
        raise ValueError("input ledger hash differs")
    rebuilt = _assemble(ledger, custody, packet.get("as_of"))
    if packet != rebuilt:
        raise ValueError("handoff projection differs from source-bound recomputation")
    return rebuilt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dutch-evidence-dir")
    parser.add_argument("--finlex-evidence-dir")
    parser.add_argument("--ledger")
    parser.add_argument("--as-of")
    parser.add_argument("--output")
    parser.add_argument("--verify")
    parser.add_argument("--expected-sha256")
    args = parser.parse_args(argv)
    if args.verify:
        packet = validate_handoff(read_packet(args.verify), expected_packet_sha256=args.expected_sha256)
    else:
        if not all((args.dutch_evidence_dir, args.finlex_evidence_dir, args.ledger, args.as_of, args.output)):
            parser.error("building requires evidence directories, ledger, as-of and output")
        packet = build_handoff(args.dutch_evidence_dir, args.finlex_evidence_dir, args.ledger, args.as_of)
        Path(args.output).write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"packet_id": packet["packet_id"], "packet_sha256": packet["packet_sha256"],
                      **packet["counts"], "candidate_only": True, "publication_authorized": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
