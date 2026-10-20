"""Source-grounded connection proposals between a published institutional need,
OSS capability metadata, and optional scholarly development source reading.

All proposed edges remain hypothesis-only. Verbatim anchors guarantee the
model referenced a given text, NOT that the relationship actually holds.
"""
from __future__ import annotations
import json
import re
from typing import Any

SCHEMA="cite_refinery.source_connected_input.v1"
FIT={"candidate_component","implementation_category_only","wrong_fit"}
OVERCLAIM=re.compile(
    r"\b(?:proves|guarantees|validated product|fully compliant|"
    r"contract awarded to (?:us|the repository)|"
    r"the buyer (?:will|must) pay|commercially proven|"
    r"confirmed paying customer|no solution exists)\b",re.I)


def text(value:Any,name:str,minimum:int=12,maximum:int=700)->str:
    if not isinstance(value,str):
        raise ValueError(name+" must be text")
    value=" ".join(value.split())
    if not minimum<=len(value)<=maximum:
        raise ValueError(name+" length")
    if OVERCLAIM.search(value):
        raise ValueError(name+" makes unsupported outcome or commercial promise")
    return value


def anchor(value:Any, original:str,name:str)->str:
    quote=text(value,name,minimum=12,maximum=190)
    normal=lambda s:" ".join(s.split()).casefold()
    if normal(quote) not in normal(original):
        raise ValueError(name+" is not an exact source-text excerpt")
    return quote


def prompt(inputs:dict[str,Any])->str:
    if inputs.get("schema")!=SCHEMA:
        raise ValueError("unknown source-bridge input")
    return (
      "You are a skeptical problem/implementation alignment investigator. "
      "You are given genuine published EU procurement notice descriptions, publicly "
      "listed GitHub repository descriptions, and *OPTIONAL* prior model-generated "
      "academic source readings from a small development corpus. "
      "Build only mechanism-justified candidate relationships: "
      "(a) candidate_component: a specific repo functionality could address one "
      "part of a published requirement, not a full solution; "
      "(b) implementation_category_only: same broad category but precise capability "
      "unknown, do not recommend reuse; or "
      "(c) wrong_fit: tempting topical similarity but technically different function. "
      "Avoid force-fitting any repository to a notice. Return ZERO to FOUR links, "
      "with at least one rigorous wrong_fit when necessary. "
      "Each proposed link MUST identify an exact notice ID, exact repo ID, "
      "and a COPY-EXACT, 12-190-character fragment from each source description "
      "as need_anchor and asset_anchor (no paraphrases). "
      "A research ID is optional and ONLY when that scientific statement truly "
      "informs the same mechanism; copy an exact anchor from that statement. "
      "If no appropriate scientific source exists, set research_id and "
      "research_anchor to null. Include which precise technical requirement is "
      "and isn't addressed, a falsifying next test, and what makes transfer "
      "unlikely (jurisdiction, scale, certification, operational support, etc.). "
      "Tender records may be awards, prior information notices, or competitions. "
      "Never call them currently open opportunities, fundable contracts, or money "
      "available to us. NO inferred user adoption, legal rights, or revenues. "
      "Do not use model research readings to establish causal outcome truth. "
      "Return exactly JSON schema: "
      '{"links":[{"need_id":"ted:number","repo_id":"github:owner/repo",'
      '"relation":"candidate_component|implementation_category_only|wrong_fit",'
      '"need_anchor":"exact excerpt from need description",'
      '"asset_anchor":"exact excerpt from repo description",'
      '"research_id":null,"research_anchor":null,'
      '"mechanism":"precise technical why/how",'
      '"limitation":"specific gap or nontransferability",'
      '"next_check":"small concrete source/code/technical test"}]}. '
      "SOURCE INPUT:\n"+json.dumps(inputs,ensure_ascii=False,separators=(",",":"))
    )


def validate(inputs:dict[str,Any], raw:dict[str,Any])->dict[str,Any]:
    if inputs.get("schema")!=SCHEMA:
        raise ValueError("bad input")
    if not isinstance(raw,dict) or not isinstance(raw.get("links"),list) or len(raw["links"])>4:
        raise ValueError("expected <=4 links")
    needs={n["id"]:n for n in inputs["needs"]}
    repos={r["id"]:r for r in inputs["repo_assets"]}
    research={r["id"]:r for r in inputs["research"]}
    found=[]
    rejected=[]
    seen=set()
    for i,link in enumerate(raw["links"]):
        try:
            if not isinstance(link,dict):
                raise ValueError("non-object link")
            need=needs.get(link.get("need_id"))
            repo=repos.get(link.get("repo_id"))
            if not need or not repo:
                raise ValueError("source not in bounded input")
            pair=(need["id"],repo["id"])
            if pair in seen:
                raise ValueError("duplicate source pair")
            seen.add(pair)
            if link.get("relation") not in FIT:
                raise ValueError("invalid link type")
            if not need.get("description") or not repo.get("description"):
                raise ValueError("no described source content")
            a=anchor(link.get("need_anchor"),need["description"],"need_anchor")
            b=anchor(link.get("asset_anchor"),repo["description"],"asset_anchor")
            research_id=link.get("research_id")
            if research_id is not None:
                if research_id not in research:
                    raise ValueError("research reference not found in development sources")
                research_quote=anchor(link.get("research_anchor"),research[research_id]["statement"],"research_anchor")
                research_ref=research[research_id]["source_url"]
            else:
                if link.get("research_anchor") is not None:
                    raise ValueError("uncited research excerpt not accepted")
                research_quote=None
                research_ref=None
            fields={k:text(link.get(k),k,minimum=25,maximum=650) for k in ("mechanism","limitation","next_check")}
            found.append({
                "id":"bridge:"+inputs["macro"]+":"+str(i+1),
                "macro":inputs["macro"],
                "need_id":need["id"],"need_url":need["source_url"],
                "need_title":need["title"],"notice_lifecycle":need["lifecycle_category"],
                "need_excerpt":a,
                "repo_id":repo["id"],"repo_url":repo["url"],
                "repo_excerpt":b,
                "relation":link["relation"],
                "research_id":research_id,"research_url":research_ref,
                "research_excerpt":research_quote,
                **fields,
                "reasoning_authority":"llm_proposed_source_anchored_relation_requires_human_review",
                "source_quote_existence_checked":True,
                "published_notice_is_not_confirmed_active_tender":True,
                "repository_rights_or_deployment_verified":False,
                "scientific_causality_verified":False,
                "buyer_contract_established":False,
            })
        except (ValueError,TypeError) as exc:
            rejected.append({"candidate":i+1,"reason":str(exc)})
    return {
        "schema":"cite_refinery.source_connected_bridges.v1",
        "macro":inputs["macro"],"links":found,"rejected_candidates":rejected,
        "status":"mechanism_interpretations_for_independent_review",
        "boundary":"Exact excerpt checks confirm text membership only; no evidence of technical equivalence, current bidding eligibility, contract value, or commercial underconversion.",
    }
