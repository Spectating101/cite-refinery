"""Opportunity conversion — from source-bounded problem/implementation fit to a
rights-aware, demand-aware action decision.

No score can prove an "underconverted" project. No public GitHub metadata can
establish revenue, legal rights, willingness to pay, adoption or spare capacity.
This module consumes explicitly attributed observations and never contacts a
buyer, maintainer or repository. Economic scenarios are conditional arithmetic.
"""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlsplit

from .commercial_guardrails import assess as assess_commercial_evidence

SCHEMA = "cite_refinery.opportunity_case.v1"
REPORT = "cite_refinery.opportunity_decision.v1"
SLUG = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{1,100}$")
SCOPE = {"reviewed", "candidate", "reported"}
LICENSE = {"recognized_permissive", "copyleft", "no_license_detected", "unverified"}
FIT = {"untested", "source_reviewed", "executed_local", "independently_replicated"}
ENGAGEMENT = {"none", "public_invitation", "direct_permission"}
BUYER = {"none", "problem_signal", "expressed_interest", "funded_request", "signed_commitment"}


def _str(value: Any, name: str, *, minimum: int = 3, maximum: int = 1200) -> str:
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError(f"{name} missing or invalid")
    return " ".join(value.split())


def _url(url: Any, name: str) -> str:
    url = _str(url, name, minimum=12, maximum=2048)
    parts = urlsplit(url)
    if (parts.scheme != "https" or not parts.netloc or parts.username or parts.password
            or parts.fragment or parts.hostname in {"localhost", "127.0.0.1", "::1"}
            or parts.hostname is None):
        raise ValueError(f"{name} must be an attributed external HTTPS reference")
    return url


def _signals(rows: Any, name: str, *, max_rows: int = 8) -> list[dict[str, str]]:
    if not isinstance(rows, list) or len(rows) > max_rows:
        raise ValueError(f"{name} must be a bounded list")
    out = []
    seen = set()
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("signal must be object")
        url = _url(item.get("url"), name + ".url")
        claim = _str(item.get("claim"), name + ".claim", minimum=12, maximum=600)
        state = item.get("status")
        if state not in SCOPE:
            raise ValueError(f"{name}: signal must disclose reviewed/candidate/reported status")
        key = (url, claim)
        if key in seen:
            raise ValueError("duplicate signal")
        seen.add(key)
        kind = item.get("kind", "context")
        if kind not in {"context", "buyer_statement", "funded_procurement", "signed_contract",
                        "upstream_invitation", "authorization"}:
            raise ValueError("unknown evidence kind")
        out.append({"url": url, "claim": claim, "status": state, "kind": kind})
    return out


def _money(value: Any, name: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{name} missing")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{name} invalid number") from exc
    if not result.is_finite() or result < 0 or result > Decimal("1000000000"):
        raise ValueError(f"{name} out of bounds")
    return result


def _economics(case: dict[str, Any]) -> dict[str, Any]:
    raw = case.get("unit_economics")
    if raw is None:
        return {"status": "not_estimated", "gross_contribution": None,
                "limitation": "No observed selling price or total delivery cost; no revenue projection."}
    if not isinstance(raw, dict) or raw.get("basis") not in {"hypothetical", "verified_contract"}:
        raise ValueError("economics must state hypothetical or verified_contract")
    currency = raw.get("currency")
    if currency not in {"TWD", "USD"}:
        raise ValueError("unit economics supports TWD/USD only")
    price = _money(raw.get("price_per_unit"), "price_per_unit")
    cost = _money(raw.get("cost_per_unit"), "cost_per_unit")
    if price == 0:
        raise ValueError("price must be positive")
    amount = price - cost
    # Verified contracts are not inferred from a label alone.
    if raw["basis"] == "verified_contract":
        if not _signals(raw.get("contract_sources", []), "contract_sources"):
            raise ValueError("verified-contract arithmetic needs an actual reference")
    return {
        "status": "illustrative_unit_scenario" if raw["basis"] == "hypothetical" else "contract_claim_requires_audit",
        "currency": currency,
        "price_per_unit": str(price), "cost_per_unit": str(cost),
        "gross_contribution": str(amount),
        "gross_margin": str((amount / price * 100).quantize(Decimal(".01"))) + "%",
        "limitation": "Gross contribution before fixed costs, tax, acquisition, support, hosting, legal and demand uncertainty. Not actual earned profit.",
    }


def evaluate(case: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(case, dict) or case.get("schema") != SCHEMA:
        raise ValueError("unsupported opportunity case schema")
    case_id = _str(case.get("case_id"), "case_id", minimum=4, maximum=90)
    problem = case.get("problem")
    repo = case.get("repository")
    fit = case.get("fit")
    market = case.get("market")
    if not all(isinstance(v, dict) for v in (problem, repo, fit, market)):
        raise ValueError("case must contain problem, repository, fit, market")
    statement = _str(problem.get("statement"), "problem", minimum=20)
    problem_sources = _signals(problem.get("sources"), "problem.sources")
    if not problem_sources:
        raise ValueError("problem requires an explicit source")
    slug = repo.get("slug")
    if not isinstance(slug, str) or not SLUG.fullmatch(slug):
        raise ValueError("invalid repository slug")
    repo_url = "https://github.com/" + slug
    repo_ref = _url(repo.get("url"), "repository.url")
    if repo_ref.rstrip("/") != repo_url:
        raise ValueError("repository slug and URL disagree")
    repo_description = _str(repo.get("description"), "repository.description", minimum=10, maximum=600)
    repo_source = _url(repo.get("capability_source"), "repository.capability_source")
    if not repo_source.startswith(repo_url + "/"):
        raise ValueError("capability source must be located inside the named repository")
    license_state = repo.get("license_status")
    if license_state not in LICENSE:
        raise ValueError("invalid license confidence")
    if repo.get("license_url") is not None:
        license_url = _url(repo["license_url"], "repository.license_url")
        if not license_url.startswith(repo_url + "/"):
            raise ValueError("license evidence must belong to repository")
    else:
        license_url = None
    if license_state in {"copyleft", "recognized_permissive"} and not license_url:
        raise ValueError("positive license classification requires repository license evidence")
    snapshots = repo.get("github_snapshot", {})
    if not isinstance(snapshots, dict):
        raise ValueError("snapshot must be object")
    if snapshots:
        if snapshots.get("source") != "github_public_repository_metadata":
            raise ValueError("snapshot source unverified")
        ts = _str(snapshots.get("observed_on"), "snapshot observed_on", minimum=10, maximum=40)
        if not re.fullmatch(r"20\d{2}-\d\d-\d\d", ts):
            raise ValueError("snapshot timestamp invalid")
        for k in ("stars", "forks"):
            value = snapshots.get(k)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError("metadata counters must be non-negative integers")
    capability = _str(fit.get("documented_capability"), "fit.documented_capability", minimum=15)
    requirement = _str(fit.get("problem_requirement"), "fit.problem_requirement", minimum=15)
    gap = _str(fit.get("unverified_gap"), "fit.unverified_gap", minimum=15)
    fit_level = fit.get("verification")
    if fit_level not in FIT:
        raise ValueError("invalid fit verification")
    if fit_level == "independently_replicated" and not _signals(fit.get("replication_evidence", []), "replication_evidence"):
        raise ValueError("independent replication requires an externally documented result")
    buyer_segment = _str(market.get("buyer_segment"), "market.buyer_segment", minimum=5, maximum=300)
    demand_level = market.get("demand_status")
    if demand_level not in BUYER:
        raise ValueError("buyer stage invalid")
    market_signals = _signals(market.get("signals"), "market.signals")
    if demand_level != "none" and not market_signals:
        raise ValueError("demand stage requires buyer-relevant evidence")
    if demand_level == "expressed_interest" and not any(
            s["kind"] == "buyer_statement" and s["status"] == "reviewed" for s in market_signals):
        raise ValueError("expressed interest demand stage requires an attributable reviewed buyer statement")
    if demand_level in {"funded_request", "signed_commitment"}:
        needed_kind = "funded_procurement" if demand_level == "funded_request" else "signed_contract"
        if not any(s.get("kind") == needed_kind and s["status"] == "reviewed" for s in market_signals):
            raise ValueError("funded demand requires reviewed procurement/contract evidence, not market commentary")
    commercial = assess_commercial_evidence(case, case_id=case_id, market_signals=market_signals)
    verified_demand = commercial["effective_demand_status"]
    upstream = case.get("upstream")
    if not isinstance(upstream, dict) or upstream.get("engagement") not in ENGAGEMENT:
        raise ValueError("upstream engagement missing")
    upstream_signal = _signals(upstream.get("signals", []), "upstream.signals")
    if upstream["engagement"] != "none" and not upstream_signal:
        raise ValueError("upstream invitation or permission must have a source")
    if upstream["engagement"] == "direct_permission" and not any(
            s["status"] == "reviewed" and s["kind"] == "authorization" for s in upstream_signal):
        raise ValueError("direct upstream permission requires an explicit reviewed authorization record")
    compliance = case.get("compliance")
    if not isinstance(compliance, dict) or not isinstance(compliance.get("rights_reviewed"), bool):
        raise ValueError("compliance needs explicit rights_reviewed flag")
    if not isinstance(compliance.get("deployment_authorized"), bool):
        raise ValueError("deployment authorization must be explicit")
    if compliance["deployment_authorized"] and not compliance["rights_reviewed"]:
        raise ValueError("cannot authorize deployment without documented rights review")
    economic = _economics(case)
    # Strictly separated routes: an AGPL project can be monetized under
    # obligations, but neither a readme nor license badge waives those duties.
    rights_missing = license_state in {"no_license_detected", "unverified"}
    if rights_missing:
        self_route = "blocked_until_rights_resolved"
    elif not compliance["rights_reviewed"]:
        self_route = "conditional_on_license_compliance_review"
    elif not compliance["deployment_authorized"]:
        self_route = "conditional_on_deployment_authorization"
    elif verified_demand not in {"funded_request", "signed_commitment"}:
        self_route = "technical_pilot_possible_buyer_unconfirmed"
    else:
        self_route = "evaluate_specific_pilot_economics"

    paid_invitation = upstream.get("paid_contribution_invitation", False)
    if not isinstance(paid_invitation, bool) or (paid_invitation and upstream["engagement"] != "public_invitation"):
        raise ValueError("paid contributor invitation needs a published and sourced public invitation")
    if paid_invitation and not any(s["kind"] == "upstream_invitation" and s["status"] == "reviewed"
                                   for s in upstream_signal):
        raise ValueError("paid contributor invitation must be explicit and reviewed")
    if upstream["engagement"] == "direct_permission":
        partner_route = "permission_reported_validate_scope_and_terms"
    elif upstream["engagement"] == "public_invitation" and paid_invitation:
        partner_route = "apply_for_published_paid_contributor_process_no_contract"
    elif upstream["engagement"] == "public_invitation":
        partner_route = "community_contribution_invitation_not_a_paid_service"
    else:
        partner_route = "research_upstream_fit_before_permission_request"

    if rights_missing:
        next_action = "Ask maintainer about license/permission; do not copy, deploy or sell the code yet."
    elif commercial["competitors"] and not commercial["competitive_attestation_valid"]:
        next_action = "Compare the existing substitutes with an actual buyer; verify differentiated value and switching costs before commercialization."
    elif paid_invitation:
        next_action = "Check whether the paid contributor application remains open and propose one bounded deliverable."
    elif upstream["engagement"] == "public_invitation":
        next_action = "Verify the named open issue and discuss a minimal, test-backed contribution; payment is unconfirmed."
    elif fit_level == "untested":
        next_action = "Run a minimal capability-to-requirement test before proposing deployment."
    elif demand_level in {"none", "problem_signal"}:
        next_action = "Interview an identifiable buyer/operator and quantify the operational cost of this problem."
    elif upstream["engagement"] == "public_invitation":
        next_action = "Prepare a bounded service proposal against the published contributor/maintainer request."
    elif not compliance["rights_reviewed"]:
        next_action = "Obtain a documented license/compliance review before offering a derived deployment."
    else:
        next_action = "Offer a paid discovery or time-boxed pilot; collect explicit acceptance and cost evidence."

    # A "conversion opportunity" can only be confirmed by execution and
    # customer/maintainer commitments, never stars, README features, or a graph.
    state = "evidence_lead_only"
    if (fit_level in {"executed_local", "independently_replicated"}
            and commercial["eligible_for_paid_pilot_candidate"]):
        state = "candidate_for_paid_pilot_subject_to_contract_and_rights"
    snapshot = {
        "slug": slug, "repository_url": repo_url,
        "description": repo_description,
        "capability_reference": repo_source,
        "license_state": license_state, "license_reference": license_url,
        "github_snapshot": snapshots,
        "caveat": "Repository activity/popularity measures do not establish user adoption, commercial underconversion or profit.",
    }
    digest = hashlib.sha256(json.dumps(case, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "schema": REPORT, "case_id": case_id, "input_sha256": digest,
        "problem": {"statement": statement, "sources": problem_sources},
        "candidate_asset": snapshot,
        "cross_layer_fit": {
            "documented_capability": capability, "required_mechanism": requirement,
            "unverified_gap": gap, "fit_status": fit_level,
            "execution_attestation_valid": commercial["technical_attestation_valid"],
            "execution_verification_limitation": commercial["technical_verification_limitation"],
            "limitation": "A semantic match is not proof of operational implementation, stakeholder fit or economic value.",
        },
        "buyer": {"segment": buyer_segment, "demand_status": demand_level,
                  "verified_demand_status": verified_demand,
                  "demand_attestation_valid": commercial["demand_attestation_valid"],
                  "verification_limitation": commercial["demand_verification_limitation"],
                  "signals": market_signals,
                  "limitation": "The business willingness-to-pay is not inferred from a research problem or popularity counts."},
        "competitive_review": {
            "alternatives": commercial["competitors"],
            "assessment": commercial["competitor_assessment"],
            "attestation_valid": commercial["competitive_attestation_valid"],
            "limitation": commercial["competitive_limitation"],
        },
        "upstream": {"engagement": upstream["engagement"], "signals": upstream_signal,
                     "paid_contribution_invitation": paid_invitation},
        "conversion_routes": {
            "self_execution": self_route, "maintainer_service": partner_route,
            "reuse_as_component": ("blocked_until_rights_resolved" if rights_missing
                                   else "technical_candidate_requires_integration_and_rights_check"),
        },
        "unit_economics": economic, "readiness": state, "recommended_next_test": next_action,
        "underconversion": {
            "status": "not_established",
            "why": "GitHub usage counters and repository feature lists do not establish a monetization gap or economically addressable demand.",
            "alternatives": ["Existing deployments may already serve buyers", "Niche demand may be small",
                             "Maintainers may intentionally reject commercial arrangements",
                             "Market access or service economics may be the binding constraint"],
            "next_evidence": "Interview operators, determine alternatives/budgets, assess conversion rights, and validate adoption economics.",
        },
        "not_proven": [
            "lack of commercial conversion", "buyer willingness-to-pay", "real deployment fitness",
            "capture of economic surplus", "ownership of third-party code",
        ],
        "boundary": "Research/technical reconnaissance only; no partner contact, contract, code reuse, license clearance or customer validation performed.",
    }
