"""Translate external research-engine outputs into *non-authoritative* semantic packets.

External search metadata, extracted paragraphs and LLM answers are NOT
academic findings. Source-lead nodes remain neutral and edges are candidate.
Packets are intended for isolated review workspaces, not automatic promotion.
"""
from __future__ import annotations

import hashlib
from typing import Any

SCHEMA = "cite_refinery.semantic_graph.v1"


def _key(prefix: str, text: str) -> str:
    return prefix + "_" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:18]


def source_lead_packet(module_id: str, module_title: str, leads: list[dict],
                       *, source_system: str = "external-openalex-discovery") -> dict:
    """Stage discovered bibliographic metadata, NOT source-validated evidence."""
    if not module_id or not module_title or not isinstance(leads, list):
        raise ValueError("module_id/title and source leads are required")
    if len(leads) > 100:
        raise ValueError("limit 100 source leads per packet")
    module = _key("module", module_id)
    nodes = [{
        "key": module, "statement": "Investigate " + module_title.strip(),
        "layer": "neutral", "kind": "research_question", "clusters": [module],
        "tags": ["module", "unreviewed"],
    }]
    edges = []
    seen = set()
    for lead in leads:
        ref = str(lead.get("source_ref") or lead.get("doi") or "").strip()
        title = str(lead.get("title") or "").strip()
        if not ref or not title or len(ref) > 2048 or len(title) > 1000:
            raise ValueError("each source lead requires a title and source_ref")
        if ref in seen:
            continue
        seen.add(ref)
        node = _key("source", ref)
        nodes.append({
            "key": node, "statement": "Unreviewed research source: " + title,
            "layer": "neutral", "kind": "source", "clusters": [module],
            "source_refs": [ref],
            "tags": ["source_lead_only", "not_an_academic_claim", "unreviewed"],
            "provenance": {
                "source_system": str(lead.get("source_provider") or source_system),
                "discovered_id": str(lead.get("id") or ""),
                "review_status": "discovery_metadata_only",
                "boundary": "Metadata exists; no source passage, claim entailment, or local outcome has been checked.",
            },
        })
        edges.append({
            "source": node, "target": module,
            "relation": "DISCOVERED_FOR", "status": "candidate",
            "evidence_refs": [ref],
            "provenance": {"boundary": "Search relevance only, not an assertion that the source supports the problem."},
        })
    return {
        "schema": SCHEMA, "source_system": source_system,
        "clusters": [{"key": module, "title": module_title,
                      "tags": ["external_source_discovery_unreviewed"]}],
        "nodes": nodes, "edges": edges,
        "conversion_metadata": {
            "status": "DISCOVERY_ONLY_NOT_ACCEPTED",
            "source_leads": len(seen),
            "limitation": "Neutral bibliographic metadata, not Practical, Academic or Program evidence. Review passages before promotion.",
        },
    }


def relation_proposal_packet(module_titles: dict[str, str],
                             proposals: list[dict], *,
                             source_system: str = "external-lightrag-proposals") -> dict:
    """Stage strictly candidate graph relations in a NEW isolated workspace."""
    if not module_titles or not isinstance(proposals, list) or len(proposals) > 100:
        raise ValueError("module_titles and at most 100 proposals are required")
    clusters = []
    nodes = []
    keys = {}
    for mid, title in module_titles.items():
        mid = str(mid)
        if not mid or not title:
            raise ValueError("module title cannot be blank")
        key = _key("module", mid)
        keys[mid] = key
        clusters.append({"key": key, "title": mid + " — " + str(title)})
        nodes.append({
            "key": key, "statement": "Investigate " + str(title),
            "layer": "neutral", "kind": "research_question", "clusters": [key],
            "tags": ["unreviewed_semantic_module", "not_a_verified_problem_claim"],
        })
    edges = []
    for p in proposals:
        if p.get("source") not in keys or p.get("target") not in keys:
            raise ValueError("proposed edge has unknown endpoint")
        if p.get("status") != "candidate":
            raise ValueError("only candidate status is permitted")
        relation = str(p.get("relation") or "")
        if relation in {"CAUSES", "SUPPORTS", "IMPLEMENTS", "ADDRESSES", "PRODUCES", "DEPLOYED_BY"}:
            raise ValueError("unsafe relation promotion")
        refs = p.get("evidence_refs")
        if not isinstance(refs, list) or not refs or not all(isinstance(r, str) and r.strip() for r in refs):
            raise ValueError("proposals require explicit source refs")
        edges.append({
            "source": keys[p["source"]], "target": keys[p["target"]],
            "relation": relation, "status": "candidate", "evidence_refs": refs,
            "provenance": {
                "reason": str(p.get("reason") or "")[:1500],
                "boundary": "Model-proposed edge; source refs are unverified pointers and causal scope is untested.",
                "source_system": source_system,
            },
        })
    return {
        "schema": SCHEMA, "source_system": source_system,
        "clusters": clusters, "nodes": nodes, "edges": edges,
        "conversion_metadata": {
            "status": "GENERATED_RELATIONS_REVIEW_REQUIRED",
            "limitations": [
                "Explicit source_refs do not prove passage-level support.",
                "No automatic merge with an accepted Cite-Refinery project.",
                "Nodes are neutral source-free questions until reviewed.",
            ],
        },
    }
