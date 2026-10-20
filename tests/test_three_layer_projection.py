from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest

from cite_refinery.three_layer_projection import SCHEMA, project, explain, render_markdown

ROOT=Path(__file__).resolve().parents[1]/"research_materials/opportunity_atlas"

def load(name):
    return json.loads((ROOT/name).read_text())

class ThreeLayerProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.primary=load("primary_mechanism_network.json")
        cls.institutional=load("connected_source_graph.json")

    def test_real_view_three_layers_not_two_networks(self):
        r=project(self.primary,self.institutional)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["layers"],["practical","academic","implementation"])
        self.assertEqual(r["coverage"]["practical"],21)
        self.assertEqual(r["coverage"]["academic"],8)
        self.assertEqual(r["coverage"]["implementation"],21)
        self.assertEqual(r["coverage"]["problems_with_all_three_layers_represented"],7)
        self.assertEqual(r["coverage"]["validated_end_to_end_solutions"],0)
        self.assertEqual(r["coverage"]["confirmed_paying_customers"],0)
        self.assertEqual(r["coverage"]["neutral_source_nodes_as_fourth_layer"],0)
        self.assertEqual(len(r["nodes"]),len({x["id"] for x in r["nodes"]}))
        self.assertEqual({x["layer"] for x in r["nodes"]},set(r["layers"]))
        self.assertTrue(r["safety"]["not_merged_into_persistent_project_graph"])
        doc=render_markdown(r)
        self.assertIn("One graph, three evidence layers",doc)
        self.assertIn("Published notice:",doc)
        self.assertIn("end-to-end validated",doc)

    def test_mechanism_case_is_three_layers_without_false_verification(self):
        r=project(self.primary,self.institutional)
        x=explain(r,"problem:battery_recycling_economics")
        self.assertTrue(x["three_layers_represented"])
        self.assertFalse(x["end_to_end_validated"])
        self.assertFalse(x["buyer_validated"])
        self.assertEqual(len(x["academic"]),1)
        self.assertEqual(len(x["implementations"]),1)
        self.assertEqual(x["implementations"][0]["relation"],"POSSIBLE_PARTIAL_IMPLEMENTATION")
        self.assertTrue(x["academic"][0]["provenance"])
        self.assertTrue(x["practical"]["provenance"])

    def test_institutional_requirement_has_no_invented_scientific_link(self):
        r=project(self.primary,self.institutional)
        x=explain(r,"ted:725724-2026")
        self.assertFalse(x["three_layers_represented"])
        self.assertEqual(x["academic"],[])
        self.assertTrue(any(g["missing_layer"]=="academic" for g in x["gaps"]))
        self.assertTrue(all(g["not_global_absence"] for g in x["gaps"]))
        self.assertEqual(x["implementations"][0]["relation"],"POSSIBLE_PARTIAL_IMPLEMENTATION")

    def test_explicit_no_match_does_not_hallucinate_implementation(self):
        r=project(self.primary,self.institutional)
        x=explain(r,"problem:gig_worker_algorithmic_harm")
        self.assertEqual(x["implementations"],[])
        self.assertFalse(x["three_layers_represented"])
        self.assertTrue(any(g["missing_layer"]=="implementation" for g in x["gaps"]))

    def test_exact_identity_only_and_rejects_claim_promotion(self):
        r=project(self.primary,self.institutional)
        paths=set((e["from"],e["to"]) for e in r["edges"])
        self.assertNotIn(("mechanism:battery_recycling_economics","ted:725724-2026"),paths)
        self.assertNotIn(("github:lingrany/EverBatt-LFP-Recycling-Analysis","ted:725724-2026"),paths)
        self.assertTrue(all(not e["technical_fit_verified"] for e in r["edges"]))
        bad=copy.deepcopy(self.institutional)
        bad["links"][0]["relation"]="CLAIMED_CONTRACT"
        with self.assertRaisesRegex(ValueError,"unrecognized"):
            project(self.primary,bad)

    def test_reproducible_readonly(self):
        p=copy.deepcopy(self.primary)
        i=copy.deepcopy(self.institutional)
        self.assertEqual(project(p,i),project(p,i))
        self.assertEqual(p,self.primary)
        self.assertEqual(i,self.institutional)

    def test_wrong_layer_and_unknown_problem_fail(self):
        bad=copy.deepcopy(self.primary)
        bad["briefs"][0]["id"]="mechanism:invented" # source product needs exact mechanism
        with self.assertRaisesRegex(ValueError,"unknown|invalid|source"):
            # No basic ID mismatch yet: this extra check is enforced below.
            project(bad,self.institutional)
        with self.assertRaises(KeyError):
            explain(project(self.primary,self.institutional),"problem:invented")
