"""Provisional emergent map -> neutral Cite-Refinery graph packet.

The graph is an inspectable hypothesis map, not an empirical knowledge base.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from .app import CiteRefinery
from .semantic import SemanticGraph

def _key(kind,name):return kind+"-"+hashlib.sha256(name.encode()).hexdigest()[:16]

def packet(atlas,provisional):
    if atlas.get("schema")!="cite_refinery.open_corpus_atlas.v1" or provisional.get("schema")!="cite_refinery.open_corpus_provisional_map.v1":
        raise ValueError("Need the completed full map and valid atlas")
    readings={r["source_id"]:r for r in provisional["readings"]}
    if atlas["mapped_source_count"]!=len(readings):raise ValueError("Atlas source count mismatch")
    nodes=[];edges=[];keyed={}
    for r in readings.values():
        key=_key("raw_source",r["source_id"]+r["source_sha256"])
        keyed[r["source_id"]]=key
        nodes.append({
            "key":key,"statement":r["statement"],
            "kind":"source","layer":"neutral",
            "tags":["corpus_dump_source","role_candidate",r["role"],r["fit"]],
            "source_refs":[r["source_url"]],
            "provenance":{"source_id":r["source_id"],
                          "passage_sha256":r["source_sha256"],
                          "exact_quote_sha256":r["quote_sha256"],
                          "source_role":"unverified_"+r["role"],
                          "caveat":r["caveat"],
                          "boundary":"Exact excerpt checks do not independently prove source claims."}})
    area_keys={}
    for domain in atlas["domains"]:
        if any(sid not in readings for sid in domain["source_ids"]):
            raise ValueError("Unknown atlas source")
        key=_key("emergent_problem_area",domain["label"])
        area_keys[domain["label"]]=key
        nodes.append({
            "key":key,"statement":domain["label"]+": "+domain["problem_node"],
            "kind":"concept","layer":"neutral",
            "tags":["emergent_problem_area","source_grounded_candidate"],
            "source_refs":[readings[s]["source_url"] for s in domain["source_ids"]],
            "provenance":{"measurement_node":domain["measurement_node"],
                          "intervention_node":domain["intervention_node"],
                          "evidence_limit":domain["evidence_limit"],
                          "boundary":"Model-defined domain, not vetted semantic gold."}})
        for sid in domain["source_ids"]:
            if sid not in keyed:raise ValueError("Unknown atlas source")
            edges.append({"source":keyed[sid],"target":key,
                          "relation":"CONTEXT_FOR",
                          "status":"candidate" if readings[sid]["fit"]=="relevant" else "unresolved",
                          "evidence_refs":[readings[sid]["source_url"]],
                          "provenance":{"candidate_role":readings[sid]["role"],
                                        "boundary":"Source supplies topical context, not accepted proof."}})
        qid=_key("open_map_gap",domain["label"]+domain["evidence_limit"])
        nodes.append({
            "key":qid,"statement":"Unresolved: "+domain["evidence_limit"][:1300],
            "kind":"research_question","layer":"neutral",
            "tags":["coverage_gap","not_evidence_of_absence"],
            "source_refs":[],
            "provenance":{"questions":domain["questions"],
                          "boundary":"Missing from this bounded dump, not absent in the universe."}})
        edges.append({"source":key,"target":qid,"relation":"REQUIRES",
                      "status":"unresolved",
                      "provenance":{"boundary":"Research gap; no measured result."}})
    for rel in atlas["cross_domain_links"]:
        if rel["from_label"] not in area_keys or rel["to_label"] not in area_keys:
            raise ValueError("Unknown semantic area relation")
        edges.append({"source":area_keys[rel["from_label"]],
                      "target":area_keys[rel["to_label"]],
                      "relation":"RELATED_TO","status":"unresolved",
                      "provenance":{"candidate_relation":rel["relation"],
                                    "justification":rel["rationale"],
                                    "boundary":"Possible analogy only, not causal or replicated result."}})
    return {"schema":"cite_refinery.semantic_graph.v1",
            "source_system":"unclassified_corpus_exploration_v1",
            "clusters":[],"nodes":nodes,"edges":edges,
            "conversion_metadata":{"accepted_scientific_conclusions":0,
                                   "same_family_model_generated":True,
                                   "all_sources_retained":True,
                                   "boundary":"Source abstracts and institutional excerpts form a neutral semantic *proposal*, not a validated causal graph."}}

def stage(atlas,provisional,workspace):
    app=CiteRefinery(Path(workspace)/"refinery")
    previous=app.store.load()
    existing=next((r for r in previous["projects"].values()
                   if r.get("title")=="Open corpus semantic atlas — unreviewed"),None)
    if existing:project_id=existing["id"]
    else:project_id=app.init_project("Open corpus semantic atlas — unreviewed",
                "Discover provisional problem nodes from an unclassified public source dump").id
    graph=SemanticGraph(app.store)
    material=packet(atlas,provisional)
    preview=graph.preview_packet(project_id,material)
    if preview["changed_existing_edge_statuses"]:
        raise ValueError("Cannot change prior source graph statuses")
    result=graph.ingest_packet(project_id,material)
    state=app.store.load()
    return {"project_id":project_id,"packet_id":result["id"],
            "declared_nodes":len(material["nodes"]),
            "declared_edges":len(material["edges"]),
            "actual_project_nodes":sum(n.get("project_id")==project_id for n in state["semantic_nodes"].values()),
            "actual_project_edges":sum(e.get("project_id")==project_id for e in state["semantic_edges"].values()),
            "replayed":preview["already_imported"],
            "accepted_scientific_conclusions":0,
            "boundary":"Staged review graph, not an accepted scientific authority."}
