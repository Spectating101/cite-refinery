"""Blinded, inspectable benchmark for source entailment, overreach, and abstention.

The gold labels were drafted from explicit published tables and scope notes,
not from an independently recruited human adjudication panel. This is a small
regression/diagnostic set, not an unbiased estimate of model accuracy.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

LABELS={"entailed","contradicted","overreach","unresolved"}


def make_judge_prompt(cases):
    if not 4<=len(cases)<=35:raise ValueError("Benchmark requires bounded case count")
    public=[]
    for c in cases:
        if not {"id","claim","evidence"} <= set(c):
            raise ValueError("Case lacks ID, claim, or source excerpt")
        public.append({"id":c["id"],"claim":c["claim"],"evidence":c["evidence"]})
    return (
        "You are a skeptical blind scientific SOURCE-ENTAILMENT ADJUDICATOR. "
        "Treat each CASE in isolation. You have only the supplied excerpts, not a "
        "general-world fact-checking task. Do not assume a published association "
        "is a causal effect. Do not confuse dog sterilization eligibility with "
        "total abundance, a pre/post estimate with an interaction, or different "
        "study populations. If the evidence DOES NOT directly establish a claim "
        "but does not negate it, classify 'overreach'. If the excerpts are too "
        "ambiguous to judge either way, 'unresolved'. 'contradicted' means the "
        "given evidence explicitly conflicts with the claim, including numerical "
        "p-values or data-access statements. 'entailed' means source content "
        "logically supports the claim AS WRITTEN, not a stronger interpretation. "
        "Return JSON only: {\"predictions\":[{\"id\":\"B01\","
        "\"label\":\"entailed|contradicted|overreach|unresolved\","
        "\"rationale\":\"concise precise rationale\"}]}. "
        "You do not receive labels or expected explanations. Some cases involve "
        "illustrative arithmetic or two separately defined estimands.\n\n"
        "BLIND_TESTS:\n"+json.dumps(public,ensure_ascii=False,separators=(",",":"))
    )


def score_benchmark(cases,answer):
    expected={c["id"]:c["expected"] for c in cases}
    if any(y not in LABELS for y in expected.values()):
        raise ValueError("Invalid reference label")
    if not isinstance(answer,dict) or not isinstance(answer.get("predictions"),list):
        raise ValueError("Missing benchmark predictions")
    actual={}
    for p in answer["predictions"]:
        if not isinstance(p,dict) or p.get("id") not in expected or p["id"] in actual or p.get("label") not in LABELS:
            raise ValueError("Unexpected, duplicate, or invalid prediction")
        if not isinstance(p.get("rationale"),str) or len(p["rationale"].strip())<12:
            raise ValueError("Each adjudication requires an inspectable rationale")
        actual[p["id"]]=p
    if set(actual)!=set(expected):
        raise ValueError("Incomplete benchmark response; do not silently score only answered cases")
    correct=sum(actual[key]["label"]==gold for key,gold in expected.items())
    confusion={g:{p:0 for p in sorted(LABELS)} for g in sorted(LABELS)}
    per_label={}
    for key,gold in expected.items():
        confusion[gold][actual[key]["label"]]+=1
    for label in sorted(LABELS):
        total=sum(1 for y in expected.values() if y==label)
        right=sum(actual[k]["label"]==label and y==label for k,y in expected.items())
        per_label[label]={"total":total,"correct":right,"accuracy":right/total if total else None}
    false_accepted=sum(actual[key]["label"]=="entailed" and gold!="entailed"
                       for key,gold in expected.items())
    false_contradictions=sum(actual[key]["label"]=="contradicted" and gold!="contradicted"
                            for key,gold in expected.items())
    audit=[]
    for c in cases:
        key=c["id"]
        audit.append({"id":key,"expected":c["expected"],"predicted":actual[key]["label"],
                      "pass":c["expected"]==actual[key]["label"],
                      "rationale":actual[key]["rationale"],
                      "gold_reason":c["gold_reason"]})
    return {
        "schema":"cite_refinery.source_entailment_benchmark_results.v1",
        "name":"Anuradhapura source-scope diagnostic set",
        "size":len(cases),"correct":correct,
        "accuracy":correct/len(cases),
        "by_reference_label":per_label,
        "confusion":confusion,
        "false_positive_entailment_count":false_accepted,
        "false_contradiction_count":false_contradictions,
        "abstentions":sum(p["label"]=="unresolved" for p in actual.values()),
        "case_results":audit,
        "validity_limit":"Curated source-anchored benchmark, labels authored for this project; no independent blinded human gold, uncertain generalization, no automatic scientific acceptance.",
    }
