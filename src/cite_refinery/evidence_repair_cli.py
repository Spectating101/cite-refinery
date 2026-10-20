"""CLI for source-diagnostic evidence repair and independent next-question fork."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .evidence_repair_frontier import build_repair_cases,stage_frontier,new_repair_investigation
from .investigation_controller import InvestigationController

def main(argv=None):
    p=argparse.ArgumentParser(prog="cite-refinery-repair")
    p.add_argument("--workspace",default=".cite-refinery-investigations")
    sub=p.add_subparsers(dest="command",required=True)
    prepare=sub.add_parser("prepare")
    prepare.add_argument("--investigation-id",required=True)
    prepare.add_argument("--table-quality",required=True,type=Path)
    prepare.add_argument("--replication-assessment",required=True,type=Path)
    prepare.add_argument("--fulltext-audit",required=True,type=Path)
    prepare.add_argument("--out",required=True,type=Path)
    stage=sub.add_parser("stage")
    stage.add_argument("--investigation-id",required=True)
    stage.add_argument("--frontier",required=True,type=Path)
    fork=sub.add_parser("fork")
    fork.add_argument("--investigation-id",required=True)
    fork.add_argument("--frontier",required=True,type=Path)
    fork.add_argument("--max-rounds",type=int,default=2)
    args=p.parse_args(argv)
    if args.command=="prepare":
        controller=InvestigationController(args.workspace,reasoner=None)
        original=controller.load(args.investigation_id)
        table=json.loads(args.table_quality.read_text(encoding="utf-8"))
        replication=json.loads(args.replication_assessment.read_text(encoding="utf-8"))
        fulltext_audit=json.loads(args.fulltext_audit.read_text(encoding="utf-8"))
        result=build_repair_cases(table,replication,original,fulltext_audit)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print(json.dumps({"path":str(args.out),"source":result["source_doi"],
            "cases":len(result["cases"]),"priorities":[x["priority"] for x in result["cases"]],
            "authority":result["authority"]},indent=2))
    else:
        frontier=json.loads(args.frontier.read_text(encoding="utf-8"))
        if args.command=="stage":
            result=stage_frontier(args.workspace,args.investigation_id,frontier)
            print(json.dumps({"receipt":result["receipt"]["id"],
                "preview":result["preview"],
                "node_count":len(result["packet"]["nodes"]),
                "edge_count":len(result["packet"]["edges"])},indent=2))
        else:
            state=new_repair_investigation(args.workspace,args.investigation_id,frontier,max_rounds=args.max_rounds)
            print(json.dumps({"id":state["id"],"stage":state["stage"],"focus":state["focus"],
                "pending_questions":len(state["frontier"]),
                "external_dependencies":len(state.get("dependency_queue",[])),
                "lineage":state["lineage"],
                "parent_untouched":True},indent=2))
if __name__=="__main__":main()
