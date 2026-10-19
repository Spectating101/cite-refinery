"""Review gates for the provisional 12-anchor, three-layer research wave."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery import CiteRefinery, SemanticGraph
from scripts.build_landscape_anchor_wave_v0_1 import (
    AUDIT, INDEX, PACKET, build, read, validate,
)
from scripts.build_landscape_research_wave1 import load_corpus


class AnchorWaveV01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = json.loads(PACKET.read_text(encoding="utf-8"))
        cls.ledger = read("anchor_sources_v0_1.json")["sources"]
        cls.sids = {s["id"]: s for s in cls.ledger}
        cls.registry, _, _ = load_corpus()
        cls.audit = json.loads(AUDIT.read_text(encoding="utf-8"))

    def test_deterministic_export_and_breadth_first_scope(self):
        self.assertEqual(build(), self.packet)
        self.assertEqual(len(self.packet["clusters"]), 64)
        self.assertEqual(len(self.packet["nodes"]), 145)
        self.assertEqual(len(self.packet["edges"]), 107)
        self.assertEqual(Counter(n["layer"] for n in self.packet["nodes"]),
                         Counter({"neutral": 90, "practical": 23, "academic": 15, "program": 17}))
        self.assertEqual(len(self.registry["modules"]), 54)
        self.assertEqual(len(self.registry["anchor_order"]), 12)
        self.assertEqual(hashlib.sha256(PACKET.read_bytes()).hexdigest(), self.audit["packet_sha256"])

    def test_evidence_nodes_have_resolvable_provenance(self):
        self.assertEqual(len(self.ledger), 36)
        for n in self.packet["nodes"]:
            if n["layer"] == "neutral":
                self.assertFalse(n.get("source_refs"))
                continue
            prov = n["provenance"]
            self.assertIn(prov["source_id"], self.sids)
            source = self.sids[prov["source_id"]]
            self.assertEqual(n["source_refs"], [source["url"]])
            for k in ("source_scope", "boundary", "review_level", "source_type", "source_date", "review_status"):
                self.assertTrue(prov[k], (n["key"], k))
            self.assertEqual(prov["outcome_evidence"], "not_established_by_this_packet")
        self.assertTrue(all(s["access"]["note"] for s in self.ledger))

    def test_missing_lanes_not_synthetically_filled(self):
        coverage = defaultdict(set)
        for s in self.ledger:
            coverage[s["module_id"]].add(s["layer"])
        self.assertEqual(set(coverage), set(self.registry["anchor_order"]))
        self.assertTrue(all(lanes == {"practical", "academic", "program"} for lanes in coverage.values()))
        for module_id, row in self.audit["source_coverage_by_module"].items():
            is_anchor = module_id in coverage
            self.assertEqual(set(row["sources_by_layer"].values()), {1} if is_anchor else {0})
            self.assertEqual(row["review_state"],
                             "source_candidate_only" if is_anchor else "unresearched_in_this_wave")
        self.assertEqual(self.audit["unresearched_second_ring_count"], 42)
        self.assertEqual(self.audit["unresolved_atomic_problem_questions"], 36)
        self.assertTrue(all(n["tags"].count("unresolved") == 1 for n in self.packet["nodes"]
                            if n["key"].startswith("question_")))

    def test_program_classification_not_false_effectiveness(self):
        p = [s for s in self.ledger if s["layer"] == "program"]
        self.assertEqual(len(p), 12)
        kinds = Counter(s["source_type"] for s in p)
        self.assertEqual(kinds["dataset_platform"], 5)
        self.assertEqual(kinds["bounded_implementation_test"], 1)
        self.assertEqual(kinds["measurement_framework"], 1)
        self.assertTrue(all("outcome_evidence" in n["provenance"] for n in self.packet["nodes"]
                            if n["layer"] == "program"))
        self.assertFalse(any(n.get("tags", []).count("proven_effective") for n in self.packet["nodes"]))
        self.assertEqual(self.sids["DP-G"]["access"]["http_status"], 404)
        self.assertIn("connected github", self.sids["DP-G"]["access"]["note"].lower())
        self.assertEqual(self.sids["DP-P"]["source_type"], "regulatory_guidance")

    def test_edge_strength_does_not_exceed_evidence(self):
        permitted = {"CONTEXT_FOR", "RELATED_TO", "PROVIDES_DATA_FOR"}
        self.assertEqual(len(self.packet["edges"]), 107)
        self.assertTrue(all(e["relation"] in permitted and
                            e["status"] == "candidate" and e["evidence_refs"] and
                            e["provenance"]["boundary"] for e in self.packet["edges"]))
        self.assertFalse(any(e["relation"] in {"CAUSES", "SUPPORTS", "ADDRESSES",
                                               "DEPLOYED_BY", "PARTIALLY_ADDRESSES",
                                               "PRODUCES", "IMPLEMENTS"} for e in self.packet["edges"]))
        bridges = [e for e in self.packet["edges"] if "bridge_id" in e["provenance"]]
        self.assertEqual(len(bridges), 16)
        self.assertTrue(all(e["provenance"]["epistemic_state"] == "not_causally_established"
                            for e in bridges))

    def test_scope_and_uncertainty_not_promoted(self):
        self.assertTrue(all(n["provenance"]["review_status"] == "candidate_not_accepted"
                            for n in self.packet["nodes"] if n["layer"] != "neutral"))
        self.assertEqual(self.packet["conversion_metadata"]["status"],
                         "CANDIDATE_RESEARCH_NOT_ACCEPTED")
        self.assertFalse(any(e["status"] == "qualified" for e in self.packet["edges"]))
        # Restricted pages remain identifiable, not falsely promoted to full-text review.
        self.assertGreater(sum(s["access"]["http_status"] == 403 for s in self.ledger), 0)
        for n in self.packet["nodes"]:
            if n["layer"] != "neutral":
                self.assertIn("not_full_primary_audit", n["provenance"]["review_level"])

    def test_csv_and_audit_are_coherent(self):
        with INDEX.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 54)
        self.assertEqual(sum(int(r["Practical_sources"]) for r in rows), 12)
        self.assertEqual(sum(int(r["Academic_sources"]) for r in rows), 12)
        self.assertEqual(sum(int(r["Program_sources"]) for r in rows), 12)
        self.assertEqual(self.audit["source_count"], 36)
        self.assertEqual(self.audit["candidate_atomic_evidence_nodes"], 55)
        self.assertEqual(self.audit["candidate_cross_module_bridges"], 16)

    def test_deterministic_idempotent_and_isolated_import(self):
        with TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project = app.init_project("Landscape trial", "Isolated, not accepted")
            graph = SemanticGraph(app.store)
            receipt = graph.ingest_packet(project.id, self.packet, packet_ref=str(PACKET))
            state = app.store.load()
            self.assertEqual(len(state["semantic_clusters"]), 64)
            self.assertEqual(len(state["semantic_nodes"]), 145)
            self.assertEqual(len(state["semantic_edges"]), 107)
            replay = graph.ingest_packet(project.id, self.packet, packet_ref=str(PACKET))
            self.assertEqual(receipt["id"], replay["id"])
            self.assertEqual(app.store.load(), state)
            report = graph.cluster_map(project.id)
            by_title = {c["title"]: c for c in report["clusters"]}
            self.assertEqual(by_title["CO-01 — Usage gap and meaningful connectivity"]["layer_presence"],
                             {"practical": True, "academic": True, "program": True})
            self.assertEqual(by_title["HO-06 — Building efficiency and retrofit affordability"]["layer_presence"],
                             {"practical": False, "academic": False, "program": False})


if __name__ == "__main__":
    unittest.main()
