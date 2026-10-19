"""Horizontal breadth expansion: regression, evidence honesty, topology and isolation."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery import CiteRefinery, SemanticGraph
from scripts.build_landscape_horizontal_wave2 import (
    PACKET, AUDIT, INDEX, material, build, analyze,
)


class HorizontalWave2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = json.loads(PACKET.read_text(encoding="utf-8"))
        cls.audit = json.loads(AUDIT.read_text(encoding="utf-8"))
        cls.sources, cls.fields = material()
        cls.refs = {r["id"]: r for r in cls.sources["source_leads"]}

    def test_breadth_counts_and_roundtrip(self):
        rebuilt, questions = build()
        self.assertEqual(rebuilt, self.packet)
        self.assertEqual(len(questions), 20)
        self.assertEqual(len(self.fields["fields"]), 4)
        self.assertEqual(len(self.fields["bridges"]), 19)
        self.assertEqual(len(self.packet["clusters"]), 76)
        self.assertEqual(len(self.packet["nodes"]), 213)
        self.assertEqual(len(self.packet["edges"]), 206)
        self.assertEqual(len(self.audit["rows"]), 62)
        self.assertEqual(self.audit["layers"],
                         {"academic": 17, "neutral": 118, "practical": 43, "program": 35})
        self.assertEqual(hashlib.sha256(PACKET.read_bytes()).hexdigest(), self.audit["packet_sha256"])

    def test_new_field_topics_and_old_empty_modules(self):
        current = {r["module_id"]: r for r in self.audit["rows"]}
        self.assertEqual(len({r["module_id"].split("-")[0] for r in self.audit["rows"]}), 13)
        self.assertTrue({"LM-01", "LM-02", "TR-01", "TR-02",
                         "AQ-01", "AQ-02", "DR-01", "DR-02"} <= set(current))
        self.assertEqual(len([r for r in self.audit["rows"] if r["source_claim_count"] == 0]), 30)
        self.assertEqual(current["AW-05"]["source_claim_count"], 0)
        self.assertEqual(current["CO-02"]["source_claim_count"], 0)
        self.assertGreater(current["PH-02"]["source_claim_count"], 0)

    def test_new_evidence_provenance_and_access_limits(self):
        new_nodes = [n for n in self.packet["nodes"] if n["key"].startswith("hclaim_")]
        self.assertEqual(len(new_nodes), 40)
        for node in new_nodes:
            prov = node["provenance"]
            self.assertIn(prov["source_id"], self.refs)
            source = self.refs[prov["source_id"]]
            self.assertEqual(node["source_refs"], [source["url"]])
            self.assertTrue(prov["source_scope"] and prov["boundary"] and prov["review_level"])
            self.assertEqual(prov["access_check"]["status"], source["access_check"]["status"])
            self.assertIs(prov["outcome_efficacy_established"], False)
        self.assertEqual(self.audit["source_http_statuses"], {"200": 28, "403": 11, "web_page_confirmed": 1})
        self.assertEqual(self.refs["H-22"]["source_type"], "standard_and_guidance")
        self.assertIn("en_chapitre_aw_stray_dog.htm", self.refs["H-22"]["url"])

    def test_no_synthetic_three_layer_completion(self):
        represented = defaultdict(set)
        for node in self.packet["nodes"]:
            if node["layer"] == "neutral":
                continue
            for module in node["clusters"]:
                if module.startswith("module_"):
                    represented[module].add(node["layer"])
        self.assertEqual(represented["module_ph_02"], {"practical"})
        self.assertEqual(represented["module_aq_02"], {"academic", "program"})
        self.assertFalse(represented["module_aw_05"])
        self.assertTrue(all(node["layer"] == "neutral" and not node.get("source_refs")
                            for node in self.packet["nodes"] if node["key"].startswith("hquestion_")))
        self.assertEqual(len([node for node in self.packet["nodes"] if node["key"].startswith("hquestion_")]), 20)

    def test_edge_causality_and_program_efficacy_not_invented(self):
        self.assertTrue(all(e["status"] == "candidate" and e["evidence_refs"] and
                            e["provenance"].get("boundary") for e in self.packet["edges"]))
        self.assertFalse(any(e["relation"] in {"CAUSES", "SUPPORTS", "DEPLOYED_BY",
                                              "IMPLEMENTS", "PRODUCES", "ADDRESSES"} for e in self.packet["edges"]))
        new_bridges = [e for e in self.packet["edges"] if e["provenance"].get("bridge_id", "").startswith("HBR-")]
        self.assertEqual(len(new_bridges), 19)
        self.assertTrue(all(e["provenance"]["inference"] ==
                            "co-occurrence_and_context_only_not_demonstrated_causality" for e in new_bridges))
        self.assertEqual(self.packet["conversion_metadata"]["status"],
                         "CANDIDATE_BREADTH_EXPANSION_NOT_ACCEPTED")

    def test_graph_topology_is_rank_of_represented_edges_only(self):
        pending = self.audit["most_connected_unresolved_modules"]
        self.assertGreater(len(pending), 0)
        self.assertEqual(pending[0]["module_id"], "HO-03")
        self.assertEqual(pending[1]["module_id"], "WA-03")
        self.assertIn("not discovered causal pathways", self.audit["interpretation"])

    def test_isolated_import_idempotence_and_older_artifacts_untouched(self):
        with TemporaryDirectory() as temp:
            app = CiteRefinery(temp)
            project = app.init_project("Horizontal v2 trial", "isolation")
            graph = SemanticGraph(app.store)
            receipt = graph.ingest_packet(project.id, self.packet, packet_ref=str(PACKET))
            first = app.store.load()
            self.assertEqual(len(first["semantic_nodes"]), 213)
            self.assertEqual(len(first["semantic_edges"]), 206)
            self.assertEqual(len(first["semantic_clusters"]), 76)
            same = graph.ingest_packet(project.id, self.packet, packet_ref=str(PACKET))
            self.assertEqual(receipt["id"], same["id"])
            self.assertEqual(first, app.store.load())
            cmap = graph.cluster_map(project.id)
            by_title = {c["title"]: c for c in cmap["clusters"]}
            self.assertEqual(by_title["AQ-02 — Air-quality standards, measurement and comparability"]["layer_presence"],
                             {"practical": False, "academic": True, "program": True})
            self.assertEqual(by_title["AW-05 — Farmed-animal welfare measurement"]["layer_presence"],
                             {"practical": False, "academic": False, "program": False})


if __name__ == "__main__":
    unittest.main()
