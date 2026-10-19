"""Horizontal semantic landscape expansion: 12 adjacent modules + 4 new fields.

Produce a *standalone snapshot*, extending rather than re-ingesting the anchor
packet. New source statements are provisional and all semantic bridges remain
candidates. Source reachability and research-source inspection differ.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from scripts.build_landscape_anchor_wave_v0_1 import build as previous_build, key_for_module
from scripts.build_landscape_research_wave1 import load_corpus

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "research_materials" / "landscape_20261020" / "horizontal_wave2"
PACKET = ROOT / "examples" / "landscape_horizontal_wave2.json"
INDEX = HERE / "coverage_matrix.csv"
AUDIT = HERE / "graph_discovery_audit.json"


def material():
    a = json.loads((HERE / "source_leads.json").read_text(encoding="utf-8"))
    b = json.loads((HERE / "fields_and_bridges.json").read_text(encoding="utf-8"))
    return a, b


def build():
    packet = previous_build()
    corpus, _source, _claim = load_corpus()
    src, fields = material()
    old_modules = {m["id"] for m in corpus["modules"]}
    new_modules = {m[0] for field in fields["fields"] for m in field["modules"]}
    adjacent = {"ED-05", "PH-02", "PH-06", "WA-05", "HO-05", "HO-06",
                "FS-06", "CO-03", "WA-04", "DP-05", "AW-03", "EN-06"}
    assert len(fields["fields"]) == 4
    assert len(new_modules) == 8 and not new_modules & old_modules
    assert len(adjacent) == 12 and adjacent < old_modules
    assert len(src["source_leads"]) == 40
    assert len({s["id"] for s in src["source_leads"]}) == 40
    assert len(fields["bridges"]) == 19
    assert {s["module_id"] for s in src["source_leads"]} == adjacent | new_modules
    ids = {s["id"] for s in src["source_leads"]}
    assert all(s["layer"] in ("practical", "academic", "program") and
               s["url"].startswith("https://") and s["claim"] and s["boundary"] and
               s["geography"] and not s["outcome_efficacy_established"]
               for s in src["source_leads"])
    assert all(b["from"] in old_modules | new_modules and
               b["to"] in old_modules | new_modules and
               b["from"] != b["to"] and b["status"] == "candidate" and b["boundary"] and
               set(b["source_ids"]) <= ids for b in fields["bridges"])

    for field in fields["fields"]:
        field_key = "field_" + field["id"].lower()
        packet["clusters"].append({
            "key": field_key, "parent": "landscape_recon_root",
            "title": field["title"], "tags": ["breadth_extension", "exploratory_field"]
        })
        for module_id, title, summary in field["modules"]:
            mk = key_for_module(module_id)
            packet["clusters"].append({
                "key": mk, "title": f"{module_id} — {title}",
                "parent": field_key, "tags": ["new_field_module", "unranked", "candidate"],
                "provenance": {"summary": summary, "research_stage": "wave2"},
            })
            packet["nodes"].append({
                "key": mk, "statement": "Investigate " + title.lower() + ".",
                "kind": "research_question", "layer": "neutral", "clusters": [mk],
                "tags": ["new_field_module", "not_a_verified_problem_claim", "research_backlog"],
                "provenance": {
                    "report_module_id": module_id, "research_summary": summary,
                    "boundary": "New candidate module from breadth diversification; not an observed fact",
                },
            })

    # Source-grounded but unresolved, distinctly worded questions, not formulaic templates.
    issue_manifest = json.loads((HERE / "specific_questions.json").read_text(encoding="utf-8"))
    issues = issue_manifest["questions"]
    assert len(issues) == 20
    assert {q["module_id"] for q in issues} == {s["module_id"] for s in src["source_leads"]}
    questions = []
    keys = {}
    for q in issues:
        module_id = q["module_id"]
        question_key = "hquestion_" + module_id.lower().replace("-", "_")
        keys[module_id] = question_key
        questions.append({**q, "question_key": question_key})
        packet["nodes"].append({
            "key": question_key, "statement": q["question"],
            "kind": "research_question", "layer": "neutral",
            "clusters": [key_for_module(module_id)],
            "tags": ["unresolved", "specific_problem_question_not_evidence"],
            "provenance": {"module_id": module_id, "boundary": q["boundary"],
                           "epistemic_status": "not_yet_answered_by_current_sources"},
        })
    for source in src["source_leads"]:
        module_id = source["module_id"]
        base_key = key_for_module(module_id)
        question_key = keys[module_id]
        claim_key = "hclaim_" + source["id"].lower().replace("-", "_")
        packet["nodes"].append({
            "key": claim_key, "statement": source["claim"],
            "kind": "academic_claim" if source["layer"] == "academic"
                    else ("dataset" if source["source_type"] in {"dataset_platform", "statistics_portal", "measurement_dataset", "reporting_database", "country_policy_database"}
                          else "program" if source["layer"] == "program"
                          else "observation"),
            "layer": source["layer"], "clusters": [base_key],
            "source_refs": [source["url"]],
            "tags": ["wave2_candidate", source["source_type"], "unverified_field_outcomes"],
            "provenance": {
                "source_id": source["id"], "source_title": source["title"],
                "source_publisher": source["publisher"], "source_type": source["source_type"],
                "source_scope": source["geography"], "review_level": source["review_level"],
                "access_check": source.get("access_check"),
                "review_status": "candidate_synthesis_not_independently_replicated",
                "boundary": source["boundary"],
                "outcome_efficacy_established": False,
            },
        })
        packet["edges"].extend([
            {"source": claim_key, "target": base_key,
             "relation": "CONTEXT_FOR" if source["layer"] == "practical" else "RELATED_TO",
             "status": "candidate", "evidence_refs": [source["url"]],
             "provenance": {"source_id": source["id"], "boundary":
                            "Topical association only. " + source["boundary"]}},
            {"source": claim_key, "target": question_key, "relation": "CONTEXT_FOR",
             "status": "candidate", "evidence_refs": [source["url"]],
             "provenance": {"source_id": source["id"], "boundary":
                            "Source motivates a new question; this is NOT evidence answering the question."}},
        ])

    by_source = {s["id"]: s for s in src["source_leads"]}
    for bridge in fields["bridges"]:
        packet["edges"].append({
            "source": key_for_module(bridge["from"]),
            "target": key_for_module(bridge["to"]),
            "relation": bridge["relation"], "status": "candidate",
            "evidence_refs": [by_source[sid]["url"] for sid in bridge["source_ids"]],
            "tags": ["wave2_bridge", "cross_field_candidate" if bridge["from"].split("-")[0] != bridge["to"].split("-")[0]
                     else "within_field_candidate"],
            "provenance": {
                "bridge_id": bridge["id"], "boundary": bridge["boundary"],
                "source_ids": bridge["source_ids"],
                "inference": "co-occurrence_and_context_only_not_demonstrated_causality",
            },
        })
    packet["source_system"] = "deep_research_landscape_horizontal_wave2_20261020"
    packet["conversion_metadata"] = {
        "status": "CANDIDATE_BREADTH_EXPANSION_NOT_ACCEPTED",
        "field_count": 13, "module_count": 62,
        "old_anchor_count": 12, "adjacent_modules_with_source_leads": 12,
        "brand_new_fields": 4, "brand_new_modules": 8,
        "new_source_leads": len(src["source_leads"]),
        "new_candidate_bridges": len(fields["bridges"]),
        "source_boundary": "Source pages and report summaries are not independent primary dataset or intervention outcome verification.",
        "representation_boundary": "Program source does not mean deployed or effective intervention.",
        "no_effectiveness_asserted": True,
        "missingness": "Remaining old modules without source claims stay neutral and source-free.",
        "isolation": "Standalone snapshot: importing alongside predecessor creates overlapping nodes; import only into a new isolated project.",
    }
    return packet, questions


def analyze(packet, questions):
    nodes = {n["key"]: n for n in packet["nodes"]}
    adj = defaultdict(set)
    by_module = defaultdict(lambda: Counter())
    for e in packet["edges"]:
        if e["status"] != "candidate" or "bridge_id" not in e.get("provenance", {}):
            continue
        adj[e["source"]].add(e["target"])
        adj[e["target"]].add(e["source"])
    for n in packet["nodes"]:
        if n["layer"] != "neutral":
            for c in n["clusters"]:
                by_module[c][n["layer"]] += 1
    rows = []
    for c in packet["clusters"]:
        if "parent" not in c or not c["key"].startswith("module_"):
            continue
        mk = c["key"]
        counts = by_module[mk]
        neighbors = sorted(adj[mk])
        rows.append({
            "module_id": c["title"].split(" — ", 1)[0],
            "title": c["title"],
            "practical_claims": counts["practical"],
            "academic_claims": counts["academic"],
            "program_claims": counts["program"],
            "source_claim_count": sum(counts.values()),
            "candidate_bridge_neighbors": [x.replace("module_", "").upper() for x in neighbors],
            "candidate_degree": len(neighbors),
            "epistemic_status": "provisional",
        })
    return {
        "fields": 13,
        "modules": len(rows),
        "nodes": len(packet["nodes"]),
        "edges": len(packet["edges"]),
        "layers": dict(sorted(Counter(n["layer"] for n in packet["nodes"]).items())),
        "candidate_only": all(e["status"] == "candidate" for e in packet["edges"]),
        "new_problem_questions": len(questions),
        "rows": rows,
        "most_connected_unresolved_modules": sorted(
            [{"module_id": r["module_id"], "neighbors": r["candidate_bridge_neighbors"]}
             for r in rows if r["source_claim_count"] == 0 and r["candidate_degree"] > 0],
            key=lambda d: (-len(d["neighbors"]), d["module_id"]),
        )[:15],
        "interpretation": "Candidate relationships are imported leads, not discovered causal pathways; centrality ranks represented adjacency only.",
    }


def write():
    packet, questions = build()
    PACKET.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audit = analyze(packet, questions)
    src, _ = material()
    audit["source_http_statuses"] = dict(sorted(Counter(str(s.get("access_check", {}).get("status", "not_checked"))
                                                       for s in src["source_leads"]).items()))
    audit["program_source_kinds_wave2"] = dict(sorted(Counter(s["source_type"] for s in src["source_leads"]
                                                            if s["layer"] == "program").items()))
    audit["source_scope_warning"] = "URL reachability is not full-text verification. No intervention effectiveness established."
    audit["packet_sha256"] = hashlib.sha256(PACKET.read_bytes()).hexdigest()
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with INDEX.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["module_id", "practical_claims", "academic_claims", "program_claims",
                    "candidate_degree", "epistemic_status"])
        for row in audit["rows"]:
            w.writerow([row["module_id"], row["practical_claims"], row["academic_claims"],
                        row["program_claims"], row["candidate_degree"], row["epistemic_status"]])
    print("WROTE", PACKET.name, "fields", audit["fields"], "modules", audit["modules"],
          "nodes", audit["nodes"], "edges", audit["edges"])
    print("UNSOURCED_NEXT", [x["module_id"] for x in audit["most_connected_unresolved_modules"][:8]])
    print("DIGEST", audit["packet_sha256"])


if __name__ == "__main__":
    write()
