"""Audit one existing investigation using newly retrieved challenge evidence."""
from __future__ import annotations

import argparse
import json

from .external_llm_runtime import invoke_semantic_llm
from .investigation_adjudication import ChallengeController


def _view(state):
    packet=state.get("packet") or {}
    return {
        "id":state["id"],"investigation_id":state["investigation_id"],
        "stage":state["stage"],"targets":(state.get("plan") or {}).get("claim_ids",[]),
        "source_count":len(state["sources"]),
        "source_types":sorted({s["origin_type"] for s in state["sources"]}),
        "source_retrieval_attempts":state["source_attempts"],
        "quote_rejected":len((state.get("findings") or {}).get("rejected",[])),
        "model_verdicts":packet.get("conversion_metadata",{}).get("model_verdicts"),
        "graph_nodes":len(packet.get("nodes",[])),
        "graph_edges":len(packet.get("edges",[])),
        "receipt":(state.get("graph_receipt") or {}).get("id"),
        "last_error":state["last_error"],
        "authority":state["authority"],
    }


def main(argv=None):
    p=argparse.ArgumentParser(prog="cite-refinery-adjudicate")
    p.add_argument("--workspace",default=".cite-refinery-investigations")
    sub=p.add_subparsers(dest="command",required=True)
    start=sub.add_parser("start")
    start.add_argument("--investigation-id",required=True)
    start.add_argument("--max-candidates",type=int,default=14)
    for name in ("step","run","status"):
        action=sub.add_parser(name)
        action.add_argument("--id",required=True)
        if name in {"step","run"}:
            action.add_argument("--provider",choices=["codex","claude","gemini","ollama"],default="codex")
            action.add_argument("--model",default=None)
            action.add_argument("--timeout",type=int,default=180)
        if name=="run":action.add_argument("--steps",type=int,default=5)
    args=p.parse_args(argv)
    def reason(prompt):
        return invoke_semantic_llm(prompt,provider=args.provider,model=args.model,
                                   timeout_seconds=args.timeout)["raw"]
    ctrl=ChallengeController(args.workspace,reasoner=reason if args.command in {"run","step"} else None)
    if args.command=="start":
        state=ctrl.start(args.investigation_id,limit=args.max_candidates)
    elif args.command=="status":
        state=ctrl.load(args.id)
    elif args.command=="step":
        state=ctrl.step(args.id)
    else:
        state=ctrl.run(args.id,steps=args.steps)
    print(json.dumps(_view(state),indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
