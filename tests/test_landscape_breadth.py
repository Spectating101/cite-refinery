"""Breadth-first map checks: source-scope, graph topology, honest empty lanes."""
import json
from pathlib import Path
import tempfile
import unittest
from collections import Counter
from cite_refinery import CiteRefinery, SemanticGraph
from scripts.build_landscape_breadth_seed import build, FIELDS

PACKET=Path(__file__).resolve().parents[1]/"examples"/"landscape_breadth_seed_v1.json"

class LandscapeBreadthTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=CiteRefinery(self.tmp.name)
        self.project=self.app.init_project("Exploratory broad problem landscape","Unranked source-backed seed")
        self.graph=SemanticGraph(self.app.store)
        self.packet=json.loads(PACKET.read_text(encoding="utf-8"))
        self.receipt=self.graph.ingest_packet(self.project.id,self.packet,packet_ref=str(PACKET))

    def tearDown(self):
        self.tmp.cleanup()

    def test_seed_is_reproducible_and_cross_field(self):
        self.assertEqual(build(),self.packet)
        self.assertEqual(len(FIELDS),9)
        self.assertEqual(len(self.packet["clusters"]),28)
        self.assertEqual(len(self.packet["nodes"]),41)
        self.assertEqual(len(self.packet["edges"]),24)
        self.assertEqual(Counter(n["layer"] for n in self.packet["nodes"]),
                         Counter({"neutral":18,"practical":10,"academic":6,"program":7}))

    def test_every_field_has_two_problem_modules(self):
        by_parent=Counter(c.get("parent") for c in self.packet["clusters"])
        self.assertEqual(by_parent["landscape_root"],9)
        for code,*_ in FIELDS:
            self.assertEqual(by_parent[code],2)

    def test_all_observations_and_programs_have_source_urls_and_bounds(self):
        for n in self.packet["nodes"]:
            if n["layer"]=="neutral":
                self.assertIn("not_a_verified_problem_claim",n["tags"])
            else:
                self.assertTrue(all(u.startswith("https://") for u in n["source_refs"]))
                self.assertTrue(n["provenance"]["boundary"])

    def test_no_claims_of_causality_solution_effectiveness_or_authority_upgrade(self):
        self.assertTrue(all(e["status"]=="candidate" for e in self.packet["edges"]))
        self.assertFalse(any(e["relation"] in {"CAUSES","PRODUCES","DEPLOYED_BY","IMPLEMENTS","SUPPORTS"} for e in self.packet["edges"]))
        self.assertTrue(all(e.get("evidence_refs") and e.get("provenance",{}).get("boundary") for e in self.packet["edges"]))

    def test_unfilled_academic_layers_remain_empty(self):
        m=self.graph.cluster_map(self.project.id)
        clusters={c["title"]:c for c in m["clusters"]}
        self.assertEqual(clusters["Hydrological monitoring gaps"]["layer_presence"],
                         {"practical":True,"academic":False,"program":True})
        self.assertEqual(clusters["Adequate housing access"]["layer_presence"],
                         {"practical":True,"academic":False,"program":False})
        self.assertEqual(clusters["Population observability"]["layer_presence"],
                         {"practical":True,"academic":True,"program":True})
        self.assertEqual(clusters["Renewable electricity systems"]["layer_presence"],
                         {"practical":True,"academic":False,"program":False})

    def test_replay_is_idempotent(self):
        again=self.graph.ingest_packet(self.project.id,self.packet,packet_ref=str(PACKET))
        self.assertEqual(self.receipt["id"],again["id"])
        state=self.app.store.load()
        self.assertEqual(len(state["semantic_nodes"]),41)
        self.assertEqual(len(state["semantic_edges"]),24)

    def test_scenarios_remain_distinct_not_merged_with_prior_pilots(self):
        self.assertEqual(self.packet["conversion_metadata"]["status"],"EXPLORATORY_UNRANKED")
        self.assertNotIn("ACCEPTED",self.packet["conversion_metadata"]["status"])
        self.assertNotIn("coverage_score",self.packet)
        self.assertTrue(all(e["status"]!="asserted" for e in self.packet["edges"]))

if __name__=="__main__":
    unittest.main()
