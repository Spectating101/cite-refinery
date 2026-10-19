"""Build a provenance-qualified breadth-first semantic packet from the research ledger.

This is a source-summary ingestion candidate, NOT a verified intervention map.
The report's 54 module names are hypotheses/containers; only the 12 first-wave
anchors have any source-linked claims. Empty evidence lanes remain empty.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "research_materials" / "landscape_20261020"
PACKET = ROOT / "examples" / "landscape_reconnaissance_wave1.json"
INDEX = CORPUS / "module_index.csv"
SCHEMA = "cite_refinery.semantic_graph.v1"


def load_corpus():
    modules = json.loads((CORPUS / "modules.json").read_text(encoding="utf-8"))
    sources = json.loads((CORPUS / "sources.json").read_text(encoding="utf-8"))
    claims = json.loads((CORPUS / "claims_and_bridges.json").read_text(encoding="utf-8"))
    return modules, sources, claims


def validate_corpus(modules, sources, claim_pack):
    fields = {f["id"] for f in modules["fields"]}
    mids = {m["id"] for m in modules["modules"]}
    sids = {s["id"] for s in sources["sources"]}
    anchors = set(modules["anchor_order"])
    assert len(fields) == len(modules["fields"]) == 9
    assert len(mids) == len(modules["modules"]) == 54
    assert len(sids) == len(sources["sources"])
    assert len(anchors) == len(modules["anchor_order"]) == 12
    assert anchors <= mids
    assert all(m["field_id"] in fields and m["id"].startswith(m["field_id"] + "-") for m in modules["modules"])
    assert all((m["id"] in anchors) == (m["stage"] == "wave1_anchor") for m in modules["modules"])
    assert all(s["url"].startswith("https://") and s["limitation"] and s["review_level"] for s in sources["sources"])
    assert len({c["id"] for c in claim_pack["claims"]}) == len(claim_pack["claims"])
    assert all(c["module_id"] in anchors and c["source_id"] in sids and
               c["layer"] in ("practical", "academic", "program") and
               c["boundary"] and c["statement"] for c in claim_pack["claims"])
    assert all(b["from"] in mids and b["to"] in mids and b["from"] != b["to"] and
               b["source_ids"] and set(b["source_ids"]) <= sids and
               b["status"] == "candidate" and b["boundary"] for b in claim_pack["bridges"])


def build():
    registry, ledger, claim_pack = load_corpus()
    validate_corpus(registry, ledger, claim_pack)
    sources = {s["id"]: s for s in ledger["sources"]}
    fields = {f["id"]: f for f in registry["fields"]}
    clusters = [{
        "key": "landscape_recon_root",
        "title": "Breadth-first research reconnaissance: 54 candidate problem modules",
        "tags": ["discovery_only", "non_exhaustive", "source_summary"],
    }]
    for field in registry["fields"]:
        clusters.append({
            "key": "field_" + field["id"].lower(),
            "title": field["name"],
            "parent": "landscape_recon_root",
            "tags": ["field", "not_a_ranking"],
        })

    nodes = []
    for module in registry["modules"]:
        field_key = "field_" + module["field_id"].lower()
        cluster_key = "module_" + module["id"].lower().replace("-", "_")
        clusters.append({
            "key": cluster_key,
            "title": module["id"] + " — " + module["title"],
            "parent": field_key,
            "tags": ["problem_module", module["stage"], "not_verified_as_a_fact"],
            "provenance": {"origin": registry["origin"], "report_summary": module["summary"]},
        })
        nodes.append({
            "key": cluster_key,
            "statement": "Investigate " + module["title"].lower() + ".",
            "kind": "research_question",
            "layer": "neutral",
            "clusters": [cluster_key],
            "tags": ["report_candidate", "not_a_verified_problem_claim", module["stage"]],
            "provenance": {
                "report_module_id": module["id"],
                "report_summary": module["summary"],
                "evidence_status": module["evidence_status"],
                "source_review": "user_supplied_reconnaissance",
            },
        })

    edges = []
    for claim in claim_pack["claims"]:
        source = sources[claim["source_id"]]
        module_id = claim["module_id"]
        field_id = module_id.split("-")[0]
        anchor = "module_" + module_id.lower().replace("-", "_")
        node_key = "claim_" + claim["id"].lower().replace("-", "_")
        nodes.append({
            "key": node_key,
            "statement": claim["statement"],
            "kind": claim["kind"],
            "layer": claim["layer"],
            "clusters": ["field_" + field_id.lower(), anchor],
            "source_refs": [source["url"]],
            "tags": ["source_summary_not_replication", "wave1_evidence", "unreviewed_for_acceptance"],
            "provenance": {
                "claim_id": claim["id"],
                "source_id": source["id"],
                "source_title": source["title"],
                "source_type": source["source_type"],
                "source_date": source["date"],
                "source_scope": source["scope"],
                "source_limitation": source["limitation"],
                "review_level": source["review_level"],
                "review_status": claim["review_status"],
                "boundary": claim["boundary"],
            },
        })
        edges.append({
            "source": node_key,
            "target": anchor,
            "relation": "CONTEXT_FOR" if claim["layer"] == "practical" else "RELATED_TO",
            "status": "candidate",
            "evidence_refs": [source["url"]],
            "provenance": {
                "source_id": source["id"],
                "claim_id": claim["id"],
                "boundary": "Topical association only; no causal, coverage or intervention-effectiveness inference. " + claim["boundary"],
            },
        })

    for bridge in claim_pack["bridges"]:
        edges.append({
            "source": "module_" + bridge["from"].lower().replace("-", "_"),
            "target": "module_" + bridge["to"].lower().replace("-", "_"),
            "relation": bridge["relation"],
            "status": "candidate",
            "evidence_refs": [sources[sid]["url"] for sid in bridge["source_ids"]],
            "tags": ["cross_field_candidate" if bridge["from"][:2] != bridge["to"][:2] else "within_field_candidate"],
            "provenance": {
                "bridge_id": bridge["id"],
                "source_ids": bridge["source_ids"],
                "boundary": bridge["boundary"],
            },
        })

    return {
        "schema": SCHEMA,
        "source_system": "deep_research_landscape_wave1_20261020",
        "clusters": clusters,
        "nodes": nodes,
        "edges": edges,
        "conversion_metadata": {
            "status": "CANDIDATE_SOURCE_SUMMARIES_NOT_ACCEPTED",
            "origin": registry["origin"],
            "module_count": len(registry["modules"]),
            "first_wave_anchors": registry["anchor_order"],
            "source_ledger_entries": len(sources),
            "evidence_claims": len(claim_pack["claims"]),
            "candidate_bridges": len(claim_pack["bridges"]),
            "limitations": [
                "54 modules are user-provided research containers, not verified world facts.",
                "Only 12 modules have source-linked claims; 42 have neutral questions only.",
                "Sources are publication pages/abstracts/provider documentation; no primary datasets downloaded or findings independently replicated.",
                "Program includes measurement tools, documentation and scenarios, not verified field outcomes.",
                "Absent layer or edge means not established in represented corpus, not absent in reality.",
                "The downloadable 54-node CSV referenced by the report was not supplied; source URLs in this ledger were recovered individually.",
                "Cross-field edges are candidate relationships only; no intervention effectiveness or causality established.",
                "English-language and institutional source selection bias; not a systematic global census.",
            ],
        },
    }


def write():
    packet = build()
    PACKET.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    registry, _, claims = load_corpus()
    counts = Counter((c["module_id"], c["layer"]) for c in claims["claims"])
    with INDEX.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["module_id", "field_id", "title", "stage",
                                                "practical_claims", "academic_claims", "program_claims"],
                                lineterminator="\n")
        writer.writeheader()
        for m in registry["modules"]:
            writer.writerow({
                "module_id": m["id"], "field_id": m["field_id"], "title": m["title"], "stage": m["stage"],
                "practical_claims": counts[(m["id"], "practical")],
                "academic_claims": counts[(m["id"], "academic")],
                "program_claims": counts[(m["id"], "program")],
            })
    print(f"wrote {PACKET}: {len(packet['clusters'])} clusters, {len(packet['nodes'])} nodes, {len(packet['edges'])} edges")
    print(f"wrote {INDEX}: {len(registry['modules'])} modules")


if __name__ == "__main__":
    write()
