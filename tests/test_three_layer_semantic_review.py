from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from cite_refinery.three_layer_semantic_review import build,markdown,SCHEMA

ROOT=Path(__file__).resolve().parents[1]/"research_materials/opportunity_atlas"

def load(name):
    return json.loads((ROOT/name).read_text())

class AcademicRiskReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph=load("three_layer_unified_atlas.json")
        cls.diagnostic=load("semantic_entailment_diagnostic_results.json")

    def test_overlay_covers_actual_research_problems_without_promotion(self):
        out=build(self.graph,self.diagnostic)
        self.assertEqual(out["schema"],SCHEMA)
        self.assertEqual(out["counts"]["covered_practical_academic_pairs"],8)
        self.assertEqual(out["counts"]["unreviewed_mechanism_entailments"],8)
        self.assertEqual(out["counts"]["qualified_academic_edges_promoted"],0)
        self.assertEqual(out["counts"]["validated_technical_fit"],0)
        self.assertEqual(out["counts"]["validated_commercial_value"],0)
        for row in out["semantic_review_queue"]:
            self.assertFalse(row["promotion_allowed"])
            self.assertFalse(row["atomic_entailment_is_mechanism_proof"])
            self.assertEqual(row["mechanism_entailment_status"],
                             "unreviewed_aggregate_cross_source_reasoning")
            self.assertEqual(len(row["inspected_claim_ids"]),3)
        result=markdown(out)
        self.assertIn("mechanism-to-implementation fit",result)
        self.assertIn("Unsupported",result)

    def test_diagnostic_promotion_attempt_blocked(self):
        fake=deepcopy(self.diagnostic)
        fake["graph_promotion_allowed"]=True
        with self.assertRaisesRegex(ValueError,"untrusted"):
            build(self.graph,fake)
        fake=deepcopy(self.diagnostic)
        fake["cases"][0]["commercial_or_scientific_status_promoted"]=True
        with self.assertRaisesRegex(ValueError,"promoted"):
            build(self.graph,fake)

    def test_missing_identity_blocks_semantic_join(self):
        bad=deepcopy(self.graph)
        bad["nodes"]=[n for n in bad["nodes"] if n["id"]!="mechanism:battery_recycling_economics"]
        with self.assertRaisesRegex(ValueError,"exact practical-academic"):
            build(bad,self.diagnostic)
        bad=deepcopy(self.graph)
        bad["problem_views"]["problem:battery_recycling_economics"]["academic_nodes"]=[]
        with self.assertRaisesRegex(ValueError,"supported source-to-mechanism"):
            build(bad,self.diagnostic)

    def test_reference_disagreement_is_review_not_economic_value(self):
        out=build(self.graph,self.diagnostic)
        self.assertGreaterEqual(out["counts"]["model_disagreements"],0)
        self.assertTrue(all(v["model_verdicts"] for v in out["semantic_review_queue"]))
        self.assertTrue(all("scientific" in out["boundary"] or
                            "human validation" in out["boundary"] for _ in [0]))

if __name__=="__main__":
    unittest.main()
