"""Audit interpretation of the published Table T2 negative-binomial sensitivity runs."""
from __future__ import annotations
import json
import math
from pathlib import Path


def assess_replication(table_quality,model_runs):
    if table_quality["table_id"]!="T2" or model_runs["schema"]!="cite_refinery.published_t2_nb_sensitivity.v1":
        raise ValueError("Incompatible source table or model reproduction schema")
    models=[]
    close=0
    unstable=0
    for key,model in model_runs["models"].items():
        item={
            "model_id":key,"status":model["status"],
            "granularity":model["grain"],"region":model["region"],
            "outcome":model["outcome"],"source_observation_count":model["observation_count"],
        }
        if model["status"]=="fit":
            irr=float(model["IRR"]);p=float(model["p_value"]);theta=float(model["theta"])
            published=model["reported_T3"]
            matches=(abs(irr-float(published["IRR"]))<0.005 and
                     abs(p-float(published["p"]))<0.005)
            pathological=theta>1e6 or not math.isfinite(theta)
            item.update({
                "IRR":irr,"p_value":p,"theta":theta,
                "published_IRR":float(published["IRR"]),
                "published_p_value":float(published["p"]),
                "matches_published_T3_within_set_tolerances":matches,
                "theta_near_poisson_limit_or_unstable":pathological,
                "fit_warnings":model.get("warnings",[]),
            })
            close+=matches;unstable+=pathological
        else:item["error"]=model.get("error")
        models.append(item)
    notable=[x for x in table_quality["arithmetic_issues"]
             if x["type"]=="within_row_sex_total_mismatch"]
    return {
        "schema":"cite_refinery.published_table_replication_assessment.v1",
        "published_study_doi":table_quality["source_doi"],
        "data_kind":"journal_published_program_level_aggregates_not_author_operational_data",
        "program_rows":table_quality["row_count"],
        "positive_effort_rows":table_quality["positive_effort_rows"],
        "zero_day_rows_excluded_in_log_offset":table_quality["row_count"]-table_quality["positive_effort_rows"],
        "subtotal_groups_checked":table_quality["source_subtotals_checked"],
        "within_row_sex_total_mismatches":notable,
        "other_table_anomalies":[x for x in table_quality["arithmetic_issues"]
                                 if x["type"]!="within_row_sex_total_mismatch"],
        "model_sensitivity_cases":models,
        "models_total":len(models),
        "close_IRR_and_p_reproductions_at_preregistered_tolerances":close,
        "very_high_or_nonfinite_theta_fits":unstable,
        "claim_scope":{
            "observed":"Published Table T2 arithmetic and 12 explicitly specified NB sensitivity fits can be independently calculated.",
            "not_observed":"Original statistical software scripts, unpublished exact analysis extracts, intervention microdata or original three-way interaction design matrix.",
            "cannot_conclude":"That the journal's authors committed a computational or statistical error. Differences can follow from missing analysis records or alternative preprocessing, or low-sample theta instability.",
            "required_next_evidence":"Anuradhapura analysis scripts, annual count/effort definitions, program-level buffer intervention records, and data dictionary from the corresponding author.",
        },
        "authority":"diagnostic_sensitive_reanalysis_not_exact_replication",
    }


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--table-quality",type=Path,required=True)
    p.add_argument("--models",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(argv)
    report=assess_replication(json.loads(args.table_quality.read_text()),
                              json.loads(args.models.read_text()))
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("REPLICATION_DIAGNOSTIC",report["models_total"],"models",
          report["close_IRR_and_p_reproductions_at_preregistered_tolerances"],
          "closely reproduced","MISMATCH_ROWS",len(report["within_row_sex_total_mismatches"]),
          "UNSTABLE_THETA",report["very_high_or_nonfinite_theta_fits"])

if __name__=="__main__":main()
