"""Publish a bounded, source-link-only manifest of a live investigation.

Full source excerpts and generated model outputs stay in the local persistent
workspace; this export intentionally avoids republishing entire abstracts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def sanitized_receipt(state):
    output={
        "schema":"cite_refinery.investigation_receipt.v1",
        "investigation_id":state["id"],
        "question":state["question"],
        "status":state["stage"],
        "project_id":state["project_id"],
        "authority":"All model-generated nodes are neutral candidates; no empirical or clinical outcome accepted.",
        "rounds":[],
        "frontier_size":len(state["frontier"]),
        "known_limitations":[
            "Both generator and critic used the same inference provider/model; not independent corroboration.",
            "Europe PMC abstract and selected official webpage excerpts are leads, not full-source verification.",
            "An LLM's entailed verdict does not verify a statistical claim or real-world intervention impact.",
            "Unreviewed, machine-generated graph coverage must not be conflated with three-family evidentiary completeness.",
            "The serialized full investigation is stored only in a local working directory, not included in this snapshot.",
        ],
    }
    for r in state["rounds"]:
        inspected=r.get("inspected",{})
        critic=r.get("critique",{})
        sources=[{
            "id":s["id"],"url":s["url"],"title":s.get("title"),
            "origin_type":s.get("origin_type"),"scope":s.get("source_scope"),
            "passage_sha256":s.get("passage_sha256"),
        } for s in r.get("sources",[])]
        packet=r.get("packet",{})
        output["rounds"].append({
            "number":r["number"],
            "focus":r["focus"],
            "plan_queries":r["plan"]["queries"],
            "hypotheses":r["plan"]["hypotheses"],
            "state":r["state"],
            "source_count":len(sources),
            "sources":sources,
            "source_error_counts":len(r.get("source_failures",[])),
            "model_propositions":len(inspected.get("propositions",[])),
            "model_candidate_bridges":len(inspected.get("bridges",[])),
            "quote_rejected_count":len(inspected.get("rejected",[])),
            "critic_proposition_verdicts":dict(Counter(p["reviewer_verdict"] for p in critic.get("propositions",[]))),
            "critic_bridge_verdicts":dict(Counter(p["reviewer_verdict"] for p in critic.get("bridges",[]))),
            "graph_node_count":len(packet.get("nodes",[])),
            "graph_edge_count":len(packet.get("edges",[])),
            "graph_edge_statuses":dict(Counter(e.get("status") for e in packet.get("edges",[]))),
            "neutral_only":all(n.get("layer")=="neutral" for n in packet.get("nodes",[])),
            "review_queue_sample":[x["question"] for x in r.get("open_questions",[])[:10]],
            "proposition_sample":[{
                "id":p["id"],"type":p["claim_type"],
                "statement":p["statement"][:200],
                "source_ids":[a["source_id"] for a in p["support"]],
                "module_ids":p["module_ids"],
            } for p in inspected.get("propositions",[])[:12]],
            "receipt_id":r.get("graph_receipt",{}).get("id"),
        })
    return output


def main():
    p=argparse.ArgumentParser()
    p.add_argument("state_json",type=Path)
    p.add_argument("output_json",type=Path)
    args=p.parse_args()
    state=json.loads(args.state_json.read_text(encoding="utf-8"))
    out=sanitized_receipt(state)
    args.output_json.parent.mkdir(parents=True,exist_ok=True)
    args.output_json.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("EXPORTED_SOURCE_LINK_RECEIPT",args.output_json,"ROUNDS",len(out["rounds"]))


if __name__=="__main__":
    main()
