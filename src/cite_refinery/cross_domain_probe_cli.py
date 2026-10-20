"""Run semantically independent 3-perspective coverage probes on new fields.

No sources are pre-picked. Planner queries provider; retrieval fetches real
publisher passages; LLM reads content and assigns roles; critic only downgrades.
These trial artifacts never promote scientific or field implementation claims.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from .external_llm_runtime import invoke_semantic_llm
from .investigation_controller import InvestigationController
from .cross_domain_roles import evidence_role_prompt, validate_roles
from .cross_domain_role_critic import critique_prompt,validate_critique
from .cross_domain_recovery import recovery_prompt,retrieve_recovery
from .cross_domain_graph import stage_coverage
import hashlib

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")

def main(argv=None):
    p=argparse.ArgumentParser(prog="cite-refinery-cross-domain-probe")
    p.add_argument("--seeds",type=Path,required=True)
    p.add_argument("--domain",required=True)
    p.add_argument("--workspace",required=True)
    p.add_argument("--out-dir",type=Path,required=True)
    p.add_argument("--provider",default="antigravity",
                   choices=["antigravity","copilot","codex","gemini","claude","ollama"])
    p.add_argument("--model",default="gemini-3.8-flash-medium")
    p.add_argument("--critic-model",default="gemini-3.8-flash-high")
    p.add_argument("--timeout",type=int,default=180)
    p.add_argument("--include-recovery",action="store_true",
                   help="Assess original and recovered source records together; retains original evaluation")
    p.add_argument("step",choices=["init","plan","collect","recover","roles","critic","graph","status"])
    args=p.parse_args(argv)
    spec=json.loads(args.seeds.read_text())
    if spec.get("schema")!="cite_refinery.cross_domain_probe_seeds.v1":
        raise ValueError("Unrecognized domain ontology")
    domain=next((x for x in spec["domains"] if x.get("id")==args.domain),None)
    if domain is None:raise ValueError("Unknown domain ID")
    allowed={"practical","academic","program","cross_perspective"}
    for m in domain["modules"]:
        if m.get("perspective") not in allowed:raise ValueError("Unknown problem perspective")
    meta_path=args.out_dir/(args.domain+".meta.json")
    def call_model(prompt,model=None):
        return invoke_semantic_llm(prompt,provider=args.provider,
                                   model=model or args.model,
                                   timeout_seconds=args.timeout)["raw"]
    ctrl=InvestigationController(args.workspace,reasoner=call_model)
    if args.step=="init":
        if meta_path.exists():raise ValueError("Existing session. Use status, never reset evidence accidentally")
        s=ctrl.start(domain["question"],domain["modules"],max_rounds=1)
        write(meta_path,{"domain":args.domain,"investigation_id":s["id"],
                         "ontology_module_ids":[m["id"] for m in domain["modules"]],
                         "sources_preselected":False})
    else:
        meta=json.loads(meta_path.read_text())
        s=ctrl.load(meta["investigation_id"])
        if args.step in {"plan","collect"}:
            target={"plan":"plan","collect":"collect"}[args.step]
            if s["stage"]!=target:raise ValueError(f"Cannot advance {args.step} from {s['stage']}")
            s=ctrl.step(s["id"])
        elif args.step=="recover":
            if s["stage"]!="reason":raise ValueError("Need completed source collection to recover evidence gaps")
            initial=json.loads((args.out_dir/(args.domain+".roles.json")).read_text())
            prior=s["rounds"][-1]["sources"]
            prompt=recovery_prompt(s["question"],domain["modules"],initial,s["rounds"][-1]["plan"])
            plan=call_model(prompt)
            recovered=retrieve_recovery(plan,prior)
            local_record=Path(args.workspace)/"cross_domain_recovery"/(args.domain+".json")
            write(local_record,recovered)
            # Only URLs/hashes, no publisher's passages, leave the container.
            write(args.out_dir/(args.domain+".recovery.json"),{
                "schema":"cite_refinery.semantic_evidence_recovery.v1",
                "domain":args.domain,"investigation_id":s["id"],
                "plan":recovered["plan"],
                "new_sources":[{"id":x["id"],"url":x["url"],"origin_type":x["origin_type"],
                                "passage_sha256":hashlib.sha256(x["text"].encode()).hexdigest()}
                               for x in recovered["sources"]],
                "search_failures":recovered["source_failures"],
                "note":"Publisher text locally retained, not accepted as evidence until semantic role review.",
            })
        elif args.step=="roles":
            if s["stage"]!="reason":raise ValueError(f"Need real retrieved sources before role classification: {s['stage']}")
            collected=s["rounds"][-1]["sources"]
            if args.include_recovery:
                extra=json.loads((Path(args.workspace)/"cross_domain_recovery"/(args.domain+".json")).read_text())["sources"]
                old={x["url"] for x in collected}
                # Preserve evidence-lane coverage in the bounded 12-source
                # model input; initial searches were dominated by off-topic
                # official hits and role recovery requires institutional pages.
                fresh=sorted((x for x in extra if x["url"] not in old),
                             key=lambda x:(not x["origin_type"].startswith("official_"),x["id"]))
                collected=collected+fresh[:4]
            raw=call_model(evidence_role_prompt(s["question"],domain["modules"],collected))
            reviewed=validate_roles(raw,s["question"],domain["modules"],collected)
            reviewed["investigation_id"]=s["id"]
            reviewed["source_count"]=len(collected)
            reviewed["model_provenance"]=f"{args.provider}:{args.model}"
            write(args.out_dir/(args.domain+(".roles.recovery.json" if args.include_recovery else ".roles.json")),reviewed)
        elif args.step=="critic":
            roles=json.loads((args.out_dir/(args.domain+(".roles.recovery.json" if args.include_recovery else ".roles.json"))).read_text())
            if roles.get("investigation_id")!=s["id"]:raise ValueError("Roles bound to another investigation")
            collected=s["rounds"][-1]["sources"]
            if args.include_recovery:
                extra=json.loads((Path(args.workspace)/"cross_domain_recovery"/(args.domain+".json")).read_text())["sources"]
                old={x["url"] for x in collected}
                # Preserve evidence-lane coverage in the bounded 12-source
                # model input; initial searches were dominated by off-topic
                # official hits and role recovery requires institutional pages.
                fresh=sorted((x for x in extra if x["url"] not in old),
                             key=lambda x:(not x["origin_type"].startswith("official_"),x["id"]))
                collected=collected+fresh[:4]
            raw=call_model(critique_prompt(roles,collected),model=args.critic_model)
            checked=validate_critique(raw,roles,domain["modules"])
            checked["investigation_id"]=s["id"]
            checked["original_model"]=roles["model_provenance"]
            checked["critic_model"]=f"{args.provider}:{args.critic_model}"
            write(args.out_dir/(args.domain+(".critique.recovery.json" if args.include_recovery else ".critique.json")),checked)
        elif args.step=="graph":
            source=args.domain+(".critique.recovery.json" if args.include_recovery else ".critique.json")
            checked=json.loads((args.out_dir/source).read_text())
            staged=stage_coverage(args.workspace,s["id"],domain,checked)
            # Expose only graph receipt and structural counts; full source
            # passages stay in local workspace.
            write(args.out_dir/(args.domain+(".graph.recovery.json" if args.include_recovery else ".graph.json")),{
                "schema":"cite_refinery.cross_domain_graph_receipt.v1",
                "domain":args.domain,"investigation_id":s["id"],
                "graph_receipt_id":staged["receipt"]["id"],
                "neutral_nodes":len(staged["packet"]["nodes"]),
                "candidate_or_unresolved_edges":len(staged["packet"]["edges"]),
                "authoritative_claims_accepted":0,
                "same_model_family_review":True,
            })
    response={"domain":args.domain,"step":args.step,"investigation_id":s["id"],"state":s["stage"],
              "round_count":len(s["rounds"]),
              "source_count":len(s["rounds"][-1]["sources"]) if s["rounds"] else 0,
              "source_types":sorted(set(x["origin_type"] for x in s["rounds"][-1]["sources"])) if s["rounds"] else [],
              "last_error":s.get("last_error")}
    if args.step in {"roles","critic"}:
        suffix="roles" if args.step=="roles" else "critique"
        file=args.domain+"."+suffix+(".recovery" if args.include_recovery else "")+".json"
        output=json.loads((args.out_dir/file).read_text())
        response["roles"]={x["source_id"]:x["role"] for x in output["results"]}
        response["coverage"]={k:v["source_coverage_status"] for k,v in output["coverage"].items()}
        response["confirmed_independent_field_outcomes"]=0
        response["authority"]="neutral_only"
    if args.step=="graph":
        response["graph_receipt"]=staged["receipt"]["id"]
        response["neutral_nodes"]=len(staged["packet"]["nodes"])
        response["review_edges"]=len(staged["packet"]["edges"])
        response["accepted_effects"]=0
    if args.step=="recover":
        response["discovered_new_leads"]=len(recovered["sources"])
        response["recovery_searches"]=recovered["plan"]["queries"]
        response["independent_research_outcome_verified"]=False
    print(json.dumps(response,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
