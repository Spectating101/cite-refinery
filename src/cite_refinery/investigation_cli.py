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
    foundation=sub.add_parser("map-foundations",
        help="Three independent source-grounded maps and within-layer search; no cross-layer inference")
    foundation.add_argument("--manifest",type=Path,
        default=Path("research_materials/runtime_trials/open_corpus_20261020/source_manifest.json"))
    foundation.add_argument("--reading-dir",type=Path,
        default=Path("research_materials/runtime_trials/open_corpus_20261020/source_readings"))
    foundation.add_argument("--emergent-atlas",type=Path,
        default=Path("research_materials/runtime_trials/open_corpus_20261020/global_atlas.json"))
    foundation.add_argument("--github-primary",type=Path,
        default=Path("research_materials/opportunity_atlas/github_repository_survey.json"))
    foundation.add_argument("--github-frontier",type=Path,
        default=Path("research_materials/opportunity_atlas/github_frontier_repository_survey.json"))
    foundation.add_argument("--repository-network",type=Path,
        default=Path("research_materials/opportunity_atlas/atlas_network.json"))
    foundation.add_argument("--ted-context",type=Path,
        default=Path("research_materials/opportunity_atlas/ted_published_notice_context.json"))
    foundation.add_argument("--layer",choices=["practical","academic","implementation"])
    foundation.add_argument("--facet",help="Existing research theme or implementation source category")
    foundation.add_argument("--terms",help="Literal within-layer search terms, NOT semantic scoring")
    foundation.add_argument("--limit",type=int,default=25)
    foundation.add_argument("--json-out",type=Path,required=True)
    foundation.add_argument("--markdown-out",type=Path,required=True)
    foundation.add_argument("--review-backlog-out",type=Path,
        help="Optional balanced, unreviewed metadata-pair review queue; no model invoked")
    foundation.add_argument("--academic-original-audit",type=Path,
        help="Optional exact original source/DOI identity checks, no scientific validation")
    foundation.add_argument("--implementation-original-audit",type=Path,
        help="Optional pinned GitHub revision and root listing receipts, no code execution")
    foundation.add_argument("--nocturnal-public-snapshot",type=Path,
        help="Local publication-approved Nocturnal public snapshot directory; no private ledgers")
    foundation.add_argument("--previous-nocturnal-atlas",type=Path,
        help="Optional prior standalone Nocturnal atlas for immutable incremental synchronization")
    foundation.add_argument("--nocturnal-terms",
        help="Literal within-Nocturnal Practical matter search, not verified semantics")
    foundation.add_argument("--nocturnal-matter-id",
        help="Browse one public Nocturnal matter, if published")
    foundation.add_argument("--nocturnal-map-out",type=Path,
        help="Optional standalone JSON Practical map with Nocturnal evidence pointers")
    qualification=sub.add_parser("qualify-conversions",
        help="Audit candidate conversion discoveries across multiple source slices, public repo metadata and pinned upstream test receipts")
    qualification.add_argument("--discovery",type=Path,action="append",required=True,
                               help="Repeat to include independent candidate discovery slices")
    qualification.add_argument("--repository-audit",type=Path,action="append",required=True,
                               help="Repeat for original GitHub metadata audit snapshots")
    qualification.add_argument("--component-tests",type=Path,required=True,
                               help="Explicit original upstream test receipt (scope-limited)")
    qualification.add_argument("--bridge-trial",type=Path,action="append",
                               help="Optional isolated source-interface compatibility receipts; never automatic promotion")
    qualification.add_argument("--functional-trial",type=Path,action="append",
                               help="Optional source-pinned cross-domain synthetic capability-transfer trial receipts")
    qualification.add_argument("--json-out",type=Path,required=True)
    qualification.add_argument("--markdown-out",type=Path,required=True)
    conversions=sub.add_parser("discover-conversions",
        help="Emergent relationship discovery over broad research and implementation samples; funding optional")
    conversions.add_argument("--atlas",type=Path,required=True,
        help="Existing 63-source emergent atlas; no input opportunity pairs")
    conversions.add_argument("--manifest",type=Path,required=True,
        help="Original source manifest with URLs and SHA-256 hashes")
    conversions.add_argument("--repository-survey",type=Path,required=True,
        help="Broad surveyed implementation repository inventory")
    conversions.add_argument("--funding-catalog",type=Path,
        help="Optional small grants/sponsorship/investment resource overlay, NOT a fourth layer")
    conversions.add_argument("--repository-audit",type=Path,
        help="Optional read-only original GitHub metadata for exact selected candidate projects, NOT proven technical quality")
    conversions.add_argument("--offset",type=int,default=0,
        help="Reproducible independent repository sampling slice offset")
    conversions.add_argument("--per-macro",type=int,default=6)
    conversions.add_argument("--model-output",type=Path,
        help="Previously saved unmodified JSON model response; review without re-running a model")
    conversions.add_argument("--provider",default="antigravity",
        choices=["copilot","antigravity","codex","claude","gemini","ollama"])
    conversions.add_argument("--model",default="claude-sonnet-5-5-medium")
    conversions.add_argument("--timeout",type=int,default=220)
    conversions.add_argument("--raw-out",type=Path,
        help="Optional write-once raw model response for independent evaluation")
    conversions.add_argument("--json-out",type=Path,required=True)
    conversions.add_argument("--markdown-out",type=Path,required=True)
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
    arb.add_argument("--market-evidence",type=Path,
                     help="Optional public, dated Taiwan marketplace snapshot; asking prices are not realized resale arbitrage")
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
    if args.command=="map-foundations":
        from .layer_foundations import build, browse, review_backlog, summary_markdown
        if (args.facet or args.terms) and not args.layer:
            raise ValueError("Within-layer browse facet/terms require --layer")
        if (args.previous_nocturnal_atlas or args.nocturnal_terms or
            args.nocturnal_matter_id or args.nocturnal_map_out) and not args.nocturnal_public_snapshot:
            raise ValueError("Nocturnal options require --nocturnal-public-snapshot")
        shards=sorted(args.reading_dir.glob("shard-*.json"))
        if not 1<=len(shards)<=40:
            raise ValueError("No bounded source-reading shard collection")
        files=[args.manifest,args.emergent_atlas,args.github_primary,
               args.github_frontier,args.repository_network,args.ted_context,*shards]
        if bool(args.academic_original_audit) != bool(args.implementation_original_audit):
            raise ValueError("Both independent source audit layers must be supplied together")
        if args.academic_original_audit:
            files.extend([args.academic_original_audit,args.implementation_original_audit])
        if any(file.stat().st_size>12_000_000 for file in files):
            raise ValueError("Source inventory exceeds bounded file size")
        outputs=[args.json_out,args.markdown_out]
        if args.review_backlog_out: outputs.append(args.review_backlog_out)
        if args.nocturnal_map_out: outputs.append(args.nocturnal_map_out)
        if (len(set(x.resolve() for x in outputs))!=len(outputs)
            or any(x.exists() for x in outputs)):
            raise ValueError("Refusing to overwrite outputs or use same path")
        def read(path):
            return json.loads(path.read_text(encoding="utf-8"))
        m=build(read(args.manifest),[read(x) for x in shards],
                read(args.emergent_atlas),read(args.github_primary),
                read(args.github_frontier),read(args.repository_network),
                read(args.ted_context))
        if args.academic_original_audit:
            from .layer_foundations import attach_independent_source_identity_checks
            m=attach_independent_source_identity_checks(
                m,read(args.academic_original_audit),
                read(args.implementation_original_audit))
        nocturnal_map = None
        nocturnal_view = None
        if args.nocturnal_public_snapshot:
            from .nocturnal_public_atlas import build_practical_atlas, browse_practical
            previous = read(args.previous_nocturnal_atlas) if args.previous_nocturnal_atlas else None
            if previous is not None and previous.get("schema") == m["schema"]:
                previous = previous["practical"]["nocturnal_public_atlas"]
            nocturnal_map = build_practical_atlas(
                args.nocturnal_public_snapshot, previous=previous)
            m["practical"]["nocturnal_public_atlas"] = nocturnal_map
            nocturnal_view = browse_practical(
                nocturnal_map, terms=args.nocturnal_terms,
                matter_id=args.nocturnal_matter_id, limit=args.limit)
            m["practical"]["nocturnal_public_browse"] = nocturnal_view
        view=(browse(m,layer=args.layer,facet=args.facet,terms=args.terms,
                     limit=args.limit) if args.layer else None)
        if view: m["within_layer_browse"]=view
        backlog=review_backlog(m) if args.review_backlog_out else None
        for path,contents in [
            (args.json_out,json.dumps(m,ensure_ascii=False,indent=2)+"\n"),
            (args.markdown_out,summary_markdown(m) + (
                "\n## Source-approved Nocturnal Practical evidence\n\n"
                + "Gated public snapshot `" + nocturnal_map["provenance"]["snapshot_id"]
                + "`: " + str(nocturnal_map["coverage"]["matter_count"])
                + " matters, " + str(nocturnal_map["coverage"]["module_count"])
                + " modules, " + str(nocturnal_map["coverage"]["correction_count"])
                + " corrections. Source URLs are not independent corroboration. "
                + "Case stages, entities and disputes are source assertions; "
                + "no cross-layer inference or verified-world-coverage claim.\n"
                if nocturnal_map else "")),
            *([(args.nocturnal_map_out,
                 json.dumps(nocturnal_map,ensure_ascii=False,indent=2)+"\n")]
              if args.nocturnal_map_out else []),
            *([(args.review_backlog_out,
                 json.dumps(backlog,ensure_ascii=False,indent=2)+"\n")]
              if backlog else [])
        ]:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(contents,encoding="utf-8")
        print(json.dumps({
            "schema":m["schema"],
            "practical_reported_cases":m["practical"]["reported_case_count"],
            "separate_procurement_notices":len(
                m["practical"]["published_procurement_notices_as_separate_context"]),
            "academic_source_abstracts":m["academic"]["source_count"],
            "implementation_repositories":m["implementation"]["unique_repositories"],
            "implementation_unreviewed_category_memberships":m["implementation"]["unreviewed_memberships"],
            "balanced_backlog_pairs":backlog["sampled_pairs"] if backlog else 0,
            "browse_matches":view["matching_count"] if view else None,
            "nocturnal_public_snapshot_id":(
                nocturnal_map["provenance"]["snapshot_id"] if nocturnal_map else None),
            "nocturnal_public_matters":(
                nocturnal_map["coverage"]["matter_count"] if nocturnal_map else 0),
            "nocturnal_public_browse_matches":(
                nocturnal_view["matching_count"] if nocturnal_view else None),
            "external_academic_doi_confirmed":m.get(
                "within_layer_original_source_audits",{}).get(
                    "publisher_doi_identity_confirmed",0),
            "original_pinned_repo_revision_checked":m.get(
                "within_layer_original_source_audits",{}).get(
                    "implementation_pinned_revision_and_root_checked",0),
            "cross_layer_edges_created":0,"world_coverage_complete":False,
        },indent=2))
        return 0
    if args.command=="qualify-conversions":
        from .open_corpus_atlas import (
            conversion_qualification_queue,render_qualification_queue)
        files=[*args.discovery,*args.repository_audit,args.component_tests,
               *(args.bridge_trial or []),*(args.functional_trial or [])]
        for file in files:
            if file.stat().st_size>12_000_000:
                raise ValueError("Source scope exceeds bounded qualification file size")
        output=(args.json_out,args.markdown_out)
        if output[0].resolve()==output[1].resolve() or any(p.exists() for p in output):
            raise ValueError("Refusing to overwrite or reuse qualification output paths")
        def read(path):
            return json.loads(path.read_text(encoding="utf-8"))
        result=conversion_qualification_queue(
            [read(p) for p in args.discovery],
            [read(p) for p in args.repository_audit],
            read(args.component_tests))
        if args.bridge_trial:
            from .open_corpus_atlas import attach_source_bridge_trials
            result=attach_source_bridge_trials(
                result,[read(path) for path in args.bridge_trial])
        if args.functional_trial:
            from .open_corpus_atlas import attach_functional_conversion_trials
            result=attach_functional_conversion_trials(
                result,[read(path) for path in args.functional_trial])
        for path,contents in (
            (args.json_out,json.dumps(result,indent=2,ensure_ascii=False)+"\n"),
            (args.markdown_out,render_qualification_queue(result))
        ):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(contents,encoding="utf-8")
        print(json.dumps({
            "schema":result["schema"],
            "candidate_links_for_review":result["candidate_links_accepted_for_review"],
            "invalid_model_links_rejected":result["candidate_links_rejected_for_invalid_source_or_schema"],
            "original_repo_metadata_checked":result["original_repo_metadata_checked"],
            "original_upstream_test_passes":result["scoped_original_test_passes_total"],
            "direct_source_interface_mismatches_reproduced":result.get(
                "direct_source_interface_mismatches_reproduced",0),
            "positive_synthetic_functional_trials":result.get(
                "positive_synthetic_functional_trials",0),
            "confirmed_high_quality_underconverted_assets":0,
            "realized_new_recombinations":0,
        },indent=2))
        return 0
    if args.command=="discover-conversions":
        from .open_corpus_atlas import (
            prepare_conversion_universe,emergent_conversion_prompt,
            validate_emergent_conversion,screen_emergent_batch,
            funding_overlay,render_conversion_discovery
        )
        files=[args.atlas,args.manifest,args.repository_survey]
        if args.funding_catalog:files.append(args.funding_catalog)
        if args.repository_audit:files.append(args.repository_audit)
        if args.model_output:files.append(args.model_output)
        for src in files:
            if src.stat().st_size>12_000_000:
                raise ValueError("Discovery sources exceed bounded size")
        def load_json(path):
            return json.loads(path.read_text(encoding="utf-8"))
        universe=prepare_conversion_universe(
            load_json(args.atlas),load_json(args.repository_survey),
            load_json(args.manifest),per_macro=args.per_macro,offset=args.offset)
        destinations=(args.json_out,args.markdown_out)
        if args.raw_out:destinations+= (args.raw_out,)
        if len({p.resolve() for p in destinations})!=len(destinations) or any(
            p.exists() for p in destinations
        ):
            raise ValueError("Refusing to overwrite outputs or reuse the same file path")
        if args.model_output:
            raw=load_json(args.model_output)
            provenance="replayed_saved_model_JSON_without_new_model_request"
        else:
            response=invoke_semantic_llm(
                emergent_conversion_prompt(universe),provider=args.provider,
                model=args.model,timeout_seconds=args.timeout)
            raw=response["raw"]
            provenance=response["provider"]+":"+response["model"]
        # Write raw receipts before schema inspection if requested; validator
        # failure must never convert a malformed model answer into graph truth.
        if args.raw_out:
            args.raw_out.parent.mkdir(parents=True,exist_ok=True)
            args.raw_out.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+"\n")
        findings=screen_emergent_batch(raw,universe)
        findings["model_provenance"]=provenance
        if args.repository_audit:
            from .open_corpus_atlas import attach_original_repository_metadata
            findings=attach_original_repository_metadata(
                findings,load_json(args.repository_audit))
        funds=funding_overlay(load_json(args.funding_catalog)) if args.funding_catalog else None
        if funds:
            findings["funding_enabler_overlay"]=funds
        for path,txt in (
            (args.json_out,json.dumps(findings,indent=2,ensure_ascii=False)+"\n"),
            (args.markdown_out,render_conversion_discovery(findings,funds))
        ):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(txt,encoding="utf-8")
        print(json.dumps({"schema":findings["schema"],
            "selected_repositories":len(universe["selected_repositories"]),
            "source_corpus_total":universe["source_corpus_total"],
            "new_candidate_connections":findings["candidate_connection_count"],
            "rejected_model_candidates":findings["rejected_candidate_count"],
            "quality_independently_verified":0,
            "underconversion_independently_verified":0,
            "funding_resources":len(funds["channels"]) if funds else 0,
            "graph_edges_promoted":0,
            "json_out":str(args.json_out),"markdown_out":str(args.markdown_out)
        },indent=2))
        return 0
    if args.command=="arbitrage-map":
        from .internal_arbitrage import build as build_map, markdown as format_map
        for file in (args.atlas,args.operator_routes,
                     *([args.scenarios] if args.scenarios else []),
                     *([args.owner_targets] if args.owner_targets else []),
                     *([args.market_evidence] if args.market_evidence else [])):
            if file.stat().st_size>3_000_000:
                raise ValueError("Arbitrage source evidence file too large")
        def load_json(path):
            return json.loads(path.read_text(encoding="utf-8"))
        report=build_map(load_json(args.atlas),load_json(args.operator_routes),
                         load_json(args.scenarios) if args.scenarios else None,
                         load_json(args.owner_targets) if args.owner_targets else None,
                         load_json(args.market_evidence) if args.market_evidence else None)
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
