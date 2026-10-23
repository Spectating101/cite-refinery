"""Evaluate atomic portfolio answers against a trivial rule-based control.

This deliberately exposes an easy-to-game task set: knowing task_kind alone
can produce the expected verdict. No run on this pack proves intelligence.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path
from .portfolio_atomic_tasks import validate_atomic_answer

SCHEMA = "cite_refinery.atomic_baseline_audit.v1"


def trivial_baseline(task):
    if task["task_kind"] == "source_attribution":
        return {"id":task["id"], "verdict":"self_reported",
                "evidence_id":task["allowed_evidence_ids"][0],
                "quote":task["reference_quote"]}
    return {"id":task["id"], "verdict":"insufficient",
            "evidence_id":None, "quote":""}


def compare(task_pack, model_receipt):
    tasks=task_pack["tasks"]
    assert len({t["id"] for t in tasks}) == len(tasks)
    assert len({r["id"] for r in model_receipt["results"]}) == len(model_receipt["results"])
    results={r["id"]:r for r in model_receipt["results"]}
    assert set(results)=={t["id"] for t in tasks}, "Missing or extra model results"
    rows=[]
    for task in tasks:
        simple=trivial_baseline(task)
        baseline_valid=validate_atomic_answer(task,simple)["contract_valid"]
        candidate=results[task["id"]]
        candidate_valid=candidate.get("contract_valid") is True
        rows.append({
            "id":task["id"],
            "task_kind":task["task_kind"],
            "baseline_valid":baseline_valid,
            "model_valid":candidate_valid,
            "model_gain_over_baseline":int(candidate_valid)-int(baseline_valid)
        })
    total=len(rows)
    by_kind={}
    for kind in sorted({r["task_kind"] for r in rows}):
        subset=[r for r in rows if r["task_kind"]==kind]
        by_kind[kind]={"n":len(subset),
                       "baseline_valid":sum(r["baseline_valid"] for r in subset),
                       "model_valid":sum(r["model_valid"] for r in subset)}
    return {
        "schema":SCHEMA, "questions":total,
        "trivial_baseline_contract_valid":sum(r["baseline_valid"] for r in rows),
        "model_contract_valid":sum(r["model_valid"] for r in rows),
        "contract_valid_delta":sum(r["model_gain_over_baseline"] for r in rows),
        "by_kind":by_kind,
        "rows":rows,
        "benchmark_is_discriminating":False,
        "no_claim_of_model_quality_or_autonomous_understanding":True,
        "next_required_evaluation":
          "Blind independently adjudicated mixed-claim tasks with verified positive, "
          "verified negative and insufficient cases; compare evidence entailment and utility."
    }


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--tasks",type=Path,required=True)
    p.add_argument("--results",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    assert not a.out.exists(), "Refuse overwrite"
    pack=json.loads(a.tasks.read_text())
    result=json.loads(a.results.read_text())
    score=compare(pack,result)
    a.out.write_text(json.dumps(score,indent=2)+"\n")
    print("ATOMIC_BASELINE_AUDIT",json.dumps({
      k:score[k] for k in ("questions","trivial_baseline_contract_valid",
                          "model_contract_valid","contract_valid_delta",
                          "benchmark_is_discriminating")},sort_keys=True))


if __name__=="__main__":
    main()
