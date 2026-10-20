import copy
import json
from pathlib import Path
import unittest

from cite_refinery.opportunity_atlas_union import merge,markdown

ROOT=Path(__file__).resolve().parents[1]/"research_materials/opportunity_atlas"

def read(name):return json.loads((ROOT/name).read_text())

class UnionTest(unittest.TestCase):
    def test_deduplicates_exact_ids_not_subject_words(self):
        g=merge(read("atlas_network.json"),read("connected_source_graph.json"),
                read("primary_mechanism_network.json"))
        a=g["inventory_links"]
        self.assertEqual(len(a["problem_mechanism_repos"]),7)
        self.assertEqual(len(a["problem_driven_repos_absent_from_topic_search_sample"]),6)
        self.assertEqual(a["shared_verified_repository_identities"],[])
        self.assertEqual(a["cross_track_inferred_edges_created"],0)
        self.assertEqual(g["validated_outcomes"]["contracted_buyers"],0)
        self.assertIn("sampling problem",markdown(g))
        self.assertGreater(len(g["edges"]),30)
    def test_rejects_promoted_buyers_and_dangling_edges(self):
        wide=read("atlas_network.json")
        n=read("connected_source_graph.json")
        m=read("primary_mechanism_network.json")
        wrong=copy.deepcopy(n)
        wrong["edges"][0]["technical_fit_confirmed"]=True
        with self.assertRaisesRegex(ValueError,"unearned"):
            merge(wide,wrong,m)
        wrong=copy.deepcopy(m)
        wrong["edges"][0]["to"]="mechanism:invented"
        with self.assertRaisesRegex(ValueError,"dangling"):
            merge(wide,n,wrong)
    def test_does_not_reclassify_source_claim_as_outcome(self):
        result=merge(read("atlas_network.json"),read("connected_source_graph.json"),
                     read("primary_mechanism_network.json"))
        self.assertEqual(result["validated_outcomes"]["causal_public_health_outcomes"],0)
        self.assertTrue(all(x["layer"] in
            {"institutional_published_requirements","original_source_mechanisms"}
            for x in result["edges"]))
