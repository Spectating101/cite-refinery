"""Generate a source-linked, unranked evidence overlay: no economic score.

Inputs are *model-proposed, exact-anchor-checked* relationships. Outputs
preserve wrong-fit/rejection signals alongside possible components.
"""
from __future__ import annotations

from collections import Counter,defaultdict
import json
import re
from pathlib import Path
from typing import Any

def assemble(network:dict[str,Any], requests:list[dict[str,Any]],
             batches:list[dict[str,Any]],
             readme_reviews:dict[str,Any]|None=None)->dict[str,Any]:
    if network.get("schema")!="cite_refinery.opportunity_atlas_network.v1":
        raise ValueError("base atlas required")
    known={x["macro"]:x for x in requests}
    if not all(x.get("schema")=="cite_refinery.source_connected_input.v1" for x in requests):
        raise ValueError("source inputs required")
    documented={}
    if readme_reviews is not None:
        if readme_reviews.get("schema")!="cite_refinery.repo_readme_scoped_checks.v1":
            raise ValueError("unsupported documentation review")
        for r in readme_reviews.get("reviews",[]):
            if (r["repo_id"] in documented or
                r.get("review_state")!="readme_scoped_evidence_not_execution" or
                not r.get("blob_sha")):
                raise ValueError("invalid or duplicate repository documentation evidence")
            documented[r["repo_id"]]=r
    links=[]
    by_macro={}
    rejects=[]
    seen_macros=set()
    for b in batches:
        if b.get("schema")!="cite_refinery.source_connected_bridges.v1":
            raise ValueError("unknown bridge packet")
        macro=b.get("macro")
        if macro in seen_macros or macro not in known:
            raise ValueError("duplicated/unknown sector")
        seen_macros.add(macro)
        allowed_needs={x["id"] for x in known[macro]["needs"]}
        allowed_assets={x["id"] for x in known[macro]["repo_assets"]}
        for l in b["links"]:
            if (l.get("macro")!=macro or l["need_id"] not in allowed_needs or
                    l["repo_id"] not in allowed_assets or
                    l.get("reasoning_authority")!="llm_proposed_source_anchored_relation_requires_human_review" or
                    l.get("buyer_contract_established") is not False or
                    l.get("repository_rights_or_deployment_verified") is not False):
                raise ValueError("non-source-bounded or improperly promoted relation")
            review=documented.get(l["repo_id"])
            augmented=dict(l)
            augmented["repository_documentation_check"] = (
                {"source_url":review["source_url"],"blob_sha":review["blob_sha"],
                 "capability_summary":review["description"],
                 "not_demonstrated":review["not_demonstrated"],
                 "review_state":review["review_state"]}
                if review and l["relation"]=="candidate_component" else None)
            augmented["unverified_negative_feature_assertion"] = bool(re.search(
                r"\b(?:lacks?|cannot|does not|completely|exclusively|without any|missing|not present)\b",
                l["limitation"],re.I))
            links.append(augmented)
        rejects.extend({"macro":macro,**x} for x in b["rejected_candidates"])
        used={x["need_id"] for x in b["links"]}
        by_macro[macro]={
            "source_need_count":len(known[macro]["needs"]),
            "source_repo_count":len(known[macro]["repo_assets"]),
            "development_research_count":len(known[macro]["research"]),
            "proposed_links":sum(l["relation"]!="wrong_fit" for l in b["links"]),
            "explicit_wrong_fits":sum(l["relation"]=="wrong_fit" for l in b["links"]),
            "published_requirements_without_proposed_link":[
                n["id"] for n in known[macro]["needs"] if n["id"] not in used
            ],
            "rejections":len(b["rejected_candidates"]),
            "caveat":"Unlinked in a bounded source selection is not evidence of a global absence.",
        }
    if not seen_macros:
        raise ValueError("no evaluated source fields")
    nodes={}
    edges=[]
    for l in links:
        needid=l["need_id"]; repoid=l["repo_id"]
        nodes.setdefault(needid,{
            "id":needid, "layer":"documented_institutional_requirement",
            "source_url":l["need_url"],"label":l["need_title"],
            "status":"published_notice_description_not_verified_active_or_eligible",
        })
        nodes.setdefault(repoid,{
            "id":repoid,"layer":"implementation_capability_listing",
            "source_url":l["repo_url"],"label":l["repo_id"].removeprefix("github:"),
            "status":"repository_description_not_code_or_deployment_verified",
        })
        edges.append({
            "from":repoid,"to":needid,"relation":l["relation"],
            "status":"model_candidate_with_exact_source_anchors",
            "evidence_refs":[l["repo_url"],l["need_url"]],
            "technical_fit_confirmed":False,
            "commercial_underconversion_confirmed":False,
        })
        if l.get("research_id"):
            academicid="academic:"+l["research_id"]
            nodes.setdefault(academicid,{
                "id":academicid,"layer":"scientific_reading",
                "source_url":l["research_url"],"label":l["research_id"],
                "status":"previous_model_source_reading_not_original_evidence_reverified",
            })
            edges.append({
                "from":academicid,"to":needid,"relation":"POSSIBLY_RELEVANT_MECHANISM",
                "status":"model_candidate_with_exact_source_anchors",
                "evidence_refs":[l["research_url"],l["need_url"]],
                "technical_fit_confirmed":False,
                "commercial_underconversion_confirmed":False,
            })
    return {
        "schema":"cite_refinery.connected_opportunity_atlas.v1",
        "base_atlas_observed_at":network["snapshot_observed_at"],
        "links":links,"by_macro":by_macro,"rejected_model_candidates":rejects,
        "nodes":sorted(nodes.values(),key=lambda x:x["id"]),
        "edges":edges,
        "counts":{
            "assessed_macros":len(seen_macros),
            "source_anchored_hypothesis_links":len(links),
            "candidate_components":sum(l["relation"]=="candidate_component" for l in links),
            "category_only":sum(l["relation"]=="implementation_category_only" for l in links),
            "wrong_fits":sum(l["relation"]=="wrong_fit" for l in links),
            "research_attachments":sum(bool(l["research_id"]) for l in links),
            "repo_readmes_inspected_for_component_leads":sum(
                bool(l["repository_documentation_check"]) for l in links),
            "validated_technical_integrations":0,
            "verified_buyer_commitments":0,
        },
        "authority":"cross_evidence_hypotheses_not_accepted_graph_or_commercial_proof",
        "boundary":"Source quote presence verified; implications and compatibility not independently checked. No active tender or buyer eligibility verified; no third-party code executed. Sealed research holdout untouched.",
    }


def markdown(packet:dict[str,Any])->str:
    if packet.get("schema")!="cite_refinery.connected_opportunity_atlas.v1":
        raise ValueError("unsupported connected map")
    c=packet["counts"]
    out=[
        "# Connected Opportunity Atlas — sources → mechanisms → implementation leads",
        "",
        "This is the **connection layer** between existing atlas discovery inventories. "
        "Every relationship below is an AI-proposed, exact-description-anchored hypothesis. "
        "It is **not** proven interoperability, product market fit, a current procurement, "
        "a verified scientific causal finding or a target recommendation.",
        "",
        "## What was and wasn't connected",
        "",
        f"Across {c['assessed_macros']} broad fields, the source linking pass proposed "
        f"{c['candidate_components']} possible components, "
        f"{c['category_only']} category-only alignments and "
        f"{c['wrong_fits']} explicit technical mismatches. "
        "All have zero independently validated integrations and zero buyer commitments.",
        "",
        "## Source-anchored relationships, including exclusions",
        "",
    ]
    for macro,data in sorted(packet["by_macro"].items()):
        out.extend(["### "+macro.replace("_"," ").title(),"",
            f"Bounded sources: {data['source_need_count']} published requirements; "
            f"{data['source_repo_count']} repository descriptions; "
            f"{data['development_research_count']} optional model-generated research readings.",""])
        results=[l for l in packet["links"] if l["macro"]==macro]
        if not results:
            out.extend(["No defensible cross-source connection survived. "
                        "This means 'unconnected in this sample', not 'no solution exists'.",""])
        for l in results:
            out.extend([
                "**"+l["relation"].replace("_"," ").title()+"** — "
                +"["+l["need_title"][:140].replace("|","/")+"]("+l["need_url"]+")"
                +" ↔ ["+l["repo_id"].removeprefix("github:")+"]("+l["repo_url"]+")",
                "",
                "Mechanism: "+l["mechanism"],
                "",
                "Important mismatch: "+l["limitation"],
                "",
                "Next verification: "+l["next_check"],
                "",
                "Anchors: institutional description: *"+l["need_excerpt"].replace("\n"," ")[:190]
                +"*; repository description: *"+l["repo_excerpt"].replace("\n"," ")[:190]+"*.",
                "",
                "Notice lifecycle: "+l["notice_lifecycle"]
                +". Source text match is not a current tender or an implementation result.",
                "",
            ])
            if l.get("repository_documentation_check"):
                chk=l["repository_documentation_check"]
                out.extend(["Repository documentation: [README at checked revision]("+chk["source_url"]+
                            ") describes "+chk["capability_summary"]+
                            " **Not demonstrated:** "+chk["not_demonstrated"]+"", ""])
            if l.get("unverified_negative_feature_assertion"):
                out.extend(["**Caution:** The mismatch claims that the asset lacks or cannot perform something. "
                            "That is NOT independently established by its README and needs a code-level check.", ""])
            if l["research_id"]:
                out.extend([
                    "Optional scientific context: ["+l["research_id"]+"]("+l["research_url"]+"), "
                    "from a previously unverified source-reading summary; not independently entailed.",
                    "",
                ])
        if data["published_requirements_without_proposed_link"]:
            out.extend(["Unlinked published requirements in this bounded comparison: "+
                ", ".join(data["published_requirements_without_proposed_link"]), ""])
        out.append("---")
        out.append("")
    out.extend([
        "## Explicit limitations and next mapping layer",
        "",
        "The public GitHub inventory was semantically audited on a subset only. "
        "Repo metadata cannot demonstrate a working feature. Official TED notice "
        "descriptions document *published requirements* but not an active tender or bidder eligibility. "
        "The small academic source selection is not comprehensive and its paraphrases were previously "
        "generated by another model.",
        "",
        "Next: sample original technical docs or a small functional integration for "
        "each type of relation, expand primary problem data beyond public procurement, "
        "and map real institutional budget/maintainer constraints. "
        "**Do not prioritize a single market or start sending pitches from these candidate edges.**",
        "",
    ])
    return "\n".join(out)


def main(argv:list[str]|None=None)->int:
    import argparse
    parser=argparse.ArgumentParser(prog="cite-refinery-connected-atlas")
    parser.add_argument("--atlas",required=True,type=Path)
    parser.add_argument("--inputs",required=True,type=Path)
    parser.add_argument("--results",required=True,type=Path)
    parser.add_argument("--readme-reviews",type=Path)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--markdown",required=True,type=Path)
    options=parser.parse_args(argv)
    def load(p:Path):return json.loads(p.read_text(encoding="utf-8"))
    ins=[load(p) for p in sorted(options.inputs.glob("*.json"))]
    res=[load(p) for p in sorted(options.results.glob("*_source_connections.json"))]
    pack=assemble(load(options.atlas),ins,res,
                  load(options.readme_reviews) if options.readme_reviews else None)
    options.output.write_text(json.dumps(pack,ensure_ascii=False,indent=2)+"\n")
    options.markdown.write_text(markdown(pack))
    print("Connected map",pack["counts"],flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
