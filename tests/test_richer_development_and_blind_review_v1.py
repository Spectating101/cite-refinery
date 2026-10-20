"""Held-out review packet is blank, development conversion excludes quota labels."""
from __future__ import annotations
import copy
import json
import unittest

from cite_refinery.richer_development_prep import build_development_map_input
from cite_refinery.richer_evidence_cli import blind_annotation_queue

def fake():
    row={
        "id":"PMC-ABC","canonical_url":"https://europepmc.org/articles/PMC123",
        "title":"Specific longitudinal observations in cities",
        "text":("A repeated study observed how different environmental conditions "
                "were associated with health in different community settings. ")*50,
        "type":"full_text_jats","source_scope":"Research text, not independently validated",
        "retrieval_url":"https://www.ebi.ac.uk/rest/example",
        "collection_quota":"s02","document_date":"2023-07-06",
        "text_sha256":__import__("hashlib").sha256((("A repeated study observed how different environmental conditions "
                "were associated with health in different community settings. ")*50).encode()).hexdigest()
    }
    return row

class MappingPrivacyTests(unittest.TestCase):
    def test_mapper_cannot_receive_collection_quota_or_holdout_text(self):
        entry=fake()
        dev={"schema":"cite_refinery.richer_development_materials.v1",
             "source_count":1,"sources":[entry],"holdout_text_not_in_this_file":True}
        mapped=build_development_map_input(dev)
        self.assertEqual(mapped["source_count"],1)
        src=mapped["sources"][0]
        self.assertNotIn("collection_quota",src)
        self.assertTrue(mapped["heldout_sources_in_this_file"] is False)
        self.assertEqual(src["origin_type"],"scholarly_open_access_fulltext_unverified")
        self.assertLessEqual(len(src["text"]),9000)
        not_safe=copy.deepcopy(dev);not_safe["holdout_text_not_in_this_file"]=False
        with self.assertRaisesRegex(ValueError,"development-only"):
            build_development_map_input(not_safe)
    def test_blind_queue_has_no_model_results_or_gold_labels(self):
        doc=fake()
        p={"schema":"cite_refinery.frozen_corpus_partition.v1",
           "held_out":[doc],"development":[doc],"seed":"fixture"}
        queue=blind_annotation_queue(p)
        self.assertEqual(queue["holdout_source_count"],1)
        self.assertIsNone(queue["items"][0]["role"])
        self.assertFalse(queue["model_classifications_visible"])
        self.assertEqual(queue["status"],"blank_no_external_ground_truth")
    def test_unrecognized_dataset_genre_fails_closed(self):
        dev={"schema":"cite_refinery.richer_development_materials.v1",
             "source_count":1,"sources":[{**fake(),"type":"quantum_provenance_verified"}],
             "holdout_text_not_in_this_file":True}
        with self.assertRaisesRegex(ValueError,"Unknown material genre"):
            build_development_map_input(dev)
if __name__=="__main__":
    unittest.main()
