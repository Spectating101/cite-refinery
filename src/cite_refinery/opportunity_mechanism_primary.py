"""Primary-source mechanism dossiers, distinct from repository discovery and commercial lead scoring.

Dossiers are investigator hypotheses, grounded in the original 63-source
development-only corpus, not in the earlier AI paraphrase. SHA-256 of each
original source is checked; cited anchor is a literal <=22-word excerpt.
Selected OSS README content is likewise matched to a known git blob SHA.

No sealed holdout material is opened, no source is promoted to scientifically
validated, and no buyer or license permission is inferred.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

IN="cite_refinery.primary_mechanism_dossiers_input.v1"
OUT="cite_refinery.primary_mechanism_graph.v1"
READ="cite_refinery.open_corpus.v1"
PROVISIONAL="cite_refinery.open_corpus_provisional_map.v1"


def phrase(text:str)->str:
    return " ".join(text.split()).casefold()


def exact_excerpt(text:str, needle:str, *, limit:int=22)->str:
    if not isinstance(text,str) or not isinstance(needle,str) or len(needle)<4 or len(needle)>120:
        raise ValueError("invalid source anchor needle")
    matches=list(re.finditer(r"\S+",text))
    hay=phrase(text);key=phrase(needle)
    if key not in hay:
        raise ValueError("source anchor not in checked original")
    # Find a location in *the original*, then render just one small bounded
    # exact contiguous excerpt. Avoid whitespace-normalization offset bugs.
    start=-1
    try:
        start=re.search(re.escape(needle),text,re.I).start()
    except AttributeError:
        for i in range(len(matches)):
            for j in range(i,min(len(matches),i+25)):
                chunk=text[matches[i].start():matches[j].end()]
                if phrase(needle) in phrase(chunk):
                    start=matches[i].start();break
            if start>=0:break
    if start<0:
        raise ValueError("anchor cannot be located without mutating original text")
    position=next((i for i,m in enumerate(matches) if m.start()<=start<m.end()),None)
    if position is None:
        raise ValueError("original quote token offset failure")
    lo=max(0,position-6)
    hi=min(len(matches),lo+limit)
    snippet=text[matches[lo].start():matches[hi-1].end()]
    if phrase(needle) not in phrase(snippet):
        lo=position
        hi=min(len(matches),position+limit)
        snippet=text[matches[lo].start():matches[hi-1].end()]
    if phrase(needle) not in phrase(snippet) or len(snippet.split())>limit:
        raise ValueError("quote contains no literal anchor or exceeds quote boundary")
    if snippet not in text:
        raise ValueError("quote must remain literally source exact")
    return snippet


def _str(value:Any,key:str,minimum:int=12,maximum:int=1200)->str:
    if not isinstance(value,str):
        raise ValueError(f"{key} requires text")
    value=" ".join(value.split())
    if not minimum <= len(value) <= maximum:
        raise ValueError(f"{key} length outside bounds")
    return value


def build(manifest:dict[str,Any],corpus:dict[str,Any],readings:dict[str,Any], *,
          readme_dir:Path,observed_at:str)->dict[str,Any]:
    if manifest.get("schema")!=IN or corpus.get("schema")!=READ or \
       corpus.get("material_type")!="unclassified_source_records" or \
       readings.get("schema")!=PROVISIONAL:
        raise ValueError("invalid source scope")
    original={r["id"]:r for r in corpus["sources"]}
    model_readings={r["source_id"]:r for r in readings["readings"]}
    if len(original)!=len(corpus["sources"]) or len(model_readings)!=len(readings["readings"]):
        raise ValueError("source identity duplication")
    if not isinstance(manifest.get("entries"),list) or not 1<=len(manifest["entries"])<=16:
        raise ValueError("bounded mechanism briefs required")
    briefs=[]
    nodes={}
    edges=[]
    used_domains=set()
    for case in manifest["entries"]:
        key=case["key"]
        if not re.fullmatch(r"[a-z][a-z0-9_]{5,80}",key) or key in used_domains:
            raise ValueError("duplicate or invalid mechanism identity")
        used_domains.add(key)
        statement={k:_str(case.get(k),k,minimum=30) for k in (
            "problem","mechanism","capability_contract","validation","gap")}
        cited=[]
        if not isinstance(case.get("basis"),list) or not 2<=len(case["basis"])<=7:
            raise ValueError("2..7 original sources required")
        seen=set()
        for sid,needle in case["basis"]:
            if sid in seen or sid not in original or sid not in model_readings:
                raise ValueError("duplicate or missing original source")
            seen.add(sid)
            r=original[sid];m=model_readings[sid]
            source=r.get("text")
            if not isinstance(source,str) or len(source)<40 or len(source)>20000:
                raise ValueError("original text not in supported bounded source form")
            digest=hashlib.sha256(source.encode("utf-8")).hexdigest()
            if digest!=r["sha256"] or digest!=m["source_sha256"] or r["url"]!=m["source_url"]:
                raise ValueError("original source SHA/url mismatches previously mapped identity")
            q=exact_excerpt(source,needle)
            cited.append({
                "id":sid,"url":r["url"],"title":r["title"],
                "origin_type":r["origin_type"],
                "scope":r["source_scope"],"original_sha256":digest,
                "quote":q,"quote_word_limit":22,
                "previous_mapper_role_unverified":m["role"],
                "verification":"original_text_hash_and_literal_quote_checked_only",
            })
            nid="source:"+sid
            nodes.setdefault(nid,{
                "id":nid,"type":"documentary_source","url":r["url"],
                "evidence_status":"original_excerpt_verified_semantic_entailment_not_adjudicated",
            })
            edges.append({
                "from":nid,"to":"mechanism:"+key,"relation":"POSSIBLE_EVIDENCE_FOR",
                "verification":"literal_source_quote_only_not_entailment_or_causal_proof",
            })
        repo=case.get("repo")
        candidate=None
        if repo is not None:
            if not isinstance(repo,str) or not re.fullmatch("[A-Za-z0-9_.-]{1,60}/[A-Za-z0-9_.-]{1,100}",repo):
                raise ValueError("invalid repository identifier")
            file=readme_dir / (repo.replace("/","__")+".md")
            if not file.is_file():
                raise ValueError("requested repository README not available for verification")
            raw=file.read_bytes()
            digest=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
            if digest!=case.get("repo_sha"):
                raise ValueError("repository README changed from recorded git blob")
            rd=raw.decode("utf-8","strict")
            q=exact_excerpt(rd,case["repo_excerpt"],limit=21)
            candidate={
                "id":"github:"+repo,"url":"https://github.com/"+repo,
                "readme_url":"https://github.com/"+repo+"/blob/HEAD/README.md",
                "git_blob_sha":digest,"readme_anchor":q,
                "role":_str(case["repo_role"],"repo_role",minimum=4,maximum=150),
                "status":"bounded_readme_capability_only_not_tested",
                "component_gap":statement["gap"],
                "license_clearance":"not_reviewed",
                "buyer_demand":"not_reviewed",
                "integration_test":"not_executed",
            }
            nodes.setdefault(candidate["id"],{
                "id":candidate["id"],"type":"reusable_implementation_lead",
                "url":candidate["url"],"evidence_status":"source_readme_blob_verified_not_operationally_replicated",
            })
            edges.append({
                "from":candidate["id"],"to":"mechanism:"+key,
                "relation":"POSSIBLE_PARTIAL_CAPABILITY_OR_ADJACENCY",
                "verification":"README_git_blob_and_quote_only_not_implementation_fitness",
            })
        else:
            if case.get("repo_role")!="no_credible_repo_link_yet":
                raise ValueError("explicit missing repo must be unfilled")
        brief={
            "id":"mechanism:"+key,"family":case["family"],**statement,
            "primary_sources":cited,"implementation_lead":candidate,
            "program_outcome_confirmed":False,"technical_fitness_confirmed":False,
            "buyer_demand_confirmed":False,"economics_confirmed":False,
            "missing_capability":"No tested end-to-end technical solution; bounded implementation lead is a hypothesis."
                if candidate else "No evidence-bounded OSS capability lead selected for this problem.",
            "verification_status":"original_source_excerpts_verified_investigator_mechanism_hypothesis_only",
        }
        briefs.append(brief)
        nodes["mechanism:"+key]={
            "id":"mechanism:"+key,"type":"interpreted_operational_mechanism",
            "label":statement["problem"],"evidence_status":"investigator_candidate_not_reviewed_for_entailment",
        }
    return {
        "schema":OUT,"observed_at":observed_at,"development_sources_total":len(original),
        "briefs":briefs,"nodes":sorted(nodes.values(),key=lambda r:r["id"]),
        "edges":edges,
        "coverage":{
            "operational_mechanisms_described":len(briefs),
            "families":dict(Counter(x["family"] for x in briefs)),
            "primary_source_identities":len({s["id"] for x in briefs for s in x["primary_sources"]}),
            "repo_readme_blobs_verified":sum(bool(x["implementation_lead"]) for x in briefs),
            "full_operational_stacks_validated":0,
            "commercial_contracts_verified":0,
            "research_holdout_touched":False,
        },
        "authority":"SOURCE_HASH_AND_QUOTE_CHECKED_NOT_SEMANTIC_OR_TECHNICAL_VALIDATION",
        "boundary":"All source text from authorized development corpus only. Source exactness is not proof of interpretation; README existence is not functionality, safety or licensing. No independent buyer, paid demand or deployed outcome confirmed.",
    }


def markdown(g:dict[str,Any])->str:
    if g.get("schema")!=OUT:
        raise ValueError("wrong mechanism map schema")
    c=g["coverage"]
    out=["# Practical mechanisms ↔ scientific context ↔ reusable capabilities", "",
         "Eight source-bounded operating-problem dossiers spanning research, engineering, "
         "health, environment, logistics and work. **These are not eight validated commercial opportunities.** "
         "Every publication excerpt was compared with the original text and SHA-256 "
         "in a development-only source dump; every named repo's README was checked "
         "against its saved git blob. Neither step validates scientific entailment "
         "or tests real-world implementation.","",
         f"Source identities checked: {c['primary_source_identities']}; README blobs: "
         f"{c['repo_readme_blobs_verified']}; tested end-to-end integrations: 0; "
         f"verified paying customers: 0.",""]
    for b in g["briefs"]:
        out+=["## "+b["id"].removeprefix("mechanism:").replace("_"," ").title(),"",
             "**Observed or documented problem (source-bounded):** "+b["problem"],"",
             "**Mechanism being investigated:** "+b["mechanism"],"",
             "**Required capability contract:** "+b["capability_contract"],"",
             "**Falsifying/decisive measurement:** "+b["validation"],"",
             "**Original-source context and limitations:**",""]
        for source in b["primary_sources"]:
            out+=["- ["+source["title"][:94]+"]("+source["url"]+") — *"+
                source["quote"].replace("\n"," ")+"*; "+source["scope"]+".",""]
        repo=b["implementation_lead"]
        if repo:
            out+=["**Potential reusable piece:** ["+repo["id"].removeprefix("github:")+"]("+repo["url"]+
                  ") — "+repo["role"]+". README evidence: *"+repo["readme_anchor"].replace("\n"," ")+
                  "*.","","**Unresolved:** "+repo["component_gap"]+"; code rights and commercial demand not reviewed.",""]
        else:
            out+=["**Implementation match:** intentionally unfilled. No credible repo has yet been shown to address the core risk.",""]
        out+=["---",""]
    out+=["## Inference boundary","",
          "This atlas is an evidence-aligned investigative worklist, not independent human semantic adjudication or a causal study. "
          "Research sources include preprints, abstracts and official-site material. Broad source claims "
          "must not be generalized across populations/geographies; designs and trial protocols are not positive outcomes. "
          "No implied paid procurement, current license grant, or proven deployment.","",
          "The next meaningful mapping pass should compare these capability contracts with multiple alternative implementations "
          "per mechanism, inspect actual APIs/engineering tests, and attach independent operator cost/demand evidence. "
          "Do not rank, select or pitch opportunities from this map alone.",""]
    return "\n".join(out)


def main(argv:list[str]|None=None)->int:
    import argparse
    p=argparse.ArgumentParser(prog="cite-refinery-primary-mechanisms")
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--corpus",required=True,type=Path)
    p.add_argument("--readings",required=True,type=Path)
    p.add_argument("--readmes",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--markdown",required=True,type=Path)
    x=p.parse_args(argv)
    def load(path):return json.loads(path.read_text(encoding="utf-8"))
    result=build(load(x.manifest),load(x.corpus),load(x.readings),
                 readme_dir=x.readmes,observed_at=datetime.now(timezone.utc).isoformat())
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    x.markdown.write_text(markdown(result),encoding="utf-8")
    print("Mechanism map:",result["coverage"],flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
