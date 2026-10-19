"""Strict claim/abstract grounding receipt -> Academic evidence nodes.

Cite's grounding verdict is treated as an allegation until checked against the
previously imported project's exact DOI and indexed abstract. No source-backed
claim creates an established relation to a real-world Nocturnal event.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from .cite_literature_bridge import doi, resolve_target, text


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def convert_grounding(
    receipt: dict[str, Any], state: dict[str, Any],
    project_id: str, candidate_id: str,
) -> dict[str, Any]:
    target = resolve_target(state, project_id, candidate_id)
    if receipt.get("tool") != "ground" or receipt.get("status") != "completed" or receipt.get("schema_version") != 1:
        raise ValueError("completed Cite-Agent v1 grounding receipt required")
    claims = receipt.get("claims")
    if not isinstance(claims, list) or not 1 <= len(claims) <= 10:
        raise ValueError("1..10 grounded claims required")
    members: dict[str, dict] = {}
    for n in state.get("semantic_nodes", {}).values():
        if n.get("project_id") != project_id or n.get("layer") != "academic" or n.get("kind") != "source":
            continue
        if target["key"] not in {
            c.get("external_key") for c in state.get("semantic_clusters", {}).values()
            if c.get("id") in n.get("cluster_ids", [])
        }:
            continue
        for p in n.get("provenance_receipts", []):
            if p.get("source_system") != "cite" or p.get("verification_state") != "retrieved_not_grounded":
                continue
            source_doi = p.get("doi")
            if source_doi:
                members[doi(source_doi)] = {"id": n["id"], "data": p, "node": n}
    if not members:
        raise ValueError("academic DOI records must be imported before grounding")
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    summary = {"supported_abstract_claims": 0, "unverified_or_unusable_claims": 0}
    receipt_hash = _digest(receipt)
    used: set[tuple[str, str]] = set()
    for idx, item in enumerate(claims):
        if not isinstance(item, dict):
            raise ValueError("claim entry must be object")
        statement = text(item.get("claim"))
        if not 15 <= len(statement) <= 2000:
            raise ValueError("claim text too short or too long")
        verdict = text(item.get("verdict")).lower()
        # Strict refusal to convert a model-suggested verdict alone into evidence.
        evidences = item.get("evidence")
        if not isinstance(evidences, list):
            raise ValueError("grounding evidence must be list")
        if verdict != "supported":
            summary["unverified_or_unusable_claims"] += 1
            continue
        if item.get("rejected_quotes", 0) != 0:
            summary["unverified_or_unusable_claims"] += 1
            continue
        if not evidences:
            summary["unverified_or_unusable_claims"] += 1
            continue
        accepted = []
        for evidence in evidences:
            if not isinstance(evidence, dict):
                raise ValueError("grounding evidence entry invalid")
            source_doi = doi(evidence.get("doi"))
            match = members.get(source_doi)
            if not match:
                raise ValueError("grounding receipt cites DOI not present in this project")
            quote = text(evidence.get("quote"))
            if not 35 <= len(quote) <= 800:
                raise ValueError("grounding quote must be a nontrivial, bounded excerpt")
            abstract = text(match["data"].get("indexed_abstract"))
            # Match only exact normalized abstract text (never against an LLM-supplied
            # abstract, the paper title, or a purported external web excerpt).
            if quote.casefold() not in abstract.casefold():
                raise ValueError("grounding quote not present in imported indexed abstract")
            title = text(evidence.get("title"))
            if title and title.casefold() != text(match["data"].get("title")).casefold():
                raise ValueError("grounding receipt title does not match DOI record")
            used_key = (statement.casefold(), source_doi)
            if used_key in used:
                raise ValueError("repeated claim/DOI grounding in one receipt")
            used.add(used_key)
            accepted.append((source_doi, quote, match))
        for source_doi, quote, match in accepted:
            key = "abstract-grounded-" + hashlib.sha256((statement + "\0" + source_doi).encode()).hexdigest()[:24]
            url = match["node"]["source_refs"][0]
            claim_provenance = {
                "source_doi": source_doi,
                "grounding_verdict": verdict,
                "grounding_receipt_digest": receipt_hash,
                "citation_quote": quote,
                "citation_quote_digest": hashlib.sha256(quote.encode()).hexdigest(),
                "indexed_abstract_digest": hashlib.sha256(text(match["data"]["indexed_abstract"]).encode()).hexdigest(),
                "evidence_scope": "retrieved_abstract",
                "verification": "exact_quote_present_in_previously_imported_indexed_abstract",
                "independent_fulltext_verification": False,
                "review_state": "source_quote_checked_not_human_approved",
                "boundary": "An abstract-backed scholarly finding is not an independently established empirical event or causal link.",
            }
            nodes.append({
                "key": key, "statement": statement, "layer": "academic",
                "kind": "academic_claim", "clusters": [target["key"]],
                "tags": ["abstract_quote_checked", "not_fulltext_verified", "not_cross_layer_reviewed"],
                "source_refs": [url], "provenance": claim_provenance,
            })
            # This relation records attribution to the cited paper itself. It does not
            # connect the finding to a Nocturnal event or establish causality.
            edges.append({
                "source": key, "target": match["id"],
                "relation": "DERIVED_FROM", "status": "qualified",
                "evidence_refs": [url],
                "provenance": {**claim_provenance, "relation_scope": "scholarly_claim_to_indexed_paper"},
            })
            edges.append({
                "source": key, "target": target["anchor"],
                "relation": "RELATED_TO", "status": "candidate",
                "evidence_refs": [url],
                "provenance": {
                    "source_doi": source_doi, "review_state": "not_reviewed",
                    "boundary": "Suggested association with the Nocturnal case context only. Never verified support for specific events.",
                },
            })
            summary["supported_abstract_claims"] += 1
    if not nodes:
        raise ValueError("no supportable abstract quotes to import; retain raw audit without graph mutation")
    return {
        "schema": "cite_refinery.semantic_graph.v1",
        "source_system": "cite",
        "clusters": [{
            "key": target["key"], "title": target["title"],
            "provenance": {
                "grounding_receipt_digest": receipt_hash,
                "boundary": "reusing existing cluster, not asserting cross-layer evidence",
            },
        }],
        "nodes": nodes, "edges": edges,
        "conversion_metadata": {
            "grounding_receipt_digest": receipt_hash,
            **summary,
            "verified_full_text_claims": 0,
            "asserted_practical_academic_links": 0,
            "boundary": "Evidence is checked against imported abstract only. Human review and full-text methods inspection not done.",
        },
    }
