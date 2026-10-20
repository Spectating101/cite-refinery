"""Combine two independently sourced discovery tracks without inventing bridging edges.

Track A: original development-document excerpts -> bounded mechanism -> README-only
component candidate. Track B: published institutional needs -> OSS metadata
candidates. Repo IDs unify only on exact GitHub identity, not word similarity.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def merge(wide:dict[str,Any], procurement:dict[str,Any],
          primary:dict[str,Any]) -> dict[str,Any]:
    if wide.get("schema")!="cite_refinery.opportunity_atlas_network.v1" or \
       procurement.get("schema")!="cite_refinery.connected_opportunity_atlas.v1" or \
       primary.get("schema")!="cite_refinery.primary_mechanism_graph.v1":
        raise ValueError("incompatible track schemas")
    inventory={"github:"+repo["repository"] for area in wide["domain_areas"]
               for repo in area["sampled_repositories"]}
    needs={n["id"]:n for n in procurement["nodes"]}
    graph=dict(needs)
    for node in primary["nodes"]:
        if node["id"] in graph and graph[node["id"]].get("type")!=node.get("type"):
            raise ValueError("conflicting node identity")
        graph[node["id"]]=node
    provenance_edges=[]
    for label,src,required in (
            ("institutional_published_requirements",procurement,"model_candidate_with_exact_source_anchors"),
            ("original_source_mechanisms",primary,None)):
        for e in src["edges"]:
            if e["from"] not in graph or e["to"] not in graph:
                raise ValueError("dangling provenance edge")
            if required is not None and e.get("status")!=required:
                raise ValueError("unreviewed institutional link promoted")
            if e.get("technical_fit_confirmed") is True or \
               e.get("commercial_underconversion_confirmed") is True:
                raise ValueError("unearned technical or commercial claim")
            provenance_edges.append({"layer":label,**e})
    primary_repos={x["implementation_lead"]["id"]
                   for x in primary["briefs"] if x["implementation_lead"] is not None}
    procurement_repos={x["repo_id"] for x in procurement["links"]}
    if any(r not in graph for r in primary_repos|procurement_repos):
        raise ValueError("unrepresented repo in source graph")
    overlaps=sorted(primary_repos&procurement_repos)
    fresh=sorted(primary_repos-inventory)
    return {
        "schema":"cite_refinery.integrated_opportunity_provenance.v1",
        "nodes":sorted(graph.values(),key=lambda x:x["id"]),
        "edges":provenance_edges,
        "inventory_links":{
            "problem_mechanism_repos":sorted(primary_repos),
            "institutional_requirement_repos":sorted(procurement_repos),
            "shared_verified_repository_identities":overlaps,
            "problem_driven_repos_absent_from_topic_search_sample":fresh,
            "cross_track_inferred_edges_created":0,
        },
        "next_work":{
            "source_to_mechanism":"Independent semantic audit of original excerpts and population/outcome scope.",
            "mechanism_to_implementation":"Reproduce capability behavior with real datasets and safety/failure cases.",
            "implementation_to_buyers":"Verify operator need, rights, current procurement rules and paid scope.",
            "cross_track":"Search for procurement needs that actually require the same mechanisms as the original-source cases; do not infer these links by subject keywords.",
        },
        "validated_outcomes":{"end_to_end_technical_systems":0,"contracted_buyers":0,
                              "financial_arbitrage_cases":0,"causal_public_health_outcomes":0},
        "boundary":"Exact source excerpts, README blob checks and notice ID links do not establish causal interpretation or conversion. Disconnected source clusters remain disconnected.",
    }


def markdown(data:dict[str,Any])->str:
    if data.get("schema")!="cite_refinery.integrated_opportunity_provenance.v1":
        raise ValueError("unknown union graph")
    links=data["inventory_links"]
    out=[
        "# Integrated atlas: source-mechanism and institution-implementation tracks","",
        "This is an **unranked** graph of two evidence tracks. "
        "Connections are preserved only when original identity or explicit "
        "source-bound mechanism assessment exists; no semantic gap is silently bridged.","",
        "## A major coverage finding","",
        "Broad topic search missed **"+str(len(links["problem_driven_repos_absent_from_topic_search_sample"]))+
        " out of "+str(len(links["problem_mechanism_repos"]))+
        "** problem-matched repository leads. This is a sampling problem, not proof "
        "that any of those projects is underutilized or technically effective.","",
        "Problem-led repositories absent from prior first-page topical samples:",
        ""]
    out+=["- ["+x.removeprefix("github:")+"](https://github.com/"+
          x.removeprefix("github:")+")" for x in links["problem_driven_repos_absent_from_topic_search_sample"]]
    out+=["","## The exact remaining gap","",
           "Source-mechanism and institution-requirement studies yielded **"+
           str(len(links["shared_verified_repository_identities"]))+
           "** exact shared repo IDs. We did not invent a cross-track solution relationship. "
           "The source graph contains two partially disconnected evidence tracks. "
           "A scientific reading is not proof of a tender requirement, and a published "
           "procurement title is not evidence of a scientific mechanism.","",
           "### Required next connections",""]
    out+=["- **"+k.replace("_"," ").title()+":** "+v
          for k,v in data["next_work"].items()]
    out+=["","No identified paid buyer, demonstrated full technology fit, "
          "or independently proven commercial arbitrage follows from these edges.",""]
    return "\n".join(out)


def main(argv:list[str]|None=None)->int:
    import argparse
    p=argparse.ArgumentParser(prog="cite-refinery-merge-atlas-evidence")
    for x in ("wide","procurement","primary"):
        p.add_argument("--"+x,required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--markdown",required=True,type=Path)
    a=p.parse_args(argv)
    def read(p):return json.loads(p.read_text(encoding="utf-8"))
    result=merge(read(a.wide),read(a.procurement),read(a.primary))
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    a.markdown.write_text(markdown(result))
    print("Integrated provenance:",len(result["nodes"]),"nodes",
          len(result["edges"]),"source-bound relationships; no inferred merges")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
