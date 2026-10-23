"""Demand-first public market screening attached to the Atlas business workbench.

This evaluates time-bounded PUBLIC invitations and third-party tender listings.
It deliberately does not transform an advertised budget, optional prize, or
buyer name into a contract, user eligibility, award, expected value or income.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any
from urllib.parse import urlsplit

SCHEMA = "cite_refinery.public_demand_scan.v1"
RESULT = "cite_refinery.public_demand_screen.v1"
TYPES = {"tender", "conditional_prize", "public_contributor_pathway"}
SOURCES = {"first_party", "third_party_listing"}
FIT = {"unvalidated", "mismatch", "validated"}
ELIGIBILITY = {"unverified", "ineligible", "verified_eligible"}
VALUE = {"procurement_budget", "conditional_prize_pool", "conditional_award", "unspecified"}
URL_COUNT_MAX = 7
ISO = re.compile(r"20\d\d-\d\d-\d\d$")
NAME = re.compile(r"^[a-z][a-z0-9_-]{4,79}$")


def _date(value: str, label: str) -> date:
    if not isinstance(value, str) or not ISO.fullmatch(value):
        raise ValueError(label + " must be ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        raise ValueError(label + " invalid date") from e


def _url(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("External source URL required")
    p = urlsplit(value)
    if p.scheme != "https" or not p.hostname or p.username or p.password or p.fragment:
        raise ValueError("Source must be valid public HTTPS URL")
    if p.hostname in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Local/private source URL disallowed")
    return value


def _amt(value: Any) -> str:
    if value is None:
        raise ValueError("Known amount field requires value")
    if isinstance(value, bool):
        raise ValueError("Money cannot be bool")
    try:
        v = Decimal(str(value))
    except (TypeError, InvalidOperation, ValueError) as e:
        raise ValueError("Invalid money amount") from e
    if not v.is_finite() or v < 0 or v > Decimal("100000000000") or v != v.quantize(Decimal(".01")):
        raise ValueError("Currency must be nonnegative finite with max two decimals")
    return f"{v:.2f}"


def validate(scan: Any) -> dict[str, Any]:
    if not isinstance(scan, dict) or scan.get("schema") != SCHEMA:
        raise ValueError("Unknown demand scan schema")
    leads = scan.get("leads")
    if not isinstance(leads, list) or not 1 <= len(leads) <= 30:
        raise ValueError("Demand scan requires 1..30 individual leads")
    seen = set()
    for x in leads:
        if not isinstance(x, dict):
            raise ValueError("Lead must be object")
        lead_id = x.get("lead_id")
        if not isinstance(lead_id, str) or not NAME.fullmatch(lead_id) or lead_id in seen:
            raise ValueError("Malformed or duplicate lead id")
        seen.add(lead_id)
        for f in ("title", "counterparty", "demand_summary", "next_evidence", "reason_to_investigate"):
            value = x.get(f)
            if not isinstance(value, str) or not 15 <= len(value) <= 1000:
                raise ValueError("Missing/bad " + f)
        if x.get("kind") not in TYPES or x.get("authority") not in SOURCES:
            raise ValueError("Lead type/authority not documented")
        for f in ("listing_url", "terms_url"):
            _url(x.get(f))
        if x.get("capability_fit") not in FIT or x.get("eligibility") not in ELIGIBILITY:
            raise ValueError("Fit/eligibility state invalid")
        if not isinstance(x.get("cost_to_attempt_known"), bool):
            raise ValueError("Explicit attempt-cost observability required")
        if x.get("commitment_status") != "no_signed_customer_contract":
            raise ValueError("This unverified public notice intake cannot declare signed contracting")
        _date(x.get("posted_on"), "posted_on")
        _date(x.get("deadline"), "deadline")
        _date(x.get("checked_on"), "checked_on")
        money = x.get("advertised_value")
        if not isinstance(money, dict) or money.get("kind") not in VALUE:
            raise ValueError("Value must be explicitly classified, never inferred revenue")
        if money["kind"] == "unspecified":
            if money.get("amount") is not None or money.get("currency") is not None:
                raise ValueError("Unspecified cannot contain amount")
        else:
            if money.get("currency") not in {"TWD", "USD", "EUR"}:
                raise ValueError("Unsupported currency")
            _amt(money.get("amount"))
        bars = x.get("known_barriers")
        if not isinstance(bars, list) or len(bars) > 12 or not all(
            isinstance(v, str) and 12 <= len(v) <= 400 for v in bars
        ):
            raise ValueError("Barriers must be disclosed bounded strings")
    return scan


def screen(scan: dict[str, Any], *, as_of: str) -> dict[str, Any]:
    validate(scan)
    today = _date(as_of, "as_of")
    decisions = []
    for x in scan["leads"]:
        deadline = _date(x["deadline"], "deadline")
        checked = _date(x["checked_on"], "checked_on")
        stale = (today - checked).days > 7 or checked > today
        days = (deadline - today).days
        reason = []
        if days < 0:
            status = "expired_no_submission"
            next_action = "Do not submit after the documented deadline; verify any genuine extension from the official issuer."
            reason.append("expired_deadline")
        elif x["capability_fit"] == "mismatch":
            status = "reject_scope_mismatch"
            next_action = "Do not spend bid or implementation effort on a capability mismatch."
            reason.append("portfolio_not_a_demonstrated_supplier")
        elif x["eligibility"] == "ineligible":
            status = "reject_ineligible"
            next_action = "Do not represent the operator as an eligible applicant."
            reason.append("eligibility_not_met")
        elif x["authority"] != "first_party" or stale:
            status = "verify_primary_notice"
            next_action = "Obtain the original issuer notice, documents, current deadline and qualification rules before action."
            reason.append("third_party_or_stale_source")
        elif x["eligibility"] != "verified_eligible":
            status = "hold_eligibility"
            next_action = "Verify operator's legal and program eligibility before any application or development."
            reason.append("no_documented_eligibility")
        elif x["capability_fit"] != "validated":
            status = "investigate_no_build"
            next_action = x["next_evidence"]
            reason.append("capability_not_validated")
        elif x["kind"] == "conditional_prize":
            status = "optional_competition_not_contract"
            next_action = "Verify assignment, originality and submission terms; proceed only if cost and time are justified without any assumed prize."
            reason.append("prize_is_conditional_not_payable_on_submission")
        else:
            status = "eligible_for_manual_diligence_only"
            next_action = "Review full official scope, qualifications, competition, cost and contract terms before any bid."
            reason.append("does_not_equal_contract_or_income")
        # Priority expressly never follows the raw advertised budget.
        decisions.append({
            "lead_id": x["lead_id"],
            "counterparty": x["counterparty"],
            "title": x["title"],
            "status": status,
            "reason_codes": reason,
            "deadline": x["deadline"],
            "days_until_deadline": days,
            "source_authority": x["authority"],
            "advertised_value": {
                **x["advertised_value"],
                "limitation": ("Public budget/prize figure only. Not awarded, receivable, "
                               "probability-weighted, net income, bid eligibility or verified profit."),
            },
            "capability_fit": x["capability_fit"],
            "eligibility": x["eligibility"],
            "attempt_cost_observed": x["cost_to_attempt_known"],
            "known_barriers": x["known_barriers"],
            "next_action": next_action,
            "listing_url": x["listing_url"],
            "official_terms_url": x["terms_url"],
            "buyer_contract_verified": False,
            "expected_profit": None,
            "award_probability": None,
        })
    fingerprint = hashlib.sha256(json.dumps(scan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "schema": RESULT, "as_of": as_of, "scan_sha256": fingerprint,
        "leads": decisions,
        "pursue_now_count": 0,
        "verified_contract_count": 0,
        "realized_revenue": None,
        "method": "source-status and constraint-driven triage; not independent verification of a procurement filing",
        "limitations": [
            "Public procurement budgets and conditional prize pools are not customer contracts.",
            "Actual operator eligibility, legal entity, tax status and delivery capacity were not verified.",
            "Third-party listings must be checked against original issuer records and updated deadlines.",
            "No expected value, bid price, assumed win rate, revenue or margin is generated.",
            "No applications, submissions, issue assignments, third-party outreach or payments performed.",
        ],
    }


def render(report: dict[str, Any]) -> str:
    if report.get("schema") != RESULT:
        raise ValueError("Unexpected market screen report")
    rows = ["# Demand-first opportunity screen", "",
            f"Screen date: {report['as_of']}. **No bids, payouts or contracts verified.**", "",
            "| Lead | Source | Gate | Deadline | Next step |",
            "| --- | --- | --- | --- | --- |"]
    for x in report["leads"]:
        rows.append(
            f"| {x['title'].replace('|','/')} | {x['source_authority']} | {x['status']} "
            f"| {x['deadline']} | {x['next_action'].replace('|','/')} |"
        )
    rows += ["", "No advertised tender budget or competition award is included in projected revenue.",
             "The list is a research queue only; unknown eligibility and customer demand remain blockers.", ""]
    return "\n".join(rows)
