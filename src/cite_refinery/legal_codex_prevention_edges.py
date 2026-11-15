"""Milestone 015: regulatory safeguards linked to concrete failure breakpoints.

The evaluator separates dated domestic legal duties, later judicial
interpretations, and engineered counterfactual controls. It never promotes
law-on-books into law-enforced, foreign analogy into applicable statute, or
a plausible interruption into observed prevention / causal effectiveness.

All case-to-rule edges are auditable candidates with explicit failure stages,
source locators, temporal checks, missing evidence and falsifying examples.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "legal_codex.regulatory_prevention.v1"
CASE_OUTCOMES = {
    "documented_failure_later_quashed",
    "remitted_for_new_decision",
    "judicial_review_recovery_upheld",
    "unresolved_documentary_authority",
    "hypothetical_inference_risk_only",
}
IMPLEMENTATION = {
    "documented_duty_failure", "earlier_interpretation_not_yet_adopted",
    "judicially_considered_no_relief", "unverified",
    "not_historically_implemented", "not_applicable",
}
KINDS = {"statute", "judicial_interpretation", "proposed_workflow"}
TRUSTED_HOSTS = {
    "www.legislation.gov.uk", "www.judiciary.uk", "www.raadvanstate.nl",
    "data.rechtspraak.nl", "peraturan.bpk.go.id",
    "www.hukumonline.com", "www.laporgub.jatengprov.go.id",
    "laporgub.jatengprov.go.id", "www.wetten.overheid.nl",
    "wetten.overheid.nl",
}
PERMITTED_CASE_IMPL = {
    "documented_failure_later_quashed": {"documented_duty_failure",
                                         "not_historically_implemented",
                                         "not_applicable"},
    "remitted_for_new_decision": {"earlier_interpretation_not_yet_adopted",
                                  "unverified", "not_applicable"},
    "judicial_review_recovery_upheld": {"judicially_considered_no_relief",
                                        "not_applicable", "unverified"},
    "unresolved_documentary_authority": {"unverified",
                                         "not_historically_implemented",
                                         "not_applicable"},
    "hypothetical_inference_risk_only": {"unverified", "not_applicable"},
}


def digest(data):
    return hashlib.sha256(json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def _index(items, name):
    if not isinstance(items, list) or not items:
        raise ValueError(name + ": nonempty records required")
    indexed = {}
    for x in items:
        ident = x.get("id") if isinstance(x, dict) else None
        if (not isinstance(ident, str) or len(ident) < 3 or
                not all(c.isalnum() or c == "_" for c in ident) or ident in indexed):
            raise ValueError("invalid or duplicate " + name + " ID")
        indexed[ident] = x
    return indexed


def _date(value):
    if not isinstance(value, str):
        raise ValueError("missing ISO date")
    return date.fromisoformat(value)


def _source(url):
    if not isinstance(url, str):
        raise ValueError("source locator missing")
    p = urlsplit(url)
    if (p.scheme != "https" or p.hostname not in TRUSTED_HOSTS or
            p.username or p.password or p.port not in (None, 443)
            or p.fragment or not p.path.strip("/")):
        raise ValueError("official/legal reporting source provenance invalid")


def _tags(raw, description):
    if not isinstance(raw, list) or not raw or len(raw) != len(set(raw)):
        raise ValueError(description + " incomplete or repeated")
    if not all(isinstance(t, str) and t.replace("_", "").isalnum()
               and len(t) >= 3 for t in raw):
        raise ValueError(description + " malformed")


def validate(bundle):
    if (not isinstance(bundle, dict) or bundle.get("schema") != SCHEMA or
            set(bundle) != {"schema", "as_of", "cases", "instruments", "proposals",
                            "original_bytes_newly_authenticated", "expert_review_completed",
                            "causal_effect_estimated", "individual_liability_proven",
                            "publication_authorized"}):
        raise ValueError("unsupported prevention edge fixture")
    asof = _date(bundle["as_of"])
    if any(bundle[key] is not False for key in (
            "original_bytes_newly_authenticated", "expert_review_completed",
            "causal_effect_estimated", "individual_liability_proven",
            "publication_authorized")):
        raise ValueError("unsupported causal/legal authority promotion")
    cases = _index(bundle["cases"], "case")
    mechanisms = _index(bundle["instruments"], "instrument")
    proposals = _index(bundle["proposals"], "proposal")
    if len({c["jurisdiction"] for c in cases.values()}) < 3:
        raise ValueError("multi-jurisdiction falsification requires three legal systems")
    for case in cases.values():
        if case.get("reported_outcome") not in CASE_OUTCOMES:
            raise ValueError("unverified or mislabelled case outcome")
        start, end = _date(case.get("failure_window_start")), _date(case.get("failure_window_end"))
        if start > end or end > asof:
            raise ValueError("invalid historical case window")
        if not isinstance(case.get("jurisdiction"), str) or not isinstance(case.get("arena"), str):
            raise ValueError("case jurisdiction/arena missing")
        _source(case.get("source_url"))
        _tags(case.get("failure_modes"), "case mechanisms")
        _tags(case.get("checkpoints"), "case intervention checkpoints")
        if (case.get("source_custody") != "existing_public_source_locator_only"
                or case.get("individual_culpability") is not False
                or case.get("exact_original_transaction_verified") is not False
                or not isinstance(case.get("evidence_note"), str)
                or len(case["evidence_note"]) < 55):
            raise ValueError("case evidence status or named liability overclaimed")
        if case["reported_outcome"] == "hypothetical_inference_risk_only" and not case.get("hypothetical"):
            raise ValueError("analytical hazard cannot masquerade as observed violation")
        if case["reported_outcome"] == "unresolved_documentary_authority" and case.get("hypothetical") is not False:
            raise ValueError("unresolved authority records must remain unverified leads")
    for instrument in mechanisms.values():
        if instrument.get("kind") not in KINDS:
            raise ValueError("unrecognized legal instrument type")
        _source(instrument.get("source_url"))
        _tags(instrument.get("addresses"), "rule addressed risks")
        _tags(instrument.get("checkpoints"), "rule checkpoints")
        if not isinstance(instrument.get("jurisdiction"), str) or not isinstance(instrument.get("arena"), str):
            raise ValueError("instrument jurisdiction/arena missing")
        if not isinstance(instrument.get("description"), str) or len(instrument["description"]) < 55:
            raise ValueError("regulation mechanism inadequately described")
        if not isinstance(instrument.get("control_action"), str) or len(instrument["control_action"]) < 45:
            raise ValueError("regulation-to-control operational action missing")
        if not isinstance(instrument.get("missing_implementation_proof"), list) or not instrument["missing_implementation_proof"]:
            raise ValueError("operational proof list missing")
        if any(not isinstance(x, str) or len(x) < 15 for x in instrument["missing_implementation_proof"]):
            raise ValueError("unhelpful operational proof criterion")
        if instrument.get("source_authenticity_claimed") is not False or instrument.get("legal_effect_certified") is not False:
            raise ValueError("legal interpretation or original custody overclaimed")
        effective = instrument.get("effective_from")
        clarified = instrument.get("interpretation_clarified_on")
        if instrument["kind"] == "proposed_workflow":
            if effective is not None or clarified is not None or instrument.get("binding_law") is not False:
                raise ValueError("engineering proposal cannot impersonate an enacted rule")
        else:
            if effective is None or _date(effective) > asof or instrument.get("binding_law") is not True:
                raise ValueError("historical instrument must have a dated legal source")
            if clarified is not None and _date(clarified) < _date(effective):
                raise ValueError("court clarification cannot predate legal instrument")
        if instrument.get("version_limit_note") is None or len(instrument["version_limit_note"]) < 50:
            raise ValueError("historic legal-version limitation missing")
    for proposal in proposals.values():
        case, instrument = cases.get(proposal.get("case_id")), mechanisms.get(proposal.get("instrument_id"))
        if case is None or instrument is None:
            raise ValueError("source and target not in the Legal Codex register")
        if proposal.get("implementation_status") not in IMPLEMENTATION:
            raise ValueError("unknown enforcement evidence state")
        if proposal["implementation_status"] not in PERMITTED_CASE_IMPL[case["reported_outcome"]]:
            raise ValueError("implementation state contradicts documented case outcome")
        if proposal.get("checkpoint") not in case["checkpoints"]:
            raise ValueError("checkpoint not present in target case")
        if (proposal.get("source_url") != case["source_url"] or
                proposal.get("analyst_review_state") != "unreviewed_hypothesis"
                or proposal.get("outcome_prevented") is not False
                or proposal.get("counterfactual_probability") is not None
                or not isinstance(proposal.get("interruption_path"), str)
                or len(proposal["interruption_path"]) < 55):
            raise ValueError("unsupported prevention claim or unverifiable case evidence")
        if not isinstance(proposal.get("missing_evidence"), list) or not proposal["missing_evidence"]:
            raise ValueError("missing counterfactual verification questions")
    return cases, mechanisms, proposals


def _evaluate_proposal(case, instrument, proposal):
    overlap = sorted(set(case["failure_modes"]) & set(instrument["addresses"]))
    stage_aligned = proposal["checkpoint"] in instrument["checkpoints"]
    arena_aligned = case["arena"] == instrument["arena"]
    domestic = case["jurisdiction"] == instrument["jurisdiction"]
    begin, end = _date(case["failure_window_start"]), _date(case["failure_window_end"])
    legal_from = instrument["effective_from"]
    if instrument["kind"] == "proposed_workflow":
        time_status = "not_enacted_historical_counterfactual"
    elif _date(legal_from) > end:
        time_status = "introduced_after_failure"
    elif _date(legal_from) <= begin:
        time_status = "rule_preexisted_failure"
    else:
        time_status = "rule_introduced_during_failure"
    interpretation_date = instrument["interpretation_clarified_on"]
    later_clarification = bool(interpretation_date and _date(interpretation_date) > end)
    status = proposal["implementation_status"]
    if not overlap or not stage_aligned or not arena_aligned:
        determination = "failure_path_or_operational_stage_mismatch"
    elif not domestic:
        determination = "foreign_analogy_not_binding_law"
    elif instrument["kind"] == "proposed_workflow":
        determination = "future_design_candidate_not_historical_law"
    elif time_status == "introduced_after_failure":
        determination = "postevent_remedy_not_historical_prevention"
    elif time_status == "rule_introduced_during_failure":
        determination = "temporal_overlap_requires_case_specific_dates"
    elif later_clarification:
        determination = "preexisting_norm_later_reattributed_by_court"
    elif status == "documented_duty_failure":
        determination = "preexisting_duty_failed_to_prevent"
    elif status == "judicially_considered_no_relief":
        determination = "documented_rule_considered_no_relief"
    else:
        determination = "potential_domestic_safeguard_implementation_unverified"
    stages = {
        "legal_source": instrument["description"],
        "trigger": overlap,
        "decision_checkpoint": proposal["checkpoint"],
        "control_action": instrument["control_action"],
        "conditional_interruption": proposal["interruption_path"],
        "implementation_evidence": status,
        "known_target_outcome": case["reported_outcome"],
    }
    return {
        "proposal_id": proposal["id"], "instrument_id": instrument["id"],
        "case_id": case["id"], "instrument_kind": instrument["kind"],
        "source_url": instrument["source_url"], "target_source_url": case["source_url"],
        "country_scope": "domestic_candidate" if domestic else "foreign_only",
        "arena_match": arena_aligned, "matched_risk_mechanisms": overlap,
        "checkpoint_match": stage_aligned, "temporal_relation": time_status,
        "court_clarified_only_after_target": later_clarification,
        "edge_determination": determination, "intervention_path": stages,
        "missing_required_evidence": list(instrument["missing_implementation_proof"])
            + list(proposal["missing_evidence"]),
        "legally_applicable_to_individual_proven": False,
        "historical_prevention_proven": False,
        "causal_effect_estimated": None,
        "cross_border_rule_applied": False,
        "publication_authorized": False,
    }


def evaluate(bundle):
    cases, instruments, proposals = validate(bundle)
    rows = [_evaluate_proposal(cases[p["case_id"]], instruments[p["instrument_id"]], p)
            for p in sorted(proposals.values(), key=lambda x: x["id"])]
    return {
        "schema": "legal_codex.regulatory_prevention_result.v1",
        "case_count": len(cases), "instrument_count": len(instruments),
        "examined_edge_count": len(rows),
        "rejected_mismatched_edges": sum(
            r["edge_determination"] == "failure_path_or_operational_stage_mismatch"
            for r in rows),
        "foreign_only_edges": sum(
            r["edge_determination"] == "foreign_analogy_not_binding_law"
            for r in rows),
        "paths": rows, "individual_guilt_proven": False,
        "historical_prevention_proven": False,
        "regulation_success_rate": None, "intervention_effect_size": None,
        "legal_publication_authorized": False,
        "input_digest": digest(bundle),
    }


def simulate_authority_gate(*, appointment_original_verified: bool,
                            effective_date_covers_order: bool,
                            role_scope_covers_order: bool,
                            original_purchase_order_verified: bool):
    """Purely synthetic proposed workflow, NOT a rule in Perpres 16/2018.

    A false verification flag means 'not verified', not 'proven nonexistent'.
    """
    values = {
        "signed_appointment_verified": appointment_original_verified,
        "date_window_matches": effective_date_covers_order,
        "delegation_scope_matches": role_scope_covers_order,
        "original_order_identity_matches": original_purchase_order_verified,
    }
    if any(type(v) is not bool for v in values.values()):
        raise ValueError("synthetic gate requires explicit boolean verifications")
    return {
        "schema": "legal_codex.synthetic_procurement_gate.v1",
        "synthetic_only": True, "control_source": "proposed_workflow_not_current_statutory_mandate",
        "result": "permit_simulated_authorization" if all(values.values())
                  else "hold_for_documentary_review",
        "missing_verifications": [k for k, v in values.items() if not v],
        "real_2020_legality_determined": False,
        "actual_person_identity_proven": False,
        "publication_authorized": False,
    }


def semantic_packet(bundle, result):
    if result.get("input_digest") != digest(bundle):
        raise ValueError("stale regulatory review cannot alter semantic graph")
    exact = evaluate(bundle)
    if result != exact:
        raise ValueError("regulatory graph requires independently recomputed result")
    cases, instruments, _ = validate(bundle)
    nodes, edges = [], []
    for c in cases.values():
        nodes.append({
            "key": "case-" + c["id"], "kind": "concept", "layer": "neutral",
            "statement": c["evidence_note"], "source_refs": [c["source_url"]],
            "provenance": {"source_review": "source_attributed_unreviewed",
                           "personal_liability_proven": False},
        })
    for i in instruments.values():
        nodes.append({
            "key": "rule-" + i["id"], "kind": "concept", "layer": "neutral",
            "statement": i["description"], "source_refs": [i["source_url"]],
            "provenance": {"legal_effect_certified": False,
                           "enacted": i["kind"] != "proposed_workflow"},
        })
    for r in result["paths"]:
        if r["edge_determination"] == "failure_path_or_operational_stage_mismatch":
            continue
        nodeid = "control-" + r["proposal_id"]
        nodes.append({
            "key": nodeid, "kind": "concept", "layer": "neutral",
            "statement": r["intervention_path"]["control_action"],
            "source_refs": [r["source_url"]],
            "provenance": {
                "interruption_point": r["intervention_path"]["decision_checkpoint"],
                "legal_analogy_only": r["country_scope"] == "foreign_only",
                "prevention_proven": False,
            },
        })
        edges.extend([
            {"source": "rule-" + r["instrument_id"], "target": nodeid,
             "relation": "PROPOSED_SAFEGUARD_MECHANISM", "status": "candidate"},
            {"source": nodeid, "target": "case-" + r["case_id"],
             "relation": "POTENTIAL_FAILURE_INTERRUPTION", "status": "candidate",
             "provenance": {"legal_effect": r["edge_determination"],
                            "causal_impact_proven": False,
                            "foreign_law_applied": False}},
        ])
    return {
        "schema": "cite_refinery.semantic_graph.v1",
        "source_system": "legal-codex-prevention-015",
        "clusters": [], "nodes": nodes, "edges": edges,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--output", default="legal_codex_prevention_015_result.json")
    p.add_argument("--packet")
    args = p.parse_args(argv)
    b = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = evaluate(b)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2)
                                 + "\n", encoding="utf-8")
    if args.packet:
        Path(args.packet).write_text(json.dumps(
            semantic_packet(b, result), ensure_ascii=False, indent=2
        ) + "\n", encoding="utf-8")
    print(json.dumps({
        "examined_edges": result["examined_edge_count"],
        "failed_or_disproved_prevention_claims": result["rejected_mismatched_edges"],
        "historical_prevention_proven": False,
        "publication_authorized": False,
    }))


if __name__ == "__main__":
    main()
