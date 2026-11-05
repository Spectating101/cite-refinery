"""Atlas source-first capability discovery: existing search + exact Git blobs.

No arbitrary external code execution, no inference of integration readiness,
no license grant, no automatic device operation. Provider text is untrusted.
"""
from __future__ import annotations
import argparse
import base64
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any,Callable
from urllib.parse import quote

from .multi_source_discovery import collect as multi_collect
from .discovery_capability_review import load_requirements,review as capability_review
from .repository_trend_bridge import SLUG

GOAL="cite_refinery.autonomous_capability_goal.v1"
SCHEMA="cite_refinery.atlas_capability_investigation.v1"
SHA=re.compile(r"^[a-f0-9]{40}$")
TOKEN=re.compile(r"^[a-z0-9 _-]{2,45}$")
PATH=re.compile(r"^[A-Za-z0-9_./-]{2,210}$")
BRANCH=re.compile(r"^[A-Za-z0-9._/-]{1,100}$")
CODE_SUFFIX=(".py",".ts",".tsx",".js",".rs",".go",".cs",".cpp",".cc",".c",".h",".hpp",".sdf",".urdf")
BAD_PREFIX=(".github/","docs/","doc/","test/","tests/","examples/","example/","vendor/","third_party/","dist/","build/")
TREE_JQ=('{truncated:.truncated,files:[.tree[]|select(.type=="blob")|'
    'select(.size>=50 and .size<=80000)|'
    'select(.path|test("(?i)(cad|cq|urdf|robot|sim|physics|kicad|pcb|drc|erc|bom|printer|mcp|gcode|klipper|octoprint|moonraker|component|geometry)"))|'
    '{path:.path,sha:.sha,size:.size}]|.[0:180]}')


def _hash(x:Any)->str:
    return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,
                  separators=(",",":")).encode()).hexdigest()


def validate_goal(data:dict[str,Any])->dict[str,Any]:
    if not isinstance(data,dict) or data.get("schema")!=GOAL:
        raise ValueError("unsupported capability objective schema")
    if not isinstance(data.get("goal"),str) or not 25<=len(data["goal"])<=500:
        raise ValueError("engineering research goal required")
    if not isinstance(data.get("project"),str) or not re.fullmatch(r"[a-z][a-z0-9_]{3,70}",data["project"]):
        raise ValueError("invalid project")
    target=data.get("target_repo")
    if target is not None and (not isinstance(target,str) or not SLUG.fullmatch(target)):
        raise ValueError("unsafe existing target GitHub repository")
    if data.get("evidence_policy")!="metadata_discovery_then_exact_sha_pinned_implementation_file_witness":
        raise ValueError("cannot relax original source code evidence policy")
    rows=data.get("requirements")
    if not isinstance(rows,list) or not 1<=len(rows)<=6:
        raise ValueError("must choose 1-6 capability questions")
    seen=set()
    for row in rows:
        ident=row.get("id") if isinstance(row,dict) else None
        if not isinstance(ident,str) or not re.fullmatch(r"[a-z][a-z0-9_]{2,40}",ident) or ident in seen:
            raise ValueError("invalid/duplicate capability")
        seen.add(ident)
        if not isinstance(row.get("query"),str) or not 4<=len(row["query"])<=110 or "\n" in row["query"]:
            raise ValueError("invalid capability-derived GitHub query")
        if not isinstance(row.get("next_test"),str) or not 25<=len(row["next_test"])<=300:
            raise ValueError("missing falsifying engineering test")
        for key in ("evidence_path_tokens","evidence_text_tokens"):
            v=row.get(key)
            if not isinstance(v,list) or not 2<=len(v)<=10 or any(
                not isinstance(x,str) or not TOKEN.fullmatch(x) for x in v):
                raise ValueError("unsafe or missing bounded evidence tokens")
    _,requirements=build_plan(data,validate=False)
    load_requirements(requirements)
    return data


def build_plan(data:dict[str,Any],*,validate:bool=True)->tuple[dict[str,Any],dict[str,Any]]:
    if validate:validate_goal(data)
    sources={"schema":"cite_refinery.multisource_discovery.v1","sources":[]}
    requirements={"schema":"cite_refinery.discovery_requirements.v1","requirements":[]}
    for r in data["requirements"]:
        sources["sources"].append({"id":r["id"]+"_search","provider":"github_search",
            "query":r["query"],"tags":["engineering"],"project_targets":[data["project"]],
            "limit":9,"ranking":"relevance"})
        requirements["requirements"].append({"id":r["id"],"project":data["project"],
            "question":r["question"],"must_match":r["must_match"],
            "bonus":r.get("bonus",["review"]),"allow_source_types":["software"]})
    return sources,requirements


def github_api(endpoint:str,*,jq:str|None=None)->dict[str,Any]:
    """GitHub CLI read-only allowlist: source metadata, commit, tree and blob."""
    if not isinstance(endpoint,str) or len(endpoint)>240 or not re.fullmatch(
        r"repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
        r"(?:(?:/commits/[A-Za-z0-9._/-]+)|(?:/git/(?:trees|blobs)/[a-f0-9]{40}(?:\?recursive=1)?))?",endpoint):
        raise ValueError("unsafe GitHub API route")
    args=["gh","api",endpoint]
    if jq:
        if jq!=TREE_JQ:raise ValueError("unsafe code evidence selector")
        args+=["--jq",jq]
    try:
        r=subprocess.run(args,capture_output=True,timeout=32,check=False)
    except (OSError,subprocess.TimeoutExpired) as e:
        raise ValueError("GitHub read failed or timed out") from e
    if r.returncode!=0 or len(r.stdout)>1_800_000:
        raise ValueError("GitHub source API unavailable/oversize")
    try:return json.loads(r.stdout)
    except (ValueError,UnicodeError) as e:raise ValueError("GitHub JSON invalid") from e


def blob_text(body:dict[str,Any],sha:str)->str:
    if (not isinstance(body,dict) or body.get("encoding")!="base64" or
        not isinstance(body.get("content"),str) or
        type(body.get("size")) is not int or not 50<=body["size"]<=80000):
        raise ValueError("original GitHub blob format/size unsupported")
    raw=base64.b64decode(body["content"])
    if len(raw)!=body["size"] or hashlib.sha1(
        b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=sha:
        raise ValueError("Git original source blob SHA differs from content")
    return raw.decode("utf-8","strict")


def file_priority(row:dict[str,Any],tokens:list[str])->int:
    p=row.get("path")
    if (not isinstance(p,str) or not PATH.fullmatch(p) or p.startswith("/") or
        ".." in p.split("/") or not p.casefold().endswith(CODE_SUFFIX) or
        any(p.casefold().startswith(prefix) for prefix in BAD_PREFIX) or
        not SHA.fullmatch(str(row.get("sha") or ""))):
        return 0
    return sum(token in p.casefold() for token in tokens)


def literal_code_indicator(text:str,tokens:list[str])->tuple[str|None,int|None]:
    for n,line in enumerate(text.splitlines(),1):
        visible=line.strip().casefold()
        if visible.startswith(("#","//","/*","*","<!--","from ","import ","using ","package ")):
            continue
        for token in tokens:
            if re.search(r"(?<![a-z0-9])"+re.escape(token).replace(r"\ ",r"\s+"),visible):
                return token,n
    return None,None


def inspect_repo(slug:str,spec:dict[str,Any],*,api:Callable[...,Any]=github_api)->dict[str,Any]:
    if not isinstance(slug,str) or not SLUG.fullmatch(slug):
        raise ValueError("invalid source repository slug")
    source={"repository":slug,"url":"https://github.com/"+slug,
        "source_sha":None,"original_source_code_files":[],
        "review_status":"SOURCE_UNAVAILABLE_ABSTAIN",
        "source_file_path_matches":0,"license_api_spdx":None,
        "license_clearance_complete":False,"runtime_integration_verified":False,
        "external_code_executed":False,"device_action_performed":False,
        "safe_to_auto_merge":False}
    endpoint="repos/"+slug
    try:
        meta=api(endpoint)
        if (meta.get("full_name")!=slug or meta.get("private") is not False or
            meta.get("archived") not in (False,True)):
            raise ValueError("original public repo identity not verified")
        branch=meta.get("default_branch")
        if not isinstance(branch,str) or not BRANCH.fullmatch(branch) or ".." in branch:
            raise ValueError("unsafe original source branch")
        source["archived"]=meta["archived"]
        lic=meta.get("license") or {}
        source["license_api_spdx"]=lic.get("spdx_id") if isinstance(lic,dict) else None
        source["stars_provider_metadata_only"]=meta.get("stargazers_count")
        source["last_pushed_provider_metadata"]=meta.get("pushed_at")
        commit=api(endpoint+"/commits/"+branch)
        sha=commit.get("sha")
        if not isinstance(sha,str) or not SHA.fullmatch(sha):
            raise ValueError("original GitHub commit SHA unavailable")
        source["source_sha"]=sha
        tree=api(endpoint+"/git/trees/"+sha+"?recursive=1",jq=TREE_JQ)
        rows=tree.get("files")
        if not isinstance(rows,list) or len(rows)>180:
            raise ValueError("original source path listing out of bounds")
        source["source_tree_truncated_or_sampled"]=tree.get("truncated") is True or len(rows)==180
        possible=[(file_priority(f,spec["evidence_path_tokens"]),f) for f in rows]
        possible=[(n,f) for n,f in possible if n>0]
        possible.sort(key=lambda x:(-x[0],x[1]["path"]))
        source["source_file_path_matches"]=len(possible)
        for _,file in possible[:2]:
            body=api(endpoint+"/git/blobs/"+file["sha"])
            text=blob_text(body,file["sha"])
            token,line=literal_code_indicator(text,spec["evidence_text_tokens"])
            source["original_source_code_files"].append({
                "path":file["path"],"git_blob_sha":file["sha"],
                "raw_bytes":body["size"],
                "pinned_url":"https://github.com/"+slug+"/blob/"+sha+"/"+quote(file["path"],safe="/"),
                "implementation_literal_found":token is not None,
                "literal_indicator":token,"indicator_line_number":line,
                "verified":"EXACT_ORIGINAL_GIT_BLOB_SHA_ONLY"})
        if any(f["implementation_literal_found"] for f in source["original_source_code_files"]):
            source["review_status"]="CODE_LITERAL_OBSERVED_NOT_TESTED"
        elif source["original_source_code_files"]:
            source["review_status"]="SOURCE_PATH_EXISTS_FUNCTION_UNCONFIRMED"
        else:
            source["review_status"]="METADATA_ONLY_ABSTAIN"
    except (ValueError,KeyError,TypeError,UnicodeError) as exc:
        source["review_status"]="SOURCE_UNAVAILABLE_ABSTAIN"
        source["error_type"]=type(exc).__name__
    return source


def run(goal:dict[str,Any],*,collector:Callable[...,Any]=multi_collect,
        api:Callable[...,Any]=github_api,probes_per_capability:int=2)->dict[str,Any]:
    validate_goal(goal)
    if probes_per_capability not in (1,2,3):
        raise ValueError("source probe budget must be 1-3")
    plan,requirements=build_plan(goal,validate=False)
    discovery=collector(plan)
    reviews=capability_review(discovery,requirements,limit=12)
    lookup={r["id"]:r for r in discovery["records"]}
    categories={r["id"]:r for r in goal["requirements"]}
    outputs=[]
    # Cache identical original GitHub metadata/tree requests across source
    # categories, but verify implementation-file evidence separately for each.
    cached_calls={}
    def cached_api(endpoint,*,jq=None):
        key=(endpoint,jq)
        if key not in cached_calls:
            cached_calls[key]=api(endpoint,jq=jq)
        return cached_calls[key]
    for group in reviews["requirements"]:
        ident=group["id"]
        category=categories[ident]
        query_id=ident+"_search:"
        provider=[r for r in discovery["records"] if r["id"].startswith(query_id)]
        baseline=provider[0]["title"] if provider else None
        lexical=[]
        for match in group["unreviewed"]:
            repo=lookup[match["record_id"]]["title"]
            if isinstance(repo,str) and SLUG.fullmatch(repo) and repo not in lexical:
                lexical.append(repo)
            if len(lexical)>=probes_per_capability:break
        selected=list(dict.fromkeys(lexical+([baseline] if baseline and SLUG.fullmatch(baseline) else [])))
        sources=[inspect_repo(repo,category,api=cached_api) for repo in selected]
        existing=inspect_repo(goal["target_repo"],category,api=cached_api) if goal.get("target_repo") else None
        def priority(x):
            return ((100 if x["review_status"]=="CODE_LITERAL_OBSERVED_NOT_TESTED" else
                     20 if x["review_status"]=="SOURCE_PATH_EXISTS_FUNCTION_UNCONFIRMED" else 0)
                    +(5 if x.get("archived") is False else 0))
        ranked=sorted(sources,key=lambda x:(-priority(x),x["repository"]))
        first=ranked[0] if ranked else None
        top_score=priority(first) if first else 0
        top_tied_repos=[x["repository"] for x in ranked if priority(x)==top_score and top_score>0]
        baseline_evidence=next((x for x in sources if x["repository"]==baseline),None)
        outputs.append({"id":ident,"question":category["question"],
            "search_query":category["query"],
            "search_provider_status":next((x["state"] for x in discovery["source_results"]
                if x["source"]==ident+"_search"),"unavailable"),
            "provider_search_baseline_repo":baseline,
            "matched_metadata_candidates":group["matched"],
            "source_probed_repos":selected,
            "ranked_original_source_witnesses":[{**s,"source_review_priority_not_adoption_score":priority(s)}
                 for s in ranked],
            "existing_target_repository_source_probe":existing,
            "target_default_branch_source_overlap_status":(
                "POSSIBLE_ALREADY_IMPLEMENTED_CHECK_FUNCTIONAL_EQUIVALENCE"
                if existing and existing["review_status"]=="CODE_LITERAL_OBSERVED_NOT_TESTED" else
                "NO_IMPL_SOURCE_INDICATOR_ON_DEFAULT_BRANCH_NOT_PROOF_OF_ABSENCE"
                if existing else "NOT_CHECKED"),
            "atlas_top_source_review_repo":first["repository"] if first else None,
            "top_evidence_tied_not_unique_winner":len(top_tied_repos)>1,
            "top_evidence_equal_priority_repositories":top_tied_repos,
            "atlas_top_source_code_indicator":bool(first and first["review_status"]=="CODE_LITERAL_OBSERVED_NOT_TESTED"),
            "baseline_source_code_indicator":(
                baseline_evidence["review_status"]=="CODE_LITERAL_OBSERVED_NOT_TESTED"
                if baseline_evidence else None),
            "next_falsifying_test":category["next_test"],
            "decision":("REVIEW_EXISTING_TARGET_CODE_BEFORE_ANY_LIBRARY_ADOPTION"
                if existing and existing["review_status"]=="CODE_LITERAL_OBSERVED_NOT_TESTED" else
                "SOURCE_CODE_REVIEW_THEN_INDEPENDENT_FIXTURE" if first and
                first["review_status"]=="CODE_LITERAL_OBSERVED_NOT_TESTED" else
                "ABSTAIN_NO_IMPLEMENTATION_PROOF")})
    return {"schema":SCHEMA,"goal":goal["goal"],"project":goal["project"],
        "goal_spec_digest_sha256":_hash(goal),
        "observed_at":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "provider_outcomes":discovery["source_results"],
        "provider_discovery_candidates":len(discovery["records"]),
        "existing_lexical_review_authority":reviews["authority"],
        "metadata_candidates_abstained":reviews["records_abstained"],
        "capability_questions":len(outputs),
        "total_code_repository_probes":sum(len(x["source_probed_repos"]) for x in outputs),
        "target_repository":goal.get("target_repo"),
        "target_default_branch_only_not_open_prs":True,
        "categories_with_possible_existing_target_code_indicators":sum(
            x["target_default_branch_source_overlap_status"]==
            "POSSIBLE_ALREADY_IMPLEMENTED_CHECK_FUNCTIONAL_EQUIVALENCE" for x in outputs),
        "capabilities_with_some_source_indicator":sum(any(s["review_status"]=="CODE_LITERAL_OBSERVED_NOT_TESTED"
            for s in x["ranked_original_source_witnesses"]) for x in outputs),
        "atlas_top_original_code_indicators":sum(x["atlas_top_source_code_indicator"] for x in outputs),
        "plain_github_first_result_code_indicators":sum(x["baseline_source_code_indicator"] is True for x in outputs),
        "comparison_note":"SAME_PROVIDER_QUERY_AND_PROBE_POLICY__NOT_INDEPENDENT_SCIENTIFIC_BENCHMARK",
        "tested_integrations":0,"independent_analyst_reviews":0,
        "source_code_presence_is_not_working_integration":True,
        "license_clearance_complete":False,"economic_opportunity_verified":False,
        "automatically_merged_repositories":0,"automatic_device_actions":0,
        "decision":"SOURCE_FIRST_INTEGRATION_HYPOTHESES_NOT_VALIDATED",
        "requirements":outputs}



def validate_snapshot(report:dict[str,Any],goal:dict[str,Any]|None=None)->bool:
    """Check a saved source receipt's internal scope; does not re-fetch GitHub."""
    if (report.get("schema")!=SCHEMA or report.get("tested_integrations")!=0 or
        report.get("independent_analyst_reviews")!=0 or
        report.get("automatically_merged_repositories")!=0 or
        report.get("automatic_device_actions")!=0 or
        report.get("source_code_presence_is_not_working_integration") is not True or
        report.get("license_clearance_complete") is not False):
        raise ValueError("source discovery output improperly claims authority")
    if goal is not None and (validate_goal(goal) is not goal or
                             report.get("goal_spec_digest_sha256")!=_hash(goal)):
        raise ValueError("source discovery output no longer matches original objective")
    requirements=report.get("requirements")
    if (not isinstance(requirements,list) or
        len(requirements)!=report.get("capability_questions") or
        not 1<=len(requirements)<=6):
        raise ValueError("source discovery capability groups missing")
    probes=0;found=0;ranked_hits=0;baseline_hits=0;overlaps=0
    for group in requirements:
        ranked=group.get("ranked_original_source_witnesses")
        if not isinstance(ranked,list) or len(ranked)>4:
            raise ValueError("source review candidates exceed allowed budget")
        probed=group.get("source_probed_repos")
        if not isinstance(probed,list) or len(ranked)!=len(probed) or (
           {x["repository"] for x in ranked}!=set(probed)):
            raise ValueError("original GitHub source review identity changed")
        probes+=len(probed)
        for item in ranked+([group["existing_target_repository_source_probe"]]
             if group.get("existing_target_repository_source_probe") else []):
            if (item.get("external_code_executed") is not False or
                item.get("device_action_performed") is not False or
                item.get("safe_to_auto_merge") is not False or
                item.get("runtime_integration_verified") is not False or
                item.get("license_clearance_complete") is not False):
                raise ValueError("original-source listing claims unverified adoption or legal rights")
            files=item.get("original_source_code_files")
            if not isinstance(files,list) or len(files)>2:raise ValueError("source file bounds exceeded")
            observed=any(f["implementation_literal_found"] for f in files)
            if observed!=(item["review_status"]=="CODE_LITERAL_OBSERVED_NOT_TESTED"):
                raise ValueError("original GitHub source indicators disagree")
            if files and not SHA.fullmatch(str(item.get("source_sha") or "")):
                raise ValueError("unidentified original repository commit")
            for f in files:
                if (not SHA.fullmatch(str(f.get("git_blob_sha") or "")) or
                    not PATH.fullmatch(str(f.get("path") or "")) or
                    f["pinned_url"]!="https://github.com/"+item["repository"]+
                      "/blob/"+item["source_sha"]+"/"+quote(f["path"],safe="/") or
                    f.get("verified")!="EXACT_ORIGINAL_GIT_BLOB_SHA_ONLY"):
                    raise ValueError("source file evidence URL/hash mismatch")
                if f["implementation_literal_found"]!=(f["literal_indicator"] is not None):
                    raise ValueError("source code literal evidence mismatch")
        top=ranked[0] if ranked else None
        if group.get("atlas_top_source_review_repo")!=(top["repository"] if top else None):
            raise ValueError("unreviewed ranking top changed")
        topcode=bool(top and top["review_status"]=="CODE_LITERAL_OBSERVED_NOT_TESTED")
        if group.get("atlas_top_source_code_indicator")!=topcode:
            raise ValueError("source-verified top condition differs")
        ranked_hits+=int(topcode)
        found+=int(any(x["review_status"]=="CODE_LITERAL_OBSERVED_NOT_TESTED" for x in ranked))
        base=next((x for x in ranked if x["repository"]==group.get("provider_search_baseline_repo")),None)
        baseline=base["review_status"]=="CODE_LITERAL_OBSERVED_NOT_TESTED" if base else None
        if group.get("baseline_source_code_indicator")!=baseline:
            raise ValueError("plain search baseline was not tested under same code witness")
        baseline_hits+=int(baseline is True)
        target=group.get("existing_target_repository_source_probe")
        status="POSSIBLE_ALREADY_IMPLEMENTED_CHECK_FUNCTIONAL_EQUIVALENCE" if (
            target and target["review_status"]=="CODE_LITERAL_OBSERVED_NOT_TESTED") else (
            "NO_IMPL_SOURCE_INDICATOR_ON_DEFAULT_BRANCH_NOT_PROOF_OF_ABSENCE" if target else "NOT_CHECKED")
        if status!=group.get("target_default_branch_source_overlap_status"):
            raise ValueError("existing target source overlap assessment differs")
        overlaps+=int(status=="POSSIBLE_ALREADY_IMPLEMENTED_CHECK_FUNCTIONAL_EQUIVALENCE")
        expected_tied=[x["repository"] for x in ranked if ranked and
                       x["source_review_priority_not_adoption_score"]==ranked[0]["source_review_priority_not_adoption_score"]
                       and ranked[0]["source_review_priority_not_adoption_score"]>0]
        if (group.get("top_evidence_equal_priority_repositories")!=expected_tied or
            group.get("top_evidence_tied_not_unique_winner")!=(len(expected_tied)>1)):
            raise ValueError("equal evidence candidates incorrectly called winners")
    if (probes!=report.get("total_code_repository_probes") or
        found!=report.get("capabilities_with_some_source_indicator") or
        ranked_hits!=report.get("atlas_top_original_code_indicators") or
        baseline_hits!=report.get("plain_github_first_result_code_indicators") or
        overlaps!=report.get("categories_with_possible_existing_target_code_indicators")):
        raise ValueError("summary source evidence totals disagree")
    return True


def render(report:dict[str,Any])->str:
    validate_snapshot(report)
    lines=["# Atlas: source-first engineering capability discovery","",
        "**Objective:** "+report["goal"],"",
        "This is objective-profile-driven GitHub search, existing Atlas lexical triage, "
        "and SHA-pinned Git source-code presence verification. This is NOT free-form "
        "autonomous planning or proven integrations.","",
        "Provider candidates: "+str(report["provider_discovery_candidates"])+
        ". Bounded original GitHub code probes: "+str(report["total_code_repository_probes"])+
        ". Capability areas with at least one implementation literal: "+
        str(report["capabilities_with_some_source_indicator"])+"/"+
        str(report["capability_questions"])+".","",
        "| Capability | First review candidate (not a winner) | GitHub first result | Code indicator observed |",
        "|---|---|---|---|"]
    for row in report["requirements"]:
        top=row["atlas_top_source_review_repo"] or "abstain"
        lines.append("| "+row["id"].replace("_"," ").title()+" | "+top+" | "+
                     str(row["provider_search_baseline_repo"] or "none")+" | "+
                     ("Yes (not run)" if row["atlas_top_source_code_indicator"] else "No") +" |")
    lines+=["","## Source-pinned engineering review queue",""]
    for row in report["requirements"]:
        lines+=["### "+row["id"].replace("_"," ").title(),"",
           "**Question:** "+row["question"],"",
           "**Provider search:** "+row["search_query"],"",
           "**Candidate metadata matches:** "+str(row["matched_metadata_candidates"])+
           "; query outcome: "+row["search_provider_status"],""]
        for repo in row["ranked_original_source_witnesses"]:
            lines+=["**"+repo["repository"]+"** — "+repo["review_status"],"",
                "Pinned commit: "+str(repo["source_sha"] or "unavailable")+
                "; GitHub license metadata: "+str(repo["license_api_spdx"] or "unknown")+
                " (legal review required).",""]
            for file in repo["original_source_code_files"]:
                lines+=["- ["+file["path"]+"]("+file["pinned_url"]+
                    ") — exact Git blob "+file["git_blob_sha"]+
                    "; literal code indicator: "+str(file["literal_indicator"] or "not found")+
                    "; external code not executed."]
            if not repo["original_source_code_files"]:
                lines+=["- No implementation file witnessed; provider description alone is insufficient."]
            lines+=[""]
        target=row.get("existing_target_repository_source_probe")
        if target:
            lines+=["**Existing target repository:** "+target["repository"]+
                " (default branch only; does not inspect open PRs).", "",
                "**Possible existing capability indicator:** "+
                row["target_default_branch_source_overlap_status"]+".",""]
            for file in target["original_source_code_files"]:
                lines+=["- [Existing source file "+file["path"]+"]("+file["pinned_url"]+
                    ") — pinned SHA "+file["git_blob_sha"]+
                    "; literal token "+str(file["literal_indicator"] or "not found")+
                    ". This is NOT proof of functional duplication."]
            lines+=[""]
        lines+=["**Next falsifying engineering test:** "+row["next_falsifying_test"],"",
            "**Equal-evidence alternatives:** "+", ".join(row["top_evidence_equal_priority_repositories"])+
            ". A tied evidence score never establishes a technical winner.","",
            "**Disposition:** "+row["decision"],""]
    lines+=["## What the baseline comparison means","",
        "Plain GitHub search baseline = first relevance result for each identical query. "
        "The Atlas-first result is ordered by available original code-file evidence after a "
        "small, bounded lexical source screening. Both first-result and Atlas candidates "
        "receive the same SHA/blob check. This is not an unbiased performance study, "
        "and missing source files do not imply no capability.",
        "",
        "Plain first-result code indicators: "+
        str(report["plain_github_first_result_code_indicators"])+"/"+
        str(report["capability_questions"])+
        "; Atlas-ranked code indicators: "+str(report["atlas_top_original_code_indicators"])+"/"+
        str(report["capability_questions"])+".","",
        "**No integrations were executed. Licensing, API semantics, safety, maintainability, "
        "cost and engineering usefulness require a separate operator-controlled test.**","",
        "Existing Hardware Splicer code indicators are limited to its default branch, not draft/open PRs. "
        "A shared token is not functional equivalence and should trigger a comparison test, not automatically block adoption.","",
        "All source observations remain review-only; no automatic merging, hardware actions, or trusted registration.",""]
    return "\n".join(lines)


def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(prog="atlas-capability-investigate")
    p.add_argument("--goal",type=Path,required=True)
    p.add_argument("--out-dir",type=Path,required=True)
    p.add_argument("--stem",default="hs_capability_source_investigation")
    p.add_argument("--probes",type=int,choices=[1,2,3],default=2)
    opts=p.parse_args(argv)
    if not re.fullmatch(r"[a-z][a-z0-9_-]{2,70}",opts.stem):
        p.error("unsafe output basename")
    obj=json.loads(opts.goal.read_text())
    result=run(obj,probes_per_capability=opts.probes)
    opts.out_dir.mkdir(parents=True,exist_ok=True)
    receipt=opts.out_dir/(opts.stem+".json")
    brief=opts.out_dir/(opts.stem+".md")
    if receipt.exists() or brief.exists():
        raise FileExistsError("immutable discovery result already exists")
    receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    brief.write_text(render(result))
    print(json.dumps({"candidate_repositories":result["provider_discovery_candidates"],
       "source_probes":result["total_code_repository_probes"],
       "source_witnessed_categories":result["capabilities_with_some_source_indicator"],
       "atlas_top_indicators":result["atlas_top_original_code_indicators"],
       "plain_search_indicators":result["plain_github_first_result_code_indicators"],
       "tested_integrations":0,"report":str(brief)}))
    return 0


if __name__=="__main__":raise SystemExit(main())
