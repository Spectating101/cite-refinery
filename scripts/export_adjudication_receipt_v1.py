"""Sanitized, reproducible receipt for a new-source contradiction audit."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def receipt(state):
    packet=state.get("packet") or {}
    findings=(state.get("findings") or {}).get("findings",[])
    return {
        "schema":"cite_refinery.adjudication_receipt.v1",
        "adjudication_id":state["id"],
        "original_investigation_id":state["investigation_id"],
        "project_id":state["project_id"],
        "stage":state["stage"],
        "targets":[{"claim_id":c["claim_id"],"statement":c["statement"],
                    "scope":c["scope"],"limitations":c["limitations"]}
                   for c in state["original_claims"]],
        "challenge_reason":(state.get("plan") or {}).get("reason"),
        "counter_hypotheses":(state.get("plan") or {}).get("counter_hypotheses",[]),
        "queries":(state.get("plan") or {}).get("queries",[]),
        "search_attempts":state["source_attempts"],
        "sources":[{
            "id":s["id"],"url":s["url"],"title":s.get("title"),
            "origin_type":s["origin_type"],"source_scope":s["source_scope"],
            "passage_sha256":s.get("passage_sha256"),
        } for s in state["sources"]],
        "excluded_original_source_urls":state["excluded_existing_source_urls"],
        "excluded_off_topic_urls":state.get("excluded_off_topic_source_urls",[]),
        "findings":[{
            "claim_id":f["claim_id"],"verdict":f["verdict"],
            "reason":f["rationale"],"scope_risk":f["scope_risk"],
            "alternative_explanation":f["alternative_explanation"],
            "next_test":f["next_test"],
            "quotes":[{"source_id":v["source_id"],"source_url":v["source_url"],
                       "quote_sha256":v["source_sha256"],"role":v["role"]}
                      for v in f["new_evidence"]],
        } for f in findings],
        "model_verdict_counts":dict(Counter(x["verdict"] for x in findings)),
        "graph_nodes_added":len(packet.get("nodes",[])),
        "graph_edges_added":len(packet.get("edges",[])),
        "graph_edge_statuses":dict(Counter(e["status"] for e in packet.get("edges",[]))),
        "graph_receipt_id":(state.get("graph_receipt") or {}).get("id"),
        "accepted_impact_claims":0,
        "limitations":[
            "Independent source discovery does not mean independent scientific verification.",
            "GPT-5.6 was unavailable through the authenticated Codex account; both research and challenge judge used GPT-6.1.",
            "No claim is automatically supported or disproved by one model's interpretation.",
            "Bibliographic abstracts and public guidance may not contain the original measurements.",
            "New model-labeled relationships are unresolved and all original graph statuses remain unchanged.",
        ],
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("input",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    state=json.loads(args.input.read_text())
    report=receipt(state)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("EXPORTED",args.output,"CLAIMS",len(report["findings"]),
          "MODEL_VERDICTS",report["model_verdict_counts"])

if __name__=="__main__":main()
