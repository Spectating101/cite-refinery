"""Evidence boundaries and reproducible import for the 54-module reconnaissance."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery import CiteRefinery, SemanticGraph
from scripts.build_landscape_research_wave1 import build, load_corpus, PACKET, INDEX


class LandscapeResearchWave1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = json.loads(PACKET.read_text(encoding="utf-8"))
        cls.registry, cls.ledger, cls.claim_pack = load_corpus()

    def test_deterministic_packet_and_report_registry(self):
        self.assertEqual(build(), self.packet)
        self.assertEqual(len(self.registry["fields"]), 9)
        self.assertEqual(len(self.registry["modules"]), 54)
        self.assertEqual(len(self.registry["anchor_order"]), 12)
        self.assertEqual(len(self.packet["clusters"]), 64)
        self.assertEqual(len(self.packet["nodes"]), 78)
        self.assertEqual(len(self.packet["edges"]), 35)
        self.assertEqual(Counter(n["layer"] for n in self.packet["nodes"]),
                         Counter({"neutral": 54, "practical": 10, "academic": 5, "program": 9}))

    def test_second_ring_remains_unverified(self):
        anchors = set(self.registry["anchor_order"])
        claims = self.claim_pack["claims"]
        self.assertTrue(all(c["module_id"] in anchors for c in claims))
        self.assertEqual(len([m for m in self.registry["modules"] if m["id"] not in anchors]), 42)
        self.assertTrue(all(n["source_refs"] == [] for n in self.packet["nodes"]
                            if n["layer"] == "neutral" and "source_refs" in n))
        self.assertTrue(all("not_a_verified_problem_claim" in n["tags"] for n in self.packet["nodes"]
                            if n["layer"] == "neutral"))

    def test_source_ledger_and_claims_are_traceable(self):
        sources = {s["id"]: s for s in self.ledger["sources"]}
        self.assertEqual(len(sources), 23)
        self.assertEqual(len(self.claim_pack["claims"]), 24)
        self.assertEqual(len(self.claim_pack["bridges"]), 11)
        self.assertTrue(all(c["source_id"] in sources and c["boundary"]
                            for c in self.claim_pack["claims"]))
        for node in self.packet["nodes"]:
            if node["layer"] == "neutral":
                self.assertFalse(node.get("source_refs"))
                continue
            self.assertEqual(len(node["source_refs"]), 1)
            self.assertTrue(node["source_refs"][0].startswith("https://"))
            self.assertEqual(node["source_refs"][0], sources[node["provenance"]["source_id"]]["url"])
            self.assertTrue(node["provenance"]["boundary"])
            self.assertTrue(node["provenance"]["review_level"])

    def test_all_relationships_are_candidate_and_bounded(self):
        self.assertTrue(all(e["status"] == "candidate" and e["evidence_refs"]
                            and e["provenance"]["boundary"] for e in self.packet["edges"]))
        self.assertFalse(any(e["relation"] in {"CAUSES", "SUPPORTS", "ADDRESSES",
                                               "PARTIALLY_ADDRESSES", "PRODUCES",
                                               "IMPLEMENTS", "DEPLOYED_BY"} for e in self.packet["edges"]))
        self.assertNotIn("coverage_score", self.packet)
        self.assertIn("NOT_ACCEPTED", self.packet["conversion_metadata"]["status"])

    def test_csv_has_all_modules_and_honest_layer_counts(self):
        with INDEX.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 54)
        by_id = {r["module_id"]: r for r in rows}
        self.assertEqual([by_id["CO-01"][k] for k in
                          ("practical_claims", "academic_claims", "program_claims")],
                         ["1", "1", "1"])
        self.assertEqual([by_id["DP-03"][k] for k in
                          ("practical_claims", "academic_claims", "program_claims")],
                         ["0", "1", "0"])
        self.assertEqual([by_id["FS-01"][k] for k in
                          ("practical_claims", "academic_claims", "program_claims")],
                         ["1", "0", "0"])
        self.assertEqual([by_id["HO-06"][k] for k in
                          ("practical_claims", "academic_claims", "program_claims")],
                         ["0", "0", "0"])

    def test_isolated_graph_import_and_idempotence(self):
        with TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project = app.init_project("Deep Research breadth-first map", "Isolated candidate graph")
            graph = SemanticGraph(app.store)
            receipt = graph.ingest_packet(project.id, self.packet, packet_ref=str(PACKET))
            state = app.store.load()
            self.assertEqual(len(state["semantic_clusters"]), 64)
            self.assertEqual(len(state["semantic_nodes"]), 78)
            self.assertEqual(len(state["semantic_edges"]), 35)
            again = graph.ingest_packet(project.id, self.packet, packet_ref=str(PACKET))
            self.assertEqual(receipt["id"], again["id"])
            cmap = graph.cluster_map(project.id)
            by_title = {c["title"]: c for c in cmap["clusters"]}
            self.assertEqual(by_title["CO-01 — Usage gap and meaningful connectivity"]["layer_presence"],
                             {"practical": True, "academic": True, "program": True})
            self.assertEqual(by_title["DP-03 — Foundation-model privacy leakage"]["layer_presence"],
                             {"practical": False, "academic": True, "program": False})
            self.assertEqual(by_title["HO-06 — Building efficiency and retrofit affordability"]["layer_presence"],
                             {"practical": False, "academic": False, "program": False})


if __name__ == "__main__":
    unittest.main()
