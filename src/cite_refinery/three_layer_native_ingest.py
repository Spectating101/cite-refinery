"""Export a read-only three-layer atlas as a CANDIDATE-ONLY native graph packet.

Export does not mutate persistence; use graph-review's digest-bound approval to
write the new packet. The existing native program layer represents implementation.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "cite_refinery.three_layer_atlas_projection.v1"
RELATIONS = {
    "EXPLAINED_BY_CANDIDATE",
    "POSSIBLE_PARTIAL_IMPLEMENTATION",
    "CATEGORY_OVERLAP_ONLY",
    "LIKELY_WRONG_FIT",
}
KIND = {"operating_problem":"problem_claim",
        "institutional_requirement":"requirement",
        "explanatory_hypothesis":"mechanism",
        "repository_capability":"repository"}

def as_packet(atlas:dict[str,Any],project_id:str)->dict[str,Any]:
    if atlas.get("schema")!=SCHEMA or atlas.get("layers")!=["practical","academic","implementation"]:
        raise ValueError("must be a three-layer projection")
    if not isinstance(project_id,str) or not project_id.strip():
        raise ValueError("an existing project ID is required")
    if not atlas.get("safety",{}).get("read_only") or any(
        atlas.get("coverage",{}).get(k)!=0 for k in
        ("validated_end_to_end_solutions","confirmed_paying_customers")):
        raise ValueError("atlas claims unsupported authority")
    nodes=[]
    identity=set()
    for row in atlas["nodes"]:
        key=row["id"]
        layer=row["layer"]
        if (key in identity or layer not in {"practical","academic","implementation"} or
            row.get("validated_technical_fit") is not False or
            row.get("verified_commercial_value") is not False or
            row.get("kind") not in KIND):
            raise ValueError("invalid or promoted node")
        identity.add(key)
        prov=row.get("provenance",[])
        if not isinstance(prov,list):
            raise ValueError("invalid provenance")
        urls=sorted({s["url"] for s in prov if isinstance(s,dict)
            and isinstance(s.get("url"),str) and s["url"].startswith("https://")})
        nodes.append({
            "key":key,"statement":row["statement"],"kind":KIND[row["kind"]],
            "layer":"program" if layer=="implementation" else layer,
            "source_refs":urls,
            "tags":["source_lead_only","not_an_evidence_claim"],
            "provenance":{"original_layer":layer,"original_authority":row["authority"],
                          "source_details":prov,"source_limitations":row["limitations"],
                          "boundary":"Read-only atlas record; scientific and technical claims unreviewed"},
        })
    edges=[]
    seen=set()
    for row in atlas["edges"]:
        a,b,rel=row.get("from"),row.get("to"),row.get("relation")
        if (a not in identity or b not in identity or rel not in RELATIONS or
            row.get("technical_fit_verified") is not False or
            row.get("causal_effect_verified") is not False or
            row.get("buyer_commitment_verified") is not False or
            (a,b,rel) in seen):
            raise ValueError("invalid, duplicate, or promoted relationship")
        seen.add((a,b,rel))
        edges.append({
            "source":a,"target":b,"relation":rel,
            "status":"not_established" if rel=="LIKELY_WRONG_FIT" else "candidate",
            "tags":["source_lead_only","not_an_evidence_claim"],
            "evidence_refs":([row["source_ref"]] if isinstance(row.get("source_ref"),str)
                and row["source_ref"].startswith("https://") else []),
            "provenance":{"original_status":row["status"],
                "boundary":"Candidate mechanism connection, not causal proof or working implementation"},
        })
    return {
        "schema":"cite_refinery.semantic_graph.v1",
        "project_id":project_id,
        "source_system":"three_layer_atlas_candidate_import_v1",
        "clusters":[],"nodes":nodes,"edges":edges,
        "conversion_metadata":{
            "accepted_scientific_claims":0,"accepted_program_outcomes":0,
            "commercial_revenue_verified":0,
            "boundary":"No automatic status upgrades or scientific validations",
        },
    }

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(prog="cite-refinery-three-layer-native-packet")
    p.add_argument("--atlas",type=Path,required=True)
    p.add_argument("--project-id",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args(argv)
    packet=as_packet(json.loads(args.atlas.read_text(encoding="utf-8")),args.project_id)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(packet,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Candidate-only packet: {len(packet['nodes'])} nodes, {len(packet['edges'])} edges; not applied")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
