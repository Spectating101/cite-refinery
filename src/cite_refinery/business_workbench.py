"""Local business operating layer for research-to-revenue experiments.

Works DOWNSTREAM of source-bounded opportunity_conversion.evaluate(). Not a CRM,
accounting ledger, contract authenticator, revenue forecast or autonomous agent.
Events are operator-reported and cannot promote independently verified buyer,
technical, rights or commercial readiness.

All local activity records are private by default and chained for accidental
tamper detection. Hash chaining does not authenticate a dishonest operator.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .opportunity_conversion import evaluate

SCHEMA = "cite_refinery.business_plan.v1"
LEDGER_SCHEMA = "cite_refinery.business_activity_ledger.v1"
REPORT_SCHEMA = "cite_refinery.business_board.v1"
ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "research_materials" / "opportunity_conversion"
CASE_ID = re.compile(r"^[a-z][a-z0-9-]{3,89}$")
EVENT_ID = re.compile(r"^[a-z][a-z0-9_-]{5,79}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
KINDS = {
    "buyer_contact_reported", "buyer_response_reported", "pilot_result_reported",
    "cost_reported", "payment_reported", "funding_lead", "decision",
}
CHANNELS = {"service", "implementation", "partnership", "internal_asset"}
DECISIONS = {"continue", "hold", "kill"}
GENESIS = "0" * 64


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def money(value: Any, name: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError(name + " requires decimal currency amount")
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as e:
        raise ValueError(name + " must be decimal") from e
    if not dec.is_finite() or dec < 0 or dec > Decimal("100000000"):
        raise ValueError(name + " outside permitted range")
    if positive and dec <= 0:
        raise ValueError(name + " must be positive")
    if dec != dec.quantize(Decimal("0.01")):
        raise ValueError(name + " supports at most two decimal places")
    return dec


def fmt(amount: Decimal) -> str:
    return format(amount.quantize(Decimal("0.01")), "f")


def validate_plan(plan: Any) -> dict[str, Any]:
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        raise ValueError("Unrecognized business plan schema")
    currency = plan.get("currency")
    if currency not in {"TWD", "USD"}:
        raise ValueError("Business plan currency must be TWD or USD")
    rows = plan.get("opportunities")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 30:
        raise ValueError("Expected 1-30 opportunities")
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Opportunity must be an object")
        cid = row.get("case_id")
        if not isinstance(cid, str) or not CASE_ID.fullmatch(cid) or cid in seen:
            raise ValueError("Invalid or repeated case_id")
        seen.add(cid)
        if row.get("channel") not in CHANNELS:
            raise ValueError("Unrecognized commercial channel")
        money(row.get("validation_budget"), "validation_budget")
        exp = row.get("experiment")
        if not isinstance(exp, dict) or set(exp) != {"question", "success_signal", "stop_signal"}:
            raise ValueError("Experiment must set question, success_signal and stop_signal")
        for field in ("question", "success_signal", "stop_signal"):
            value = exp[field]
            if not isinstance(value, str) or not 20 <= len(value) <= 600:
                raise ValueError("Experiment " + field + " missing or unbounded")
        # Strictly pin business entries to the known, source-bounded casebook.
        source = SOURCE_DIR / (cid + ".json")
        if not source.is_file():
            raise ValueError("Unknown reviewed opportunity case " + cid)
        data = json.loads(source.read_text(encoding="utf-8"))
        if data.get("case_id") != cid:
            raise ValueError("Case file identity mismatch")
        evaluate(data)  # Reject malformed source evidence.
    return plan


def validate_event(event: Any, known_ids: set[str], currency: str) -> dict[str, Any]:
    if not isinstance(event, dict) or set(event) - {
        "event_id", "case_id", "on", "kind", "note", "evidence_url",
        "artifact_sha256", "amount", "currency", "action",
    }:
        raise ValueError("Unsupported event fields")
    eid, cid, kind = event.get("event_id"), event.get("case_id"), event.get("kind")
    if not isinstance(eid, str) or not EVENT_ID.fullmatch(eid):
        raise ValueError("Invalid event_id")
    if cid not in known_ids or kind not in KINDS:
        raise ValueError("Unknown opportunity or event type")
    when = event.get("on")
    if not isinstance(when, str) or not re.fullmatch(r"20\d\d-\d\d-\d\d", when):
        raise ValueError("Event needs ISO date")
    from datetime import date
    try:
        date.fromisoformat(when)
    except ValueError as exc:
        raise ValueError("Impossible event date") from exc
    note = event.get("note")
    if not isinstance(note, str) or not 12 <= len(note.strip()) <= 1000:
        raise ValueError("Event requires bounded explanatory note")
    url = event.get("evidence_url")
    if url is not None and (not isinstance(url, str) or not url.startswith("https://")
                            or len(url) > 2048):
        raise ValueError("Optional evidence_url must be HTTPS")
    sha = event.get("artifact_sha256")
    if sha is not None and (not isinstance(sha, str) or not SHA256.fullmatch(sha)):
        raise ValueError("Invalid local evidence artifact fingerprint")
    if kind in {"cost_reported", "payment_reported"}:
        amount = money(event.get("amount"), "event.amount", positive=True)
        if event.get("currency") != currency:
            raise ValueError("Do not mix currencies without verified FX")
        normalized_amount = fmt(amount)
    else:
        if event.get("amount") is not None or event.get("currency") is not None:
            raise ValueError("Only reported cost/payment events carry monetary amounts")
        normalized_amount = None
    if kind == "decision":
        if event.get("action") not in DECISIONS:
            raise ValueError("Decision requires continue/hold/kill")
    elif "action" in event:
        raise ValueError("Only a decision event may set action")
    normalized = {k: v for k, v in event.items() if v is not None}
    if normalized_amount is not None:
        normalized["amount"] = normalized_amount
    return normalized


def new_ledger(plan: dict[str, Any]) -> dict[str, Any]:
    validate_plan(plan)
    return {
        "schema": LEDGER_SCHEMA, "plan_sha256": digest(plan),
        "currency": plan["currency"], "entries": [], "head_sha256": GENESIS,
        "accounting_boundary": "All events are operator reported, not independent financial verification.",
    }


def validate_ledger(plan: dict[str, Any], ledger: Any) -> dict[str, Any]:
    validate_plan(plan)
    if (not isinstance(ledger, dict) or ledger.get("schema") != LEDGER_SCHEMA
            or ledger.get("plan_sha256") != digest(plan)
            or ledger.get("currency") != plan["currency"]):
        raise ValueError("Activity ledger does not belong to this pinned plan")
    entries = ledger.get("entries")
    if not isinstance(entries, list) or len(entries) > 5000:
        raise ValueError("Activity ledger outside bounds")
    prev, ids = GENESIS, set()
    cases = {row["case_id"] for row in plan["opportunities"]}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"prev_sha256", "entry_sha256", "event"}:
            raise ValueError("Invalid ledger entry")
        event = validate_event(entry["event"], cases, plan["currency"])
        if event["event_id"] in ids:
            raise ValueError("Repeated event identity")
        ids.add(event["event_id"])
        expected = digest({"prev_sha256": prev, "event": event})
        if entry["prev_sha256"] != prev or entry["entry_sha256"] != expected:
            raise ValueError("Ledger hash chain mismatch (may indicate tampering)")
        prev = expected
    if ledger.get("head_sha256") != prev:
        raise ValueError("Ledger head does not match entries")
    return ledger


def append_event(plan: dict[str, Any], ledger: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    validate_ledger(plan, ledger)
    cases = {r["case_id"] for r in plan["opportunities"]}
    clean = validate_event(event, cases, plan["currency"])
    if any(x["event"]["event_id"] == clean["event_id"] for x in ledger["entries"]):
        raise ValueError("Duplicate event ID; no overwrite")
    if len(ledger["entries"]) >= 5000:
        raise ValueError("Ledger full")
    prev = ledger["head_sha256"]
    h = digest({"prev_sha256": prev, "event": clean})
    out = {**ledger, "entries": [*ledger["entries"], {
        "prev_sha256": prev, "entry_sha256": h, "event": clean,
    }], "head_sha256": h}
    validate_ledger(plan, out)
    return out


def build_board(plan: dict[str, Any], ledger: dict[str, Any] | None = None) -> dict[str, Any]:
    validate_plan(plan)
    ledger = new_ledger(plan) if ledger is None else validate_ledger(plan, ledger)
    rows = []
    totals = {"validation_budget": Decimal(0), "reported_cost": Decimal(0),
              "reported_payment": Decimal(0)}
    for spec in plan["opportunities"]:
        cid = spec["case_id"]
        source = json.loads((SOURCE_DIR / (cid + ".json")).read_text(encoding="utf-8"))
        decision = evaluate(source)
        events = [e["event"] for e in ledger["entries"] if e["event"]["case_id"] == cid]
        cap = money(spec["validation_budget"], "validation_budget")
        expenses = sum((money(e["amount"], "expense") for e in events if e["kind"] == "cost_reported"), Decimal(0))
        receipts = sum((money(e["amount"], "payment") for e in events if e["kind"] == "payment_reported"), Decimal(0))
        headroom = max(Decimal(0), cap - expenses)
        human = next((e["action"] for e in reversed(events) if e["kind"] == "decision"), None)
        if human == "kill":
            state = "kill_by_operator"
            next_step = "Stop new work; preserve receipts and document lessons."
        elif expenses >= cap and cap > 0:
            state = "stop_validation_budget"
            next_step = "Stop spending; seek explicit reviewed budget amendment before further work."
        elif human == "hold":
            state = "hold_by_operator"
            next_step = "No work pending explicit operator reassessment."
        elif decision["candidate_asset"]["license_state"] in {"unverified", "no_license_detected"}:
            state = "rights_blocked"
            next_step = decision["recommended_next_test"]
        elif decision["readiness"] != "evidence_lead_only":
            state = "independently_reviewed_pilot_candidate"
            next_step = "Obtain explicit authorization and independently verify contract/economics."
        else:
            state = "research_validation_only"
            next_step = decision["recommended_next_test"]
        blockers = []
        if not decision["buyer"]["demand_attestation_valid"]:
            blockers.append("buyer_and_budget_unverified")
        if not decision["cross_layer_fit"]["execution_attestation_valid"]:
            blockers.append("technical_execution_unattested")
        if not decision["competitive_review"]["attestation_valid"]:
            blockers.append("commercial_substitution_unresolved")
        if decision["conversion_routes"]["self_execution"] != "evaluate_specific_pilot_economics":
            blockers.append("delivery_rights_or_permission_not_cleared")
        if decision["upstream"]["paid_onboarding_requirements"]:
            blockers.append("paid_contributor_onboarding_unconfirmed")
        totals["validation_budget"] += cap
        totals["reported_cost"] += expenses
        totals["reported_payment"] += receipts
        rows.append({
            "case_id": cid, "channel": spec["channel"], "state": state,
            "original_case_sha256": decision["input_sha256"],
            "buyer_stage": decision["buyer"]["verified_demand_status"],
            "documented_technical_fit": decision["cross_layer_fit"]["fit_status"],
            "conversion_readiness": decision["readiness"],
            "commercial_blockers": blockers,
            "experiment": spec["experiment"],
            "next_test": next_step,
            "evidence_source_urls": [r["url"] for r in decision["problem"]["sources"]],
            "competitive_alternatives": decision["competitive_review"]["alternatives"],
            "economics": {
                "currency": plan["currency"],
                "validation_budget": fmt(cap),
                "reported_cost_unreconciled": fmt(expenses),
                "reported_payment_unreconciled": fmt(receipts),
                "validation_budget_remaining": fmt(headroom),
                "illustrative_unit_scenario": (
                    decision["unit_economics"] if decision["unit_economics"]["status"] == "illustrative_unit_scenario"
                    and decision["unit_economics"]["currency"] == plan["currency"] else None
                ),
                "independently_verified_revenue": None,
                "independently_verified_profit": None,
            },
            "activity_count": len(events), "last_operator_decision": human,
        })
    return {
        "schema": REPORT_SCHEMA, "plan_sha256": digest(plan),
        "ledger_head_sha256": ledger["head_sha256"],
        "currency": plan["currency"], "opportunities": rows,
        "total": {**{k: fmt(v) for k, v in totals.items()},
                  "validation_budget_remaining": fmt(max(
                      Decimal(0), totals["validation_budget"] - totals["reported_cost"]))},
        "accounting_boundary": (
            "Amounts recorded by operators are unverified, not recognized income or audited costs. "
            "No currency conversion, forecast revenue, demonstrated ROI, customer contact or real contract "
            "is inferred from GitHub issues, research, simulated scenarios, or local activity events."
        ),
        "funding_boundary": "Funding leads are options, not grants, approved budgets or cash receipts.",
        "private_activity_not_exported": True,
    }


def render_board(report: dict[str, Any]) -> str:
    if report.get("schema") != REPORT_SCHEMA:
        raise ValueError("Not a business workbench report")
    out = ["# Atlas business workbench", "",
           "**Experimental research-to-conversion operating board; not audited finance.**", "",
           "| Opportunity | Route | Gate | Reported costs | Remaining cap | Next check |",
           "| --- | --- | --- | ---: | ---: | --- |"]
    for r in report["opportunities"]:
        next_test = r["next_test"].replace("|", "/")
        if len(next_test) > 95:
            next_test = next_test[:92] + "..."
        e = r["economics"]
        out.append(f"| {r['case_id']} | {r['channel']} | {r['state']} | "
                   f"{e['reported_cost_unreconciled']} | {e['validation_budget_remaining']} | {next_test} |")
    out.extend(["", f"Currency: {report['currency']}. Aggregate planned validation cap: "
                f"{report['total']['validation_budget']}; recorded spend: "
                f"{report['total']['reported_cost']}; recorded payments: "
                f"{report['total']['reported_payment']}.", "",
                "No recorded payment here is recognized as independently verified revenue.", "",
                report["accounting_boundary"], ""])
    return "\n".join(out)
