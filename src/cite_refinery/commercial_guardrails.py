"""Commercial promotion gates for opportunity conversion.

Case JSON is UNTRUSTED, including "reviewed", "signed_contract", and
"executed_local" labels. An authorized external reviewer may sign a bounded
attestation over a case's evidence list or competitor review using a key held
only by the trusted worker. This verifies custody of a review decision, NOT
the truth of a linked document, counterparties or a payment.

No key is stored in this repository. Without verified attestations, promotion
is fail-closed. Report the candidate evidence without granting authority.
"""
from __future__ import annotations

from datetime import date, timedelta
import hashlib
import hmac
import json
import os
import re
from typing import Any

KEY_ENV = "CITE_REFINERY_COMMERCIAL_REVIEW_KEY"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DEMAND_KIND = {
    "expressed_interest": "buyer_statement",
    "funded_request": "funded_procurement",
    "signed_commitment": "signed_contract",
}
KNOWN_SCOPE = {"direct", "partial", "adjacent"}


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _review_valid(envelope: Any, *, purpose: str, case_id: str,
                  subject_sha256: str, urls: set[str],
                  buyer_id: str | None = None) -> tuple[bool, str | None]:
    if not isinstance(envelope, dict) or set(envelope) != {"payload", "signature"}:
        return False, "missing or malformed independent review attestation"
    payload = envelope["payload"]
    if not isinstance(payload, dict) or not isinstance(envelope["signature"], str):
        return False, "malformed review payload"
    if (payload.get("schema") != "cite_refinery.commercial_review_attestation.v1"
            or payload.get("purpose") != purpose
            or payload.get("case_id") != case_id
            or payload.get("subject_sha256") != subject_sha256):
        return False, "review does not bind to this specific case and evidence snapshot"
    if buyer_id is not None and payload.get("buyer_id") != buyer_id:
        return False, "demand and competitor comparison concern different buyers"
    if not isinstance(payload.get("buyer_id"), str) or len(payload["buyer_id"].strip()) < 3:
        return False, "review lacks identified counterparty"
    if not isinstance(payload.get("reviewer_id"), str) or len(payload["reviewer_id"].strip()) < 3:
        return False, "review lacks responsible reviewer"
    source = payload.get("evidence_url")
    if not isinstance(source, str) or source not in urls:
        return False, "review does not bind to cited evidence URL"
    if not isinstance(payload.get("evidence_sha256"), str) or not HEX64.fullmatch(payload["evidence_sha256"]):
        return False, "review does not identify an inspected source snapshot"
    try:
        reviewed = date.fromisoformat(payload["reviewed_on"])
        expires = date.fromisoformat(payload["expires_on"])
    except (ValueError, TypeError, KeyError):
        return False, "review dates are invalid"
    today = date.today()
    if (reviewed > today or today > expires or expires < reviewed
            or expires - reviewed > timedelta(days=180)):
        return False, "review expired, dated in future, or valid too long"
    secret = os.environ.get(KEY_ENV, "")
    if len(secret.encode("utf-8")) < 32:
        return False, "authorized reviewer key unavailable"
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, envelope["signature"]):
        return False, "review signature failed"
    return True, None


def assess(case: dict[str, Any], *, case_id: str, market_signals: list[dict[str, str]]) -> dict[str, Any]:
    market = case["market"]
    claimed = market["demand_status"]
    claimed_kind = DEMAND_KIND.get(claimed)
    demand_valid = False
    demand_reason: str | None = None
    buyer_id: str | None = None
    if claimed_kind:
        citations = {s["url"] for s in market_signals
                     if s["kind"] == claimed_kind and s["status"] == "reviewed"}
        demand_valid, demand_reason = _review_valid(
            market.get("demand_attestation"), purpose="buyer_demand",
            case_id=case_id, subject_sha256=digest(market_signals),
            urls=citations,
        )
        payload = market.get("demand_attestation", {}).get("payload", {}) if isinstance(market.get("demand_attestation"), dict) else {}
        if not isinstance(payload, dict) or payload.get("demand_status") != claimed:
            demand_valid = False
            demand_reason = "review does not attest the claimed demand stage"
        if demand_valid:
            buyer_id = payload["buyer_id"]
    effective = claimed if (claimed_kind is None or demand_valid) else "unverified_claim"

    alternatives = case.get("competitive_alternatives", [])
    if not isinstance(alternatives, list) or len(alternatives) > 20:
        raise ValueError("competitive_alternatives must be a bounded list")
    cleaned = []
    seen = set()
    for alt in alternatives:
        if not isinstance(alt, dict):
            raise ValueError("competitive alternative must be object")
        name, url, scope = alt.get("name"), alt.get("url"), alt.get("scope")
        if (not isinstance(name, str) or not 3 <= len(name.strip()) <= 180
                or not isinstance(url, str) or not url.startswith("https://")
                or not isinstance(scope, str) or scope not in KNOWN_SCOPE):
            raise ValueError("alternative requires name, HTTPS source URL and direct/partial/adjacent scope")
        if url in seen:
            raise ValueError("duplicate competitor URL")
        seen.add(url)
        cleaned.append({"name": name.strip(), "url": url, "scope": scope})

    review = case.get("competitive_review")
    valid_competition = False
    competitor_reason = "No verified buyer-specific comparison against real alternatives."
    assessment = "unreviewed"
    if review is not None:
        if not isinstance(review, dict):
            raise ValueError("competitive_review must be object")
        assessment = review.get("assessment", "unreviewed")
        if assessment not in {"unreviewed", "unresolved", "buyer_verified_differentiation", "no_material_substitute"}:
            raise ValueError("unsupported competitor assessment")
        if assessment == "buyer_verified_differentiation":
            if not cleaned:
                competitor_reason = "Differentiation cannot be established without named alternatives."
            elif not buyer_id:
                competitor_reason = "No independently attested buyer to anchor comparison."
            else:
                urls = {a["url"] for a in cleaned}
                # Review links to an actual competitor's documented offering.
                valid_competition, why = _review_valid(
                    review.get("attestation"), purpose="competitive_differentiation",
                    case_id=case_id, subject_sha256=digest(cleaned),
                    urls=urls, buyer_id=buyer_id,
                )
                competitor_reason = why or "Signed reviewer attestation present; independently audit real customer comparison before contract."
        elif assessment == "no_material_substitute":
            competitor_reason = "Claimed no material substitute; this is not itself verified absence."
        else:
            competitor_reason = "Substitutes still need buyer-specific differentiation assessment."

    return {
        "claimed_demand_status": claimed,
        "effective_demand_status": effective,
        "demand_attestation_valid": demand_valid,
        "demand_verification_limitation": demand_reason or (
            "Signed review attests custody, not contract authenticity; authorization and original evidence still need human audit."
            if demand_valid else "No validated funded buyer or signed commitment."),
        "competitors": cleaned,
        "competitor_assessment": assessment,
        "competitive_attestation_valid": valid_competition,
        "competitive_limitation": competitor_reason,
        "eligible_for_paid_pilot_candidate": (
            effective in {"funded_request", "signed_commitment"} and valid_competition
        ),
    }
