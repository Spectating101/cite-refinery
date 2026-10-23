"""Original-issue paid-work preflight: fail closed before any bounty coding.

Research fixture metadata is operator-supplied, not an authenticated live GitHub
feed. A link or bounty label is NOT escrow, available assignment, payout or
permission. This stage cannot claim, comment, fork, contact a sponsor or code.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from urllib.parse import urlsplit
from typing import Any

SCHEMA = "cite_refinery.paid_work_preflight.v1"
REPORT = "cite_refinery.paid_work_preflight_report.v1"
ID = re.compile(r"^[a-z][a-z0-9_-]{4,90}$")
ORIGINAL_ISSUE = re.compile(r"^https://github[.]com/([^/]+)/([^/]+)/issues/([0-9]+)$")
REVIEW = {"verified", "unverified"}
PAYMENT = {"unknown", "self_reported", "independently_confirmed"}
HARDWARE = {"none", "required_verified", "required_unverified"}
CLAIM = {"unknown", "unclaimed", "assigned_to_other", "assigned_to_operator"}
FIT = {"unknown", "documented", "not_fit"}


def _iso(x: Any) -> date:
    if not isinstance(x, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", x):
        raise ValueError("Date must be YYYY-MM-DD")
    try:
        return date.fromisoformat(x)
    except ValueError as e:
        raise ValueError("Invalid calendar date") from e


def _url(x: Any) -> str:
    if not isinstance(x, str) or len(x) > 2048:
        raise ValueError("Source URL missing")
    p = urlsplit(x)
    if p.scheme != "https" or not p.hostname or p.username or p.password or p.fragment:
        raise ValueError("Source must be HTTPS")
    return x


def _amount(x: Any) -> str:
    if isinstance(x, bool):
        raise ValueError("Invalid advertised amount")
    try:
        v = Decimal(str(x))
    except (TypeError, InvalidOperation, ValueError) as e:
        raise ValueError("Invalid advertised amount") from e
    if not v.is_finite() or v <= 0 or v > 10000000 or v != v.quantize(Decimal("0.01")):
        raise ValueError("Advertised amount must be positive finite USD with 2 decimals")
    return format(v.quantize(Decimal("0.01")), ".2f")


def validate(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("Wrong paid-work scan schema")
    listings = data.get("listings")
    if not isinstance(listings, list) or not 1 <= len(listings) <= 30:
        raise ValueError("Scan must include 1..30 listings")
    seen = set()
    for x in listings:
        if not isinstance(x, dict):
            raise ValueError("Listing must be object")
        key = x.get("lead_id")
        if not isinstance(key, str) or not ID.fullmatch(key) or key in seen:
            raise ValueError("Duplicate/invalid paid-work identity")
        seen.add(key)
        original = x.get("original_issue_url")
        if not isinstance(original, str) or not ORIGINAL_ISSUE.fullmatch(original):
            raise ValueError("A DIRECT original GitHub issue URL is required; aggregator copies cannot be primary")
        if x.get("issue_state") not in {"open", "closed"}:
            raise ValueError("Original issue open/closed state required")
        if x.get("claimed_status") not in CLAIM or x.get("technical_fit") not in FIT:
            raise ValueError("Claim status and tech fit required")
        if x.get("hardware") not in HARDWARE:
            raise ValueError("Specific hardware access must be disclosed")
        if x.get("payment_state") not in PAYMENT:
            raise ValueError("Payment confirmation status required")
        if x.get("payment_promise") not in {"after_merge", "upon_acceptance", "unknown"}:
            raise ValueError("Payout conditions missing")
        if x.get("payout_rail") not in {"sponsor_direct", "provider", "unknown"}:
            raise ValueError("Payout route unspecified")
        for b in ("payout_rail_checked", "operator_can_receive_payout",
                  "original_issue_checked", "known_active_submission"):
            if not isinstance(x.get(b), bool):
                raise ValueError("Boolean preflight requirement: " + b)
        for field in ("title", "scope", "payment_limitation", "next_verification"):
            if not isinstance(x.get(field), str) or not 15 <= len(x[field]) <= 900:
                raise ValueError("Invalid or missing " + field)
        if x.get("currency") != "USD":
            raise ValueError("Only explicit USD nominal bounty values supported")
        _amount(x.get("advertised_amount"))
        comments = x.get("issue_comment_count")
        if isinstance(comments, bool) or not isinstance(comments, int) or not 0 <= comments <= 1000000:
            raise ValueError("Original-issue comment count required")
        _iso(x.get("last_checked_on"))
        sources = x.get("sources")
        if not isinstance(sources, list) or not 1 <= len(sources) <= 8:
            raise ValueError("At least one original-source receipt required")
        parsed = {_url(s) for s in sources}
        if original not in parsed:
            raise ValueError("Original issue is not in evidence URLs")
        if x["payment_state"] == "independently_confirmed" and len(parsed) < 2:
            raise ValueError("Independent payment verification needs distinct primary payment record")
        if x.get("payment_claim_disputed") not in {True, False}:
            raise ValueError("Payment contradiction flag required")
        if x.get("prior_success_receipt") is not None:
            _url(x["prior_success_receipt"])
    return data


def evaluate(data: dict[str, Any], *, as_of: str) -> dict[str, Any]:
    validate(data)
    today = _iso(as_of)
    outputs = []
    for x in data["listings"]:
        observed = _iso(x["last_checked_on"])
        stale = (today - observed).days > 2 or observed > today
        risk = []
        if not x["original_issue_checked"] or stale:
            gate = "hold_refresh_original_issue"
            risk.append("stale_or_unverified_original_issue")
        elif x["issue_state"] == "closed":
            gate = "reject_closed_issue"
            risk.append("original_issue_closed")
        elif x["claimed_status"] == "assigned_to_other":
            gate = "reject_already_assigned"
            risk.append("no_available_assignment")
        elif x["technical_fit"] == "not_fit":
            gate = "reject_capability_mismatch"
            risk.append("solution_not_proven")
        elif x["hardware"] == "required_unverified":
            gate = "hold_hardware_validation"
            risk.append("required_hardware_unverified")
        elif x["payment_claim_disputed"]:
            gate = "reject_payment_discrepancy"
            risk.append("offer_and_payment_provider_conflict")
        elif x["issue_comment_count"] > 100:
            gate = "reject_crowded_unverified_rail"
            risk.append("crowded_issue_and_nonexclusive_work")
        elif x["payout_rail"] == "unknown" or not x["payout_rail_checked"] or x["payment_state"] != "independently_confirmed":
            gate = "hold_payment_evidence"
            risk.append("payout_custody_or_sponsor_obligation_unverified")
        elif not x["operator_can_receive_payout"]:
            gate = "hold_payout_eligibility"
            risk.append("payment_recipient_eligibility_not_verified")
        elif x["technical_fit"] != "documented":
            gate = "hold_technical_fit"
            risk.append("implementation_not_qualified")
        elif x["claimed_status"] not in {"unclaimed", "assigned_to_operator"}:
            gate = "hold_assignment"
            risk.append("assignment_right_unverified")
        else:
            gate = "manual_claim_review_only"
            risk.append("reward_is_not_guaranteed_or_receivable")
        outputs.append({
            "lead_id": x["lead_id"],
            "title": x["title"],
            "original_issue_url": x["original_issue_url"],
            "issue_state": x["issue_state"],
            "gate": gate,
            "risk_codes": risk,
            "nominal_bounty": {"currency": "USD", "amount": _amount(x["advertised_amount"]),
                               "value_type": "contingent_advertised_bounty_not_earned"},
            "payment_verified": x["payment_state"] == "independently_confirmed",
            "claim_eligibility_confirmed": x["claimed_status"] in {"unclaimed", "assigned_to_operator"},
            "competition_proxy_issue_comments": x["issue_comment_count"],
            "competition_proxy_limitation": "Comments are not a count of competing PRs or verified submissions.",
            "payout_mechanics_limitation": x["payment_limitation"],
            "next_verification": x["next_verification"],
            "recorded_earned_income": None,
            "expected_value": None,
            "recommended_work_start": False,
        })
    return {
        "schema": REPORT,
        "as_of": as_of,
        "scan_sha256": hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "listings": outputs,
        "ready_to_code_count": 0,
        "verified_paid_contract_count": 0,
        "actual_earnings": None,
        "limitations": [
            "The original issue and provider terms must be rechecked before acting.",
            "A bounty label is not escrow, assignment, guarantee or recognized earned revenue.",
            "Even manual claim review never auto-authorizes submission, coding, payment, public comments or customer contact.",
            "Provider payment terms may contradict sponsor assertions; contradictions block work.",
            "No legal, work-permit or cross-border payout eligibility established by this screen.",
            "Nominal reward divided by imagined hours or acceptance rates is not reliable expected ROI.",
        ],
    }


def render(report: dict[str, Any]) -> str:
    if report.get("schema") != REPORT:
        raise ValueError("Not a paid-work report")
    lines = ["# Public paid-work bounty preflight", "",
             "**Source-dated research only; no claim, accepted contract or earned income.**", "",
             "| Original task | Advertised | Gate | Blocker |",
             "| --- | ---: | --- | --- |"]
    for r in report["listings"]:
        lines.append(f"| {r['title'].replace('|', '/')} | "
                     f"USD {r['nominal_bounty']['amount']} | {r['gate']} | {', '.join(r['risk_codes'])} |")
    lines.extend(["", "No payout, win probability, gross margin or return is inferred.", ""])
    return "\n".join(lines)
