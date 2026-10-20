"""Attach limited atomic claim diagnostics to Academic nodes without status promotion.

A correct model verdict about a published abstract does not validate the
synthesized mechanism, technical suitability, an actual intervention or a
revenue hypothesis. The original three-layer graph remains read-only.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

SCHEMA="cite_refinery.three_layer_semantic_review_queue.v1"

def build(graph:dict[str,Any],diagnostic:dict[str,Any],
          cross_source:dict[str,Any]|None=None)->dict[str,Any]:
    if graph.get("schema")!="cite_refinery.three_layer_atlas_projection.v1" or \
       diagnostic.get("schema")!="cite_refinery.entailment_diagnostic_report.v1" or \
       diagnostic.get("graph_promotion_allowed") is not False:
        raise ValueError("untrusted graph or promoted diagnostic")
    critic={}
    if cross_source is not None:
        if (cross_source.get("schema")!="cite_refinery.cross_source_mechanism_review.v1" or
            cross_source.get("promotion_allowed") is not False):
            raise ValueError("cross-source critic must be unpromoted model review")
        for evaluation in cross_source.get("assessments",[]):
            key=evaluation["id"]
            if (key in critic or evaluation.get("accepted_academic_edge") is not False or
                evaluation.get("validated_implementation") is not False or
                evaluation.get("commercial_conversion_confirmed") is not False):
                raise ValueError("cross-source interpretation cannot accept evidence")
            critic[key]=evaluation
    indexed={n["id"]:n for n in graph["nodes"]}
    if not isinstance(graph.get("problem_views"),dict):
        raise ValueError("query graph unavailable")
    queue=[]
    seen=set()
    for case in diagnostic["cases"]:
        if case["id"] in seen or case["reference"] not in {
            "entailed","contradicted","overreach","unresolved"} or \
           case["model_label"] not in {"entailed","contradicted","overreach","unresolved"} or \
           case.get("commercial_or_scientific_status_promoted") is not False or \
           case.get("human_adjudication_complete") is not False:
            raise ValueError("promoted or duplicate semantic diagnostic")
        seen.add(case["id"])
    by_domain={}
    for case in diagnostic["cases"]:
        by_domain.setdefault(case["domain"],[]).append(case)
    for domain, cases in sorted(by_domain.items()):
        practical="problem:"+domain
        academic="mechanism:"+domain
        if practical not in indexed or academic not in indexed or \
           indexed[practical]["layer"]!="practical" or \
           indexed[academic]["layer"]!="academic":
            raise ValueError("diagnostic domain not an exact practical-academic pair")
        if academic not in graph["problem_views"][practical]["academic_nodes"]:
            raise ValueError("no supported source-to-mechanism link in graph")
        types=Counter(x["model_label"] for x in cases)
        wrong=[x for x in cases if x["reference"]!=x["model_label"]]
        unsafe=[x for x in cases if x["model_label"]=="entailed" and x["reference"]!="entailed"]
        queue.append({
            "practical_id":practical,
            "academic_id":academic,
            "source_ids":sorted({x["source_id"] for x in cases}),
            "inspected_claim_ids":[x["id"] for x in cases],
            "model_verdicts":dict(types),
            "disagreements":[{"id":x["id"],"model":x["model_label"],
                               "reference":x["reference"],"reason":x["reason"]}
                              for x in wrong],
            "unsupported_claims":[{"id":x["id"],"claim":x["claim"],
                                    "reference":x["reference"],
                                    "source_url":x["source_url"]}
                                   for x in cases if x["reference"]!="entailed"],
            "false_source_entailment_claims":[x["id"] for x in unsafe],
            "atomic_entailment_is_mechanism_proof":False,
            "source_entailment_status":"model_diagnostic_only_not_human_confirmed",
            "mechanism_entailment_status":"unreviewed_aggregate_cross_source_reasoning",
            "implementation_fit_status":"not_evaluated_by_this_evidence_reading",
            "cross_source_mechanism_review":(
                {"assessment":critic[academic]["assessment"],
                 "supported_context":critic[academic]["what_is_supported"],
                 "unsupported_leap":critic[academic]["unsupported_leap"],
                 "source_id":critic[academic]["source_id"],
                 "original_quote":critic[academic]["quote"],
                 "next_decisive_check":critic[academic]["next_decisive_check"],
                 "implementation_boundary":critic[academic]["implementation_scope"],
                 "authority":"model_review_only_no_scientific_promotion"}
                if academic in critic else None),
            "promotion_allowed":False,
            "next_evidence_gate":"Independent reviewer must check claim/context alignment and "
                                 "the complete proposed mechanism against source methods and contrary studies.",
        })
    if critic and set(critic)!={x["academic_id"] for x in queue}:
        raise ValueError("cross-source critic must cover exactly the known academic mechanisms")
    return {
        "schema":SCHEMA,
        "semantic_review_queue":queue,
        "counts":{
            "covered_practical_academic_pairs":len(queue),
            "unreviewed_mechanism_entailments":len(queue),
            "model_disagreements":sum(len(x["disagreements"]) for x in queue),
            "unsafe_false_source_entailments":sum(len(x["false_source_entailment_claims"]) for x in queue),
            "qualified_academic_edges_promoted":0,
            "validated_technical_fit":0,
            "validated_commercial_value":0,
            "cross_source_reviews_attached":sum(
                bool(x["cross_source_mechanism_review"]) for x in queue),
        },
        "status":"bounded_development_diagnostic_not_authoritative_scientific_review",
        "boundary":"Three layers are unchanged. Diagnostic gold is investigator-authored, "
                   "independent human validation absent; atomic abstract entailment does not "
                   "validate the synthesized mechanism or a source-to-implementation link. "
                   "No holdout touched or graph promoted.",
    }


def markdown(result:dict[str,Any])->str:
    if result.get("schema")!=SCHEMA:raise ValueError("review queue required")
    out=[
        "# Semantic validation overlay for the three-layer atlas", "",
        "This view overlays **retrieved-abstract atomic-claim diagnostics** on the "
        "Academic node of each relevant Practical problem. It cannot establish "
        "the full aggregate mechanism, solution performance, or market demand.", "",
        "A source can be accurately quoted yet misinterpreted through "
        "population shifts, unjustified causal claims, or invented interventions.", "",
    ]
    for group in result["semantic_review_queue"]:
        out+=["## "+group["practical_id"].removeprefix("problem:").replace("_"," ").title(), "",
              "Academic source-entailment: **not independently approved**; "
              "mechanism-to-implementation fit: **not verified**.", "",
              "Unsupported or contradicted study-level inferences (investigator reference labels):",""]
        for u in group["unsupported_claims"]:
            out+=["- "+u["claim"]+" — **"+u["reference"]+"** [Abstract]("+u["source_url"]+")"]
        out.append("")
        if group["cross_source_mechanism_review"]:
            r=group["cross_source_mechanism_review"]
            out+=["**Synthesized mechanism:** "+r["assessment"].replace("_"," ")+".","",
                  "**Unsupported link:** "+r["unsupported_leap"],"",
                  "**Decisive next check:** "+r["next_decisive_check"],""]
        if group["disagreements"]:
            out+=["Model/reference disagreements require review: "+
                  ", ".join(x["id"]+" ("+x["reference"]+" / "+x["model"]+")"
                            for x in group["disagreements"]),""]
    out+=["## Gate", "",
          "No academic, implementation, or commercialization claim has been "
          "promoted. Reviewer confirmation of evidence scope and mechanism "
          "entailment remains required before any authorization-changing graph packet.",
          ""]
    return "\n".join(out)

def main(argv:list[str]|None=None)->int:
    import argparse
    p=argparse.ArgumentParser(prog="cite-refinery-three-layer-semantic-overlay")
    p.add_argument("--graph",required=True,type=Path)
    p.add_argument("--diagnostic",required=True,type=Path)
    p.add_argument("--cross-source",type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--markdown",required=True,type=Path)
    args=p.parse_args(argv)
    def load(path):return json.loads(path.read_text(encoding="utf-8"))
    obj=build(load(args.graph),load(args.diagnostic),
              load(args.cross_source) if args.cross_source else None)
    args.output.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n")
    args.markdown.write_text(markdown(obj),encoding="utf-8")
    print("Semantic review queue:",obj["counts"],flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
