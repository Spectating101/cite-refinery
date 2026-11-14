"""Milestone 013: official-reporting outcome ledger with strict cohort boundaries.

This is an inspectable snapshot of distinct administrative casework cohorts,
NOT an individual remedy registry or a legal effectiveness estimator. Each
published figure is pinned to its reporting authority, reference date, unit,
and stage taxonomy. Source URLs are official locators but their original bytes
are not captured by this evaluator. Never derive cross-cohort coverage,
court-appellant identity, individual compensation, causal impact, or guilt.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import hashlib
import json
import re

SCHEMA = "legal_codex.outcome_trace.v1"
SOURCE_PINS = {
    "s_uk_moj": (
        "https://www.gov.uk/government/publications/post-office-horizon-system-offences-act-2024-quashed-convictions-management-information/summary-quashed-convictions-management-information-24-september-2026",
        "England and Wales", "2026-09-15", "2026-09-24",
        "official_casework_summary",
    ),
    "s_uk_redress_oct": (
        "https://www.gov.uk/government/publications/post-office-horizon-financial-redress-and-legal-costs-data-for-2026/post-office-horizon-financial-redress-data-as-of-30-october-2026",
        "England and Wales", "2026-10-30", "2026-11-13",
        "official_redress_statistics",
    ),
    "s_uk_redress_sep": (
        "https://www.gov.uk/government/publications/post-office-horizon-financial-redress-and-legal-costs-data-for-2026/post-office-horizon-financial-redress-data-as-of-30-september-2026",
        "England and Wales", "2026-09-30", "2026-11-13",
        "corrected_official_statistics",
    ),
    "s_nl_dashboard": (
        "https://herstel.toeslagen.nl/dashboard-kinderopvangtoeslag/",
        "Netherlands", "2026-10-16", None,
        "official_dynamic_programme_dashboard",
    ),
    "s_nl_update_sep": (
        "https://www.rijksoverheid.nl/actueel/nieuws/2026/09/18/steeds-meer-ouders-ronden-hun-aanvullende-schade-af",
        "Netherlands", "2026-09-18", "2026-09-18",
        "official_ministerial_update",
    ),
}
COUNT_PINS = {
    "uk_moj_casework": ("s_uk_moj", "case_records", 1011,
                        {"assessed": 1011}, False, False),
    "uk_quashed_people": ("s_uk_moj", "individuals", 620,
                          {"notified": 584}, False, False),
    "uk_hcrs_claims": ("s_uk_redress_oct", "claims", 545,
                       {"settled": 515, "offer_not_accepted": 14, "under_assessment": 16}, True, False),
    "uk_hss_claims": ("s_uk_redress_oct", "claims", 14901,
                      {"settled": 13541, "offer_not_accepted": 582, "under_assessment": 778}, True, False),
    "uk_glo_claims": ("s_uk_redress_oct", "claims", 492,
                      {"settled": 463, "offer_not_accepted": 26, "under_assessment": 3}, True, False),
    "uk_hssa_claims": ("s_uk_redress_oct", "claims", 173,
                       {"settled": 28, "offer_not_accepted": 86, "under_assessment": 59}, True, False),
    "nl_parent_classification": ("s_nl_dashboard", "parent_registrations", 69738,
                                 {"recognized": 44131, "not_recognized": 25607}, True, False),
    "nl_objections": ("s_nl_dashboard", "objections", 18886,
                      {"decision_issued": 13570, "pending": 5316}, True, False),
    "nl_cws_cases": ("s_nl_dashboard", "applications", 12377,
                     {"advice_issued": 1964, "waiting": 669, "in_review": 714,
                      "on_hold": 304, "no_longer_in_review": 8726}, True, False),
    "nl_integral_assessments": ("s_nl_dashboard", "assessment_processes", 69517,
                                {}, False, False),
    "nl_additional_damages_approx": ("s_nl_update_sep", "parents", 4500,
                                     {}, False, True),
}
MONEY_PINS = {
    "uk_all_redress_oct": ("s_uk_redress_oct", "GBP_million", 1756),
    "uk_all_redress_sep_corrected": ("s_uk_redress_sep", "GBP_million", 1727),
    "uk_hss_paid": ("s_uk_redress_oct", "GBP_million", 1106),
    "uk_hssa_paid": ("s_uk_redress_oct", "GBP_million", 18),
    "uk_glo_paid": ("s_uk_redress_oct", "GBP_million", 237),
    "uk_hcrs_paid": ("s_uk_redress_oct", "GBP_million", 326),
    "uk_oc_closed_paid": ("s_uk_redress_oct", "GBP_million", 68),
    "nl_first_check_disbursed": ("s_nl_dashboard", "EUR_million", 795.5),
    "nl_integral_assessment_disbursed": ("s_nl_dashboard", "EUR_million", 1760),
    "nl_actual_damage_disbursed": ("s_nl_dashboard", "EUR_million", 42.1),
}
CORRECTION_PINS = {
    "uk_sep_total_correction": ("uk_all_redress_sep_corrected", 1731, 1727),
}
EXPECTED_LINKS = {
    "link_hamilton_hcrs": ("hamilton_2021", "uk_hcrs_claims"),
    "link_3535_programme": ("dutch_3535", "nl_parent_classification"),
    "link_3536_objections": ("dutch_3536", "nl_objections"),
}
JUDGMENTS = {"hamilton_2021", "dutch_3535", "dutch_3536"}
_ID = re.compile(r"[a-z][a-z0-9_]{2,70}\Z")


def _hash(value):
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def _indexed(items, label):
    if not isinstance(items, list) or not items:
        raise ValueError(label + ": required nonempty list")
    out = {}
    for row in items:
        if not isinstance(row, dict):
            raise ValueError(label + ": invalid record")
        ident = row.get("id")
        if not isinstance(ident, str) or not _ID.fullmatch(ident) or ident in out:
            raise ValueError(label + ": duplicate or malformed id")
        out[ident] = row
    return out


def _day(s):
    if not isinstance(s, str):
        raise ValueError("missing date")
    return date.fromisoformat(s)


def validate(bundle):
    if not isinstance(bundle, dict) or bundle.get("schema") != SCHEMA:
        raise ValueError("unsupported outcome ledger schema")
    if set(bundle) != {"schema", "as_of", "sources", "cohorts", "money",
                       "corrections", "court_context_links", "unresolved_gaps",
                       "original_sources_archived", "independent_audit_completed",
                       "publication_authorized", "causal_effect_estimated"}:
        raise ValueError("unsupported evidence or unreviewed output fields")
    as_of = _day(bundle["as_of"])
    if (_day(bundle["as_of"]).isoformat() != "2026-11-15" or
            any(bundle[name] is not False for name in (
                "original_sources_archived", "independent_audit_completed",
                "publication_authorized", "causal_effect_estimated"))):
        raise ValueError("archive, independent audit or causal effect not established")
    sources = _indexed(bundle["sources"], "sources")
    if set(sources) != set(SOURCE_PINS):
        raise ValueError("unreviewed source inserted or removed")
    for sid, row in sources.items():
        expected_url, region, data_date, publication, klass = SOURCE_PINS[sid]
        if any(row.get(k) != v for k,v in (
            ("url",expected_url), ("jurisdiction",region),
            ("data_as_of",data_date), ("published_or_corrected_on",publication),
            ("source_kind",klass))):
            raise ValueError("official source or dated snapshot substituted")
        url = urlsplit(row["url"])
        if (url.scheme != "https" or url.username or url.password or url.fragment or
                url.hostname not in {"www.gov.uk","herstel.toeslagen.nl","www.rijksoverheid.nl"}):
            raise ValueError("official source host mismatch")
        if any(row.get(k) is not False for k in (
            "original_bytes_captured", "individual_records_obtained",
            "source_independent_truth_verified")):
            raise ValueError("source locator is not authenticated original custody")
        if row.get("reporting_tier") != "official_aggregate_reporting":
            raise ValueError("reported aggregate is not a court finding")
        if not isinstance(row.get("scope"), str) or len(row["scope"]) < 40:
            raise ValueError("cohort reporting scope not documented")
        if _day(data_date) > as_of or (publication is not None and _day(publication) > as_of):
            raise ValueError("future source")
    cohorts = _indexed(bundle["cohorts"], "cohorts")
    if set(cohorts) != set(COUNT_PINS):
        raise ValueError("cohort missing or silently replaced")
    for ident, row in cohorts.items():
        src, unit, total, stages, partition, approximate = COUNT_PINS[ident]
        if (row.get("source_id") != src or row.get("unit") != unit or
                type(row.get("reported_total")) is not int or row["reported_total"] != total or
                row.get("stages") != stages or row.get("is_exhaustive_partition") is not partition or
                row.get("approximate") is not approximate or
                row.get("data_as_of") != sources[src]["data_as_of"]):
            raise ValueError("cohort report, unit, date or source figure altered")
        if not isinstance(row.get("scope_note"), str) or len(row["scope_note"]) < 45:
            raise ValueError("missing denominator and stage caveat")
        if (row.get("court_appellants_matched") is not False or
                row.get("same_persons_as_other_cohort") is not False or
                row.get("all_fully_compensated") is not False):
            raise ValueError("aggregate cohort cannot prove matched individuals or complete redress")
        if any(type(x) is not int or x < 0 for x in stages.values()):
            raise ValueError("invalid administrative stage")
        if partition and sum(stages.values()) != total:
            raise ValueError("cohort stage reconciliation failed")
        if not partition and stages and sum(stages.values()) > total:
            raise ValueError("reported subset exceeds its own denominator")
    money = _indexed(bundle["money"], "money")
    if set(money) != set(MONEY_PINS):
        raise ValueError("missing or altered reported money categories")
    for ident, row in money.items():
        src, unit, value = MONEY_PINS[ident]
        if (row.get("source_id") != src or row.get("unit") != unit or
                type(row.get("reported_amount")) not in (int,float) or
                row.get("reported_amount") != value or
                row.get("data_as_of") != sources[src]["data_as_of"] or
                row.get("amount_kind") != "cumulative_official_reported_amount" or
                row.get("is_rounded") is not True or
                row.get("individually_reconciled") is not False or
                row.get("additive_to_other_categories") is not False):
            raise ValueError("wrong currency, amount, time, reconciliation or double-count assumption")
        if not isinstance(row.get("scope_note"), str) or len(row["scope_note"]) < 35:
            raise ValueError("payment scope missing")
    corrections = _indexed(bundle["corrections"], "corrections")
    if set(corrections) != set(CORRECTION_PINS):
        raise ValueError("official revision history omitted")
    for ident,row in corrections.items():
        target, old, new = CORRECTION_PINS[ident]
        if (row.get("target_amount_id") != target or
                row.get("superseded_amount") != old or
                row.get("corrected_amount") != new or
                row.get("revision_published_on") != "2026-11-13" or
                row.get("superseded_not_current") is not True or
                row.get("change_is_new_payment") is not False or
                row.get("source_url") != SOURCE_PINS["s_uk_redress_sep"][0]):
            raise ValueError("stale UK redress data promoted or revision misrepresented")
    links = _indexed(bundle["court_context_links"], "court links")
    if set(links) != set(EXPECTED_LINKS):
        raise ValueError("missing or extra judicial mapping")
    for ident,row in links.items():
        j,c = EXPECTED_LINKS[ident]
        if (row.get("judgment_id") != j or row.get("cohort_id") != c or
                row.get("review_status") != "aggregate_context_only" or
                row.get("individual_case_identity_verified") is not False or
                row.get("causal_link_to_judgment_proven") is not False or
                row.get("case_specific_payment_verified") is not False):
            raise ValueError("statistics cannot automatically prove a particular litigant was remedied")
        if j not in JUDGMENTS or c not in cohorts:
            raise ValueError("missing judgment or aggregate source")
    gaps = _indexed(bundle["unresolved_gaps"], "gaps")
    if {g.get("judgment_id") for g in gaps.values()} != JUDGMENTS:
        raise ValueError("open evidence gaps required for all three judgments")
    for g in gaps.values():
        if (g.get("state") != "unverified_original_individual_record" or
                g.get("individual_outcome_proven") is not False or
                not isinstance(g.get("record_needed"), str) or len(g["record_needed"]) < 40):
            raise ValueError("individual outcome presumed resolved without primary record")
    return sources, cohorts, money, corrections, links, gaps


def evaluate(bundle):
    sources, cohorts, money, corrections, links, gaps = validate(bundle)
    rows = []
    for ident,row in sorted(cohorts.items()):
        stages = row["stages"]
        rows.append({
            "cohort_id":ident, "jurisdiction":sources[row["source_id"]]["jurisdiction"],
            "source_url": sources[row["source_id"]]["url"],
            "data_as_of": row["data_as_of"], "reported_total": row["reported_total"],
            "unit": row["unit"], "scope_note": row["scope_note"],
            "is_exhaustive_partition": row["is_exhaustive_partition"],
            "approximate":row["approximate"],
            "stages": stages,
            "stage_fraction_within_same_cohort_only": {
                key: round(value / row["reported_total"], 6)
                for key,value in stages.items()
            } if row["is_exhaustive_partition"] else {},
            "individual_recipient_verification":False,
            "global_remedy_success_rate": None,
        })
    return {
        "schema":"legal_codex.outcome_trace_result.v1",
        "as_of":bundle["as_of"],
        "source_count":len(sources), "cohort_count":len(cohorts),
        "monetary_category_count":len(money), "correction_count":len(corrections),
        "context_only_court_link_count":len(links), "unresolved_individual_record_count":len(gaps),
        "cohorts":rows,
        "monetary_categories":[{
            "id":id,"source_url": sources[row["source_id"]]["url"],
            "data_as_of":row["data_as_of"],"amount":row["reported_amount"],
            "unit":row["unit"],"scope_note":row["scope_note"],
            "rounding_and_overlap_restricted":True,
        } for id,row in sorted(money.items())],
        "corrected_official_figures":[{
            "id":id,"superseded":row["superseded_amount"],
            "current":row["corrected_amount"],
            "revision_date":row["revision_published_on"],
            "source_url":row["source_url"],
            "not_new_disbursement":True,
        } for id,row in sorted(corrections.items())],
        "court_links":[{
            "judgment_id":x["judgment_id"],"cohort_id":x["cohort_id"],
            "individual_link_verified":False, "legal_causation_established":False,
        } for x in links.values()],
        "missing_original_records":[g["record_needed"] for g in gaps.values()],
        "individual_case_outcomes_authenticated":0,
        "global_remedy_effectiveness_proven":False,
        "foreign_law_applied":False, "individual_culpability_inferred":False,
        "document_bytes_authenticated":False,"publication_authorized":False,
        "input_digest":_hash(bundle),
    }


def semantic_packet(bundle, result):
    if result.get("input_digest") != _hash(bundle):
        raise ValueError("changed ledger cannot reuse stale preview")
    sources, cohorts, money, corrections, links, gaps = validate(bundle)
    nodes,edges=[],[]
    for ident,row in sources.items():
        nodes.append({"key":"source-"+ident,"kind":"source","layer":"neutral",
                      "statement":row["url"],"source_refs":[row["url"]],
                      "provenance":{"data_as_of":row["data_as_of"],
                                    "original_bytes_captured":False}})
    for ident,row in cohorts.items():
        nodes.append({"key":"cohort-"+ident,"kind":"concept","layer":"neutral",
                      "statement":row["scope_note"],
                      "source_refs":[sources[row["source_id"]]["url"]],
                      "provenance":{"unit":row["unit"],"denominator":row["reported_total"],
                                    "individuals_matched":False}})
        edges.append({"source":"source-"+row["source_id"],"target":"cohort-"+ident,
                      "relation":"REPORTS_AGGREGATE_COHORT","status":"candidate"})
        for key,value in row["stages"].items():
            nodekey="stage-"+ident+"-"+key
            nodes.append({"key":nodekey,"kind":"observation","layer":"neutral",
                          "statement":f"{key}: {value} {row['unit']} ({row['data_as_of']})",
                          "source_refs":[sources[row["source_id"]]["url"]],
                          "provenance":{"source_only":True,"individual_outcome_verified":False}})
            edges.append({"source":"cohort-"+ident,"target":nodekey,
                          "relation":"REPORTS_STAGE_COUNT","status":"candidate"})
    for ident,row in money.items():
        nodes.append({"key":"amount-"+ident,"kind":"observation","layer":"neutral",
                      "statement":f"{row['reported_amount']} {row['unit']}: {row['scope_note']}",
                      "source_refs":[sources[row["source_id"]]["url"]],
                      "provenance":{"rounded":True,"additive_with_other_amounts":False}})
        edges.append({"source":"source-"+row["source_id"],"target":"amount-"+ident,
                      "relation":"REPORTS_CUMULATIVE_AMOUNT","status":"candidate"})
    for ident,row in corrections.items():
        nodes.append({"key":"revision-"+ident,"kind":"observation","layer":"neutral",
                      "statement":f"Superseded {row['superseded_amount']} corrected to {row['corrected_amount']}",
                      "source_refs":[row["source_url"]],
                      "provenance":{"old_value_superseded":True,"new_payment_established":False}})
        edges.append({"source":"revision-"+ident,"target":"amount-"+row["target_amount_id"],
                      "relation":"CORRECTS_PRIOR_REPORT","status":"candidate"})
    for ident,g in gaps.items():
        nodes.append({"key":"gap-"+ident,"kind":"concept","layer":"neutral",
                      "statement":g["record_needed"],"provenance":{"original_record_obtained":False}})
    # No court -> aggregate graph relation: source context is not an
    # individual litigant identity crosswalk or a proof of causal redress.
    return {"schema":"cite_refinery.semantic_graph.v1",
            "source_system":"legal-codex-outcome-trace-013",
            "clusters":[],"nodes":nodes,"edges":edges}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--output",default="legal_codex_outcome_trace_013_result.json")
    p.add_argument("--packet")
    args=p.parse_args(argv)
    bundle=json.loads(Path(args.input).read_text(encoding="utf-8"))
    result=evaluate(bundle)
    Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    if args.packet:
        Path(args.packet).write_text(json.dumps(
            semantic_packet(bundle,result),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({
        "cohorts":result["cohort_count"],"sources":result["source_count"],
        "independently_verified_individual_remedies":0,
        "global_remedy_effectiveness_proven":False,
        "publication_authorized":False,
    }))


if __name__=="__main__":
    main()
