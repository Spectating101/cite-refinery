"""Project-scoped bidirectional three-layer navigation in persisted SemanticGraph.

This is an evidence navigation tool, not a mechanism similarity ranker.
Traversal follows only explicit within-project stored edges and never turns
two-hop connectivity or a shared source into a causal or commercial claim.
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

LAYERS=("practical","academic","implementation")
WALKABLE={"qualified","candidate","unresolved"}
NON_WALKABLE={"asserted","not_established"}

def _concept_layer(n:dict[str,Any])->str|None:
    layer=n.get("layer")
    if layer=="program" or layer=="implementation":
        return "implementation"
    if layer in ("practical","academic"):
        return layer
    if layer!="neutral":
        raise ValueError("unrecognized persisted semantic layer")
    if n.get("kind") in ("problem_claim","observation","requirement"):
        return "practical"
    # A neutral source/document/concept is provenance or unresolved ontology.
    # It is never silently interpreted as academic evidence.
    return None


def investigate(state:dict[str,Any],project_id:str,node_id:str, *,
                max_depth:int=2)->dict[str,Any]:
    if not isinstance(max_depth,int) or isinstance(max_depth,bool) or not 0<=max_depth<=3:
        raise ValueError("bounded traversal depth must be 0..3")
    if not isinstance(state,dict) or project_id not in state.get("projects",{}):
        raise KeyError("unknown native semantic project")
    own={id:n for id,n in state.get("semantic_nodes",{}).items()
         if n.get("project_id")==project_id}
    if node_id not in own:
        raise ValueError("semantic root does not belong to project")
    all_project_edges={}
    adjacency=defaultdict(list)
    for id,e in state.get("semantic_edges",{}).items():
        if e.get("project_id")!=project_id:
            continue
        a,b=e.get("source_id"),e.get("target_id")
        if a not in own or b not in own:
            raise ValueError("cross-project or dangling semantic edge")
        if e.get("status") not in WALKABLE|NON_WALKABLE:
            raise ValueError("unknown persisted relation authority status")
        all_project_edges[id]=e
        adjacency[a].append(id)
        adjacency[b].append(id)
    for v in adjacency.values():v.sort()
    root=own[node_id]
    seen={node_id:0}
    q=deque([node_id])
    selected=[]
    blocked=[]
    visited_edges=set()
    truncated=False
    while q:
        current=q.popleft()
        depth=seen[current]
        if depth>=max_depth:
            continue
        for eid in adjacency[current]:
            edge=all_project_edges[eid]
            a,b=edge["source_id"],edge["target_id"]
            other=b if a==current else a
            if eid not in visited_edges and edge["status"] in NON_WALKABLE:
                blocked.append({"edge_id":eid,"source":a,"target":b,
                                "relation":edge["relation"],"status":edge["status"],
                                "reason":"asserted_only_unreviewed" if edge["status"]=="asserted"
                                         else "explicitly_not_established"})
                visited_edges.add(eid)
                continue
            if edge["status"] in NON_WALKABLE:
                continue
            if _concept_layer(own[other]) is None:
                # No traversal through a neutral document/provenance node.
                continue
            if eid not in visited_edges:
                selected.append({
                    "id":eid,"from":a,"to":b,
                    "relation":edge["relation"],"status":edge["status"],
                    "evidence_refs":edge.get("evidence_refs",[]),
                    "from_layer":_concept_layer(own[a]),
                    "to_layer":_concept_layer(own[b]),
                    "review_state":"explicit_graph_edge_not_independent_semantic_proof",
                })
                visited_edges.add(eid)
            if other not in seen:
                if len(seen)>=200:
                    truncated=True
                    break
                seen[other]=depth+1
                q.append(other)
        if truncated:break
    rows=[]
    semantic_reviews_count=0
    functional_trials_count=0
    component_defects_count=0
    for key,depth in sorted(seen.items(),key=lambda v:(v[1],v[0])):
        n=own[key]
        receipts=n.get("provenance_receipts",[]) if isinstance(n.get("provenance_receipts"),list) else []
        sem_review=next((r.get("semantic_entailment_review") for r in reversed(receipts)
                         if isinstance(r,dict) and isinstance(r.get("semantic_entailment_review"),dict)),None)
        func_trial=next((r.get("functional_component_trial") for r in reversed(receipts)
                         if isinstance(r,dict) and isinstance(r.get("functional_component_trial"),dict)),None)
        row:dict[str,Any]={
            "id":key,"kind":n.get("kind"),"layer":_concept_layer(n),
            "native_layer":n.get("layer"),"statement":n.get("statement"),
            "source_refs":n.get("source_refs",[]),
            "depth":depth,
            "provenance_status":"stored_graph_record_not_independently_verified",
        }
        if sem_review is not None:
            row["semantic_entailment_review"]=sem_review
            semantic_reviews_count+=1
        if func_trial is not None:
            row["functional_component_trial"]=func_trial
            functional_trials_count+=1
            if func_trial.get("reproducible_component_defect_detected"):
                component_defects_count+=1
        rows.append(row)
    layer_groups={layer:[n for n in rows if n["layer"]==layer] for layer in LAYERS}
    return {
        "schema":"cite_refinery.native_three_layer_investigation.v1",
        "project_id":project_id,"root_id":node_id,
        "root_layer":_concept_layer(root),"max_depth":max_depth,
        "three_layers":layer_groups,"edges":selected,
        "blocked_unreviewed_edges":blocked,
        "coverage":{key:bool(v) for key,v in layer_groups.items()},
        "evidence_diagnostics":{
            "semantic_reviews_in_subgraph":semantic_reviews_count,
            "functional_trials_in_subgraph":functional_trials_count,
            "reproduced_component_defects_in_subgraph":component_defects_count,
        },
        "truncated":truncated,
        "scope":"single_existing_project_no_cross_project_edges",
        "boundary":"Explicit provenance only; reversed traversal is navigation, NOT inferred causal or commercial equivalence. Candidate and unresolved links stay unverified; neutral documents are not a fourth conceptual layer.",
    }
