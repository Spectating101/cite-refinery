"""Export source-to-module *review assignments*, not inferred module-to-module truth.

A source passage can touch many problem modules without proving that the
problems are causally related. This packet represents evidence acquisition as
typed neutral source nodes with candidate context links, not a validated graph.
"""
from __future__ import annotations
import hashlib


def stage_source_module_review(modules, passages, ranked, *, top_k=4, min_score=.30):
    if not 1 <= top_k <= 10:
        raise ValueError("top_k must be 1..10")
    ids={m["id"] for m in modules}
    if len(ids)!=len(modules) or len(set(p["id"] for p in passages))!=len(passages):
        raise ValueError("module and source identifiers must be unique")
    bysource={x["id"]:x for x in passages}
    if set(bysource)!={row["source_id"] for row in ranked}:
        raise ValueError("sources and semantic rankings do not align")
    clusters=[{"key":"unreviewed_evidence_root","title":"External source acquisition / unverified mappings"}]
    nodes=[]
    edges=[]
    for module in modules:
        mk="module_"+module["id"].lower().replace("-","_")
        clusters.append({"key":mk,"parent":"unreviewed_evidence_root",
                         "title":module["id"]+" — "+module["title"]})
        nodes.append({
            "key":mk,"statement":module["title"]+": "+module["summary"],
            "kind":"research_question","layer":"neutral","clusters":[mk],
            "tags":["problem_module_unreviewed","no_claim_of_field_coverage"],
            "provenance":{"module_id":module["id"],
                          "boundary":"Candidate topic container, not a verified state of the world."},
        })
    for row in ranked:
        sid=row["source_id"]
        source=bysource[sid]
        raw=source["text"]
        digest=hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if row["source_passage_sha256"]!=digest:
            raise ValueError("Source excerpt digest mismatch")
        if not source["url"].startswith("https://"):
            raise ValueError("Only HTTPS source URLs supported")
        sk="source_"+digest[:24]
        selected=[x for x in row["ranked_modules"][:top_k] if x["score"]>=min_score]
        nodes.append({
            "key":sk,"statement":"Review this institutional passage: "+raw[:700],
            "kind":"source","layer":"neutral","clusters":["unreviewed_evidence_root"],
            "source_refs":[source["url"]],
            "tags":["machine_retrieved_source","not_a_validated_academic_or_program_claim"],
            "provenance":{
                "source_id":sid,"source_url":source["url"],
                "passage_sha256":digest,
                "review_status":"machine_retrieved_unverified",
                "boundary":"Exact source passage is available for inspection; no proposition has been entailed or accepted.",
            },
        })
        for entry in selected:
            if entry["module_id"] not in ids:
                raise ValueError("Unrecognized module in ranked evidence")
            edges.append({
                "source":sk, "target":"module_"+entry["module_id"].lower().replace("-","_"),
                "relation":"CONTEXT_FOR","status":"candidate","evidence_refs":[source["url"]],
                "provenance":{
                    "source_id":sid,"passage_sha256":digest,
                    "similarity":entry["score"],"rank":entry["rank"],
                    "boundary":"Automatic topic relevance only; NOT evidence that the quoted passage establishes the module's problem or an intervention's effect.",
                },
            })
    return {
        "schema":"cite_refinery.semantic_graph.v1",
        "source_system":"source_first_module_review_v1",
        "clusters":clusters,"nodes":nodes,"edges":edges,
        "conversion_metadata":{
            "status":"EXTERNAL_SOURCE_TO_MODULE_CANDIDATES_UNREVIEWED",
            "module_count":len(modules),"source_passage_count":len(passages),
            "candidate_assignment_count":len(edges),
            "no_module_to_module_edges":True,
            "no_accepted_evidence":True,
            "warning":"Review evidence passages before making ANY module-to-module assertion.",
        },
    }
