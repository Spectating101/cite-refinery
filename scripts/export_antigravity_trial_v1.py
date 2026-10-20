"""Sanitized report of a real Copilot/Gemini investigation session.

Model identifiers must be supplied from the actually used CLI commands.
The saved controller state itself stores reasoning outputs, not backend IDs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from cite_refinery.investigation_controller import InvestigationController

def make_report(workspace,ident,generator_model,critic_model):
    controller=InvestigationController(workspace,reasoner=None)
    s=controller.load(ident)
    if not s.get("rounds"):raise ValueError("No actual investigation round")
    rnd=s["rounds"][-1]
    if not rnd.get("graph_receipt") or "critique" not in rnd:
        raise ValueError("Investigation round is not actually staged and reviewed")
    if generator_model not in ("gemini-3.8-flash-medium","gemini-3.8-flash-high"):
        raise ValueError("Generator model label must be explicitly verified")
    if critic_model not in ("gemini-3.8-flash-high","gemini-3.8-flash-medium"):
        raise ValueError("Critic model label must be explicitly verified")
    saved=controller.app.store.load(); pid=s["project_id"]
    return {
        "schema":"cite_refinery.antigravity_research_trial.v1",
        "investigation_id":ident,"parent_id":s.get("lineage",{}).get("parent_investigation"),
        "focus":rnd["focus"],"state":s["stage"],
        "generator_backend":"antigravity_cli","generator_model":generator_model,
        "critic_backend":"antigravity_cli","critic_model":critic_model,
        "same_model_family_critique":True,
        "sources":[{
            "id":x["id"],"url":x["url"],"origin_type":x["origin_type"],
            "parent_source_url":x.get("parent_source_url"),
            "same_study_as_parent":x.get("same_study_as_parent",False),
            "passage_sha256":x.get("passage_sha256") or hashlib.sha256(x["text"].encode()).hexdigest()
        } for x in rnd["sources"]],
        "off_topic_exclusions":[{"source_id":x["source_id"],"url":x["url"]}
                               for x in rnd.get("excluded_off_topic_sources",[])],
        "source_attempts":rnd.get("source_attempts"),"recovery_plans":len(rnd.get("recovery_plans",[])),
        "propositions":[{"id":x["id"],"statement":x["statement"],
                         "quoted_source_ids":[z["source_id"] for z in x["support"]]}
                        for x in rnd["inspected"]["propositions"]],
        "bridges":[{"from":x["from"],"to":x["to"],"relation":x["relation"]}
                   for x in rnd["inspected"]["bridges"]],
        "proposition_model_review":dict(Counter(x["reviewer_verdict"] for x in rnd["critique"]["propositions"])),
        "bridge_model_review":dict(Counter(x["reviewer_verdict"] for x in rnd["critique"]["bridges"])),
        "unresolved_questions":[x["question"] for x in rnd.get("open_questions",[])],
        "graph_nodes":sum(x.get("project_id")==pid for x in saved["semantic_nodes"].values()),
        "graph_edges":sum(x.get("project_id")==pid for x in saved["semantic_edges"].values()),
        "graph_receipt_id":rnd["graph_receipt"]["id"],
        "accepted_scientific_findings":0,
        "boundaries":[
            "These are new source-backed candidates, not independent replication of the original Sri Lankan intervention.",
            "Gemini 3.8 Flash medium and high use the same model family; review agreement is not an independent model consensus.",
            "WHO-hosted regional scholarly material is not automatically an implemented institutional policy or outcome evaluation.",
            "Off-topic official hits were removed by a scoped lexical safeguard; remaining sources still require semantic appraisal.",
            "No verified geographically matched human rabies/PEP time series was obtained in this round.",
            "Do not infer reduced dog abundance or human morbidity from sterilization/clinic counts.",
        ],
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--workspace",required=True)
    p.add_argument("--id",required=True)
    p.add_argument("--generator-model",required=True)
    p.add_argument("--critic-model",required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=make_report(a.workspace,a.id,a.generator_model,a.critic_model)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("SANITIZED_REPORT",a.out,"SOURCES",len(result["sources"]),
          "CLAIMS",len(result["propositions"]),"BRIDGES",len(result["bridges"]))
if __name__=="__main__":
    main()
