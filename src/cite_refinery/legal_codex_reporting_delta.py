"""Milestone 014: separate real reporting-period deltas from retroactive corrections.

Uses the already validated official 013 aggregate fixture. All amounts are
rounded cumulative publisher-reported figures, not audited bank transactions.
A difference across comparable reporting periods is NOT a correction; a
correction to an older reporting period is NOT new redress paid. No cross-
scheme or cross-country denominator manipulation is permitted.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path

from .legal_codex_outcome_trace import validate as validate_outcome

SCHEMA = "legal_codex.reporting_delta_result.v1"
PAIRS = (
    ("uk_total_sep_to_oct", "uk_all_redress_sep_corrected", "uk_all_redress_oct"),
    ("uk_hssa_sep_to_oct", "uk_hssa_sep_corrected", "uk_hssa_paid"),
)
CURRENT_TOTAL="uk_all_redress_oct"
OCT_COMPONENTS=("uk_hss_paid", "uk_hssa_paid", "uk_glo_paid",
                "uk_hcrs_paid", "uk_oc_closed_paid")
CORRECTIONS=("uk_sep_total_correction","uk_sep_hssa_correction")


def _hash(data):
    return hashlib.sha256(json.dumps(
        data, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")).hexdigest()


def evaluate(bundle):
    validate_outcome(bundle)
    rows = {m["id"]:m for m in bundle["money"]}
    revisions = {r["id"]:r for r in bundle["corrections"]}
    results = []
    for ident,before,after in PAIRS:
        old, new = rows[before],rows[after]
        if (old["unit"] != new["unit"] or
                old["amount_kind"] != new["amount_kind"] or
                old["unit"] != "GBP_million"):
            raise ValueError("incommensurable currency or measurement unit")
        start,end=date.fromisoformat(old["data_as_of"]),date.fromisoformat(new["data_as_of"])
        if start >= end:
            raise ValueError("observations must reflect later underlying reporting periods")
        change = new["reported_amount"]-old["reported_amount"]
        results.append({
            "id": ident,"earlier_metric":before,"later_metric":after,
            "earlier_data_as_of":old["data_as_of"],
            "later_data_as_of":new["data_as_of"],
            "earlier_official_reported":old["reported_amount"],
            "later_official_reported":new["reported_amount"],
            "rounded_reported_change":change,
            "unit":old["unit"],
            "change_type":"newer_published_cumulative_observation",
            "source_urls":[next(s["url"] for s in bundle["sources"]
                                if s["id"]==old["source_id"]),
                           next(s["url"] for s in bundle["sources"]
                                if s["id"]==new["source_id"])],
            "exact_cash_disbursed_from_difference_proven":False,
            "individual_remedy_verified":False,
        })
    corrections=[]
    for ident in CORRECTIONS:
        r=revisions[ident]
        m=rows[r["target_amount_id"]]
        if m["reported_amount"] != r["corrected_amount"]:
            raise ValueError("corrected amount must equal current official snapshot")
        corrections.append({
            "id":ident,"metric_id":r["target_amount_id"],
            "data_as_of":m["data_as_of"],
            "revision_published_on":r["revision_published_on"],
            "superseded_reported":r["superseded_amount"],
            "revised_reported":r["corrected_amount"],
            "revision_difference":r["corrected_amount"]-r["superseded_amount"],
            "change_type":"retrospective_reported_data_correction",
            "not_an_incremental_payment":True,
            "source_url":r["source_url"],
            "original_pre_revision_bytes_captured":False,
        })
    components=sum(rows[ident]["reported_amount"] for ident in OCT_COMPONENTS)
    reported=rows[CURRENT_TOTAL]["reported_amount"]
    if any(rows[ident]["data_as_of"] != rows[CURRENT_TOTAL]["data_as_of"] for ident in OCT_COMPONENTS):
        raise ValueError("reported component dates do not align")
    return {
        "schema": SCHEMA,
        "real_time_series_pair_count":len(results),
        "retrospective_revision_count":len(corrections),
        "period_comparisons":results,
        "retroactive_corrections":corrections,
        "october_component_rounded_total":components,
        "october_reported_overall_rounded_total":reported,
        "rounded_component_gap":reported-components,
        "rounded_gap_is_an_audited_accounting_error":False,
        "dutch_time_series_computed":False,
        "original_pre_revision_source_bytes_archived":False,
        "source_reporting_truth_independently_verified":False,
        "exact_disbursement_inferred":False,
        "cross_country_effectiveness_ranked":False,
        "publication_authorized":False,
        "input_digest":_hash(bundle),
    }


def semantic_packet(bundle,result):
    if result.get("input_digest") != _hash(bundle):
        raise ValueError("stale reporting data cannot move into graph")
    checked=evaluate(bundle)
    if result != checked:
        raise ValueError("reporting delta values differ from validated fixture")
    nodes,edges=[],[]
    by_id={row["id"]:row for row in bundle["money"]}
    src={row["id"]:row["url"] for row in bundle["sources"]}
    emitted=set()
    for comparison in result["period_comparisons"]:
        a,b=comparison["earlier_metric"],comparison["later_metric"]
        for ident in (a,b):
            if ident in emitted:
                continue
            row=by_id[ident]
            nodes.append({"key":"metric-"+ident,"kind":"observation","layer":"neutral",
                          "statement":f"Reported {row['reported_amount']} {row['unit']} as at {row['data_as_of']}",
                          "source_refs":[src[row["source_id"]]],
                          "provenance":{"official_reported_rounded":True,
                                        "original_bytes_archived":False}})
            emitted.add(ident)
        edges.append({"source":"metric-"+a,"target":"metric-"+b,
                      "relation":"LATER_PUBLISHED_PERIOD_VALUE",
                      "status":"candidate",
                      "provenance":{"not_exact_cash_flow":True,"not_revision":True}})
    for revision in result["retroactive_corrections"]:
        ident=revision["id"]
        nodes.append({"key":"correction-"+ident,"kind":"observation","layer":"neutral",
                      "statement":f"Reported correction from {revision['superseded_reported']} to {revision['revised_reported']}",
                      "source_refs":[revision["source_url"]],
                      "provenance":{"original_pre_revision_bytes_archived":False,
                                    "publication_authorized":False}})
        edges.append({"source":"correction-"+ident,
                      "target":"metric-"+revision["metric_id"],
                      "relation":"RETROSPECTIVE_REPORT_REVISION",
                      "status":"candidate",
                      "provenance":{"is_new_money":False}})
    return {"schema":"cite_refinery.semantic_graph.v1",
            "source_system":"legal-codex-reporting-delta-014",
            "clusters":[],"nodes":nodes,"edges":edges}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--output",default="legal_codex_reporting_delta_014.json")
    p.add_argument("--packet")
    args=p.parse_args(argv)
    bundle=json.loads(Path(args.input).read_text(encoding="utf-8"))
    result=evaluate(bundle)
    Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",
                                 encoding="utf-8")
    if args.packet:
        Path(args.packet).write_text(json.dumps(
            semantic_packet(bundle,result),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({
        "period_deltas":result["real_time_series_pair_count"],
        "prior_period_corrections":result["retrospective_revision_count"],
        "exact_cash_flow_established":False,"publication_authorized":False,
    }))


if __name__=="__main__":
    main()
