"""Create small, auditable portfolio evidence tasks from REAL Atlas graph nodes.

This is deterministic task preparation, not semantic understanding or entailment.
"""
from __future__ import annotations
import json
import re
from hashlib import sha256
from pathlib import Path
from .portfolio_autonomous_dossier import evidence_index, project_evidence, DossierError, require

SCHEMA="cite_refinery.portfolio_atomic_tasks.v1"
UNKNOWN_PROBES=(
 ("physical_validation","Was a fabricated physical prototype independently measured?"),
 ("adoption","Has an independent organization adopted the system in production?"),
 ("commercial","Is there independently verified paying customer revenue?"),
)

def tasks_from_receipt(report):
    require(report.get("private_repositories_included")==0,"Public task pack requires public-only receipt")
    index=evidence_index(report)
    snapshots=report.get("source_snapshots",[])
    require(len(snapshots)==8,"Expected eight pinned public projects")
    tasks=[]
    for row in snapshots:
        repo=row["repo"]
        scope=project_evidence(report,repo,index)
        root="repo_"+re.sub(r"[^a-z0-9]+","_",repo.lower()).strip("_")
        require(root in scope,"Missing primary program node")
        node=scope[root]
        require(node["layer"]=="program","Primary evidence is not program description")
        statement=node["text"]
        source_refs=node["source_refs"]
        require(source_refs and all(isinstance(u,str) and
                 u.startswith("https://github.com/Spectating101/") for u in source_refs),
                 "Source identity not pinned to public GitHub")
        tasks.append({
            "id":repo+":self_description",
            "repo":repo,"task_kind":"source_attribution",
            "question":"What does the repository maintainer describe this project as doing?",
            "allowed_evidence_ids":[root],
            "evidence_text":statement,
            "reference_quote":statement[:min(140,len(statement))],
            "source_refs":source_refs,
            "gold_scope":"self_report_only_not_independent_verification",
        })
        for kind,question in UNKNOWN_PROBES:
            tasks.append({
                "id":repo+":"+kind,"repo":repo,
                "task_kind":"requires_independent_evidence",
                "question":question,
                "allowed_evidence_ids":list(scope),
                "gold_scope":"not_verified_by_this_source_packet",
                "evidence_text":statement[:600],
                "source_refs":source_refs,
            })
    return {
        "schema":SCHEMA,"source":"actual_atlas_program_nodes",
        "project_count":len(snapshots),"task_count":len(tasks),
        "tasks":tasks,
        "task_generation_independently_reasoned":False,
        "unknown_probes_are_evidence_coverage_not_real_world_negative_claims":True,
        "digest":sha256(json.dumps(tasks,sort_keys=True).encode()).hexdigest(),
    }


def validate_atomic_answer(task,answer):
    """Check controlled answer contract; does not certify semantic entailment."""
    require(isinstance(answer,dict),"Invalid atomic answer")
    require(answer.get("id")==task["id"],"Question ID mismatch")
    verdict=answer.get("verdict")
    require(verdict in {"self_reported","insufficient"},"Overclaimed answer")
    citation=answer.get("evidence_id")
    if task["task_kind"]=="source_attribution":
        require(verdict=="self_reported","Source attribution was not recognized")
        require(citation in task["allowed_evidence_ids"],"Unknown evidence citation")
        quote=answer.get("quote")
        require(isinstance(quote,str) and len(quote)>=12
                and quote in task["evidence_text"],"Source quote not verified")
    else:
        require(verdict=="insufficient","Maintainer source cannot prove independent outcome")
        require(not answer.get("quote"),"Unknown claim was falsely quoted as proof")
    return {"id":task["id"],"contract_valid":True,
            "semantic_entailment_verified":False,
            "answer":answer}


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--receipt",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(argv)
    require(not args.out.exists(),"Will not overwrite task pack")
    report=json.loads(args.receipt.read_text())
    result=tasks_from_receipt(report)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+"\n")
    print("ATOMIC_TASK_PACK",json.dumps({"projects":result["project_count"],"tasks":result["task_count"]}))


if __name__=="__main__":
    main()
