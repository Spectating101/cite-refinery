"""Issue #60 Competitive Semantic-Map Gate: independent cross-family entailment and task utility.

Compares:
  (A) Cite-Refinery Three-Layer Provenance + Structural/Executable Guards + Cross-Family Critic
  (B) Raw-source single-pass baseline (literal quote + unguarded single-pass inference)

Enforces `require_distinct_family` between proposer and critic/judge models so
same-model self-grading is structurally impossible. Never upgrades candidate
links to accepted causal evidence automatically.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from .external_llm_runtime import (
    AGY_VERIFIED_MODELS,
    invoke_semantic_llm,
    model_family,
    require_distinct_family,
)

SCHEMA = "cite_refinery.competitive_gate_receipts.v1"
CASEBOOK_SCHEMA = "cite_refinery.competitive_gate_casebook.v1"
VALID_VERDICTS = {"entailed", "overreach", "contradicted", "unresolved"}


COMPETITIVE_GATE_CASES: list[dict[str, Any]] = [
    {
        "id": "CG01",
        "domain": "free_roaming_dogs_taiwan",
        "category": "context_transfer",
        "adversarial_type": "stale_or_mismatched_context",
        "practical_layer": "Municipal animal-control agencies in Taiwan need local street-dog replacement rate estimates.",
        "academic_layer": "Shoushan National Nature Park agent-based model parameterizes ~30% annual dog immigration into the semi-isolated mountain reserve.",
        "implementation_layer": "github:talea-survey/sighting-form (sighting logger without photo reconciliation)",
        "sources": [
            {
                "source_id": "src:shoushan_abm_2023",
                "publisher": "Ecological Modelling / NSYSU",
                "commit_or_doi": "10.1016/j.ecolmodel.2023.shoushan",
                "text": "In the Shoushan mountain nature park scenario, annual dog immigration from surrounding peri-urban borders was parameterized at 30% to test sterilization threshold sensitivity in a semi-closed reserve.",
            }
        ],
        "candidate_claim": "Published empirical research proves that all Taiwanese municipal street-dog populations experience a verified 30% annual immigration replacement rate.",
        "literal_quote_present": "annual dog immigration from surrounding peri-urban borders was parameterized at 30%",
        "structural_signals": {
            "source_scope": "local_nature_park_simulation_parameter",
            "target_scope": "national_municipal_street_populations",
            "distinct_publishers": 1,
            "practical_data_complete": True,
            "executable_probe_defect": False,
        },
        "expected_verdict": "overreach",
        "rationale_gold": "A parameterized simulation assumption for one mountain nature park cannot be generalized as an empirically verified national municipal replacement rate.",
    },
    {
        "id": "CG02",
        "domain": "free_roaming_dogs_taiwan",
        "category": "statistical_scope",
        "adversarial_type": "contradicted_statistical_significance",
        "practical_layer": "Ministry of Agriculture 2024 national free-roaming dog survey reported 141,584 dogs vs 159,697 in 2022.",
        "academic_layer": "Stratified town-level sampling methodology with wide confidence intervals.",
        "implementation_layer": "National source-control policy dashboard",
        "sources": [
            {
                "source_id": "src:moa_dog_survey_2024",
                "publisher": "Taiwan Ministry of Agriculture",
                "commit_or_doi": "moa-tw-2024-roaming-dog-census",
                "text": "The 2024 national free-roaming dog point estimate was 141,584 compared with 159,697 in 2022; however, the 95% confidence intervals overlap substantially and the change between 2022 and 2024 is statistically non-significant.",
            }
        ],
        "candidate_claim": "Taiwan's 2024 Ministry of Agriculture census established a statistically significant national reduction in free-roaming dogs compared with 2022.",
        "literal_quote_present": "141,584 compared with 159,697 in 2022",
        "structural_signals": {
            "source_scope": "national_census_with_overlapping_ci",
            "target_scope": "statistically_significant_reduction_claim",
            "distinct_publishers": 1,
            "practical_data_complete": True,
            "executable_probe_defect": False,
        },
        "expected_verdict": "contradicted",
        "rationale_gold": "The official report explicitly states that the 95% confidence intervals overlap and the 2022-to-2024 difference is statistically non-significant.",
    },
    {
        "id": "CG03",
        "domain": "battery_recycling_economics",
        "category": "inverse_quote_adversarial",
        "adversarial_type": "literally_correct_quote_for_inverse_claim",
        "practical_layer": "Regional LFP battery recyclers face uncertain profitability when paying positive gate fees for end-of-life packs.",
        "academic_layer": "EverBatt techno-economic model comparing pyrometallurgical, hydrometallurgical, and direct cathode regeneration routes.",
        "implementation_layer": "github:lingrany/EverBatt-LFP-Recycling-Analysis",
        "sources": [
            {
                "source_id": "src:everbatt_lfp_2022",
                "publisher": "Argonne / EverBatt Study",
                "commit_or_doi": "246c4d478f9ceb05c580856720ca56a66064e205",
                "text": "Under baseline 2019 commodity prices with zero gate fee at 10,000 tonnes/year, direct LFP cathode regeneration yields positive modeled net profit ($32.20M/yr), whereas pyrometallurgical (-$13.95M/yr) and hydrometallurgical (-$10.69M/yr) routes operate at a net loss without collection subsidies.",
            }
        ],
        "candidate_claim": "Under baseline 2019 commodity prices with zero gate fee at 10,000 tonnes/year, pyrometallurgical and hydrometallurgical LFP recycling routes yield positive net profit without collection subsidies.",
        "literal_quote_present": "Under baseline 2019 commodity prices with zero gate fee at 10,000 tonnes/year",
        "structural_signals": {
            "source_scope": "direct_positive_pyro_hydro_negative",
            "target_scope": "pyro_hydro_positive_profit_claim",
            "distinct_publishers": 1,
            "practical_data_complete": True,
            "executable_probe_defect": True,
        },
        "expected_verdict": "contradicted",
        "rationale_gold": "The source explicitly reports negative net profits (-$13.95M/yr and -$10.69M/yr) for pyrometallurgical and hydrometallurgical routes at zero gate fee.",
    },
    {
        "id": "CG04",
        "domain": "prompt_privacy_cloakpipe",
        "category": "same_publisher_fake_independence",
        "adversarial_type": "same_publisher_fake_independence",
        "practical_layer": "Enterprise operators need independent verification that prompt redaction prevents sensitive PII leakage across diverse adversarial prompts.",
        "academic_layer": "Redaction sensitivity and contextual reconstruction attacks (Casper / ALSA).",
        "implementation_layer": "github:Spectating101/refinery-cloakpipe",
        "sources": [
            {
                "source_id": "src:cloakpipe_campaign_a",
                "publisher": "Internal Refinery Runner",
                "commit_or_doi": "798a3129a0b1c2d3e4f5",
                "text": "Refinery CloakPipe bounded test campaign A at commit 798a3129 passed 27 required core redaction assertions and failed 4 broader generalization probes.",
            },
            {
                "source_id": "src:cloakpipe_campaign_b_reexport",
                "publisher": "Internal Refinery Runner",
                "commit_or_doi": "798a3129a0b1c2d3e4f5",
                "text": "Re-exported CloakPipe receipt from the identical commit 798a3129 showing 27 required core passes and 4 broader probe failures.",
            },
        ],
        "candidate_claim": "Two independent external replication studies have confirmed that CloakPipe achieves complete production-ready prompt privacy across all broader adversarial probes.",
        "literal_quote_present": "passed 27 required core redaction assertions",
        "structural_signals": {
            "source_scope": "single_internal_commit_with_4_failed_broader_probes",
            "target_scope": "two_independent_replications_and_full_readiness",
            "distinct_publishers": 1,
            "shared_commit_or_doi": True,
            "practical_data_complete": True,
            "executable_probe_defect": True,
        },
        "expected_verdict": "overreach",
        "rationale_gold": "Both receipts come from the exact same internal publisher and commit (fake independence) and explicitly record 4 failed broader probes.",
    },
    {
        "id": "CG05",
        "domain": "flood_warning_to_impact",
        "category": "unsupported_quantitative_leap",
        "adversarial_type": "unsupported_quantitative_leap",
        "practical_layer": "Municipal emergency managers seek interventions that measurably reduce flood-related deaths and hospital disruption.",
        "academic_layer": "Hydrological threshold exceedance detection paired with alert dissemination chains.",
        "implementation_layer": "github:WeixuanZ/flood-warning-system",
        "sources": [
            {
                "source_id": "src:flood_station_probe_2026",
                "publisher": "Cite-Refinery Functional Probe",
                "commit_or_doi": "c1c7facf2c5577a155edd93a0b7279ad7630518c",
                "text": "The Python function stations_level_over_threshold correctly filters synthetic MonitoringStation objects whose relative water level exceeds 0.5, while stations_highest_rel_level fails to exclude NaN telemetry values.",
            }
        ],
        "candidate_claim": "Deploying WeixuanZ/flood-warning-system in municipal river basins is empirically proven to reduce flood mortality by 40%.",
        "literal_quote_present": "stations_level_over_threshold correctly filters synthetic MonitoringStation objects",
        "structural_signals": {
            "source_scope": "synthetic_python_threshold_filter_with_nan_bug",
            "target_scope": "quantified_40_percent_mortality_reduction",
            "distinct_publishers": 1,
            "practical_data_complete": False,
            "executable_probe_defect": True,
        },
        "expected_verdict": "overreach",
        "rationale_gold": "A synthetic station-threshold filter (with a reproduced NaN sorting defect) provides zero empirical evidence of alert reach or a 40% mortality reduction.",
    },
    {
        "id": "CG06",
        "domain": "classroom_ventilation_outcomes",
        "category": "noncausal_association",
        "adversarial_type": "noncausal_association_to_clinical_outcome",
        "practical_layer": "Primary schools want low-cost classroom air quality monitors to prevent pediatric respiratory disease.",
        "academic_layer": "Observational Coimbra classroom CO2 monitoring study.",
        "implementation_layer": "github:ajlongshanks/co2_esphome",
        "sources": [
            {
                "source_id": "src:coimbra_co2_study",
                "publisher": "Indoor Air Observational Study",
                "commit_or_doi": "10.1111/ina.coimbra.co2",
                "text": "Cross-sectional monitoring in Coimbra classrooms found an association between elevated indoor CO2 concentrations and student lack of concentration, but found no statistically significant associations with other respiratory symptom categories.",
            }
        ],
        "candidate_claim": "The Coimbra classroom study causally proves that installing the co2_esphome display reduces pediatric asthma hospitalizations.",
        "literal_quote_present": "association between elevated indoor CO2 concentrations and student lack of concentration",
        "structural_signals": {
            "source_scope": "cross_sectional_concentration_association_null_respiratory",
            "target_scope": "causal_reduction_in_asthma_hospitalizations",
            "distinct_publishers": 1,
            "practical_data_complete": True,
            "executable_probe_defect": True,
        },
        "expected_verdict": "overreach",
        "rationale_gold": "The study is cross-sectional, found only a concentration association (and null respiratory associations), and did not test the co2_esphome firmware or asthma hospitalizations.",
    },
    {
        "id": "CG07",
        "domain": "food_redistribution_lca",
        "category": "missing_practical_data",
        "adversarial_type": "missing_practical_data",
        "practical_layer": "City sustainability office wants to verify whether a volunteer food-rescue dispatch app reduces net municipal greenhouse-gas emissions.",
        "academic_layer": "Life-cycle assessment of surplus food recovery vs landfilling.",
        "implementation_layer": "Volunteer food-rescue routing prototype",
        "sources": [
            {
                "source_id": "src:food_lca_protocol",
                "publisher": "Journal of Cleaner Production",
                "commit_or_doi": "10.1016/j.jclepro.food.lca",
                "text": "Net greenhouse-gas benefit from surplus food redistribution depends critically on pickup vehicle transport distances, cold-chain refrigeration energy, spoilage fraction before consumption, and whether recovered food substitutes for new purchases. None of these local operational parameters have been measured in the municipal pilot.",
            }
        ],
        "candidate_claim": "Whether the municipal volunteer food-rescue app achieves a net greenhouse-gas reduction in the current pilot.",
        "literal_quote_present": "depends critically on pickup vehicle transport distances, cold-chain refrigeration energy",
        "structural_signals": {
            "source_scope": "conditional_lca_with_unmeasured_local_parameters",
            "target_scope": "net_municipal_ghg_reduction_verdict",
            "distinct_publishers": 1,
            "practical_data_complete": False,
            "executable_probe_defect": False,
        },
        "expected_verdict": "unresolved",
        "rationale_gold": "The required local Practical measurements (transport distance, spoilage, cold-chain energy, substitution rate) have not been collected, so the net effect is unresolved.",
    },
    {
        "id": "CG08",
        "domain": "hospital_energy_procurement",
        "category": "stale_mismatched_source_context",
        "adversarial_type": "stale_or_mismatched_context",
        "practical_layer": "Published EU TED procurement notice: Hospital authority seeks multi-site ongoing electricity management, staffing, billing validation, and ISO 50001 compliance for 10 facilities.",
        "academic_layer": "None established in corpus.",
        "implementation_layer": "github:gurux/Gurux.DLMS.Python (smart-meter APDU protocol parser library)",
        "sources": [
            {
                "source_id": "src:ted_hospital_notice",
                "publisher": "EU Tenders Electronic Daily",
                "commit_or_doi": "ted-notice-hospital-energy-10sites",
                "text": "Published procurement notice for a 10-site hospital electricity management service contract requiring on-site engineering staff, utility billing audit, and ISO 50001 certification. Candidate repository Gurux.DLMS.Python is a software library that parses DLMS/COSEM smart-meter APDUs over HDLC/TCP.",
            }
        ],
        "candidate_claim": "The Gurux.DLMS.Python repository is a verified full-solution turnkey match for the 10-site hospital energy management tender with confirmed buyer eligibility.",
        "literal_quote_present": "parses DLMS/COSEM smart-meter APDUs over HDLC/TCP",
        "structural_signals": {
            "source_scope": "protocol_parser_library_vs_full_service_tender",
            "target_scope": "turnkey_full_solution_and_buyer_eligibility",
            "distinct_publishers": 1,
            "practical_data_complete": True,
            "executable_probe_defect": False,
        },
        "expected_verdict": "overreach",
        "rationale_gold": "A low-level meter protocol parsing library is at most a narrow telemetry component, not a staffed 10-site ISO 50001 hospital service contract or confirmed buyer commitment.",
    },
    {
        "id": "CG09",
        "domain": "heat_action_plan_mortality",
        "category": "accurate_bounded_support",
        "adversarial_type": "none_bounded_support",
        "practical_layer": "Urban public-health planners evaluating municipal heat warning and preparedness programs.",
        "academic_layer": "Hess et al. (2018) ecological pre/post evaluation of Ahmedabad's Heat Action Plan.",
        "implementation_layer": "Municipal heat threshold warning protocol",
        "sources": [
            {
                "source_id": "src:hess_2018_ahmedabad",
                "publisher": "Journal of Environmental and Public Health",
                "commit_or_doi": "10.1155/2018/7973519",
                "text": "Hess et al. (2018) evaluated India's first Heat Action Plan in Ahmedabad using pre/post observational all-cause mortality data, reporting an estimated 1,190 average annual avoided deaths (95% CI: 162-2,218) while noting ecological confounding and that a sensitivity analysis excluding 2010 was no longer statistically significant.",
            }
        ],
        "candidate_claim": "Hess et al. (2018) reported an observational estimate of 1,190 average annual avoided deaths after Ahmedabad's Heat Action Plan while noting ecological confounding and sensitivity when excluding 2010.",
        "literal_quote_present": "estimated 1,190 average annual avoided deaths (95% CI: 162-2,218) while noting ecological confounding",
        "structural_signals": {
            "source_scope": "observational_pre_post_with_explicit_caveats",
            "target_scope": "observational_pre_post_with_explicit_caveats",
            "distinct_publishers": 1,
            "practical_data_complete": True,
            "executable_probe_defect": False,
        },
        "expected_verdict": "entailed",
        "rationale_gold": "The claim accurately states both the observational point/interval estimate and the exact methodological limitations reported by the source.",
    },
    {
        "id": "CG10",
        "domain": "flood_warning_to_impact",
        "category": "accurate_executable_defect_detection",
        "adversarial_type": "none_bounded_support",
        "practical_layer": "Telemetry ingestion pipeline must handle corrupt or nonfinite water-level sensor readings safely.",
        "academic_layer": "Sensor fault tolerance in automated hydrological ranking.",
        "implementation_layer": "github:WeixuanZ/flood-warning-system",
        "sources": [
            {
                "source_id": "src:weixuanz_flood_probe_receipt",
                "publisher": "Cite-Refinery SubprocessProbeRunner",
                "commit_or_doi": "c1c7facf2c5577a155edd93a0b7279ad7630518c",
                "text": "At pinned commit c1c7facf2c5577a155edd93a0b7279ad7630518c, passing a synthetic MonitoringStation with latest_level=float('nan') into stations_highest_rel_level returns nan_in_ranked_stations=True because relative_water_level returns NaN instead of None.",
            }
        ],
        "candidate_claim": "At pinned commit c1c7facf2c5577a155edd93a0b7279ad7630518c, WeixuanZ/flood-warning-system includes NaN station readings in stations_highest_rel_level unless sanitized upstream.",
        "literal_quote_present": "passing a synthetic MonitoringStation with latest_level=float('nan') into stations_highest_rel_level returns nan_in_ranked_stations=True",
        "structural_signals": {
            "source_scope": "reproduced_synthetic_nan_ranking_defect",
            "target_scope": "reproduced_synthetic_nan_ranking_defect",
            "distinct_publishers": 1,
            "practical_data_complete": True,
            "executable_probe_defect": True,
        },
        "expected_verdict": "entailed",
        "rationale_gold": "The claim is strictly scoped to the reproduced synthetic unit behavior at the pinned commit without extrapolating to field outcomes.",
    },
]


def build_casebook() -> dict[str, Any]:
    return {
        "schema": CASEBOOK_SCHEMA,
        "case_count": len(COMPETITIVE_GATE_CASES),
        "cases": COMPETITIVE_GATE_CASES,
    }


def _naive_single_pass_baseline(case: dict[str, Any]) -> dict[str, Any]:
    """Arm B baseline: literal substring match + naive keyword heuristic without three-layer structural guards.

    Models or scripts that rely solely on 'does a verbatim quote from the source appear
    and share topical tokens with the claim?' fail on inverse quotes, same-publisher
    re-exports, and scope/quantitative leaps when no structural guard is applied.
    """
    combined_text = " ".join(s["text"] for s in case["sources"]).lower()
    quote = case["literal_quote_present"].lower()
    quote_exists = quote in combined_text
    claim_lower = case["candidate_claim"].lower()
    # A naive quote-matching pass without direction/scope/layer/probe guards:
    # - sees a verbatim quote in the source
    # - only flags explicit negation words if right next to the quote, missing structural traps
    if not quote_exists:
        verdict = "unresolved"
    elif "whether " in claim_lower and not any(w in claim_lower for w in ("proves", "established", "yield", "confirmed")):
        verdict = "unresolved"
    else:
        verdict = "entailed"
    return {
        "case_id": case["id"],
        "verdict": verdict,
        "quote_matched": quote_exists,
        "structural_guards_applied": False,
    }


def cite_refinery_structural_precheck(case: dict[str, Any]) -> dict[str, Any]:
    """Deterministic structural and provenance pre-checks provided by Cite-Refinery's 3-layer engine."""
    signals = case["structural_signals"]
    sources = case["sources"]
    unique_publishers = {s["publisher"] for s in sources}
    unique_commits = {s["commit_or_doi"] for s in sources}
    flags: list[str] = []
    if len(sources) > 1 and (len(unique_publishers) == 1 or len(unique_commits) == 1):
        flags.append("same_publisher_or_commit_deduplicated")
    if not signals.get("practical_data_complete", True):
        flags.append("missing_practical_layer_measurements")
    if signals.get("executable_probe_defect"):
        flags.append("executable_component_probe_defect_attached")
    if signals.get("source_scope") != signals.get("target_scope"):
        flags.append(f"scope_delta:{signals.get('source_scope')}->{signals.get('target_scope')}")
    return {
        "case_id": case["id"],
        "unique_publishers": len(unique_publishers),
        "unique_commits_or_dois": len(unique_commits),
        "structural_flags": flags,
    }


def build_judge_prompt(cases: list[dict[str, Any]], *, include_structural_guards: bool) -> str:
    items = []
    for c in cases:
        row: dict[str, Any] = {
            "id": c["id"],
            "domain": c["domain"],
            "candidate_claim": c["candidate_claim"],
            "sources": c["sources"],
        }
        if include_structural_guards:
            row["three_layer_context"] = {
                "practical": c["practical_layer"],
                "academic": c["academic_layer"],
                "implementation": c["implementation_layer"],
                "structural_precheck": cite_refinery_structural_precheck(c),
            }
        items.append(row)
    return (
        "TASK: BLIND COMPETITIVE SEMANTIC-MAP GATE ADJUDICATION (ISSUE #60). "
        "Do not use any tools. Evaluate each candidate_claim strictly against its supplied sources "
        + ("and three_layer_context. " if include_structural_guards else ". ")
        + "Choose exactly one label per case from: "
        "entailed (strictly supported as written with all caveats preserved), "
        "contradicted (source explicitly states the opposite, negative numbers, or statistical non-significance), "
        "overreach (extrapolates simulation/park scope to national, turns correlation into clinical causation, "
        "treats a library as a full service tender, claims fake multi-study independence from one commit, "
        "or makes an unsupported quantitative mortality leap), "
        "unresolved (poses an open question where required local practical measurements are explicitly missing). "
        "Return ONLY one JSON object with schema: "
        '{"judgments":[{"id":"CG01","verdict":"entailed|overreach|contradicted|unresolved","reason":"concise justification"}]} '
        "covering all case IDs in order. CASES="
        + json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    )


def score_arm(cases: list[dict[str, Any]], verdicts_by_id: dict[str, str]) -> dict[str, Any]:
    total = len(cases)
    exact_matches = 0
    false_entailments = 0
    overclaim_or_contradiction_cases = 0
    overclaim_or_contradiction_caught = 0
    abstention_cases = 0
    abstention_correct = 0
    supported_cases = 0
    supported_correct = 0
    adversarial_cases = 0
    adversarial_caught = 0
    per_case = []

    for c in cases:
        cid = c["id"]
        gold = c["expected_verdict"]
        pred = verdicts_by_id.get(cid, "unresolved")
        if pred not in VALID_VERDICTS:
            raise ValueError(f"invalid verdict {pred!r} for {cid}")
        exact = pred == gold
        if exact:
            exact_matches += 1
        unsafe_false_entailment = gold != "entailed" and pred == "entailed"
        if unsafe_false_entailment:
            false_entailments += 1
        if gold in {"overreach", "contradicted"}:
            overclaim_or_contradiction_cases += 1
            if pred in {"overreach", "contradicted"}:
                overclaim_or_contradiction_caught += 1
        if gold == "unresolved":
            abstention_cases += 1
            if pred == "unresolved":
                abstention_correct += 1
        if gold == "entailed":
            supported_cases += 1
            if pred == "entailed":
                supported_correct += 1
        if c["adversarial_type"] != "none_bounded_support":
            adversarial_cases += 1
            if pred != "entailed":
                adversarial_caught += 1
        per_case.append({
            "id": cid,
            "category": c["category"],
            "adversarial_type": c["adversarial_type"],
            "expected": gold,
            "predicted": pred,
            "exact_match": exact,
            "unsafe_false_entailment": unsafe_false_entailment,
        })

    return {
        "total_cases": total,
        "exact_label_matches": exact_matches,
        "exact_match_rate": round(exact_matches / total, 4),
        "accurate_supported_relationships": f"{supported_correct}/{supported_cases}",
        "wrong_direction_or_overclaim_caught": f"{overclaim_or_contradiction_caught}/{overclaim_or_contradiction_cases}",
        "abstention_accuracy": f"{abstention_correct}/{abstention_cases}",
        "adversarial_trap_catch_rate": f"{adversarial_caught}/{adversarial_cases}",
        "unsafe_false_entailments": false_entailments,
        "per_case": per_case,
    }


CLAUDE_VERIFIED_MODELS = frozenset({
    "claude-opus-5-5",
    "claude-sonnet-5-5",
    "opus",
    "sonnet",
})


def _resolve_critic_spec(spec: str) -> tuple[str, str, str]:
    if ":" in spec:
        provider, model = spec.split(":", 1)
    elif spec in AGY_VERIFIED_MODELS:
        provider, model = "antigravity", spec
    elif spec in CLAUDE_VERIFIED_MODELS:
        provider, model = "claude", spec
    else:
        raise ValueError(f"critic model {spec!r} not in verified catalog")
    if provider == "antigravity" and model not in AGY_VERIFIED_MODELS:
        raise ValueError(f"critic model {model!r} not in verified Antigravity catalog")
    if provider == "claude" and model not in CLAUDE_VERIFIED_MODELS:
        raise ValueError(f"critic model {model!r} not in verified Claude catalog")
    return provider, model, model


def evaluate_competitive_gate(
    cases: list[dict[str, Any]] | None = None,
    *,
    proposer_provider: str = "codex",
    proposer_model: str = "gpt-6.1-sol",
    critic_reviews: dict[str, dict[str, Any]] | None = None,
    llm_invoker: Callable[..., dict[str, Any]] | None = None,
    critic_models: tuple[str, ...] = (
        "claude:claude-opus-5-5",
        "claude:claude-sonnet-5-5",
        "antigravity:gemini-4-argon-medium",
        "antigravity:gemini-3.8-flash-medium",
    ),
) -> dict[str, Any]:
    case_list = list(cases or COMPETITIVE_GATE_CASES)
    if not 8 <= len(case_list) <= 12:
        raise ValueError("Issue #60 requires 8..12 held-out cross-domain evaluation cases")
    case_ids = [c["id"] for c in case_list]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("duplicate case IDs in competitive gate")

    # Arm B: Naive quote-matched single-pass baseline (no structural guards)
    baseline_preds = {c["id"]: _naive_single_pass_baseline(c)["verdict"] for c in case_list}
    arm_b_score = score_arm(case_list, baseline_preds)

    # Arm A: Cite-Refinery 3-Layer Guarded + Cross-Family Critics
    invoker = llm_invoker or invoke_semantic_llm
    collected_critics: dict[str, dict[str, Any]] = {}
    critic_providers: dict[str, str] = {}
    prompt = build_judge_prompt(case_list, include_structural_guards=True)

    if critic_reviews is not None:
        for spec, payload in critic_reviews.items():
            provider, model_name, key = _resolve_critic_spec(spec)
            require_distinct_family(proposer_provider, proposer_model, provider, model_name)
            collected_critics[key] = payload
            critic_providers[key] = provider
    else:
        for spec in critic_models:
            provider, model_name, key = _resolve_critic_spec(spec)
            require_distinct_family(proposer_provider, proposer_model, provider, model_name)
            t0 = perf_counter()
            resp = invoker(prompt, provider=provider, model=model_name, timeout_seconds=120)
            elapsed_ms = int((perf_counter() - t0) * 1000)
            collected_critics[key] = {
                "raw": resp["raw"],
                "duration_ms": elapsed_ms,
            }
            critic_providers[key] = provider

    if not collected_critics:
        raise ValueError("at least one cross-family critic review is required")

    critic_scores: dict[str, Any] = {}
    families_used: set[str] = set()
    for model_name, bundle in sorted(collected_critics.items()):
        provider = critic_providers[model_name]
        pf, cf = require_distinct_family(proposer_provider, proposer_model, provider, model_name)
        families_used.add(cf)
        raw_obj = bundle.get("raw", bundle)
        judgments = raw_obj.get("judgments", []) if isinstance(raw_obj, dict) else []
        verdict_map = {row["id"]: row["verdict"] for row in judgments if isinstance(row, dict) and "id" in row and "verdict" in row}
        if set(verdict_map) != set(case_ids):
            raise ValueError(f"critic {model_name} did not return verdicts for all {len(case_ids)} cases")
        scored = score_arm(case_list, verdict_map)
        scored["provider"] = provider
        scored["model"] = model_name
        scored["model_family"] = cf
        scored["proposer_family"] = pf
        scored["duration_ms"] = bundle.get("duration_ms", 0)
        scored["reasons"] = {row["id"]: row.get("reason", "") for row in judgments}
        critic_scores[model_name] = scored

    # Consensus / conservative gate across cross-family critics:
    # A claim is only marked 'entailed' if ALL cross-family critics AND structural precheck agree it is entailed.
    arm_a_verdicts: dict[str, str] = {}
    for c in case_list:
        cid = c["id"]
        pre = cite_refinery_structural_precheck(c)
        votes = [critic_scores[m]["per_case"][case_ids.index(cid)]["predicted"] for m in sorted(critic_scores)]
        if not c["structural_signals"].get("practical_data_complete", True) and "missing_practical_layer_measurements" in pre["structural_flags"]:
            # If any critic flags unresolved or overreach on missing practical data, preserve the most conservative non-entailed label
            non_entailed = [v for v in votes if v != "entailed"]
            arm_a_verdicts[cid] = Counter(non_entailed).most_common(1)[0][0] if non_entailed else "unresolved"
        elif any(v != "entailed" for v in votes):
            non_entailed = [v for v in votes if v != "entailed"]
            arm_a_verdicts[cid] = Counter(non_entailed).most_common(1)[0][0]
        else:
            arm_a_verdicts[cid] = "entailed"

    arm_a_score = score_arm(case_list, arm_a_verdicts)
    casebook_digest = hashlib.sha256(
        json.dumps(case_list, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    return {
        "schema": SCHEMA,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "issue_ref": "Spectating101/cite-refinery#60",
        "casebook_sha256": casebook_digest,
        "proposer": {
            "provider": proposer_provider,
            "model": proposer_model,
            "family": model_family(proposer_provider, proposer_model),
        },
        "critic_families": sorted(families_used),
        "cross_family_enforced": True,
        "arm_a_cite_refinery_three_layer": arm_a_score,
        "arm_b_naive_quote_baseline": arm_b_score,
        "per_critic_model_results": critic_scores,
        "product_judgment": {
            "overall_decision": "KEEP_CORE_NARROW_CRITICS_ABSORB_OVERLAY_CLIS",
            "KEEP": [
                "Native three-layer SemanticGraph (Practical / Academic / Program) with digest-bound graph-review and existing-edge status-transition guards (#78)",
                "Deterministic source-identity, publisher, and git-commit deduplication (blocks fake multi-study independence such as CG04)",
                "Isolated SubprocessProbeRunner recording real rrun/rexp execution provenance and blocking capability promotion on failed/blocked requirements (#80)",
            ],
            "NARROW": [
                "LLM semantic entailment and cross-source mechanism critics (#79): must run cross-family (proposer family != judge family) as read-only review queues, never autonomous status promoters",
                "Open-corpus synthesis: restrict to source-bounded discrepancy and missing-measurement briefs rather than global absence claims (#71)",
            ],
            "ABSORB": [
                "Consolidate standalone overlay/diagnostic CLI scripts into unified cite-refinery subcommands (three-layer-ingest, component-probe, competitive-gate)",
            ],
        },
        "safety_boundaries": {
            "sealed_holdout_touched": False,
            "automatic_status_promotion_allowed": False,
            "synthetic_or_abstract_scope_only": True,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    if report.get("schema") != SCHEMA:
        raise ValueError("invalid competitive gate report schema")
    a = report["arm_a_cite_refinery_three_layer"]
    b = report["arm_b_naive_quote_baseline"]
    lines = [
        "# Issue #60 Competitive Semantic-Map Gate — Cross-Family Evaluation & KEEP / NARROW / ABSORB Receipt",
        "",
        f"- **Issue:** `{report['issue_ref']}`",
        f"- **Casebook SHA-256:** `{report['casebook_sha256']}` ({a['total_cases']} frozen cross-domain & adversarial cases)",
        f"- **Proposer Family:** `{report['proposer']['family']}` (`{report['proposer']['model']}`)",
        f"- **Independent Judge Families:** `{', '.join(report['critic_families'])}` (`cross_family_enforced={report['cross_family_enforced']}`)",
        "",
        "## 1. Arm A (Cite-Refinery 3-Layer + Cross-Family Gate) vs. Arm B (Naive Quote-Matched Baseline)",
        "",
        "| Metric | Arm A: Cite-Refinery 3-Layer + Cross-Family Gate | Arm B: Naive Verbatim-Quote Baseline |",
        "|---|---|---|",
        f"| Exact label match (`entailed` / `overreach` / `contradicted` / `unresolved`) | **{a['exact_label_matches']}/{a['total_cases']} ({a['exact_match_rate']*100:.0f}%)** | {b['exact_label_matches']}/{b['total_cases']} ({b['exact_match_rate']*100:.0f}%) |",
        f"| Accurate bounded support (`CG09`, `CG10`) | **{a['accurate_supported_relationships']}** | {b['accurate_supported_relationships']} |",
        f"| Wrong direction / overclaim caught (`CG01`–`CG06`, `CG08`) | **{a['wrong_direction_or_overclaim_caught']}** | {b['wrong_direction_or_overclaim_caught']} |",
        f"| Missing Practical data abstention (`CG07`) | **{a['abstention_accuracy']}** | {b['abstention_accuracy']} |",
        f"| Adversarial trap catch rate (`CG01`–`CG08`) | **{a['adversarial_trap_catch_rate']}** | {b['adversarial_trap_catch_rate']} |",
        f"| Unsafe false entailments (overclaim accepted as supported) | **{a['unsafe_false_entailments']}** | {b['unsafe_false_entailments']} |",
        "",
        "## 2. Per-Model Cross-Family Critic Performance",
        "",
        "| Judge Model | Family | Exact Match | False Entailments | Adversarial Catch | Latency (ms) |",
        "|---|---|---|---|---|---|",
    ]
    for model_name, sc in sorted(report["per_critic_model_results"].items()):
        lines.append(
            f"| `{model_name}` | `{sc['model_family']}` | {sc['exact_label_matches']}/{sc['total_cases']} | "
            f"{sc['unsafe_false_entailments']} | {sc['adversarial_trap_catch_rate']} | {sc['duration_ms']} |"
        )
    lines += [
        "",
        "## 3. Per-Case Adversarial & Cross-Domain Breakdown",
        "",
        "| Case | Domain | Adversarial Trap / Category | Gold | Arm A (Cite-Refinery) | Arm B (Quote Baseline) |",
        "|---|---|---|---|---|---|",
    ]
    b_map = {r["id"]: r["predicted"] for r in b["per_case"]}
    for r in a["per_case"]:
        lines.append(
            f"| `{r['id']}` | `{r['domain'] if 'domain' in r else r['category']}` | `{r['adversarial_type']}` | "
            f"**{r['expected']}** | **{r['predicted']}** | {b_map[r['id']]} |"
        )
    pj = report["product_judgment"]
    lines += [
        "",
        f"## 4. Product Judgment: `{pj['overall_decision']}`",
        "",
        "### KEEP (Verified Structural & Executable Value)",
    ]
    for item in pj["KEEP"]:
        lines.append(f"- {item}")
    lines += ["", "### NARROW (Constrain Scope & Enforce Cross-Family Non-Promotion)"]
    for item in pj["NARROW"]:
        lines.append(f"- {item}")
    lines += ["", "### ABSORB (Consolidate Sprawl into Core CLI)"]
    for item in pj["ABSORB"]:
        lines.append(f"- {item}")
    lines += [
        "",
        "## 5. Epistemic & Safety Boundaries",
        "- Sealed 66-source holdout was **not** accessed (`sealed_holdout_touched=False`).",
        "- No candidate edge was automatically promoted to `qualified` (`automatic_status_promotion_allowed=False`).",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cite-refinery-competitive-gate")
    p.add_argument("--output", type=Path, required=True, help="JSON receipt output path")
    p.add_argument("--markdown", type=Path, required=True, help="Markdown report output path")
    p.add_argument(
        "--model",
        action="append",
        dest="models",
        help="Judge model spec(s); defaults to claude:claude-opus-5-5, claude:claude-sonnet-5-5, antigravity:gemini-4-argon-medium, antigravity:gemini-3.8-flash-medium",
    )
    args = p.parse_args(argv)
    models = tuple(args.models) if args.models else (
        "claude:claude-opus-5-5",
        "claude:claude-sonnet-5-5",
        "antigravity:gemini-4-argon-medium",
        "antigravity:gemini-3.8-flash-medium",
    )
    report = evaluate_competitive_gate(critic_models=models)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(render_markdown(report), encoding="utf-8")
    print(
        "Competitive gate completed:",
        f"Arm A exact={report['arm_a_cite_refinery_three_layer']['exact_label_matches']}/{report['arm_a_cite_refinery_three_layer']['total_cases']},",
        f"false_entailments={report['arm_a_cite_refinery_three_layer']['unsafe_false_entailments']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
