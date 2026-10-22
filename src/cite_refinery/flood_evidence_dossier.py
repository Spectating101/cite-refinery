"""Evidence-bounded first Atlas opportunity dossier: flood warning.

Reconstructs PREEXISTING, limited development receipts. Does not independently
replay upstream code, query live hydrology, or promote cross-layer source matches.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
import argparse
import json

SCHEMA = "cite_refinery.flood_early_warning_opportunity_dossier.v1"
ALIGNMENT_SCHEMA = "cite_refinery.cross_layer_alignment.v1"
TRIAL_SCHEMA = "cite_refinery.functional_component_trials.v1"
QUEUE_SCHEMA = "cite_refinery.conversion_qualification_queue.v1"
READING = "OA-f84a08fcbd0caa"
REVIEW_DOI = "https://doi.org/10.3390/hydrology9030050"
WHO = "OFFICIAL-f3e30d7ac5a5"
WHO_URL = ("https://www.who.int/news-room/feature-stories/detail/"
           "the-importance-of-preparedness--strengthening-community-resilience-against-flash-floods")
ASSET = "github:WeixuanZ/flood-warning-system"
SOURCE_COMMIT = "c1c7facf2c5577a155edd93a0b7279ad7630518c"
EVIDENCE_STATUSES = {"pass", "fail", "blocked", "not_tested"}
REQUIRED_FIXTURES = {
    "threshold_selection": "pass",
    "missing_level_handling": "pass",
    "invalid_typical_range_handling": "pass",
    "nonfinite_sensor_level_is_excluded": "fail",
    "nonfinite_station_corrupts_top_one_ordering": "fail",
    "local_warning_distribution_and_health_outcomes": "not_tested",
}


def _require(test, msg):
    if not test:
        raise ValueError(msg)


def _load(path):
    p = Path(path)
    _require(p.is_file() and not p.is_symlink() and p.stat().st_size < 7_000_000,
             "Invalid or oversized original development receipt")
    return json.loads(p.read_text("utf-8"))


def _canon(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _unique_row(rows, key, value):
    candidates = [x for x in rows if x.get(key) == value]
    _require(len(candidates) == 1, "Missing or ambiguous source anchor: " + value)
    return candidates[0]


def _perspective(item, layer, sid, url):
    row = _unique_row(item["perspectives"][layer], "source_id", sid)
    _require(row["source_url"] == url and row.get("source_caveat"),
             "Original cross-layer source identity or caveat changed")
    return row


def build_dossier(alignment, trial_report, queue, *, reading=None):
    """Reconcile original authority scopes and reject unsupported promotion."""
    _require(alignment.get("schema") == ALIGNMENT_SCHEMA
             and alignment.get("authority") == "MODEL_GENERATED_HYPOTHESIS_ONLY"
             and trial_report.get("schema") == TRIAL_SCHEMA
             and queue.get("schema") == QUEUE_SCHEMA,
             "Requires the actual archived non-promoted development artifacts")
    candidates = alignment.get("alignments", [])
    early = _unique_row(candidates, "id", "alignment-1")
    integrated = _unique_row(candidates, "id", "alignment-2")
    for row in (early, integrated):
        _require(row.get("status") == "llm_candidate_requires_independent_source_review"
                 and row.get("outcome_verified") is False,
                 "Existing cross-layer hypothesis has been incorrectly promoted")
    who = _perspective(early, "program", WHO, WHO_URL)
    reviewed = _perspective(integrated, "academic", READING, REVIEW_DOI)
    _require(not early["perspectives"].get("practical"),
             "Original absence of independent Practical source overwritten")
    if reading is not None:
        _require(reading.get("source_id") == READING
                 and reading.get("source_url") == REVIEW_DOI
                 and reading.get("epistemic_status") == "unverified_role_and_proposition"
                 and reading.get("source_sha256"), "Academic original role receipt changed")
    probe = _unique_row(trial_report.get("probes", []), "asset_id", ASSET)
    _require(probe.get("mechanism_id") == "mechanism:flood_warning_to_impact"
             and probe["source"]["git_commit"] == SOURCE_COMMIT
             and probe["source"]["test_isolated_from_authority"] is True
             and probe["execution"] == "actual_upstream_python_code_synthetic_station_fixtures",
             "Original pinned source and execution authority mismatch")
    case_rows = probe.get("cases")
    _require(isinstance(case_rows, list) and len(case_rows) == len(REQUIRED_FIXTURES),
             "Original bounded flood fixtures changed")
    cases = {row["name"]: row for row in case_rows}
    _require(len(cases) == len(case_rows)
             and set(cases) == set(REQUIRED_FIXTURES)
             and all(cases[n]["status"] == state
                     and cases[n].get("critical") is True
                     and cases[n]["status"] in EVIDENCE_STATUSES
                     for n, state in REQUIRED_FIXTURES.items()),
             "Original flood fixture results changed; manual reassessment required")
    _require(cases["nonfinite_sensor_level_is_excluded"]["actual"]
             .get("nan_in_ranked_stations") is True
             and cases["nonfinite_station_corrupts_top_one_ordering"]["actual"]
             .get("top_one") == ["low"],
             "Critical upstream NaN sorting counterexample changed")
    _require(queue.get("independently_qualified_high_quality_assets") == 0
             and queue.get("confirmed_underconverted_assets") == 0
             and queue.get("realized_value") == 0,
             "Legacy queue falsely credited verified market conversions")
    alternatives = []
    for ids in (
        ["github:AuvroIslam/Nongor"],
        ["github:soypat/lneto"],
        ["github:TheWillMiller/river-wise", "github:sdmlua/FIMserv"],
    ):
        matches = [x for x in queue["rows"] if x.get("asset_ids") == ids
                   and "Urban Flood Hydrology, Warning Systems, and Public Health Vulnerability"
                   in x.get("domain_labels", [])]
        _require(len(matches) == 1
                 and matches[0].get("proposed_recombination_tested") is False
                 and matches[0].get("new_value_realized") is False
                 and matches[0].get("technical_quality_complete_for_all_required_assets") is False,
                 "Historical alternative candidate changed its validation authority")
        x = matches[0]
        alternatives.append({
            "candidate_id": x["candidate_id"], "asset_ids": ids,
            "possible_use_hypothesis_only": x.get("possible_use"),
            "original_falsification_proposal": x.get("original_model_falsification"),
            "status": "unqualified_development_candidate",
            "actual_integration_verified": False,
        })
    counts = dict(Counter(c["status"] for c in case_rows))
    _require(counts == {"pass": 3, "fail": 2, "not_tested": 1},
             "Historical source fixture distribution changed")
    pillars = [
        {
            "pillar": "disaster_risk_knowledge",
            "status": "not_demonstrated_for_target_community",
            "gap": "No target watershed risk/exposure map or local vulnerability assessment validated",
        },
        {
            "pillar": "observation_monitoring_forecasting",
            "status": "component_partially_tested_with_critical_failures",
            "gap": "UK-style sensor station ranking has NaN safety defects; no local telemetry calibration, forecasting accuracy or lead-time test",
        },
        {
            "pillar": "warning_communication",
            "status": "not_tested",
            "gap": "No authorized warning channel, receipt acknowledgments, latency, recipient coverage, or accessibility test",
        },
        {
            "pillar": "preparedness_response",
            "status": "external_WHO_report_not_software_integration",
            "gap": "WHO describes trained responders in Laos, but that does not establish integration with this GitHub software",
        },
    ]
    base = {
        "schema": SCHEMA,
        "case_id": "flood-warning-laos-report-versus-station-code-2026-10-22",
        "scope": "historical_bounded_development_receipt_and_public_source_review",
        "source_reconciliation": {
            "practical": {
                "reported_example": "Ban Kao Many community, Laos",
                "original_id": WHO,
                "original_url": WHO_URL,
                "evidence_role": "WHO_2023_institutional_operational_narrative",
                "source_caveat": who["source_caveat"],
                "Nocturnal_approved_public_case_imported": False,
                "local_before_after_causal_efficacy_proven": False,
            },
            "academic": {
                "original_id": READING,
                "original_url": REVIEW_DOI,
                "source_scope": reviewed["source_scope"],
                "source_caveat": reviewed["source_caveat"],
                "direct_2022_review_primary_field_trial": False,
                "source_record_identity_checked_not_entailment": True,
            },
            "implementation": {
                "asset_id": ASSET,
                "original_source_commit": SOURCE_COMMIT,
                "original_source_url": probe["source"]["source_url"],
                "entry_point": probe["source_entry_point"],
                "execution_scope": probe["execution"],
                "synthetic_test_results": [{"name": n, "status": cases[n]["status"],
                                            "actual": cases[n].get("actual")}
                                           for n in REQUIRED_FIXTURES],
                "synthetic_test_counts": counts,
                "live_field_execution_verified": False,
                "source_code_has_verified_local_Laos_adapter": False,
                "outcome_or_health_benefit_demonstrated": False,
                "upstream_license_label_not_external_data_authorization": True,
            },
        },
        "framework": {
            "original_url": "https://public.wmo.int/all-activities/build-resilience/early-warnings-all",
            "four_pillars": pillars,
            "same_geography_or_system_as_WHO_example": False,
            "research_paper_urban_review_vs_rural_community_transfer_verified": False,
        },
        "alternative_candidates": alternatives,
        "verification_gates": [
            {"id": "SOURCE", "state": "partially_met",
             "condition": "Direct source identity, exact original revision, original field and program scope verified"},
            {"id": "TELEMETRY", "state": "failed_synthetic",
             "condition": "NaN/inf/malformed/out-of-order station readings cannot suppress real high-risk stations"},
            {"id": "CALIBRATION", "state": "not_tested",
             "condition": "Risk threshold and lead-time calibrated against source-authorized local hydrology"},
            {"id": "DISSEMINATION", "state": "not_tested",
             "condition": "Authorized warning receipt, latency and response audited end to end"},
            {"id": "UTILITY", "state": "not_tested",
             "condition": "Compare operator task with ordinary evidence search and engineering workflow"},
            {"id": "IMPACT", "state": "not_tested",
             "condition": "Independent evidence of real benefit and qualified actual adopter demand"},
        ],
        "decision": {
            "status": "LAB_ONLY_FALSIFICATION_PRIORITY_NO_DEPLOYMENT_RECOMMENDATION",
            "reason": "Two critical station data-handling counterexamples and unverified target-system fit; real risk-reduction outcome absent",
            "cross_map_relation": "candidate_hypothesis_only",
            "automatic_cross_layer_promotion": False,
            "funding_or_value_established": False,
            "underconversion_established": False,
            "field_use_authorized": False,
            "falsifying_next_test": (
                "Reproduce the exact pinned NaN ranking counterexample, then test finite-only "
                "filtering and stable top-one ordering under shuffled inputs. Only after "
                "clearing this gate, test locally authorized station adapters, alert delivery "
                "and response for a consenting target operator."
            ),
        },
        "data_boundaries": {
            "no_sealed_academic_holdout_used": True,
            "no_private_nocturnal_ledgers_ingested": True,
            "no_real_warning_or_public_alert_generated": True,
            "historical_synthetic_results_not_reexecuted_in_this_build": True,
            "hypothesis_not_implementation_or_scientific_truth": True,
        },
    }
    base["source_artifacts_fingerprint_sha256"] = sha256(_canon({
        "alignment": alignment,
        "trials": trial_report,
        "qualification": queue,
        "academic": reading,
    }).encode("utf-8")).hexdigest()
    return base


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cross-layer-alignment", required=True, type=Path)
    p.add_argument("--functional-trials", required=True, type=Path)
    p.add_argument("--conversion-queue", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)
    _require(not args.out.exists(), "Refusing to overwrite prior dossier")
    result = build_dossier(_load(args.cross_layer_alignment),
                           _load(args.functional_trials),
                           _load(args.conversion_queue))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({"case_id": result["case_id"], "decision": result["decision"]["status"],
                      "fixtures": result["source_reconciliation"]["implementation"]["synthetic_test_counts"],
                      "falsification_required": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
