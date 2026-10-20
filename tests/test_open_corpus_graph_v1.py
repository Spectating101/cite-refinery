"""Open corpus neutral graph conversion + pending blank human annotation pack."""
from __future__ import annotations
import copy
import unittest
from cite_refinery.open_corpus_graph import packet
from cite_refinery.open_corpus_review import create_review_queue,public_queue_stub

def toy():
    sources=[{"id":f"S-{i}","url":f"https://doi.org/10.1000/x{i}",
              "title":"Independent journal content","text":"A hypothetical study discusses field measurements.",
              "sha256":str(i)*64,"origin_type":"scholarly_abstract_lead"} for i in range(8)]
    provisional={"schema":"cite_refinery.open_corpus_provisional_map.v1",
       "readings":[{"source_id":x["id"],"source_url":x["url"],"source_sha256":x["sha256"],
                    "quote_sha256":"a"*64,"role":"academic_method","fit":"relevant",
                    "statement":"Study describes measurement under uncertainty.",
                    "caveat":"No independent replication"} for x in sources]}
    atlas={"schema":"cite_refinery.open_corpus_atlas.v1","mapped_source_count":8,
           "domains":[{"label":"Specific measurement node cluster "+str(i),
                       "source_ids":[sources[i*2]["id"],sources[i*2+1]["id"]],
                       "problem_node":"Uncertain exposure metrics",
                       "measurement_node":"Measurements need calibration",
                       "intervention_node":"No implementation observed",
                       "evidence_limit":"Missing original validation",
                       "questions":["Does real field validation exist?"]} for i in range(4)],
           "cross_domain_links":[]}
    return sources,provisional,atlas

class OpenCorpusGraphTests(unittest.TestCase):
    def test_all_sources_become_neutral_nodes_and_no_causality(self):
        src,prov,atlas=toy()
        graph=packet(atlas,prov)
        self.assertEqual(len(graph["nodes"]),16)
        self.assertEqual(len(graph["edges"]),12)
        self.assertTrue(all(n["layer"]=="neutral" for n in graph["nodes"]))
        self.assertTrue(all(e["status"] in {"candidate","unresolved"} for e in graph["edges"]))
        self.assertNotIn("CAUSES",{e["relation"] for e in graph["edges"]})
        self.assertEqual(graph["conversion_metadata"]["accepted_scientific_conclusions"],0)
    def test_provenance_mapping_fails_when_sources_disappear(self):
        src,prov,atlas=toy()
        atlas["domains"][0]["source_ids"][0]="missing-foreign"
        with self.assertRaisesRegex(ValueError,"Unknown atlas source"):packet(atlas,prov)
    def test_blind_review_has_no_model_labels(self):
        src,_,_=toy()
        corpus={"schema":"cite_refinery.open_corpus.v1","sources":src}
        q=create_review_queue(corpus,per_origin=4)
        self.assertEqual(q["source_count"],4)
        self.assertTrue(all(e["role_annotation"] is None for e in q["items"]))
        self.assertTrue(all("source_text" in e for e in q["items"]))
        stub=public_queue_stub(q)
        self.assertNotIn("source_text",str(stub))
        self.assertEqual(stub["gold_label_count"],0)
if __name__=="__main__":unittest.main()
