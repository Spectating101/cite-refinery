"""Cross-model *diagnostic agreement*, grounded against executable source checks.

Never equate several AI readings with independent empirical validation.
Reads saved responses from authenticated local model CLIs; no model outputs
write accepted graph state. The functional trial remains the reference.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

from .external_llm_runtime import AGY_VERIFIED_MODELS

SCHEMA="cite_refinery.cross_model_evidence_diagnostic.v1"

def family(name:str)->str:
    return "gemini" if name.startswith("gemini-") else "claude" if name.startswith("claude-") else "other"

def compare(trials:dict[str,Any],answers:dict[str,dict[str,Any]])->dict[str,Any]:
    if trials.get("schema")!="cite_refinery.functional_component_trials.v1" or (
        trials.get("graph_status_promotion_allowed") is not False):
        raise ValueError("unreviewed or promoted reference trials")
    battery=next((p for p in trials["probes"]
                  if p["asset_id"]=="github:lingrany/EverBatt-LFP-Recycling-Analysis"),None)
    if not battery:
        raise ValueError("real functional battery test missing")
    test=next((x for x in battery["cases"]
               if x["name"]=="direct_positive_fee_accounting"),None)
    if not test or test["status"]!="fail":
        raise ValueError("reference accounting invariant was not actually exercised")
    observed=float(test["actual"]["actual_profit_reduction_usd"])
    expected=float(test["expected"]["profit_reduction_usd"])
    # The LLM pilot defines delta as profit(+1) - profit(0).
    reference_expected=-expected
    reference_observed=-observed
    if len(answers)<2 or len(answers)>8:
        raise ValueError("need bounded distinct model reviews")
    rows=[]
    for name,answer in sorted(answers.items()):
        if name not in AGY_VERIFIED_MODELS or not isinstance(answer,dict):
            raise ValueError("model ID must match the local verified catalog")
        verdict=answer.get("defect_verdict",answer.get("verdict"))
        want=answer.get("expected_positive_fee_profit_delta_usd",answer.get("expected_delta_usd"))
        got=answer.get("actual_positive_fee_profit_delta_usd",answer.get("actual_delta_usd"))
        try:
            arithmetic=abs(float(want)-reference_expected)<1e-4 and abs(float(got)-reference_observed)<1e-4
        except (ValueError,TypeError):
            arithmetic=False
        identifies=verdict in ("reproduced_accounting_defect","accounting_omission")
        has_boundary=bool(answer.get("scope_boundary") or answer.get("limitation"))
        rows.append({
            "model":name,"model_family":family(name),
            "reported_defect":verdict,"arithmetic_matches_executed_reference":arithmetic,
            "includes_scope_limitation_text":has_boundary,
            "diagnostic_agreement":bool(arithmetic and identifies and has_boundary),
            "model_is_independent_executor":False,
            "automatic_evidence_promotion_allowed":False,
        })
    groups=sorted({r["model_family"] for r in rows})
    return {
        "schema":SCHEMA,
        "source_case":"battery_recycling_positive_gate_fee_10k_tonnes_per_year",
        "reference_source_commit":battery["source"]["git_commit"],
        "reference_function":"lfp_analysis_verified.py:analyze_method",
        "reference_expected_delta_usd":reference_expected,
        "reference_observed_delta_usd":reference_observed,
        "model_reviews":rows,
        "distinct_model_families":groups,
        "all_reviews_agree_with_executed_reference":all(x["diagnostic_agreement"] for x in rows),
        "reliability_statement":"Model agreement is reproducible claim interpretation, not independent code execution; the executed upstream accounting test establishes the bounded defect, and no real plant economics have been verified.",
        "evidence_status":"source_pinned_synthetic_accounting_defect_not_commercial_validation",
        "research_holdout_touched":False,
        "native_graph_status_promoted":False,
    }

def markdown(report:dict[str,Any])->str:
    if report.get("schema")!=SCHEMA:raise ValueError("invalid comparative report")
    out=[
        "# Authenticated Optiplex cross-model accounting review", "",
        "Three distinct model IDs analyzed the same synthetic fee-accounting "
        "discrepancy. **Models do not independently execute or certify the economic outcome**; "
        "their interpretation is compared to the separately executed test.", "",
        "| Model | Provider family | Explains defect and delta correctly? |",
        "|---|---|---|",
    ]
    for r in report["model_reviews"]:
        out.append("| "+r["model"]+" | "+r["model_family"]+" | "+
                   ("yes" if r["diagnostic_agreement"] else "no / requires inspection")+" |")
    out+=["","The pinned source test expects profit(+1) − profit(0) = **"+
          format(report["reference_expected_delta_usd"],",.0f")+
          " USD** but observes **"+format(0 if report["reference_observed_delta_usd"]==0 else report["reference_observed_delta_usd"],",.0f")+
          " USD**.","",
          "Argon belongs to the Gemini family. Opus and Sonnet are different "
          "Claude models in the **same provider family**, not three wholly "
          "independent research groups. The initial long-format Sonnet response "
          "was rejected by the JSON parser; a shorter separately documented "
          "structured-prompt retry succeeded. Do not hide this interface limit.","",
          "**No graph status upgrade, scientific validation, actual recycler profit, "
          "rights review or commercial lead is implied.**",""]
    return "\n".join(out)

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(prog="cite-refinery-cross-model-evidence-check")
    p.add_argument("--trials",type=Path,required=True)
    p.add_argument("--review",action="append",required=True,
                   help="MODEL=PATH to a locally saved, authenticated, structured review")
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    a=p.parse_args(argv)
    answers={}
    for item in a.review:
        if "=" not in item:
            raise ValueError("review must be MODEL=PATH")
        name,path=item.split("=",1)
        if name in answers:
            raise ValueError("duplicate model review")
        answers[name]=json.loads(Path(path).read_text(encoding="utf-8"))
    result=compare(json.loads(a.trials.read_text(encoding="utf-8")),answers)
    a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    a.markdown.write_text(markdown(result),encoding="utf-8")
    print("Model reviews",len(result["model_reviews"]),
          "all checked",result["all_reviews_agree_with_executed_reference"])
    return 0

if __name__=="__main__":
    raise SystemExit(main())
