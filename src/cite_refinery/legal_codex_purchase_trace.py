"""Channel-aware Chromebook procurement trail; no inferred signatures or bribery.

Contrasts ministry announcements, prosecution allegations, annual performance
self-reports, procurement regulator circulars, and later official oversight.
Do not collapse an APBN school-transfer grant, a school SIPLah order, a
ministry e-catalog purchase, or a 2022 DAK framework into one contract.

Primary procurement identifiers, appointment instruments, purchase order
signatures, invoices, delivery acceptance, and supplier beneficial ownership
remain unverified. This is a *source claim organizer* only.
"""
from __future__ import annotations

import json
import re
import calendar
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "legal_codex.procurement_channel_trace.v1"
SOURCES = {
    "contemporary_ministry_announcement", "retrospective_prosecution_statement",
    "ministry_performance_self_report", "procurement_regulator_circular",
    "official_regulatory_listing", "public_oversight_statement",
}
CHANNELS = {"apbn_directorate_grant_to_school", "school_siplah_purchase",
            "directorate_ecatalog_purchase", "dak_regional_ecatalog",
            "ministerial_policy_or_guideline", "marketplace_registration_not_purchase"}
STATUSES = {"contemporaneous_official_statement", "prosecutor_allegation",
            "ministry_self_report", "regulatory_scope_statement",
            "oversight_statement"}
METRICS = {
    "schools_earmarked_for_grants", "grant_allocation_per_school_idr",
    "output_packages_reported", "announced_package_allocation_idr",
    "reported_program_expenditure_idr", "framework_unit_ceiling_idr",
}
KINDS = {"PA_KPA_PPK_APPOINTMENT", "DIPA_RUP_PACKAGE_ID", "TECHNICAL_KAK_SIGNATURE",
         "E_CATALOG_PURCHASE_ORDER", "SIPLAH_SCHOOL_ORDER", "VENDOR_CONTRACT",
         "DELIVERY_AND_ACCEPTANCE", "BENEFICIAL_OWNERSHIP", "HPS_PRICE_WORKSHEET",
         "SCHOOL_USAGE_EVIDENCE"}
_ID = re.compile(r"[a-z][a-z0-9_]{2,79}\Z")


def _valid_url(s):
    if not isinstance(s, str):
        return False
    try:
        parsed = urlsplit(s)
        return parsed.scheme == "https" and bool(parsed.hostname) and not (
            parsed.username or parsed.password)
    except ValueError:
        return False


def _date(s):
    if not isinstance(s, str):
        raise ValueError("calendar date required")
    return date.fromisoformat(s)


def _latest_source_date(s):
    """Only upper-bound an explicitly month-dated document; never invent a day."""
    if isinstance(s, str) and re.fullmatch(r"\d{4}-\d{2}", s):
        yr, mo = map(int, s.split("-"))
        return date(yr, mo, calendar.monthrange(yr, mo)[1])
    return _date(s)


def _index(rows, label):
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{label} records required")
    out = {}
    for x in rows:
        key = x.get("id") if isinstance(x, dict) else None
        if not isinstance(key, str) or not _ID.fullmatch(key) or key in out:
            raise ValueError(f"invalid or duplicate {label} ID")
        out[key] = x
    return out


def validate(data):
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("unsupported channel-trace schema")
    sources = _index(data.get("sources"), "source")
    channels = _index(data.get("channels"), "channel")
    observations = _index(data.get("observations"), "observation")
    requests = _index(data.get("required_records"), "required-record")
    if data.get("verified_procurement_packages") != []:
        raise ValueError("no verified package IDs or signed procurement instruments supplied")
    if data.get("accepted_signatures") != [] or data.get("verified_contracts") != []:
        raise ValueError("no signed contract or appointment yet independently verified")
    if data.get("state_loss_estimate") is not None:
        raise ValueError("price or grant totals cannot stand in for fiscal loss")
    for key, s in sources.items():
        if s.get("type") not in SOURCES or not _valid_url(s.get("url")):
            raise ValueError(f"{key}: invalid source")
        _latest_source_date(s.get("source_date"))
        if s.get("source_claims_fully_adjudicated") is not False:
            raise ValueError(f"{key}: may not certify source truth")
        if s.get("original_document_archive_status") != "not_archived_in_this_repo":
            raise ValueError(f"{key}: cannot imply original full-record custody")
        capture = s.get("capture_receipt")
        if capture is not None:
            if (capture.get("class") != "nocturnal_private_ci_capture"
                    or type(capture.get("workflow_run")) is not int
                    or not re.fullmatch(r"cap-[a-f0-9]{24}", str(capture.get("capture_id", "")))
                    or not re.fullmatch(r"[a-f0-9]{64}", str(capture.get("raw_sha256", "")))
                    or not re.fullmatch(r"[a-f0-9]{64}", str(capture.get("text_sha256", "")))
                    or not isinstance(capture.get("captured_at"), str)):
                raise ValueError(f"{key}: invalid private Nocturnal capture receipt")

    for key, c in channels.items():
        if c.get("type") not in CHANNELS or not isinstance(c.get("description"), str):
            raise ValueError(f"{key}: invalid purchase channel")
        if len(c["description"]) < 30:
            raise ValueError(f"{key}: channel lacks scope")
        if not isinstance(c.get("year"), int) or not 2018 <= c["year"] <= 2026:
            raise ValueError(f"{key}: invalid channel year")
        if c.get("actual_signing_officer") is not None or c.get("actual_contract_id") is not None:
            raise ValueError(f"{key}: cannot invent officer, signer or contract ID")
        if c.get("source_id") not in sources:
            raise ValueError(f"{key}: unknown channel source")
    for key, o in observations.items():
        src = sources.get(o.get("source_id"))
        c = channels.get(o.get("channel_id"))
        if src is None or c is None:
            raise ValueError(f"{key}: missing claim source or channel")
        when = _date(o.get("event_date"))
        reported = _latest_source_date(src["source_date"])
        if when > reported:
            raise ValueError(f"{key}: source cannot report future event as completed")
        if when.year != c["year"]:
            raise ValueError(f"{key}: observation assigned to wrong procurement year")
        if o.get("stance") not in STATUSES or o.get("review") != "pending":
            raise ValueError(f"{key}: purported finding or unknown evidence class")
        if not isinstance(o.get("statement"), str) or len(o["statement"]) < 40:
            raise ValueError(f"{key}: observation lacks description")
        if o.get("named_signatory_verified") is not False or o.get("legal_breach_verified") is not False:
            raise ValueError(f"{key}: cannot manufacture signature or violation")
        if o["stance"] == "prosecutor_allegation" and src["type"] != "retrospective_prosecution_statement":
            raise ValueError(f"{key}: prosecutor allegation misattributed to independent record")
        if o["stance"] == "ministry_self_report" and src["type"] != "ministry_performance_self_report":
            raise ValueError(f"{key}: performance claim has wrong source type")
        if o["stance"] == "regulatory_scope_statement" and src["type"] not in {
            "official_regulatory_listing", "procurement_regulator_circular"}:
            raise ValueError(f"{key}: regulatory claim misclassified")
        if o["stance"] == "contemporaneous_official_statement" and src["type"] != "contemporary_ministry_announcement":
            raise ValueError(f"{key}: contemporaneous claim not from original source")
        if o["stance"] == "oversight_statement" and src["type"] != "public_oversight_statement":
            raise ValueError(f"{key}: oversight provenance mismatched")
        monetary = o.get("metric")
        if monetary is not None:
            if (not isinstance(monetary, dict) or set(monetary) !=
                    {"kind", "value", "unit", "scope", "verified_transaction_value"}):
                raise ValueError(f"{key}: metric must preserve package units and reporting scope")
            if monetary["kind"] not in METRICS or type(monetary["value"]) is not int or monetary["value"] <= 0:
                raise ValueError(f"{key}: invalid numeric measure")
            if monetary["kind"] in {"grant_allocation_per_school_idr",
                                    "announced_package_allocation_idr",
                                    "reported_program_expenditure_idr", "framework_unit_ceiling_idr"}:
                if monetary["unit"] != "IDR":
                    raise ValueError(f"{key}: price unit mismatch")
            elif monetary["unit"] != "count":
                raise ValueError(f"{key}: count must not be treated as currency")
            if monetary["scope"] not in {"APBN_2020_SD_school_grant", "APBN_2021_SD_package",
                                         "DAK_2022_catalogue_laptop"}:
                raise ValueError(f"{key}: cannot generalize price to a different procurement stream")
            if monetary.get("verified_transaction_value") is not False:
                raise ValueError(f"{key}: reported figure is not individual signed transaction")
            if monetary["kind"] == "framework_unit_ceiling_idr" and (
                    o["stance"] != "regulatory_scope_statement" or c["type"] != "dak_regional_ecatalog"
                    or when.year != 2022):
                raise ValueError("2022 DAK framework ceiling cannot price 2020 school kits")
    for key, req in requests.items():
        if req.get("channel_id") not in channels or req.get("record_kind") not in KINDS:
            raise ValueError(f"{key}: unknown procurement channel or requested record")
        if req.get("status") != "unobtained":
            raise ValueError(f"{key}: receipt of original signed record not established")
        if not isinstance(req.get("reason"), str) or len(req["reason"]) < 20:
            raise ValueError(f"{key}: missing scope of records to seek")
    return sources, channels, observations, requests


def evaluate(data):
    sources, channels, observations, requests = validate(data)
    outputs = []
    for c in sorted(channels.values(), key=lambda x: (x["year"], x["id"])):
        related = sorted((o for o in observations.values() if o["channel_id"] == c["id"]),
                         key=lambda o: (o["event_date"], o["id"]))
        missing = sorted((r for r in requests.values() if r["channel_id"] == c["id"]),
                         key=lambda r: r["id"])
        outputs.append({
            "channel_id": c["id"], "year": c["year"], "purchase_mode": c["type"],
            "context": c["description"],
            "source_observations": [{
                "observation_id": o["id"], "source_url": sources[o["source_id"]]["url"],
                "stance": o["stance"], "reported_event_date": o["event_date"],
                "source_date": sources[o["source_id"]]["source_date"],
                "statement": o["statement"], "metric": o.get("metric"),
                "review": "pending", "legally_established": False,
            } for o in related],
            "missing_documents": [{
                "id": r["id"], "record_kind": r["record_kind"], "reason": r["reason"],
                "status": "unobtained",
            } for r in missing],
            "purchase_order_ids_verified": 0, "signatories_verified": 0,
            "supplier_contracts_verified": 0, "actual_decision_maker": None,
            "transaction_price_verified": False,
        })
    return {
        "schema": "legal_codex.procurement_channel_trace_result.v1",
        "channels": outputs,
        "source_count": len(sources), "observation_count": len(observations),
        "unobtained_records": len(requests),
        "2020_school_grant_is_not_laptop_unit_price": True,
        "2022_catalogue_ceiling_is_not_2020_purchase_price": True,
        "2021_output_package_count_is_not_independent_usage_measure": True,
        "later_vendor_marketplace_designation_is_not_2020_contract_award": True,
        "cross_channel_transactions_reconciled": False,
        "corruption_or_state_loss_established_by_system": False,
        "publication_authorized": False,
    }


def semantic_packet(data):
    """Only candidate *source-reports* links; no claim→actor guilt edges."""
    sources, channels, observations, requests = validate(data)
    nodes = [{
        "key": "source-" + s["id"], "kind": "source", "layer": "neutral",
        "statement": s["url"], "source_refs": [s["url"]],
        "provenance": {"source_class": s["type"], "claims_adjudicated": False},
    } for s in sources.values()]
    nodes += [{
        "key": "channel-" + c["id"], "kind": "concept", "layer": "neutral",
        "statement": c["description"],
        "source_refs": [sources[c["source_id"]]["url"]],
        "provenance": {"year": c["year"], "channel": c["type"],
                       "signatory_verified": False},
    } for c in channels.values()]
    nodes += [{
        "key": "observation-" + o["id"], "kind": "observation",
        "layer": "neutral", "statement": "Attributed " + o["stance"] + ": " + o["statement"],
        "source_refs": [sources[o["source_id"]]["url"]],
        "provenance": {"source_date": sources[o["source_id"]]["source_date"],
                       "event_date": o["event_date"],
                       "metric": o.get("metric"), "review": "pending"},
    } for o in observations.values()]
    edges = []
    for o in observations.values():
        edges.append({
            "source": "source-" + o["source_id"],
            "target": "observation-" + o["id"], "relation": "REPORTS",
            "status": "candidate",
        })
        edges.append({
            "source": "observation-" + o["id"],
            "target": "channel-" + o["channel_id"], "relation": "CONTEXT_FOR",
            "status": "candidate",
        })
    return {
        "schema": "cite_refinery.semantic_graph.v1",
        "source_system": "legal-codex-channel-trace",
        "clusters": [], "nodes": nodes, "edges": edges,
    }


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--output", default="chromebook_channel_trace_result.json")
    p.add_argument("--packet")
    args = p.parse_args(argv)
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = evaluate(data)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.packet:
        Path(args.packet).write_text(
            json.dumps(semantic_packet(data), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
    print(json.dumps({"channels": len(result["channels"]),
                      "missing_documents": result["unobtained_records"],
                      "signatories_verified": 0, "publication_authorized": False}))


if __name__ == "__main__":
    main()
