"""Persistent LLM Investigator CLI: init, bounded stage, status.

Always require an explicit model backend for autonomous steps. 'init' and
'status' never invoke an LLM; no fabricated fallback. Candidate graph writes
are review-only in the controller's separate workspace.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .external_llm_runtime import invoke_semantic_llm
from .investigation_controller import InvestigationController


def _summary(s):
    return {
        "id":s["id"],"project_id":s["project_id"],
        "question":s["question"],"current_focus":s["focus"],
        "stage":s["stage"],"rounds_count":len(s["rounds"]),
        "max_rounds":s["max_rounds"],"frontier_count":len(s["frontier"]),
        "rounds":[{
            "number":r["number"],"focus":r.get("focus"),
            "state":r["state"],"source_count":r.get("source_count",0),
            "origin_types":sorted({x["origin_type"] for x in r.get("sources",[])}),
            "propositions":len(r.get("inspected",{}).get("propositions",[])),
            "candidate_bridges":len(r.get("inspected",{}).get("bridges",[])),
            "open_questions":len(r.get("open_questions",[])),
            "graph_receipt":r.get("graph_receipt",{}).get("id"),
        } for r in s["rounds"]],
        "last_error":s.get("last_error"),
        "authority":s["authority"],
        "module_origins":sorted({str(m.get("origin","provided_ontology"))
                                 for m in s["modules"]}),
        "known_missing_evidence_families":[
            "independent_practical_field_observations",
            "verified_implementation_execution_and_operator_outcomes",
        ],
        "end_to_end_three_layer_validation_complete":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(prog="cite-refinery-investigate")
    p.add_argument("--workspace",default=".cite-refinery-investigations")
    sub=p.add_subparsers(dest="command",required=True)
    init=sub.add_parser("init",help="Create persistent project and seed question; no bibliography")
    init.add_argument("--question",required=True)
    init.add_argument(
        "--modules",
        help="Optional reviewed problem-ontology JSON list. Without it, start with a single explicitly unverified user-question module.",
    )
    init.add_argument("--max-rounds",type=int,default=2)
    init.add_argument("--fulltext-enrichment",action="store_true",
                      help="Fetch bounded methods/results JATS extracts for public PMC papers")
    for name in ("step","run","status"):
        action=sub.add_parser(name)
        action.add_argument("--id",required=True)
        if name!="status":
            action.add_argument("--provider",choices=["copilot","antigravity","codex","claude","gemini","ollama"],default="copilot")
            action.add_argument("--model",default=None)
            action.add_argument("--timeout",type=int,default=180)
        if name=="run":action.add_argument("--steps",type=int,default=5)
    args=p.parse_args(argv)
    def reasoner(prompt):
        execution=invoke_semantic_llm(prompt,provider=args.provider,model=args.model,
                                      timeout_seconds=args.timeout)
        return execution["raw"]
    ctrl=InvestigationController(args.workspace,reasoner=reasoner if args.command in {"run","step"} else None)
    if args.command=="init":
        if args.modules:
            modules=json.loads(Path(args.modules).read_text(encoding="utf-8"))
        else:
            # Entry framing is NOT a measurement, a source or an established
            # practical problem. The controller still searches and stages only
            # neutral candidates; it must never treat this as corroboration.
            modules=[{
                "id":"RQ-01",
                "title":args.question.strip()[:120],
                "summary":"Unverified user-supplied research question; no measured practical need, academic finding, or deployed implementation established.",
                "origin":"user_question_provisional",
                "status":"unreviewed",
            }]
        state=ctrl.start(args.question,modules,max_rounds=args.max_rounds,
                         fulltext_enrichment=args.fulltext_enrichment)
    elif args.command=="status":
        state=ctrl.load(args.id)
    elif args.command=="step":
        state=ctrl.step(args.id)
    else:
        state=ctrl.run(args.id,max_steps=args.steps)
    print(json.dumps(_summary(state),indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
