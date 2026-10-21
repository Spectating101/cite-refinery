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
        "supplied_source_count":len(s.get("supplied_sources",[])),
        "supplied_source_families":sorted({x["source_family"] for x in s.get("supplied_sources",[])}),
        "supplied_provenance_status":"user_supplied_url_not_retrieved",
        "supplied_source_ids":[x["id"] for x in s.get("supplied_sources",[])],
        "cross_layer_review_count":len(s.get("cross_layer_assessments",[])),
        "cross_layer_latest_outcomes":[
            {"id":x["id"],"status":x["status"],"graph_authority":"CANDIDATE_ONLY"}
            for x in s.get("cross_layer_assessments",[])[-1].get("rows",[])
        ] if s.get("cross_layer_assessments") else [],
        "publisher_checked_source_count":len(s.get("source_authentication",[])),
        "publisher_text_matches":sum(x.get("status")=="publisher_passage_matched_claim_unreviewed"
                                      for x in s.get("source_authentication",[])),
        "publisher_text_mismatches":sum(x.get("status")=="submitted_text_does_not_match_publisher"
                                         for x in s.get("source_authentication",[])),
        "publisher_checks":[{"id":x["id"],"status":x["status"],
                            "publisher_url":x.get("publisher_url"),
                            "source_claim_verified":False}
                           for x in s.get("source_authentication",[])],
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
    init.add_argument(
        "--evidence",help="Optional local supplied_evidence.v1 JSON (Practical/Academic/Implementation); never fetched or auto-approved"
    )
    init.add_argument("--max-rounds",type=int,default=2)
    init.add_argument("--fulltext-enrichment",action="store_true",
                      help="Fetch bounded methods/results JATS extracts for public PMC papers")
    attach=sub.add_parser("attach-evidence",help="Attach bounded user-provided evidence before reasoning; no external fetch or graph write")
    attach.add_argument("--id",required=True)
    attach.add_argument("--evidence",required=True)
    verify=sub.add_parser("verify-evidence",
        help="Explicit, read-only original publisher text matching; GitHub or Europe PMC allowlisted routes only")
    verify.add_argument("--id",required=True)
    assess=sub.add_parser("assess-links",help="Preflight authenticated three-layer links, optionally obtain bounded LLM critique; NEVER promote")
    assess.add_argument("--id",required=True)
    assess.add_argument("--proposals",required=True)
    assess.add_argument("--provider",choices=["copilot","antigravity","codex","claude","gemini","ollama"],
                        help="Optional provider for independent source applicability critique; omitted = structural source preflight only")
    assess.add_argument("--model",default=None)
    assess.add_argument("--timeout",type=int,default=150)
    brief=sub.add_parser("operator-brief",
        help="Render one source-to-solution delivery brief from verified source receipts and bounded component test artifacts")
    brief.add_argument("--id",required=True)
    brief.add_argument("--markdown-out",type=Path,required=True)
    brief.add_argument("--json-out",type=Path,required=True)
    brief.add_argument("--framework-artifact",type=Path,
                       help="Optional previously verified committed framework_scoped_integration.json; exact SHA-256 required (useful with wheel installs)")
    arb=sub.add_parser("arbitrage-map",
        help="Create a read-only internal self-arbitrage reconnaissance atlas and conditional asset spreads; not a fourth layer")
    arb.add_argument("--atlas",type=Path,
                     default=Path("research_materials/opportunity_atlas/three_layer_unified_atlas.json"))
    arb.add_argument("--operator-routes",type=Path,
                     default=Path("research_materials/opportunity_atlas/operator_conversion_routes.json"))
    arb.add_argument("--scenarios",type=Path,
                     help="Optional user-supplied complete purchase/repair/resale scenarios; conditional, not verified prices")
    arb.add_argument("--owner-targets",type=Path,
                     help="Optional user strategy priorities/data overlay; never automatically creates cross-layer edges")
    arb.add_argument("--json-out",type=Path,required=True)
    arb.add_argument("--markdown-out",type=Path,required=True)
    for name in ("step","run","status"):
        action=sub.add_parser(name)
        action.add_argument("--id",required=True)
        if name!="status":
            action.add_argument("--provider",choices=["copilot","antigravity","codex","claude","gemini","ollama"],default="copilot")
            action.add_argument("--model",default=None)
            action.add_argument("--timeout",type=int,default=180)
        if name=="run":action.add_argument("--steps",type=int,default=5)
    args=p.parse_args(argv)
    def read_evidence(path):
        # Fail before allocating huge or non-text data; never open URL.
        file=Path(path)
        if file.stat().st_size>42_000:
            raise ValueError("Local supplied evidence JSON exceeds 42 KB")
        return json.loads(file.read_text(encoding="utf-8"))
    def reasoner(prompt):
        execution=invoke_semantic_llm(prompt,provider=args.provider,model=args.model,
                                      timeout_seconds=args.timeout)
        return execution["raw"]
    if args.command=="arbitrage-map":
        from .internal_arbitrage import build as build_map, markdown as format_map
        for file in (args.atlas,args.operator_routes,
                     *([args.scenarios] if args.scenarios else []),
                     *([args.owner_targets] if args.owner_targets else [])):
            if file.stat().st_size>3_000_000:
                raise ValueError("Arbitrage source evidence file too large")
        def load_json(path):
            return json.loads(path.read_text(encoding="utf-8"))
        report=build_map(load_json(args.atlas),load_json(args.operator_routes),
                         load_json(args.scenarios) if args.scenarios else None,
                         load_json(args.owner_targets) if args.owner_targets else None)
        outputs=(args.json_out,args.markdown_out)
        if outputs[0].resolve()==outputs[1].resolve() or any(p.exists() for p in outputs):
            raise ValueError("Refusing to overwrite existing/duplicate arbitrage-map output paths")
        for path,blob in (
            (args.json_out,json.dumps(report,indent=2,ensure_ascii=False)+"\n"),
            (args.markdown_out,format_map(report))
        ):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(blob,encoding="utf-8")
        print(json.dumps({
            "schema":report["schema"],"coverage":report["coverage"],
            "json_out":str(args.json_out),
            "markdown_out":str(args.markdown_out),
            "graph_authority_promoted":False,
            "executed_trade_or_order":False,
        },indent=2))
        return 0
    # Map creation must not create an investigation workspace as a side effect.
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
                         fulltext_enrichment=args.fulltext_enrichment,
                         evidence_document=read_evidence(args.evidence) if args.evidence else None)
    elif args.command=="attach-evidence":
        state=ctrl.attach_supplied_evidence(args.id,read_evidence(args.evidence))
    elif args.command=="operator-brief":
        from .operator_delivery import build,render_markdown
        source=ctrl.load(args.id)
        report=build(source,framework_artifact=args.framework_artifact)
        md=render_markdown(report)
        destination=(args.markdown_out,args.json_out)
        if destination[0].resolve()==destination[1].resolve() or any(
            path.exists() for path in destination
        ):
            raise ValueError("Refusing to overwrite existing or duplicate operator brief paths")
        for path,data in ((args.markdown_out,md),
                          (args.json_out,json.dumps(report,indent=2,ensure_ascii=False)+"\n")):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(data,encoding="utf-8")
        print(json.dumps({"schema":report["schema"],"id":report["investigation_id"],
            "markdown_out":str(args.markdown_out),
            "json_out":str(args.json_out),
            "cases":len(report["case_decisions"]),
            "attached_scoped_runtime_receipts":sum(bool(x["bounded_component_executable_receipt"])
                    for x in report["case_decisions"]),
            "buyer_interest_verified":False,
            "full_application_approvals":0},ensure_ascii=False,indent=2))
        return 0
    elif args.command=="assess-links":
        from .cross_layer_review import SCHEMA
        file=Path(args.proposals)
        if file.stat().st_size>36_000:
            raise ValueError("Cross-layer proposals exceed 36 KB")
        proposals=json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(proposals,dict) or proposals.get("schema")!=SCHEMA:
            raise ValueError("Cross-layer proposal schema mismatch")
        if args.model and not args.provider:
            raise ValueError("A named model requires an explicit provider")
        def critic(prompt):
            return invoke_semantic_llm(prompt,provider=args.provider,
                                       model=args.model,
                                       timeout_seconds=args.timeout)["raw"]
        result=ctrl.assess_cross_layer_links(
            args.id,proposals,critic=critic if args.provider else None,
            model_metadata={"provider":args.provider,
                            "model":args.model or "provider_default"} if args.provider else None
        )
        print(json.dumps(result,indent=2,ensure_ascii=False))
        return 0
    elif args.command=="verify-evidence":
        state=ctrl.authenticate_supplied_evidence(args.id)
    elif args.command=="status":
        state=ctrl.load(args.id)
    elif args.command=="step":
        state=ctrl.step(args.id)
    else:
        state=ctrl.run(args.id,max_steps=args.steps)
    print(json.dumps(_summary(state),indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
