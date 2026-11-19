"""022 — Source-bound decision checkpoints and *conditional* control replays.

This is NOT a retrospective causal estimate, an original agency event log,
an enactment of new legal duties, a review of criminal guilt or live enforcement.
Court dates and reporter publication dates do not establish first-known times.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from datetime import date
from .legal_codex_source_timeline import load_sources, build as build_timeline
from .legal_codex_source_timeline_catalogue import make_fixture
from .legal_codex_signature_chain import validate as validate_indonesia, evaluate as evaluate_indonesia
from .legal_codex_control_replay import replay as replay_synthetic
from .legal_codex_control_scenarios import scenarios as synthetic_scenarios

SCHEMA = "legal_codex.decision_checkpoint_audit_022.v1"
BOUNDARIES = {
    "original_operational_logs_obtained": False,
    "historical_control_deployment_verified": False,
    "historical_prevention_established": False,
    "live_transaction_executed": False,
    "legal_guilt_inferred": False,
    "court_order_equated_to_cash_payment": False,
    "cross_jurisdiction_law_transplanted": False,
    "publication_authorized": False,
}
# Event ids are bound to verified 017 raw XML paragraphs, not generated names.
NL_CHECKPOINTS = (
    ("nl_application", "assisted_application", "staff_assisted_application",
     "preserve application-field versions and staff-contact provenance before later recovery"),
    ("nl_recovery", "original_recovery", "agency_recovery_decision",
     "check retrievable application provenance and mandate reasoned review for agency record gaps"),
    ("nl_objection", "objection_rejected", "agency_objection_decision",
     "verify hearing notice, response, and decision reasoning; this alone is not a waiver rule"),
    ("nl_district", "district_recovery_upheld", "first_instance_judgment",
     "record that defects were found but recovery was initially upheld"),
    ("nl_appeal", "appeal_zero_recovery", "appellate_judgment",
     "record court-ordered zero recovery, without inferring any refund"),
)
ID_CHECKPOINTS = (
    ("id_appointment", "r_court_handover_missing", "reported_ppk_replacement",
     "require signed role/period/scope evidence before accepting a replacement officer"),
    ("id_order", "r_prosecution_sd_click", "alleged_e_catalog_order",
     "verify proposed package identity and delegated authority before a binding order"),
)
EXPECTED_SYNTHETIC = {
    "valid_purchase": "SIMULATED_COMMIT",
    "missing_appointment": "HOLD_PURCHASE",
    "revocation_after_approval": "HOLD_PURCHASE",
    "changed_package": "HOLD_PURCHASE",
    "late_evidence_no_hindsight": "SIMULATED_COMMIT",
    "agency_record_missing": "HOLD_ADVERSE_COLLECTION",
    "waiver_after_reasoned_review": "NO_COLLECTION_SIMULATED",
    "recovery_after_reasoned_review": "SIMULATED_COLLECTION",
    "missingness_not_considered": "HOLD_ADVERSE_COLLECTION",
}
NL_DOCS = {
    "nl_application": ("original 12 April 2023 application and field/version history",
                       "data_subject_or_verified_representative"),
    "nl_recovery": ("original 5 January 2024 decision inputs, missing-record search/audit and execution ledger",
                    "data_subject_or_verified_representative"),
    "nl_objection": ("28 February contact/waiver record and 18 March objection file",
                     "data_subject_or_verified_representative"),
}
ID_DOCS = {
    "id_appointment": ("signed 30 June 2020 PPK appointment, delegation annex, effective interval and handover record",
                       "official_original_record"),
    "id_order": ("identified SD June 30 2020 e-catalog proposal/order and immutable authorization event",
                 "official_original_record"),
}
NL_SOURCE = "https://data.rechtspraak.nl/uitspraken/content?Id="
DESIGN_SCOPE = "proposed_2026_workflow_not_historical_statutory_mandate"


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _date(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError("invalid source-reported event date")
    return value


def _nl_checkpoint(facts, tag, fact_id, stage, design):
    row = facts[fact_id]
    if row["case_id"] != "benefits_2023":
        raise ValueError("Dutch anchor switched cases")
    _date(row["day"])
    return {
        "id": tag, "case_id": "nl_benefits_2023", "stage": stage,
        "reported_event_day": row["day"], "event_day_basis": row["day_basis"],
        "historical_event_evidence_tier": "published_judicial_account",
        "reported_by": row["source_ecli"], "report_date": row["source_decided_on"],
        "source_url": row["source_url"], "source_paragraph_id": row["paragraph_id"],
        "source_paragraph_sha256": row["paragraph_sha256"],
        "source_original_sha256": row["source_raw_sha256"],
        "judicial_role": row["role"], "event_summary": row["summary"],
        "historical_actor_first_known_at": None, "historical_control_deployed": None,
        "candidate_design": design, "candidate_design_scope": DESIGN_SCOPE,
        "original_agency_decision_log_obtained": False,
    }


def _id_checkpoint(reports, docs, sources, tag, report_id, stage, design):
    row = reports[report_id]
    doc = docs[row["document_id"]]
    source = sources[row["source_id"]]
    if row["assertion_adjudicated"] or row["legal_guilt_established"]:
        raise ValueError("source attribution improperly converted to judicial truth")
    if doc["original_instrument_obtained"] or doc["signed_document_verified"]:
        raise ValueError("unsigned secondary evidence treated as authenticated original")
    if doc["event_date"] != "2020-06-30":
        raise ValueError("other procurement event laundered into June 30")
    return {
        "id": tag, "case_id": "id_sd_ppk_2020", "stage": stage,
        "reported_event_day": "2020-06-30", "event_day_basis": "2026_secondary_account_of_2020",
        "historical_event_evidence_tier": row["stance"],
        "reported_by": row["source_id"], "report_date": source["published_at"],
        "source_url": source["url"], "source_report_id": report_id,
        "source_capture_receipt": deepcopy(source.get("capture_receipt")),
        "event_summary": row["statement"],
        "historical_actor_first_known_at": None, "historical_control_deployed": None,
        "candidate_design": design, "candidate_design_scope": DESIGN_SCOPE,
        "original_procurement_transaction_obtained": False,
        "assertion_adjudicated": False,
    }


def _scenario_matrix():
    scenarios = {s["scenario_id"]: s for s in synthetic_scenarios()}
    result = []
    for name, expected in EXPECTED_SYNTHETIC.items():
        packet = scenarios[name]
        audit = replay_synthetic(packet)
        actual = audit["trace"][-1]["status"]
        if actual != expected:
            raise ValueError("counterfactual regression diverged: " + name)
        result.append({
            "scenario": name, "domain": packet["domain"],
            "synthetic_final_state": actual,
            "source": "016_proposed_control_replay",
            "synthetic_only": True, "historical_case_execution_reconstructed": False,
            "historical_prevention_established": False,
            "trace_head_sha256": audit["result_head_sha256"],
        })
    # A later source cannot retroactively turn earlier held purchases into executed ones.
    late = replay_synthetic(scenarios["late_evidence_no_hindsight"])["trace"]
    if not any(x["status"] == "HOLD_PURCHASE" for x in late) or late[-1]["status"] != "SIMULATED_COMMIT":
        raise ValueError("late-evidence anti-hindsight regression failed")
    return result


def _case_gaps(nl_facts, documents):
    if "appeal_missing_agency_form" not in nl_facts or "appeal_hearing_ground_rejected" not in nl_facts:
        raise ValueError("missing retrospective counterevidence")
    for required in ("d_wahyu_replacement", "d_sd_june30_purchase"):
        d = documents[required]
        if d["original_instrument_obtained"] or d["signed_document_verified"] or d["procurement_package_id_verified"]:
            raise ValueError("Indonesian original unexpectedly verified: revision required")
    return [
        {"case_id": "nl_benefits_2023", "gap_id": "actor_knowledge_2024",
         "historical_record_status": "unverified", "first_known_time": None,
         "later_court_report": nl_facts["appeal_missing_agency_form"]["source_ecli"],
         "later_court_report_date": nl_facts["appeal_missing_agency_form"]["source_decided_on"],
         "cannot_infer": "An unavailable document at appeal was necessarily unavailable or known missing in January 2024."},
        {"case_id": "id_sd_ppk_2020", "gap_id": "signed_ppk_original_and_e_order",
         "historical_record_status": "unverified", "first_known_time": None,
         "later_court_report": None, "later_court_report_date": None,
         "cannot_infer": "Failure to retrieve an original in 2026 proves the officer lacked authority in 2020."},
    ]


def run(evidence_folder, indo_fixture):
    """All historical rows must survive verified 017 and 008 validators."""
    dutch_sources = load_sources(evidence_folder)
    dutch_ledger = build_timeline(make_fixture(dutch_sources), dutch_sources)
    nl_facts = {f["id"]: f for f in dutch_ledger["facts"]}
    if len(nl_facts) != 24:
        raise ValueError("incomplete Dutch research corpus")
    if not isinstance(indo_fixture, dict):
        raise ValueError("Indonesian fixture must be an object")
    validate_indonesia(indo_fixture)
    evaluate_indonesia(indo_fixture)
    reports = {x["id"]: x for x in indo_fixture["reports"]}
    documents = {x["id"]: x for x in indo_fixture["documents"]}
    id_sources = {x["id"]: x for x in indo_fixture["sources"]}
    for cid in ("c_replacement_reason", "c_procedural_handover"):
        if not any(c["id"] == cid and c["resolution"] == "unresolved_pending_original_court_reasoning"
                   for c in indo_fixture["conflicts"]):
            raise ValueError("competing testimony silently resolved")
    checkpoints = (
        [_nl_checkpoint(nl_facts, *x) for x in NL_CHECKPOINTS] +
        [_id_checkpoint(reports, documents, id_sources, *x) for x in ID_CHECKPOINTS]
    )
    nl_cmp = nl_facts["comparator_recovery_upheld"]
    if nl_cmp["case_id"] != "child_budget_2014" or nl_cmp["role"] != "court_order":
        raise ValueError("disconfirming court comparator misclassified")
    exceptions = [
        {"kind": "hearing_breach_did_not_produce_waiver", "basis": "appeal_hearing_ground_rejected",
         "source_url": nl_facts["appeal_hearing_ground_rejected"]["source_url"],
         "source_paragraph_sha256": nl_facts["appeal_hearing_ground_rejected"]["paragraph_sha256"]},
        {"kind": "proportionality_did_not_always_waive_recovery", "basis": nl_cmp["id"],
         "source_url": nl_cmp["source_url"], "source_paragraph_sha256": nl_cmp["paragraph_sha256"]},
        {"kind": "separate_agency_assessment_otherwise_upheld", "basis": "appeal_other_parts_upheld",
         "source_url": nl_facts["appeal_other_parts_upheld"]["source_url"],
         "source_paragraph_sha256": nl_facts["appeal_other_parts_upheld"]["paragraph_sha256"]},
        {"kind": "competing_2020_ppk_replacement_accounts", "basis": "c_replacement_reason",
         "source_url": id_sources["s_trial_hukumonline"]["url"], "source_paragraph_sha256": None},
    ]
    # People and offices are named only as attributed public-source participants.
    # Do not merge the anonymized Dutch claimant with a named person.
    actors = [
        {"id": "id_bambang", "name": "Bambang Hadi Waluyo", "role": "reported former 2020 SD PPK",
         "source_report_ids": ["r_bambang_voluntary_resign", "r_court_resignation_context"],
         "identity_status": "reported_public_identity_not_an_original_appointment_record"},
        {"id": "id_wahyu", "name": "Wahyu Haryadi", "role": "reported replacement 2020 SD PPK",
         "source_report_ids": ["r_court_handover_missing", "r_prosecution_sd_click"],
         "identity_status": "reported_public_identity_not_an_original_appointment_record"},
        {"id": "id_sri", "name": "Sri Wahyuningsih", "role": "reported SD KPA in trial coverage",
         "source_report_ids": ["r_court_handover_missing", "r_ibam_cross_docket"],
         "identity_status": "reported_public_identity_not_a_liability_determination"},
        {"id": "nl_claimant", "name": "anonymous claimant", "role": "claimant in published 2025/2026 proceedings",
         "source_report_ids": [], "identity_status": "anonymity_preserved_do_not_resolve"},
        {"id": "nl_toeslagen", "name": "Dienst Toeslagen", "role": "administrative benefits agency",
         "source_report_ids": [], "identity_status": "named_in_official_judgment"},
    ]
    actor_links = [
        {"from": "id_bambang", "to": "id_wahyu", "relation": "REPORTED_PPK_REPLACEMENT",
         "source_report_ids": ["r_prosecution_removed_for_refusal", "r_court_resignation_context"],
         "competing_accounts": True, "verified_original": False},
        {"from": "id_sri", "to": "id_wahyu", "relation": "REPORTED_KPA_APPOINTMENT_CONTEXT",
         "source_report_ids": ["r_court_handover_missing"],
         "competing_accounts": True, "verified_original": False},
        {"from": "nl_toeslagen", "to": "nl_claimant", "relation": "COURT_REPORTED_BENEFIT_RECOVERY_DECISION",
         "source_report_ids": [], "competing_accounts": False, "verified_original": False},
    ]
    for a in actors:
        if any(rid not in reports for rid in a["source_report_ids"]):
            raise ValueError("public actor role is not attributable to the case ledger")
    for e in actor_links:
        if any(rid not in reports for rid in e["source_report_ids"]):
            raise ValueError("actor relationship lost source attribution")
    targets = []
    for checkpoint, (record, access) in {**NL_DOCS, **ID_DOCS}.items():
        c = next(x for x in checkpoints if x["id"] == checkpoint)
        targets.append({
            "checkpoint_id": checkpoint, "case_id": c["case_id"],
            "record_request": record, "required_access": access,
            "status": "NOT_OBTAINED", "request_sent": False,
            "proof_of_who_knew_what_when": False,
            "source_url": c["source_url"],
        })
    result = {
        "schema": SCHEMA, "method": "retrospective_judicial_chronology_plus_explicit_synthetic_policy_matrix",
        "source_corpus": {"dutch_verified_originals": len(dutch_sources),
                          "dutch_court_anchored_facts": len(nl_facts),
                          "indonesian_source_reports": len(reports),
                          "indonesian_signed_originals": 0},
        "checkpoints": checkpoints, "synthetic_control_outcomes": _scenario_matrix(),
        "actors": actors, "actor_relationships": actor_links,
        "disconfirming_outcomes": exceptions, "missing_originals": _case_gaps(nl_facts, documents),
        "next_original_record_targets": targets,
        "historical_prevention_effect": None,
        "historical_trigger_observability": "unknown",
        "real_transaction_execution_proven_by_replay": False,
        "boundaries": deepcopy(BOUNDARIES),
        "source_identity": {
            "nl_primary_sha256": {sid: s["raw_sha256"] for sid, s in dutch_sources.items()},
            "id_secondary_claims_sha256": digest(indo_fixture),
        },
    }
    result["result_sha256"] = digest(result)
    return result


def semantic_packet(result, *, evidence_folder, indonesia_fixture):
    """Rebuild from source bytes: a recomputed report hash alone is not trust."""
    if not isinstance(result, dict) or result.get("schema") != SCHEMA:
        raise ValueError("wrong audit report")
    if result != run(evidence_folder, indonesia_fixture):
        raise ValueError("source-bound audit differs from independently rebuilt result")
    value = deepcopy(result)
    claimed = value.pop("result_sha256", None)
    if digest(value) != claimed or value.get("boundaries") != BOUNDARIES:
        raise ValueError("modified or promoted audit refused")
    if (value.get("historical_prevention_effect") is not None or
            value.get("historical_trigger_observability") != "unknown"):
        raise ValueError("unverified historical causal or trigger inference")
    nodes, edges = [], []
    for c in value["checkpoints"]:
        source = "source-" + c["id"]
        dest = "checkpoint-" + c["id"]
        nodes += [
            {"key": source, "kind": "source", "layer": "neutral",
             "statement": "Source reporting " + c["stage"], "source_refs": [c["source_url"]]},
            {"key": dest, "kind": "observation", "layer": "neutral",
             "statement": c["event_summary"], "source_refs": [c["source_url"]],
             "provenance": {"event_date": c["reported_event_day"],
                            "evidence_tier": c["historical_event_evidence_tier"],
                            "historical_actor_first_known_at": None,
                            "historical_control_deployed": None}}
        ]
        edges.append({"source": source, "target": dest,
                      "relation": "LATER_SOURCE_REPORTS_CHECKPOINT", "status": "candidate"})
    actor_urls = {c["case_id"]: c["source_url"] for c in value["checkpoints"]}
    actor_map = set()
    for a in value["actors"]:
        if a["id"] in actor_map:
            raise ValueError("duplicate actor identity")
        actor_map.add(a["id"])
        case = "id_sd_ppk_2020" if a["id"].startswith("id_") else "nl_benefits_2023"
        nodes.append({"key": "actor-" + a["id"], "kind": "concept", "layer": "neutral",
                      "statement": "ATTRIBUTED: " + a["name"] + " — " + a["role"],
                      "source_refs": [actor_urls[case]]})
    for e in value["actor_relationships"]:
        if e["from"] not in actor_map or e["to"] not in actor_map or e["verified_original"]:
            raise ValueError("unverified actor relationship promoted to fact")
        edges.append({"source": "actor-" + e["from"], "target": "actor-" + e["to"],
                      "relation": "REPORTED_RELATION_NOT_ORIGINAL_VERIFIED",
                      "status": "candidate"})
    for t in value["next_original_record_targets"]:
        key = "target-" + t["checkpoint_id"]
        nodes.append({"key": key, "kind": "concept", "layer": "neutral",
                      "statement": "UNSENT: " + t["record_request"], "source_refs": [t["source_url"]]})
        edges.append({"source": "checkpoint-" + t["checkpoint_id"], "target": key,
                      "relation": "REQUIRES_ORIGINAL_RECORD_TO_TEST_PROPOSED_CONTROL",
                      "status": "candidate"})
    return {"schema": "cite_refinery.semantic_graph.v1", "source_system": "legal-decision-audit-022",
            "clusters": [], "nodes": nodes, "edges": edges}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dutch-evidence-dir", required=True)
    p.add_argument("--indonesia-fixture", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--packet")
    a = p.parse_args(argv)
    fixture = json.loads(Path(a.indonesia_fixture).read_text(encoding="utf-8"))
    result = run(a.dutch_evidence_dir, fixture)
    Path(a.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if a.packet:
        Path(a.packet).write_text(json.dumps(semantic_packet(result, evidence_folder=a.dutch_evidence_dir,
            indonesia_fixture=fixture), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checkpoints": len(result["checkpoints"]),
                      "synthetic_control_checks": len(result["synthetic_control_outcomes"]),
                      "historical_prevention_effect": None,
                      "original_request_sent": False}))


if __name__ == "__main__":
    main()
