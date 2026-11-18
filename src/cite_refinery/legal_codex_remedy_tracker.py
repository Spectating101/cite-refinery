"""Source-bound, obligation-level remedy tracking; no automatic legal adjudication.

The caller supplies authenticated public-source documents. This module verifies
block bindings, case scope and temporal visibility; event kinds, evidence roles,
publication choices and legal interpretations remain curated analyst inputs.
No state implies possession of claimant files, breach, guilt or penalty accrual.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
import re

SCHEMA = "legal_codex.remedy_ledger_020.v1"
AUTHORITATIVE = {"court_finding", "operative_order", "regulator_finding", "regulator_order"}
ROLES = AUTHORITATIVE | {"court_records_claimant_confirmation", "regulator_records_claimant_confirmation",
    "court_records_controller_submission", "regulator_records_controller_submission",
    "claimant_statement", "controller_statement", "official_execution_record"}
KINDS = {
    "request_reported": "request", "order_reported": "disposition",
    "request_rejected": "disposition", "requirement_reversed": "disposition",
    "further_order_not_issued": "disposition",
    "remedial_decision_reported": "administrative_action",
    "receipt_reported": "delivery", "partial_receipt_reported": "delivery",
    "nonreceipt_reported": "delivery", "adequacy_confirmed": "adequacy",
    "inadequacy_found": "adequacy", "fulfillment_confirmed": "fulfillment",
    "nonfulfillment_confirmed": "fulfillment", "assurance_of_compliance": "assurance",
    "record_unavailable_reported": "availability", "penalty_ordered": "penalty_authority",
    "penalty_declined": "penalty_authority", "penalty_accrual_confirmed": "penalty_accrual",
    "penalty_payment_confirmed": "penalty_payment",
}
CONFIRMATIONS = {"adequacy_confirmed", "inadequacy_found", "fulfillment_confirmed",
    "nonfulfillment_confirmed", "order_reported", "request_rejected", "requirement_reversed",
    "penalty_ordered", "penalty_declined", "further_order_not_issued"}


def _day(value, field):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{field} requires an ISO calendar date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid {field}") from exc


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} requires nonempty text")
    return value


def _flags(value):
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(x, str) and x.strip() for x in value):
        raise ValueError("data_quality_flags must be a list of nonempty strings")
    return list(value)


def _unique(rows, field):
    if not isinstance(rows, list):
        raise ValueError(f"{field} must be a list")
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"malformed {field} entry")
        key = _text(row.get("id"), f"{field}.id")
        if key in result:
            raise ValueError(f"duplicate {field} id: {key}")
        result[key] = row
    return result


def _binding(ref, sources, configured):
    sid = ref.get("source_id")
    if sid not in configured or sid not in sources:
        raise ValueError("unconfigured evidence source")
    blocks = sources[sid].get("blocks", [])
    matches = [b for b in blocks if b.get("id") == ref.get("block_id")]
    if len(matches) != 1 or not matches[0].get("text"):
        raise ValueError("missing, empty or duplicate evidence block")
    block = matches[0]
    actual = hashlib.sha256(block["text"].encode("utf-8")).hexdigest()
    if block.get("sha256") != actual or ref.get("block_sha256") != actual:
        raise ValueError("evidence block hash mismatch")
    return block


def _prepare(ledger, sources):
    if ledger.get("schema") != SCHEMA:
        raise ValueError("wrong remedy ledger schema")
    configured = ledger.get("sources")
    if not isinstance(configured, dict) or not configured:
        raise ValueError("source availability bindings required")
    source_rows = {}
    for sid, selection in configured.items():
        if sid not in sources or not isinstance(selection, dict):
            raise ValueError("source unavailable")
        source = sources[sid]
        when = selection.get("available_on")
        _day(when, "source.available_on")
        _text(selection.get("publication_basis"), "publication_basis")
        basis = selection.get("availability_basis", "publication_metadata")
        if basis == "publication_metadata":
            if when not in source.get("metadata", {}).get("publication_values", []):
                raise ValueError("availability date is not in source publication metadata")
        elif basis == "first_verified_capture":
            if when != source.get("captured_at", "")[:10]:
                raise ValueError("availability date differs from first verified capture")
        else:
            raise ValueError("unknown availability basis")
        if _day(source.get("date"), "source.date") > _day(when, "available_on"):
            raise ValueError("source cannot be publicly known before its own date")
        if not re.fullmatch(r"[0-9a-f]{64}", source.get("raw_sha256", "")):
            raise ValueError("source raw hash required")
        source_rows[sid] = {"source_id": sid, "identity": _text(source.get("identity"), "source.identity"),
            "source_url": _text(source.get("source_url"), "source_url"),
            "raw_sha256": source["raw_sha256"], "source_date": source["date"],
            "available_on": when, "availability_basis": basis,
            "publication_basis": selection["publication_basis"],
            "historical_version_verified": source.get("historical_version_verified") is True,
            "visibility_note": "Known captured version; no earlier public availability inferred." if basis == "first_verified_capture" else
                "Publication-date filter only; historical availability of this exact text requires separate version evidence.",
            "decision_finality": source.get("decision_finality", source.get("metadata", {}).get("decision_finality", "unverified"))}
    obligations = _unique(ledger.get("obligations"), "obligations")
    links = set()
    for link in ledger.get("case_links", []):
        if link.get("relationship") != "reviewed_same_proceeding":
            raise ValueError("citation alone cannot establish a shared proceeding")
        _text(link.get("review_note"), "case link review_note")
        block = _binding(link, sources, configured)
        case_id = _text(link.get("case_id"), "case link case_id")
        if case_id not in block["text"]:
            raise ValueError("reviewed case link lacks literal target case reference")
        links.add((link["source_id"], case_id))

    def check_case(sid, case_id):
        if source_rows[sid]["identity"] != case_id and (sid, case_id) not in links:
            raise ValueError("evidence belongs to a different proceeding")

    for obligation in obligations.values():
        for key in ("case_id", "label", "scope"):
            _text(obligation.get(key), "obligation." + key)
        _flags(obligation.get("data_quality_flags"))
        deadline = obligation.get("deadline")
        if deadline is not None:
            if not isinstance(deadline, dict):
                raise ValueError("deadline must be an object")
            _text(deadline.get("literal"), "deadline.literal")
            basis = deadline.get("basis", {})
            _binding(basis, sources, configured)
            check_case(basis["source_id"], obligation["case_id"])
            if deadline.get("due_on") is not None:
                _day(deadline["due_on"], "deadline.due_on")
                _text(deadline.get("review_note"), "deadline.review_note")
    events = _unique(ledger.get("events"), "events")
    prepared = []
    for event in events.values():
        oid = event.get("obligation_id")
        if oid not in obligations:
            raise ValueError("event refers to unknown obligation")
        kind, role = event.get("kind"), event.get("role")
        if kind not in KINDS or role not in ROLES:
            raise ValueError("unknown event kind or evidence role")
        if kind in CONFIRMATIONS and role not in AUTHORITATIVE:
            raise ValueError("a party assertion cannot be promoted to authoritative confirmation")
        if kind in {"penalty_accrual_confirmed", "penalty_payment_confirmed"} and role not in AUTHORITATIVE | {"official_execution_record"}:
            raise ValueError("penalty execution requires explicit authoritative evidence")
        block = _binding(event, sources, configured)
        sid = event["source_id"]
        check_case(sid, obligations[oid]["case_id"])
        occurred = event.get("occurred_on")
        if "occurred_on" not in event:
            raise ValueError("event.occurred_on must be a date or explicit null")
        if occurred is not None:
            _day(occurred, "event.occurred_on")
            if occurred > source_rows[sid]["available_on"]:
                raise ValueError("event cannot occur after its source became available")
            if occurred > source_rows[sid]["source_date"]:
                raise ValueError("factual event cannot occur after the source decision date")
        _text(event.get("label"), "event.label")
        supersedes = event.get("supersedes", [])
        if not isinstance(supersedes, list) or not all(isinstance(x, str) for x in supersedes) or len(set(supersedes)) != len(supersedes):
            raise ValueError("supersedes must contain unique event IDs")
        for old_id in supersedes:
            old = events.get(old_id)
            if not old or old_id == event["id"] or old.get("obligation_id") != oid or KINDS.get(old.get("kind")) != KINDS[kind]:
                raise ValueError("supersedes must target another event in the same obligation and dimension")
            if not occurred or not old.get("occurred_on") or occurred <= old["occurred_on"]:
                raise ValueError("superseding event requires a strictly later occurrence date")
            if old.get("role") in AUTHORITATIVE and role not in AUTHORITATIVE:
                raise ValueError("party assertion cannot supersede an authoritative finding")
            if old.get("source_id") not in source_rows:
                raise ValueError("superseded evidence source is unconfigured")
            if source_rows[old["source_id"]]["available_on"] > source_rows[sid]["available_on"]:
                raise ValueError("superseding event cannot predate visibility of the original")
        target_id = event.get("fulfills_order_id")
        if target_id is not None:
            target = events.get(target_id)
            if kind not in {"fulfillment_confirmed", "nonfulfillment_confirmed"} or not target or target.get("kind") != "order_reported" or target.get("obligation_id") != oid:
                raise ValueError("fulfillment reference must identify an order for the exact obligation")
            if not occurred or not target.get("occurred_on") or occurred < target["occurred_on"]:
                raise ValueError("fulfillment cannot predate the referenced order")
            if target.get("source_id") not in source_rows or source_rows[target["source_id"]]["available_on"] > source_rows[sid]["available_on"]:
                raise ValueError("fulfillment reference cannot precede visibility of the order evidence")
        prepared.append({**deepcopy(event), "dimension": KINDS[kind],
            "supersedes": list(supersedes), "source_identity": source_rows[sid]["identity"],
            "source_url": source_rows[sid]["source_url"], "source_date": source_rows[sid]["source_date"],
            "available_on": source_rows[sid]["available_on"], "source_quote": block["text"],
            "data_quality_flags": _flags(event.get("data_quality_flags")),
            "independent_legal_interpretation_reviewed": False})
    return obligations, prepared, source_rows


def _binary(kinds, positive, negative, yes, no, unknown="unverified"):
    has_yes, has_no = bool(set(positive) & kinds), bool(set(negative) & kinds)
    return "contested" if has_yes and has_no else yes if has_yes else no if has_no else unknown


def evaluate(ledger, sources, as_of):
    """Evaluate source-date-filtered evidence without inferring missing transitions.

    ``supersedes`` is an explicit curated correction/resolution, never inferred
    from a vote, a later timestamp or a judgment's citation to another case.
    A publication date does not establish historical availability of the exact
    captured text. Capture-bound visibility supports the narrower claim.
    """
    _day(as_of, "as_of")
    obligations, prepared, source_rows = _prepare(ledger, sources)
    visible = [e for e in prepared if e["available_on"] <= as_of and (e.get("occurred_on") is None or e["occurred_on"] <= as_of)]
    rows = []
    for oid, obligation in obligations.items():
        history = sorted((e for e in visible if e["obligation_id"] == oid),
            key=lambda e: (e["available_on"], e.get("occurred_on") or "", e["id"]))
        superseded = {old for e in history for old in e["supersedes"]}
        active = [e for e in history if e["id"] not in superseded]
        kinds = {e["kind"] for e in active}
        dispositions = kinds & {"order_reported", "request_rejected", "requirement_reversed", "further_order_not_issued"}
        disposition = ({"order_reported": "ordered", "request_rejected": "request_rejected",
            "requirement_reversed": "requirement_reversed", "further_order_not_issued": "further_order_not_issued"}.get(next(iter(dispositions)), "requested_only")
            if len(dispositions) == 1 else "contested" if dispositions else "requested_only" if "request_reported" in kinds else "not_established")
        orders = [e for e in active if e["kind"] == "order_reported"]
        dates = [e["occurred_on"] for e in orders if e.get("occurred_on")]
        latest_order = max(dates) if dates and len(dates) == len(orders) else None
        receipts = [e for e in active if e["kind"] in {"receipt_reported", "partial_receipt_reported"}]
        confirmations = [e for e in active if e["kind"] in {"fulfillment_confirmed", "nonfulfillment_confirmed"}]
        current_order_ids = {e["id"] for e in orders if e.get("occurred_on") == latest_order}
        current_confirmations = [e for e in confirmations if not orders or
            (latest_order is not None and e.get("occurred_on") is not None and e["occurred_on"] >= latest_order
             and e.get("fulfills_order_id") in current_order_ids)]
        fulfillment = _binary({e["kind"] for e in current_confirmations}, {"fulfillment_confirmed"},
            {"nonfulfillment_confirmed"}, "confirmed_by_public_source", "nonfulfillment_confirmed_by_public_source")
        # This schema binds each confirmation to one order. It cannot close
        # multiple active orders through the most recent order alone. Explicit
        # supersession can establish which single order remains operative.
        if len(orders) > 1 and fulfillment == "confirmed_by_public_source":
            fulfillment = "unverified"
        delivery = _binary(kinds, {"receipt_reported", "partial_receipt_reported"},
            {"nonreceipt_reported"}, "receipt_reported", "nonreceipt_reported")
        if delivery == "receipt_reported" and "partial_receipt_reported" in kinds:
            delivery = "partial_receipt_reported" if "receipt_reported" not in kinds else "extent_contested"
        adequacy = _binary(kinds, {"adequacy_confirmed"}, {"inadequacy_found"},
            "adequacy_confirmed_by_public_source", "inadequacy_found_by_public_source")
        if fulfillment == "confirmed_by_public_source" and (delivery in {"contested", "extent_contested", "nonreceipt_reported"} or adequacy in {"contested", "inadequacy_found_by_public_source"}):
            fulfillment = "contested"
        deadline = deepcopy(obligation.get("deadline")) if history else None
        deadline_status = "not_specified"
        if deadline:
            basis_visible = source_rows[deadline["basis"]["source_id"]]["available_on"] <= as_of
            if not basis_visible:
                deadline = None
                deadline_status = "not_yet_publicly_evidenced"
        if deadline:
            deadline_status = "not_calculated"
            if deadline.get("due_on"):
                deadline_status = "review_due" if as_of > deadline["due_on"] else "not_due"
            if disposition in {"request_rejected", "requirement_reversed"}:
                deadline_status = "requirement_not_active"
            elif fulfillment == "confirmed_by_public_source":
                deadline_status = "fulfillment_reported"
        rows.append({"id": oid, "case_id": obligation["case_id"], "label": obligation["label"],
            "scope": obligation["scope"], "disposition": disposition, "delivery": delivery,
            "adequacy": adequacy, "fulfillment": fulfillment,
            "remedial_decision_reported": "remedial_decision_reported" in kinds,
            "assurance_reported": "assurance_of_compliance" in kinds,
            "record_unavailable_reported": "record_unavailable_reported" in kinds,
            "penalty_authority": _binary(kinds, {"penalty_ordered"}, {"penalty_declined"}, "ordered", "declined"),
            "penalty_accrual": "confirmed_by_public_source" if "penalty_accrual_confirmed" in kinds else "unverified",
            "penalty_payment": "confirmed_by_public_source" if "penalty_payment_confirmed" in kinds else "unverified",
            "deadline": deadline, "deadline_status": deadline_status,
            "deadline_legal_effect_assessed": False, "deadline_review_marker_only": True,
            "latest_order_on": latest_order,
            "active_order_count": len(orders),
            "pre_order_receipt_ids": [e["id"] for e in receipts if latest_order and e.get("occurred_on") and e["occurred_on"] < latest_order],
            "post_order_receipt_ids": [e["id"] for e in receipts if latest_order and e.get("occurred_on") and e["occurred_on"] >= latest_order],
            "unclassified_receipt_ids": [e["id"] for e in receipts if not latest_order or not e.get("occurred_on")],
            "historical_confirmation_ids": [e["id"] for e in confirmations if e not in current_confirmations],
            "event_ids": [e["id"] for e in history], "active_event_ids": [e["id"] for e in active],
            "superseded_event_ids": sorted(superseded),
            "data_quality_flags": (_flags(obligation.get("data_quality_flags")) if history else []) + [flag for e in history for flag in e["data_quality_flags"]],
            "original_record_custody": False, "breach_inferred_from_elapsed_time": False,
            "intentional_deletion_inferred": False})
    used = {e["source_id"] for e in visible}
    return {"schema": "legal_codex.remedy_tracker_020.v1", "as_of": as_of,
        "sources": [source_rows[sid] for sid in sorted(used)], "obligations": rows,
        "events": visible, "hidden_future_event_count": len(prepared) - len(visible),
        "confirmed_obligation_count": sum(r["fulfillment"] == "confirmed_by_public_source" for r in rows),
        "original_record_custody": False, "operational_replay_allowed": False,
        "independent_legal_interpretation_reviewed": False,
        "method": "Curated source-bound events and obligation-scoped evaluation. Publication-date filtering is not proof of a historical text version; capture-based visibility supports only the verified capture date. No independent semantic entailment validation."}


def semantic_packet(ledger, sources, as_of):
    """Recompute from authenticated source inputs, not an editable result object."""
    report = evaluate(ledger, sources, as_of)
    nodes = [{"key": "source:" + s["source_id"], "kind": "source", "layer": "neutral",
        "statement": s["identity"], "source_refs": [s["source_url"]]} for s in report["sources"]]
    edges = []
    for row in report["obligations"]:
        if not row["event_ids"]:
            continue
        refs = sorted({e["source_url"] for e in report["events"] if e["obligation_id"] == row["id"]})
        nodes.append({"key": "obligation:" + row["id"], "kind": "observation", "layer": "neutral",
            "statement": row["label"], "source_refs": refs,
            "provenance": {"scope": row["scope"], "reported_fulfillment": row["fulfillment"],
                "original_record_custody": False, "independent_legal_review": False}})
    for event in report["events"]:
        key = "event:" + event["id"]
        nodes.append({"key": key, "kind": "observation", "layer": "neutral", "statement": event["label"],
            "source_refs": [event["source_url"]], "provenance": {"event_kind": event["kind"],
                "block_sha256": event["block_sha256"], "available_on": event["available_on"],
                "occurred_on": event.get("occurred_on"), "evidence_role": event["role"]}})
        edges.extend([{"source": "source:" + event["source_id"], "target": key,
            "relation": "REPORTS_SCOPED_REMEDY_EVENT", "status": "candidate"},
            {"source": key, "target": "obligation:" + event["obligation_id"],
            "relation": "CONCERNS_EXACT_OBLIGATION", "status": "candidate"}])
    return {"schema": "cite_refinery.semantic_graph.v1", "source_system": "remedy-tracker-020",
        "clusters": [], "nodes": nodes, "edges": edges}
