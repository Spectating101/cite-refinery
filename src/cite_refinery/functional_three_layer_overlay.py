"""Attach executed bounded component trials to exact three-layer identities.

A tested component method is NOT a validated intervention or a full technical
implementation. Failed checks block any status promotion. Results stay outside
native accepted-evidence ingestion and must be reviewed before operational use.
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
from typing import Any

SCHEMA="cite_refinery.functional_three_layer_overlay.v1"
STATES={"pass","fail","blocked","not_tested"}

def build(graph:dict[str,Any],trials:dict[str,Any], *,
          semantic_review:dict[str,Any]|None=None)->dict[str,Any]:
    if graph.get("schema")!="cite_refinery.three_layer_atlas_projection.v1" or \
       trials.get("schema")!="cite_refinery.functional_component_trials.v1" or \
       trials.get("graph_status_promotion_allowed") is not False or \
       trials.get("technical_fit_confirmed") is not False:
        raise ValueError("untrusted conceptual graph or promoted trial")
    ids={x["id"]:x for x in graph["nodes"]}
    queued={}
    if semantic_review:
        if semantic_review.get("schema")!="cite_refinery.three_layer_semantic_review_queue.v1" or \
           semantic_review.get("counts",{}).get("qualified_academic_edges_promoted")!=0:
            raise ValueError("semantic review cannot be promoted into functional evidence")
        queued={row["academic_id"]:row for row in semantic_review["semantic_review_queue"]}
    grouped={}
    for probe in trials["probes"]:
        aid=probe["asset_id"];mid=probe["mechanism_id"]
        if aid in grouped or aid not in ids or mid not in ids or \
           ids[aid]["layer"]!="implementation" or ids[mid]["layer"]!="academic":
            raise ValueError("functional proof must match exact existing technical and academic IDs")
        related=[e for e in graph["edges"]
                 if e["from"]==mid and e["to"]==aid and
                    e["relation"]=="POSSIBLE_PARTIAL_IMPLEMENTATION"]
        if len(related)!=1:
            raise ValueError("no exact candidate relationship to audited component")
        if not isinstance(probe["cases"],list) or not probe["cases"]:
            raise ValueError("empty functional trial is not evidence")
        if len({c["name"] for c in probe["cases"]})!=len(probe["cases"]) or any(
            c.get("status") not in STATES or c.get("claim_authority")!=
            "synthetic_code_or_static_configuration_probe_only"
            for c in probe["cases"]
        ):
            raise ValueError("malformed or unreviewed functional cases")
        cases=probe["cases"]
        counts=Counter(c["status"] for c in cases)
        graph_problems=[k for k,v in graph["problem_views"].items()
                        if mid in v["academic_nodes"] and any(
                            x["id"]==aid for x in v["implementation_links"])]
        if len(graph_problems)!=1:
            raise ValueError("component must belong to precisely one defined practical question")
        practical=graph_problems[0]
        scholarly=queued.get(mid)
        grouped[aid]={
            "practical_id":practical,"academic_id":mid,
            "implementation_id":aid,
            "checked_commit":probe["source"]["git_commit"],
            "execution_type":probe["execution"],
            "component_requirement_checks":cases,
            "check_counts":dict(counts),
            "reproducible_component_defect_detected":bool(counts["fail"]),
            "deployment_prerequisites_missing":bool(counts["blocked"] or counts["not_tested"]),
            "source_scope":"Upstream code at pinned revision for synthetic tested behavior only",
            "scientific_mechanism_status":(
                scholarly["cross_source_mechanism_review"]["assessment"] if scholarly and
                scholarly.get("cross_source_mechanism_review") else "not_reviewed_in_this_overlay"
            ),
            "research_entailment_approved":False,
            "partial_component_behavior_reproduced":bool(counts["pass"]),
            "end_to_end_functionality_verified":False,
            "real_world_outcome_verified":False,
            "licensed_commercial_use_confirmed":False,
            "value_capture_verified":False,
            "operator_action":"Investigate failed checks, clarify rights and compare alternative components before any implementation or business decision.",
            "graph_transition_authorized":False,
        }
    return {
        "schema":SCHEMA,"linked_trials":list(grouped.values()),
        "counts":{
            "practical_academic_implementation_paths_tested":len(grouped),
            "candidate_paths_with_reproduced_component_defects":sum(
                bool(x["reproducible_component_defect_detected"]) for x in grouped.values()),
            "candidate_paths_with_full_tech_validation":0,
            "academic_edges_qualified":0,
            "confirmed_buyers":0,
        },
        "authority":"read_only_comparative_functionality_evidence_for_manual_review",
        "status":"No source or functional trial can automatically qualify an implementation for deployment",
        "boundary":"Two tested Python component modules, one YAML-only static audit. Operational behavior, hazard controls, actual deployment, software rights, research mechanisms and economic value remain independently unvalidated. No native graph writes or holdout changes.",
    }


def markdown(result:dict[str,Any])->str:
    if result.get("schema")!=SCHEMA:
        raise ValueError("functional overlay required")
    lines=[
        "# Practical ↔ Academic ↔ Implementation: execution results, not a commercial shortlist","",
        "The previously unified conceptual graph now has **read-only functional "
        "trial evidence** attached to three existing three-layer paths. The "
        "status of every edge remains **candidate** or lower; outcomes below "
        "are synthetic or static and cannot validate the full system.",""]
    for row in result["linked_trials"]:
        lines+=["## "+row["practical_id"].removeprefix("problem:").replace("_"," ").title(),"",
                "- **Academic mechanism:** "+row["academic_id"]+
                " (review: "+row["scientific_mechanism_status"]+")",
                "- **Implementation:** "+row["implementation_id"]+
                " at pinned revision "+row["checked_commit"][:12],
                "- **Test execution:** "+row["execution_type"],
                "- **Reproduced failures:** "+str(row["check_counts"].get("fail",0))+
                "; missing prerequisites: "+str(row["check_counts"].get("blocked",0))+".","",
                "### Exact failed or blocked requirements",""]
        for case in row["component_requirement_checks"]:
            if case["status"] in {"fail","blocked"}:
                lines+=["- **"+case["name"]+" ("+case["status"]+")**: "+
                        case["requirement"]+" Evidence: "+
                        json.dumps(case["actual"],ensure_ascii=False)[:235]]
        lines+=["","**Conversion gate:** FAIL/UNVERIFIED. No full technical fit, "
                "license clearance, scientific efficacy, or buyer.",
                ""]
    lines+=["## Next engineering work","",
            "For each failed check, ask whether the flaw can be repaired under "
            "proper license or whether another implementation is safer or cheaper. "
            "Only run actual hardware, field deployment, or economic simulations "
            "with measured inputs and independent controls; passing synthetic "
            "unit calculations does not clear the deployment gate.",""]
    return "\n".join(lines)

def main(argv:list[str]|None=None)->int:
    import argparse
    p=argparse.ArgumentParser(prog="cite-refinery-functional-overlay")
    p.add_argument("--graph",type=Path,required=True)
    p.add_argument("--trials",type=Path,required=True)
    p.add_argument("--semantic",type=Path)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    args=p.parse_args(argv)
    def read(path):return json.loads(path.read_text(encoding="utf-8"))
    result=build(read(args.graph),read(args.trials),
                 semantic_review=read(args.semantic) if args.semantic else None)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    args.markdown.write_text(markdown(result),encoding="utf-8")
    print("Three-layer functional overlay:",result["counts"],flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
