"""Ambiguity audit for sampled GitHub repo descriptions in an opportunity atlas.

A GitHub topical match is not a semantic match. This is a model-assisted
metadata REVIEW layer (never license clearance, domain truth, or code analysis).
Missing reviews remain explicitly unaudited, not silently removed.
"""
from __future__ import annotations

import json
import re
from typing import Any

SCHEMA = "cite_refinery.opportunity_atlas_semantic_input.v1"
LABELS = {"relevant", "adjacent", "different_meaning", "insufficient_metadata"}


def create_batches(snapshot: dict[str, Any], meanings: dict[str, Any], *,
                   per_domain: int = 5, domains_per_batch: int = 11) -> list[dict[str, Any]]:
    if snapshot.get("schema") != "cite_refinery.opportunity_atlas_github_snapshot.v1":
        raise ValueError("unexpected snapshot")
    if meanings.get("schema") != "cite_refinery.opportunity_atlas_meanings.v1":
        raise ValueError("domain meanings required")
    if not 1 <= per_domain <= 12 or not 1 <= domains_per_batch <= 20:
        raise ValueError("bounded sampling needed")
    all_repos = snapshot["repositories"]
    lookup = {r["full_name"]:r for r in all_repos}
    sample_groups = []
    for s in snapshot["strata"]:
        domain = s["id"]
        if domain not in meanings["intents"]:
            raise ValueError("missing semantic meaning for "+domain)
        observed = [r for r in all_repos if domain in r["found_in"]]
        # Rank by stars merely to target particularly visible search results
        # for metadata review; no model label is propagated to other repos.
        observed.sort(key=lambda r: (-int(r.get("stars") or 0), r["full_name"]))
        sample_groups.append({
            "domain_id": domain, "intent": meanings["intents"][domain],
            "sampled_repositories": [{
                "id": r["full_name"], "description": r["description"],
                "topics": r["topics"][:8], "language": r["language"],
                "source_url": r["url"],
            } for r in observed[:per_domain]],
        })
    return [{
        "schema": SCHEMA, "batch_id": "semantic_audit_"+str(i//domains_per_batch+1),
        "domain_groups": sample_groups[i:i+domains_per_batch],
        "review_basis": "README not inspected; metadata-only",
    } for i in range(0,len(sample_groups),domains_per_batch)]


def prompt(batch: dict[str, Any]) -> str:
    if batch.get("schema") != SCHEMA:
        raise ValueError("invalid semantic batch")
    return (
        "You are an exacting semantic survey auditor. For EACH supplied "
        "(domain_id, repository_id) pair, classify whether the PUBLIC REPOSITORY "
        "DESCRIPTION truly fits the domain's intended mechanism. Recognize polysemy: "
        "flood hazard vs network-flood DDoS, physical repair vs JSON repair, "
        "electrical battery systems vs unrelated software labels, physical robotics "
        "vs web automation, engineering simulation vs games. "
        "Use 'insufficient_metadata' if description fails to demonstrate a fit. "
        "Do not inspect unstated README/code and do not infer adoption, commercial value, "
        "operational performance or domain approval. All results are candidates. "
        "Give exactly one item per supplied pair; do not invent IDs. "
        'Respond JSON ONLY: {"judgments":[{"domain_id":"same ID",'
        '"repository_id":"exact ID","label":"relevant|adjacent|different_meaning|insufficient_metadata",'
        '"reason":"short explicit semantic distinction"}]}. '
        "INPUT:\n"+json.dumps(batch,ensure_ascii=False,separators=(",",":"))
    )


def validate(batch: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    if batch.get("schema") != SCHEMA or not isinstance(answer, dict) or not isinstance(answer.get("judgments"), list):
        raise ValueError("invalid audit")
    pairs = {(g["domain_id"],r["id"]): r for g in batch["domain_groups"]
             for r in g["sampled_repositories"]}
    judgments, seen = [],set()
    for j in answer["judgments"]:
        if not isinstance(j,dict):
            raise ValueError("non-object judgment")
        key=j.get("domain_id"),j.get("repository_id")
        if key not in pairs or key in seen:
            raise ValueError("unknown or duplicate repo-domain judgment")
        seen.add(key)
        if j.get("label") not in LABELS or not isinstance(j.get("reason"),str) or not 15 <= len(j["reason"].strip()) <= 300:
            raise ValueError("invalid meaning label/reason")
        judgments.append({
            "domain_id": key[0], "repository_id": key[1],
            "label": j["label"],"reason": " ".join(j["reason"].split()),
            "review_state": "model_metadata_judgment_not_code_verified",
            "source_url": pairs[key]["source_url"],
        })
    if set(pairs)!=seen:
        raise ValueError("incomplete semantic audit; missing "+str(len(set(pairs)-seen))+" judgments")
    return {
        "schema":"cite_refinery.opportunity_atlas_semantic_review.v1",
        "batch_id": batch["batch_id"],
        "judgments": judgments, "source": "authenticated_model_on_public_repo_metadata",
        "limitation":"No README/code inspection; classification can be wrong; unaudited repos stay unlabeled.",
    }
