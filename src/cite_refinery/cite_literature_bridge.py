"""Cite-Agent search -> Academic literature in an existing Nocturnal cluster.

Retrieval is never claim grounding; related case links remain candidate.
"""
from __future__ import annotations
import hashlib
import json
import re
from typing import Any
from urllib.parse import quote

DOI = re.compile(r"^10\.[0-9]{4,9}/[A-Za-z0-9._;()/:+-]+$")
PROVIDERS = {"semantic_scholar", "openalex", "crossref", "pubmed"}


def text(v: Any) -> str:
    return " ".join(str(v or "").split())


def doi(v: Any) -> str:
    s = text(v).removeprefix("https://doi.org/")
    if not DOI.fullmatch(s):
        raise ValueError("invalid or missing DOI")
    return s.lower()


def resolve_target(state: dict, project: str, candidate: str) -> dict:
    key = "nocturnal-" + candidate
    clusters = [c for c in state.get("semantic_clusters", {}).values()
                if c.get("project_id") == project and c.get("external_key") == key]
    if len(clusters) != 1:
        raise ValueError("Nocturnal case module missing")
    cluster = clusters[0]
    receipts = cluster.get("provenance_receipts", [])
    if not any(r.get("source_system") == "nocturnal"
               and r.get("candidate_id") == candidate
               and r.get("frozen_empirical_commit") for r in receipts):
        raise ValueError("module has no frozen Nocturnal provenance")
    anchors = [n for n in state.get("semantic_nodes", {}).values()
               if n.get("project_id") == project
               and n.get("external_key") == "nocturnal:" + key + "-scope"
               and n.get("layer") == "neutral"
               and cluster["id"] in n.get("cluster_ids", [])]
    if len(anchors) != 1:
        raise ValueError("source case anchor missing")
    return {"key": key, "title": cluster["title"], "anchor": anchors[0]["id"],
            "candidate": candidate}


def convert_search(result: dict, target: dict, *, limit: int = 20) -> dict:
    if result.get("tool") != "search" or result.get("status") != "completed":
        raise ValueError("completed Cite search required")
    rows = result.get("papers")
    if not isinstance(rows, list) or type(result.get("paper_count")) is not int:
        raise ValueError("structured search list required")
    if len(rows) != result["paper_count"] or len(rows) > limit:
        raise ValueError("Cite paper count invalid")
    topic = text(result.get("topic"))
    if not topic or len(topic) > 1000:
        raise ValueError("search topic missing")
    digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    nodes, edges, seen = [], [], set()
    for row in rows:
        if not isinstance(row, dict) or text(row.get("source")) not in PROVIDERS:
            raise ValueError("unsupported source record")
        title = text(row.get("title"))
        if not title or len(title) > 750:
            raise ValueError("invalid paper title")
        d = doi(row.get("doi"))
        if d in seen:
            raise ValueError("duplicate DOI")
        seen.add(d)
        abstract = text(row.get("abstract"))
        if target["candidate"] == "china-kangmei-2020":
            if "kangmei" not in (title + " " + abstract).casefold():
                raise ValueError("paper not explicitly about Kangmei")
        year = row.get("year")
        if type(year) is not int or year < 1800 or year > 2100:
            raise ValueError("invalid paper year")
        authors = row.get("authors") or []
        if not isinstance(authors, list) or any(not isinstance(a, str) for a in authors):
            raise ValueError("invalid authors")
        key = "doi-" + hashlib.sha256(d.encode()).hexdigest()[:18]
        url = "https://doi.org/" + quote(d, safe="/._-;()+")
        nodes.append({
            "key": key, "statement": f"Literature record: {title} ({year})",
            "kind": "source", "layer": "academic", "clusters": [target["key"]],
            "tags": ["literature_retrieved", "claims_not_grounded"],
            "source_refs": [url],
            "provenance": {
                "doi": d, "title": title, "authors": authors,
                "venue": text(row.get("venue")), "year": year,
                "retrieval_provider": text(row.get("source")),
                "retrieval_engine": "cite-agent-research search",
                "retrieval_query": topic, "retrieval_digest": digest,
                "indexed_abstract": abstract[:6500],
                "verification_state": "retrieved_not_grounded",
                "boundary": "Index and abstract do not validate underlying empirical facts",
            },
        })
        edges.append({
            "source": key, "target": target["anchor"],
            "relation": "RELATED_TO", "status": "candidate",
            "evidence_refs": [url],
            "provenance": {
                "doi": d, "review_state": "not_reviewed",
                "proposal_origin": "topical_literature_retrieval",
                "boundary": "No verified case support, contradiction or causal relation",
            },
        })
    return {
        "schema": "cite_refinery.semantic_graph.v1", "source_system": "cite",
        "clusters": [{
            "key": target["key"], "title": target["title"],
            "tags": ["academic_literature_retrieved"],
            "provenance": {"matched_case": target["candidate"],
                           "boundary": "shared source-case cluster, discovery only"},
        }],
        "nodes": nodes, "edges": edges,
        "conversion_metadata": {
            "target_candidate_id": target["candidate"],
            "literature_count": len(nodes),
            "candidate_cross_layer_links": len(edges),
            "retrieval_digest": digest,
            "supported_claims": 0,
            "boundary": "Discovery only; full-text reading and link review outstanding",
        },
    }
