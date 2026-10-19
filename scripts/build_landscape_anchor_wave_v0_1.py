"""Convert Deep Research's 12-anchor source leads into a reviewable semantic graph.

This version is a *research staging packet*, not an accepted field report.
An HTTP 200 or a citation is not full-text validation. Program evidence is typed
as measurement, plans, funded activity, software, or bounded tests, never outcomes.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from scripts.build_landscape_research_wave1 import build as build_reconnaissance, load_corpus

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "research_materials" / "landscape_20261020" / "anchor_wave_v0_1"
PACKET = ROOT / "examples" / "landscape_anchor_wave_v0_1.json"
INDEX = SOURCE_DIR / "anchor_evidence_matrix_v0_1.csv"
AUDIT = SOURCE_DIR / "coverage_and_topology_v0_1.json"
SCHEMA = "cite_refinery.semantic_graph.v1"


def read(name):
    return json.loads((SOURCE_DIR / name).read_text(encoding="utf-8"))


def key_for_module(module_id):
    return "module_" + module_id.lower().replace("-", "_")


def validate(registry, sources, questions, extra):
    anchors = registry["anchor_order"]
    mids = {m["id"] for m in registry["modules"]}
    source_ids = [s["id"] for s in sources]
    assert len(anchors) == 12 and len(set(anchors)) == 12
    assert len(registry["modules"]) == 54
    assert len(sources) == 36 and len(set(source_ids)) == 36
    assert len(questions["questions"]) == 36
    assert len(extra["extras"]) == 19
    assert {s["module_id"] for s in sources} == set(anchors)
    assert set((s["module_id"], s["layer"]) for s in sources) == {
        (module, layer) for module in anchors for layer in ("practical", "academic", "program")
    }
    by_id = {s["id"]: s for s in sources}
    for source in sources:
        assert source["url"].startswith("https://")
        assert source["limitation"] and source["scope"] and source["date"]
        assert source["initial_claim"] and source["source_type"] and source["access"]["note"]
        assert source["access"]["http_status"] in (200, 403, 404)
    assert len({q["id"] for q in questions["questions"]}) == 36
    assert all(q["module_id"] in anchors and q["source_id"] in by_id
               and by_id[q["source_id"]]["module_id"] == q["module_id"]
               and q["status"] == "unresolved" and q["boundary"] for q in questions["questions"])
    assert all(c["source_id"] in by_id and c["boundary"] for c in extra["extras"])
    for bridge in questions["bridges"]:
        assert bridge["from"] in mids and bridge["to"] in mids
        assert bridge["from"] != bridge["to"] and bridge["status"] == "candidate"
        assert bridge["source_ids"] and all(s in by_id for s in bridge["source_ids"])
        assert bridge["boundary"]


def build():
    registry, _, _ = load_corpus()
    lead = read("anchor_sources_v0_1.json")
    questions = read("anchor_questions_and_bridges_v0_1.json")
    extra = read("atomized_extra_claims_v0_1.json")
    sources = lead["sources"]
    validate(registry, sources, questions, extra)
    base = build_reconnaissance()
    nodes = [dict(n) for n in base["nodes"] if n["layer"] == "neutral"]
    clusters = base["clusters"]
    edges = []
    by_id = {s["id"]: s for s in sources}
    question_nodes = {}
    for q in questions["questions"]:
        key = "question_" + q["id"].lower().replace("-", "_")
        question_nodes[q["id"]] = key
        nodes.append({
            "key": key,
            "statement": q["question"],
            "kind": "research_question",
            "layer": "neutral",
            "clusters": [key_for_module(q["module_id"])],
            "tags": ["atomic_problem_question", "research_backlog", "unresolved"],
            "provenance": {
                "module_id": q["module_id"],
                "context_source_lead": q["source_id"],
                "review_status": q["status"],
                "boundary": q["boundary"],
                "epistemic_note": "The question is not a verified factual observation.",
            },
        })

    claims = [
        {
            "id": "A-" + s["id"], "module_id": s["module_id"],
            "source_id": s["id"], "layer": s["layer"],
            "kind": s["initial_kind"], "statement": s["initial_claim"],
            "boundary": s["limitation"],
        }
        for s in sources
    ]
    for item in extra["extras"]:
        s = by_id[item["source_id"]]
        claims.append({
            **item, "module_id": s["module_id"], "layer": s["layer"]
        })
    for claim in claims:
        s = by_id[claim["source_id"]]
        anchor = key_for_module(s["module_id"])
        node_key = "anchorclaim_" + claim["id"].lower().replace("-", "_")
        nodes.append({
            "key": node_key,
            "statement": claim["statement"],
            "kind": claim["kind"],
            "layer": claim["layer"],
            "clusters": [anchor],
            "source_refs": [s["url"]],
            "tags": ["anchor_wave_v0_1", "candidate_not_accepted", s["source_type"]],
            "provenance": {
                "claim_id": claim["id"],
                "source_id": s["id"],
                "source_title": s["title"],
                "source_type": s["source_type"],
                "source_publisher": s["publisher"],
                "source_date": s["date"],
                "source_scope": s["scope"],
                "source_limitation": s["limitation"],
                "access_check": s["access"],
                "review_level": "research_synthesis_and_url_check_not_full_primary_audit",
                "review_status": "candidate_not_accepted",
                "boundary": claim["boundary"],
                "outcome_evidence": "not_established_by_this_packet",
            },
        })
        edges.append({
            "source": node_key, "target": anchor,
            "relation": "CONTEXT_FOR" if claim["layer"] == "practical" else "RELATED_TO",
            "status": "candidate",
            "evidence_refs": [s["url"]],
            "provenance": {
                "source_id": s["id"], "claim_id": claim["id"],
                "boundary": "Topical module association, not causal, effective or generalizable. " + claim["boundary"],
            },
        })
        # Pair the primary source-backed claim with the research questions it motivated.
        if claim["id"] == "A-" + s["id"]:
            for q in questions["questions"]:
                if q["source_id"] == s["id"]:
                    edges.append({
                        "source": node_key, "target": question_nodes[q["id"]],
                        "relation": "CONTEXT_FOR", "status": "candidate",
                        "evidence_refs": [s["url"]],
                        "provenance": {
                            "source_id": s["id"], "question_id": q["id"],
                            "boundary": "Source motivates the research question; it does not answer or validate it.",
                        },
                    })

    for bridge in questions["bridges"]:
        edges.append({
            "source": key_for_module(bridge["from"]),
            "target": key_for_module(bridge["to"]),
            "relation": bridge["relation"],
            "status": "candidate",
            "evidence_refs": [by_id[s]["url"] for s in bridge["source_ids"]],
            "tags": ["cross_field_candidate" if bridge["from"][:2] != bridge["to"][:2]
                     else "within_field_candidate"],
            "provenance": {
                "bridge_id": bridge["id"], "source_ids": bridge["source_ids"],
                "boundary": bridge["boundary"],
                "epistemic_state": bridge["epistemic_state"],
            },
        })

    packet = {
        "schema": SCHEMA,
        "source_system": "deep_research_anchor_wave_v0_1_20261020",
        "clusters": clusters, "nodes": nodes, "edges": edges,
        "conversion_metadata": {
            "status": "CANDIDATE_RESEARCH_NOT_ACCEPTED",
            "origin": lead["origin"],
            "source_count": len(sources),
            "anchor_count": len(registry["anchor_order"]),
            "module_count": len(registry["modules"]),
            "evidence_claim_count": len(claims),
            "question_count": len(questions["questions"]),
            "bridge_count": len(questions["bridges"]),
            "limitations": [
                "Source pages and Deep Research summaries are not primary dataset replication.",
                "Several publisher URLs return 403 to automated access; a 200 URL response is not an academic content audit.",
                "CloakPipe evidence is accessible using authenticated GitHub connector; anonymous URL returns 404.",
                "All 12 anchors have three source categories, not three proven outcomes.",
                "Practical FTC source is regulatory warning rather than a measured real-world leak.",
                "Program sources include data portals, measurement frameworks, initiative descriptions and one bounded implementation; effectiveness is not established.",
                "Only the first 12 modules have source-linked claims; 42 modules remain without evidence in this packet.",
                "All 16 semantic bridges remain candidates; no causal dependency or geographic transfer is established.",
                "This packet must be imported into an isolated project; do not promote candidate claims to accepted pilots.",
            ],
        },
    }
    return packet


def audit(packet):
    lead = read("anchor_sources_v0_1.json")
    registry, _, _ = load_corpus()
    sources = lead["sources"]
    counts = Counter((n["provenance"].get("source_id", ""),
                      n["layer"]) for n in packet["nodes"]
                     if n["layer"] != "neutral")
    typed = Counter(s["source_type"] for s in sources if s["layer"] == "program")
    per_module = {}
    for m in registry["modules"]:
        ss = [s for s in sources if s["module_id"] == m["id"]]
        per_module[m["id"]] = {
            "stage": m["stage"],
            "sources_by_layer": {layer: sum(s["layer"] == layer for s in ss)
                                 for layer in ("practical", "academic", "program")},
            "review_state": "source_candidate_only" if ss else "unresearched_in_this_wave",
            "program_kind": next((s["source_type"] for s in ss if s["layer"] == "program"), None),
        }
    bridges = read("anchor_questions_and_bridges_v0_1.json")["bridges"]
    incoming = defaultdict(list)
    for b in bridges:
        incoming[b["from"]].append(b)
        incoming[b["to"]].append(b)
    unresearched_queue = []
    for module_id, row in per_module.items():
        if row["review_state"] != "unresearched_in_this_wave" or not incoming[module_id]:
            continue
        near_evidence = [b for b in incoming[module_id]
                         if per_module[b["from"] if b["to"] == module_id else b["to"]]["review_state"]
                         == "source_candidate_only"]
        unresearched_queue.append({
            "module_id": module_id,
            "candidate_bridge_count": len(incoming[module_id]),
            "adjacent_evidenced_anchor_count": len(near_evidence),
            "candidate_bridge_ids": [b["id"] for b in incoming[module_id]],
            "meaning": "Navigation priority only, not scientific importance or impact",
        })
    unresearched_queue.sort(key=lambda e: (-e["adjacent_evidenced_anchor_count"],
                                                -e["candidate_bridge_count"], e["module_id"]))
    return {
        "module_count": 54,
        "evidence_anchor_count": 12,
        "unresearched_second_ring_count": 42,
        "source_count": len(sources),
        "candidate_atomic_evidence_nodes": sum(n["layer"] != "neutral" for n in packet["nodes"]),
        "unresolved_atomic_problem_questions": sum(n["layer"] == "neutral" and
                                                    n["kind"] == "research_question" and
                                                    n["key"].startswith("question_") for n in packet["nodes"]),
        "candidate_cross_module_bridges": len(bridges),
        "cross_field_bridges": sum(b["from"].split("-")[0] != b["to"].split("-")[0] for b in bridges),
        "program_source_types": dict(sorted(typed.items())),
        "source_outcome_support_status": "No independently verified intervention outcome in this wave",
        "bridge_investigation_queue": unresearched_queue,
        "source_http_statuses": dict(sorted(Counter(s["access"]["http_status"] for s in sources).items())),
        "source_coverage_by_module": per_module,
        "interpretation": [
            "36 source leads across three lanes is source presence, not field completeness.",
            "All candidate edges require source-specific cross-scope review before promoting relation strength.",
            "Program sources overwhelmingly describe monitoring, frameworks or planned activity rather than independently validated outcomes.",
        ],
        "next_wave": ["ED-05", "PH-02", "PH-06", "WA-05", "HO-05", "HO-06",
                      "FS-06", "CO-03", "WA-04", "DP-05", "AW-03", "EN-06"],
    }


def write():
    packet = build()
    PACKET.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = audit(packet)
    summary["packet_sha256"] = hashlib.sha256(PACKET.read_bytes()).hexdigest()
    AUDIT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with INDEX.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["module_id", "stage", "Practical_sources", "Academic_sources",
                         "Program_sources", "Program_kind", "review_state"])
        for id, row in summary["source_coverage_by_module"].items():
            c = row["sources_by_layer"]
            writer.writerow([id, row["stage"], c["practical"], c["academic"], c["program"],
                             row["program_kind"] or "", row["review_state"]])
    print(f"packet: {len(packet['nodes'])} nodes / {len(packet['edges'])} edges, "
          f"sha256={summary['packet_sha256']}")
    print(f"sources: {summary['source_count']}, follow-up questions: "
          f"{summary['unresolved_atomic_problem_questions']}, bridges: "
          f"{summary['candidate_cross_module_bridges']}")


if __name__ == "__main__":
    write()
