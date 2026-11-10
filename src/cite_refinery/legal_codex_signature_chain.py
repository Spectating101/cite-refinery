"""Trace named procurement instruments without inventing signatures.

Evidence classes are deliberately conservative:
- official government *reference* to an instrument is not the instrument;
- hearing testimony quoted by a journalist is not a signed appointment;
- third-party transcription of a court exhibit list is not original custody;
- a contract addendum number is not its underlying original purchase order.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
import json
import re

SCHEMA = "legal_codex.signature_chain.v1"
_SOURCE_CLASSES = {
    "official_administrative_response", "reported_witness_testimony",
    "reported_judicial_reasoning", "prosecution_allegation",
    "third_party_court_transcription", "third_party_government_document_copy",
}
_DOC_KINDS = {
    "kpa_appointment_decree", "ppk_replacement_decree", "resignation_letter",
    "kpa_procurement_guideline", "smp_purchase_addendum",
    "original_2020_purchase_order", "court_judgment",
}
_CHANNELS = {
    "sd_2020_budget_office", "sd_2020_school_siplah",
    "sd_2020_directorate_ecatalog", "smp_2020_directorate_ecatalog",
    "sd_2021_policy", "judicial_2026",
}
_REFERENCE_STATES = {"full_reference_reported", "partial_reference_reported",
                     "no_reference_found"}
_FACT_STANCES = {
    "administrative_record_reference", "witness_reported",
    "court_reasoning_reported", "prosecution_allegation",
    "third_party_transcription",
}
_ID = re.compile(r"[a-z][a-z0-9_]{2,79}\Z")
_FULL = re.compile(r"[A-Za-z0-9.-]+(?:/[A-Za-z0-9.-]+){2,}\Z")


def _index(items, label):
    if not isinstance(items, list) or not items:
        raise ValueError(f"{label} records required")
    d = {}
    for row in items:
        key = row.get("id") if isinstance(row, dict) else None
        if not isinstance(key, str) or not _ID.fullmatch(key) or key in d:
            raise ValueError(f"invalid/duplicate {label} id")
        d[key] = row
    return d


def _url(value):
    try:
        u = urlsplit(value)
        return u.scheme == "https" and bool(u.hostname) and not u.username and not u.password
    except (TypeError, ValueError):
        return False


def _date(d):
    if not isinstance(d, str):
        raise ValueError("date is required")
    return date.fromisoformat(d)


def validate(bundle):
    if not isinstance(bundle, dict) or bundle.get("schema") != SCHEMA:
        raise ValueError("invalid signature-chain schema")
    sources = _index(bundle.get("sources"), "source")
    docs = _index(bundle.get("documents"), "document")
    reports = _index(bundle.get("reports"), "report")
    conflicts = _index(bundle.get("conflicts"), "conflict")
    if (bundle.get("signed_instruments_in_hand") != []
            or bundle.get("verified_e_purchase_ids") != []
            or bundle.get("verified_named_signatories") != []):
        raise ValueError("unverified signature or purchase order may not be promoted")
    for key, s in sources.items():
        if (s.get("class") not in _SOURCE_CLASSES or not _url(s.get("url"))
                or s.get("original_legal_document_archived") is not False):
            raise ValueError(f"{key}: invalid source provenance")
        _date(s.get("published_at"))
    for key, doc in docs.items():
        if doc.get("document_kind") not in _DOC_KINDS or doc.get("channel") not in _CHANNELS:
            raise ValueError(f"{key}: invalid legal instrument type or procurement channel")
        if doc.get("locator_source_id") not in sources:
            raise ValueError(f"{key}: unknown source")
        if doc.get("reference_status") not in _REFERENCE_STATES:
            raise ValueError(f"{key}: invalid reference completeness")
        ref = doc.get("reported_reference")
        if doc["reference_status"] == "full_reference_reported":
            if not isinstance(ref, str) or not _FULL.fullmatch(ref):
                raise ValueError(f"{key}: malformed reported instrument reference")
        elif doc["reference_status"] == "partial_reference_reported":
            if not isinstance(ref, str) or not ref.strip() or "/" in ref:
                raise ValueError(f"{key}: ambiguous partial reference must be kept separate")
        elif ref is not None:
            raise ValueError(f"{key}: cannot invent a reference")
        if doc.get("event_date") is not None:
            _date(doc["event_date"])
        if (doc.get("original_instrument_obtained") is not False
                or doc.get("signed_document_verified") is not False
                or doc.get("procurement_package_id_verified") is not False
                or doc.get("actual_signatory") is not None):
            raise ValueError(f"{key}: instrument or signatory not verified")
        if doc.get("evidence_status") != "reported_locator_unverified":
            raise ValueError(f"{key}: external document may not self-certify")
        if doc["document_kind"] == "smp_purchase_addendum" and doc["channel"] != "smp_2020_directorate_ecatalog":
            raise ValueError("SMP addendum cannot be asserted as SD purchase order")
        if doc["document_kind"] == "original_2020_purchase_order" and doc["event_date"] is not None and not doc["event_date"].startswith("2020"):
            raise ValueError("out-of-year purchase order")
    for key, r in reports.items():
        if r.get("source_id") not in sources or r.get("document_id") not in docs:
            raise ValueError(f"{key}: source/document relation missing")
        if r.get("stance") not in _FACT_STANCES:
            raise ValueError(f"{key}: evidence stance unknown")
        if not isinstance(r.get("statement"), str) or len(r["statement"]) < 25:
            raise ValueError(f"{key}: unsupported claim")
        if (r.get("status") != "unreviewed_source_account"
                or r.get("assertion_adjudicated") is not False
                or r.get("legal_guilt_established") is not False):
            raise ValueError(f"{key}: impermissible truth or guilt upgrade")
        if r["stance"] == "court_reasoning_reported" and sources[r["source_id"]]["class"] != "reported_judicial_reasoning":
            raise ValueError("court finding cannot be substituted by prosecution allegation")
        if r["stance"] == "prosecution_allegation" and sources[r["source_id"]]["class"] != "prosecution_allegation":
            raise ValueError("prosecution claim lost attribution")
        if r["stance"] == "administrative_record_reference" and sources[r["source_id"]]["class"] not in {
                "official_administrative_response", "third_party_government_document_copy"}:
            raise ValueError("document reference is not an official administrative report")
    for key, c in conflicts.items():
        ids = c.get("report_ids")
        if (not isinstance(ids, list) or len(ids) < 2
                or any(i not in reports for i in ids)):
            raise ValueError(f"{key}: competing evidence identifiers required")
        if c.get("resolution") != "unresolved_pending_original_court_reasoning":
            raise ValueError(f"{key}: legal reasoning conflict cannot be adjudicated automatically")
        if not isinstance(c.get("question"), str) or len(c["question"]) < 25:
            raise ValueError(f"{key}: conflict question missing")
    return sources, docs, reports, conflicts


def evaluate(bundle):
    sources, docs, reports, conflicts = validate(bundle)
    return {
        "schema": "legal_codex.signature_chain_result.v1",
        "source_count": len(sources), "document_locator_count": len(docs),
        "report_count": len(reports), "competing_account_count": len(conflicts),
        "document_leads": [{
            "id": d["id"], "kind": d["document_kind"],
            "channel": d["channel"], "reported_reference": d["reported_reference"],
            "reference_status": d["reference_status"], "date": d["event_date"],
            "source_url": sources[d["locator_source_id"]]["url"],
            "primary_signed_instrument_verified": False,
            "specific_package_transaction_verified": False,
            "actual_signatory": None,
            "required_next_record": d["required_next_record"],
        } for d in sorted(docs.values(), key=lambda d: d["id"])],
        "competing_accounts": [{
            "id": c["id"], "question": c["question"],
            "accounts": [{
                "id": rid, "stance": reports[rid]["stance"],
                "source_url": sources[reports[rid]["source_id"]]["url"],
                "statement": reports[rid]["statement"],
                "court_original_confirmed": False,
            } for rid in c["report_ids"]],
            "resolution": c["resolution"],
        } for c in conflicts.values()],
        "full_signed_2020_appointment_verified": False,
        "2020_egov_purchase_order_matched": False,
        "name_to_initials_resolution": "candidate_not_established",
        "court_reasoning_is_not_procurement_original": True,
        "reported_resignation_does_not_prove_procedural_compliance": True,
        "published_culpability_finding": None,
        "publication_authorized": False,
    }


def semantic_packet(bundle):
    sources, docs, reports, _ = validate(bundle)
    nodes = [{
        "key": "source-" + x["id"], "kind": "source",
        "layer": "neutral", "statement": x["url"],
        "source_refs": [x["url"]],
        "provenance": {"source_class": x["class"],
                       "original_legal_document_archived": False},
    } for x in sources.values()]
    nodes.extend({
        "key": "document-" + d["id"], "kind": "concept",
        "layer": "neutral", "statement": d["title"],
        "source_refs": [sources[d["locator_source_id"]]["url"]],
        "provenance": {"reported_reference": d["reported_reference"],
                       "document_kind": d["document_kind"],
                       "signed_document_verified": False,
                       "transaction_id_verified": False},
    } for d in docs.values())
    nodes.extend({
        "key": "report-" + r["id"], "kind": "observation",
        "layer": "neutral", "statement": "Source-reported: " + r["statement"],
        "source_refs": [sources[r["source_id"]]["url"]],
        "provenance": {"stance": r["stance"], "assertion_adjudicated": False},
    } for r in reports.values())
    edges = []
    for r in reports.values():
        edges.extend([
            {"source": "source-" + r["source_id"], "target": "report-" + r["id"],
             "relation": "REPORTS", "status": "candidate"},
            {"source": "report-" + r["id"], "target": "document-" + r["document_id"],
             "relation": "CONTEXT_FOR", "status": "candidate"},
        ])
    return {"schema": "cite_refinery.semantic_graph.v1",
            "source_system": "legal-codex-signature-chain",
            "clusters": [], "nodes": nodes, "edges": edges}


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("--output", default="signature_chain_result.json")
    p.add_argument("--packet")
    opts = p.parse_args(argv)
    bundle = json.loads(Path(opts.input).read_text(encoding="utf-8"))
    result = evaluate(bundle)
    Path(opts.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if opts.packet:
        Path(opts.packet).write_text(json.dumps(semantic_packet(bundle), ensure_ascii=False,
                                         indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"document_leads": result["document_locator_count"],
                      "signed_appointments_found": False,
                      "purchase_orders_matched": False, "publication_authorized": False}))


if __name__ == "__main__":
    main()
