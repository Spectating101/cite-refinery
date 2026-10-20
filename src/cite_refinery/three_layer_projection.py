"""A single, read-only THREE-layer atlas projection from existing evidence products.

Practical = operating problems or published institutional requirements.
Academic = source-bounded explanatory mechanisms (NOT independently verified science).
Implementation = documented software/program capability leads (NOT working solutions).

Evidence documents remain citations/provenance attached to these layers, NOT a
fourth conceptual layer. Conversion is an analysis of these relationships, not
a fourth conceptual layer. No invented links and no elevation of hypotheses.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

LAYERS=("practical","academic","implementation")
SCHEMA="cite_refinery.three_layer_atlas_projection.v1"


def project(primary:dict[str,Any],procurement:dict[str,Any])->dict[str,Any]:
    if primary.get("schema")!="cite_refinery.primary_mechanism_graph.v1":
        raise ValueError("requires original-source mechanism dossiers")
    if procurement.get("schema")!="cite_refinery.connected_opportunity_atlas.v1":
        raise ValueError("requires source-connected institutional requirements")
    nodes:dict[str,dict[str,Any]]={}
    edges:list[dict[str,Any]]=[]
    questions=[]
    seen=set()
    primary_identity={n["id"] for n in primary.get("nodes",[]) if isinstance(n,dict)}
    institutional_identity={n["id"] for n in procurement.get("nodes",[]) if isinstance(n,dict)}
    if not primary_identity or not institutional_identity:
        raise ValueError("source graphs cannot be empty")

    def node(id:str,layer:str,statement:str,kind:str,*,sources:list[dict[str,Any]],
             authority:str,limitations:str)->None:
        if layer not in LAYERS:
            raise ValueError("fourth conceptual layer not accepted")
        if not id or not isinstance(statement,str) or not statement:
            raise ValueError("invalid typed node")
        if id in nodes:
            existing=nodes[id]
            if existing["layer"]!=layer:
                raise ValueError("conflicting conceptual layer for exact identity")
            # Multiple discovery routes can name the same repo; do not treat this
            # as evidence that two different practical problems are related.
            for source in sources:
                if source not in existing["provenance"]:
                    existing["provenance"].append(source)
            return
        nodes[id]={"id":id,"layer":layer,"kind":kind,"statement":statement,
                   "provenance":sources,"authority":authority,"limitations":limitations,
                   "validated_technical_fit":False,"verified_commercial_value":False}

    def edge(a:str,b:str,relation:str,*,status:str,source_ref:str,
             verified:bool=False)->None:
        if a not in nodes or b not in nodes:
            raise ValueError("missing typed endpoint")
        if verified:
            raise ValueError("source product cannot assert verified compatibility")
        if (a,b,relation) in seen:
            raise ValueError("duplicate source-specific edge")
        seen.add((a,b,relation))
        edges.append({
            "from":a,"to":b,"relation":relation,
            "status":status,"source_ref":source_ref,
            "technical_fit_verified":False,"causal_effect_verified":False,
            "buyer_commitment_verified":False,
        })

    for brief in primary["briefs"]:
        mechanism_id=brief["id"]
        if not mechanism_id.startswith("mechanism:") or mechanism_id not in primary_identity:
            raise ValueError("unknown scientific mechanism identity in source graph")
        practical_id="problem:"+mechanism_id.removeprefix("mechanism:")
        support=[{"url":s["url"],"source_id":s["id"],"sha256":s["original_sha256"],
                  "evidence_role":"original_excerpt_not_entailment_review",
                  "quote":s["quote"]} for s in brief["primary_sources"]]
        if not support:
            raise ValueError("mechanism with no source support")
        node(practical_id,"practical",brief["problem"],"operating_problem",sources=support,
             authority="investigator_problem_framing_requires_field_review",
             limitations="No independent operational cost or buyer demand demonstrated.")
        node(mechanism_id,"academic",brief["mechanism"],"explanatory_hypothesis",sources=support,
             authority="primary_source_quotes_checked_not_scientific_entailment",
             limitations="Source authenticity is not independent evaluation of this explanation.")
        edge(practical_id,mechanism_id,"EXPLAINED_BY_CANDIDATE",
             status="source_anchored_investigator_hypothesis",
             source_ref="primary_mechanism_network")
        tech=brief["implementation_lead"]
        if tech:
            if tech["id"] in nodes and nodes[tech["id"]]["layer"]!="implementation":
                raise ValueError("implementation identity collision")
            node(tech["id"],"implementation",
                 "Candidate: "+tech["role"],"repository_capability",
                 sources=[{"url":tech["readme_url"],"git_blob_sha":tech["git_blob_sha"],
                           "quote":tech["readme_anchor"],
                           "evidence_role":"readme_blob_checked_not_executed"}],
                 authority="readme_metadata_only",
                 limitations=tech["component_gap"])
            edge(mechanism_id,tech["id"],"POSSIBLE_PARTIAL_IMPLEMENTATION",
                 status="readme_supported_untested",
                 source_ref=tech["readme_url"])
        else:
            questions.append({"root":practical_id,"missing_layer":"implementation",
                              "reason":"No source-grounded technical implementation proposed",
                              "not_global_absence":True})

    for l in procurement["links"]:
        practical_id=l["need_id"]
        if not practical_id.startswith("ted:") or practical_id not in institutional_identity:
            raise ValueError("published requirements must retain known notice identity")
        source={"url":l["need_url"],"quote":l["need_excerpt"],
                "evidence_role":"published_notice_not_verified_currently_open",
                "notice_lifecycle":l["notice_lifecycle"]}
        node(practical_id,"practical",l["need_title"],"institutional_requirement",
             sources=[source],authority="published_notice_source_not_procurement_eligibility",
             limitations="Tender may be expired, awarded, or ineligible for our operations.")
        rid=l["repo_id"]
        if not rid.startswith("github:") or rid not in institutional_identity:
            raise ValueError("implementation needs known exact repo identity")
        node(rid,"implementation",l["repo_id"].removeprefix("github:"),
             "repository_capability",
             sources=[{"url":l["repo_url"],"quote":l["repo_excerpt"],
                       "evidence_role":"public_repository_description_not_code_reviewed"}],
             authority="candidate_repository_metadata",
             limitations=l["limitation"])
        relation={
            "candidate_component":"POSSIBLE_PARTIAL_IMPLEMENTATION",
            "implementation_category_only":"CATEGORY_OVERLAP_ONLY",
            "wrong_fit":"LIKELY_WRONG_FIT",
        }.get(l["relation"])
        if relation is None:
            raise ValueError("unrecognized source-to-capability interpretation")
        edge(practical_id,rid,relation,status="source_anchored_model_hypothesis",
             source_ref=l["need_url"])
        # Absolutely no academic source is invented for these institutional
        # requirements; none was justified in the earlier source-bounded trial.
        if l["research_id"]:
            raise ValueError("source product unexpectedly contains academic link; review before promoting")
        questions.append({"root":practical_id,"missing_layer":"academic",
                          "reason":"No established matching scientific explanation attached to this institutional requirement",
                          "not_global_absence":True})

    neighbors=defaultdict(list)
    for e in edges:
        neighbors[e["from"]].append(e)
    indexed={}
    for practical in sorted((n for n in nodes.values() if n["layer"]=="practical"),
                            key=lambda n:n["id"]):
        direct=neighbors[practical["id"]]
        academic=[nodes[x["to"]] for x in direct if nodes[x["to"]]["layer"]=="academic"]
        implementation=[]
        for e in direct:
            if nodes[e["to"]]["layer"]=="implementation":
                implementation.append({"node":nodes[e["to"]],"relation":e["relation"],
                                       "status":e["status"]})
            if nodes[e["to"]]["layer"]=="academic":
                for downstream in neighbors[e["to"]]:
                    if nodes[downstream["to"]]["layer"]=="implementation":
                        implementation.append({"node":nodes[downstream["to"]],
                                               "relation":downstream["relation"],
                                               "status":downstream["status"]})
        indexed[practical["id"]]={
            "root":practical["id"],"academic_nodes":[x["id"] for x in academic],
            "implementation_links":[{"id":x["node"]["id"],"relation":x["relation"],
                                     "status":x["status"]} for x in implementation],
            "three_layers_represented":bool(academic and implementation),
            "end_to_end_validated":False,
            "buyer_validated":False,
            "gaps":[x for x in questions if x["root"]==practical["id"]],
        }
    for p in indexed.values():
        if not p["academic_nodes"] and not any(
            x["missing_layer"]=="academic" for x in p["gaps"]
        ):
            p["gaps"].append({"root":p["root"],"missing_layer":"academic",
                              "reason":"Not represented in bounded graph","not_global_absence":True})
        if not p["implementation_links"] and not any(
            x["missing_layer"]=="implementation" for x in p["gaps"]
        ):
            p["gaps"].append({"root":p["root"],"missing_layer":"implementation",
                              "reason":"No linked technical implementation","not_global_absence":True})
    counts=Counter(n["layer"] for n in nodes.values())
    return {
        "schema":SCHEMA,"layers":list(LAYERS),
        "nodes":sorted(nodes.values(),key=lambda n:n["id"]),
        "edges":edges,"problem_views":indexed,
        "coverage":{
            "practical":counts["practical"],
            "academic":counts["academic"],
            "implementation":counts["implementation"],
            "problems_with_all_three_layers_represented":sum(
                p["three_layers_represented"] for p in indexed.values()),
            "validated_end_to_end_solutions":0,
            "confirmed_paying_customers":0,
            "neutral_source_nodes_as_fourth_layer":0,
        },
        "safety":{
            "read_only":True,"candidate_edges_only":True,
            "no_cross_document_keyword_join":True,"no_procurement_to_academic_join_inferred":True,
            "not_merged_into_persistent_project_graph":True,
            "note":"A populated path is NOT a verified solution. Sources are provenance attached to the three layers, not a fourth layer.",
        },
    }


def explain(atlas:dict[str,Any],problem_id:str)->dict[str,Any]:
    if atlas.get("schema")!=SCHEMA:
        raise ValueError("not a projected three-layer atlas")
    if problem_id not in atlas["problem_views"]:
        raise KeyError("unknown practical problem")
    view=atlas["problem_views"][problem_id]
    lookup={n["id"]:n for n in atlas["nodes"]}
    return {
        "schema":"cite_refinery.three_layer_explanation.v1",
        "practical":lookup[problem_id],
        "academic":[lookup[x] for x in view["academic_nodes"]],
        "implementations":[{"asset":lookup[x["id"]],"relation":x["relation"],
                            "status":x["status"]} for x in view["implementation_links"]],
        "gaps":view["gaps"],
        "three_layers_represented":view["three_layers_represented"],
        "end_to_end_validated":False,"buyer_validated":False,
        "boundary":"Source-bounded interpretation, not an independently validated solution or arbitrage.",
    }



def render_markdown(atlas:dict[str,Any],*,max_examples:int=10)->str:
    if atlas.get("schema")!=SCHEMA:
        raise ValueError("not a unified three-layer view")
    if not 1 <= max_examples <= 30:
        raise ValueError("bounded presentation required")
    views=atlas["problem_views"]
    by_id={n["id"]:n for n in atlas["nodes"]}
    coverage=atlas["coverage"]
    lines=[
        "# One graph, three evidence layers", "",
        "**Practical reality ⇄ Academic explanations ⇄ Implementations/solutions**",
        "",
        "The relationships below form **one typed query view**, not two independent "
        "research networks. Evidence sources are attached as provenance, not "
        "promoted to a fourth conceptual layer. Commercial conversion is an "
        "analysis performed on this graph, not another fundamental layer.", "",
        "## Coverage of current bounded inputs", "",
        "| Layer | Source-bounded records |",
        "|---|---:|",
        "| Practical | "+str(coverage["practical"])+" |",
        "| Academic (proposed mechanisms) | "+str(coverage["academic"])+" |",
        "| Implementations (candidate capabilities) | "+str(coverage["implementation"])+" |",
        "",
        f"All three layers are represented for {coverage['problems_with_all_three_layers_represented']} "
        "problem records. This **does not establish** that the proposed explanations or "
        "capabilities are correct. There are no independently validated end-to-end "
        "solutions or confirmed paying customers in this dataset.", "",
        "## Readable problem paths", "",
    ]
    ordered=sorted(views,
        key=lambda i:(not views[i]["three_layers_represented"],i))
    if len(ordered)>max_examples:
        ordered=ordered[:max_examples-2]+[
            next((i for i in ordered[max_examples-2:] if i.startswith("ted:")),
                 ordered[max_examples-2]),
            next((i for i in ordered[max_examples-2:] if i=="problem:gig_worker_algorithmic_harm"),
                 ordered[max_examples-1]),
        ]
        ordered=list(dict.fromkeys(ordered))
    for id in ordered:
        v=views[id]
        lines+=["### "+id.replace("_"," ").replace("problem:","Problem: ").replace("ted:","Published notice: "), "",
                "**Practical:** "+by_id[id]["statement"], ""]
        if v["academic_nodes"]:
            lines+=["**Academic (hypothesis, not independent proof):** "+
                    " / ".join(by_id[m]["statement"] for m in v["academic_nodes"]),"",]
        else:
            lines+=["**Academic:** no source-bounded mechanism attached in this sample.",""]
        if v["implementation_links"]:
            lines+=["**Implementation candidates / exclusions:**"]
            for e in v["implementation_links"]:
                label=by_id[e["id"]]["statement"]
                lines.append("- "+e["id"]+" ("+e["relation"]+"): "+label)
            lines.append("")
        else:
            lines+=["**Implementation:** no linked capability candidate in this sample.",""]
        lines+=["**Three layers represented:** "+("yes" if v["three_layers_represented"] else "no")+
                "; **end-to-end validated:** no; **buyer validated:** no.", ""]
        if v["gaps"]:
            lines+=["**Evidence gaps:** "+"; ".join(g["reason"] for g in v["gaps"]),""]
    lines+=["## Architecture boundary","",
             "This projection is **read-only** and does not yet migrate the separate "
             "source products into a transactionally backed persistent SemanticGraph. "
             "The original native store still permits neutral nodes and uses program "
             "for solution/implementation. The next ingestion gate should normalize "
             "those terms, preserve source provenance and require human approval "
             "before any status upgrade.","",
             "Some real connections are absent. The output must not infer a "
             "scientific link to a published requirement solely because the "
             "institution and an unrelated research abstract share words.",
             ""]
    return "\n".join(lines)



def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(prog="cite-refinery-three-layer")
    parser.add_argument("--primary",required=True,type=Path)
    parser.add_argument("--institutional",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--problem-id")
    parser.add_argument("--markdown",type=Path)
    args=parser.parse_args(argv)
    def read(path):return json.loads(path.read_text(encoding="utf-8"))
    atlas=project(read(args.primary),read(args.institutional))
    output=explain(atlas,args.problem_id) if args.problem_id else atlas
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if args.markdown:
        args.markdown.write_text(render_markdown(atlas),encoding="utf-8")
    print(atlas["coverage"],flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
