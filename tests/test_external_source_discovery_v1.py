"""Evidence-first discovery is explicitly candidate only and reproducible."""
from __future__ import annotations

import hashlib
import json
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest

try:
    import numpy as np
except ImportError:
    np = None

from cite_refinery import CiteRefinery, SemanticGraph
from cite_refinery.external_semantic_discovery import (
    read_module_catalog, encode_documents, proposal_pairs,
    sentence_fragments, aggregate_sentence_rankings,
)
from cite_refinery.external_requirement_graph import stage_source_module_review
from scripts.external_source_first_discovery_v1 import evaluate, read_snapshot

class FakeEncoder:
    def encode(self, texts, *, normalize_embeddings=True, convert_to_numpy=True):
        # Stable vector example exercises module ranking without loading ML weights
        mapping={"Water access":[1.0,0.0],"Health services":[0.0,1.0],
                 "water quality status":[.97,.25]}
        return np.asarray([mapping[x] for x in texts],dtype=np.float32)

class SemanticDiscoveryTests(unittest.TestCase):
    @unittest.skipIf(np is None, "NumPy belongs to the optional semantic_discovery extra")
    def test_source_retrieval_and_ranked_candidates(self):
        mods=[{"id":"WA-01","title":"Water access","summary":""},
              {"id":"PH-01","title":"Health services","summary":""}]
        source=[{"id":"WATER","url":"https://example.org/water","text":"water quality status"}]
        class Encoder:
            def encode(self,texts,**kwargs):
                return np.asarray([[1.0,0.0],[0.0,1.0],[.96,.28]],dtype=np.float32)
        rows=encode_documents(mods,source,embedder=Encoder())
        self.assertEqual(rows[0]["ranked_modules"][0]["module_id"],"WA-01")
        self.assertEqual(rows[0]["review_status"],"semantic_similarity_only_not_claim_support")
        self.assertEqual(proposal_pairs(rows,top_k=2,min_score=.5),[])

    def test_no_unverified_source_to_source_causality(self):
        modules=[{"id":"WA-06","title":"Hydrology","summary":"Hydrological status"},
                 {"id":"DR-01","title":"Warning","summary":"Early warning"}]
        source=[{"id":"WMO","url":"https://example.org/wmo",
                 "text":"Hydrological status informs early warning services."}]
        digest=hashlib.sha256(source[0]["text"].encode()).hexdigest()
        ranking=[{"source_id":"WMO","source_url":source[0]["url"],
                  "source_passage_sha256":digest,
                  "ranked_modules":[
                      {"module_id":"WA-06","score":.86,"rank":1,"title":"Hydrology"},
                      {"module_id":"DR-01","score":.76,"rank":2,"title":"Warning"},
                  ]}]
        packet=stage_source_module_review(modules,source,ranking,top_k=2)
        self.assertEqual(len(packet["nodes"]),3)
        self.assertEqual(len(packet["edges"]),2)
        self.assertTrue(packet["conversion_metadata"]["no_module_to_module_edges"])
        self.assertTrue(packet["conversion_metadata"]["no_accepted_evidence"])
        self.assertTrue(all(e["status"]=="candidate" and e["source"].startswith("source_")
                            and e["relation"]=="CONTEXT_FOR" for e in packet["edges"]))
        self.assertTrue(all(n["layer"]=="neutral" for n in packet["nodes"]))
        self.assertTrue(all("boundary" in e["provenance"] for e in packet["edges"]))
        with TemporaryDirectory() as directory:
            app=CiteRefinery(directory)
            project=app.init_project("Source review","No accepted evidence")
            graph=SemanticGraph(app.store)
            first=graph.ingest_packet(project.id,packet)
            state=app.store.load()
            second=graph.ingest_packet(project.id,packet)
            self.assertEqual(first["id"],second["id"])
            self.assertEqual(app.store.load(),state)

    def test_reject_modified_evidence_and_unknown_modules(self):
        mods=[{"id":"WA-06","title":"Hydrology","summary":"Status"}]
        source=[{"id":"WMO","url":"https://example.org/wmo","text":"A verified source paragraph"}]
        bad=[{"source_id":"WMO","source_passage_sha256":"bad",
              "ranked_modules":[{"module_id":"WA-06","score":.8,"rank":1}]}]
        with self.assertRaises(ValueError):
            stage_source_module_review(mods,source,bad)
        good=[{"source_id":"WMO","source_passage_sha256":hashlib.sha256(source[0]["text"].encode()).hexdigest(),
              "ranked_modules":[{"module_id":"WA-99","score":.8,"rank":1}]}]
        with self.assertRaises(ValueError):
            stage_source_module_review(mods,source,good)

    def test_sentence_level_review_preserves_exact_quote_and_no_inferred_edges(self):
        source=[{"id":"WMO", "url":"https://example.org/wmo",
                 "text":"Monitoring observes the hydrological status of a river. "
                        "An early warning system communicates flood risk to people."}]
        fragments=sentence_fragments(source)
        self.assertEqual(len(fragments),2)
        self.assertTrue(all(f["text"] in source[0]["text"] for f in fragments))
        self.assertEqual(len(set(f["sentence_sha256"] for f in fragments)),2)
        self.assertTrue(all(f["parent_passage_sha256"] ==
                            hashlib.sha256(source[0]["text"].encode()).hexdigest()
                            for f in fragments))
        # Rank each fragment against separate modules and stage two separate source nodes.
        mods=[{"id":"WA-06","title":"River monitoring","summary":"Water flows"},
              {"id":"DR-01","title":"Early warning","summary":"Community warnings"}]
        rankings=[]
        for f,i in zip(fragments,[0,1]):
            rankings.append({"source_id":f["id"],"source_passage_sha256":f["sentence_sha256"],
                             "ranked_modules":[{"module_id":mods[i]["id"],"score":.81,"rank":1}]})
        packet=stage_source_module_review(mods,fragments,rankings,top_k=1)
        self.assertEqual(len(packet["edges"]),2)
        self.assertTrue(all(e["source"].startswith("source_") and e["status"]=="candidate"
                            for e in packet["edges"]))
        self.assertEqual(len({e["source"] for e in packet["edges"]}),2)
        merged=aggregate_sentence_rankings([
            {"source_id":f["id"],"source_passage_sha256":f["sentence_sha256"],
             "ranked_modules":[{"module_id":mods[i]["id"],"score":.81,
                                "rank":1,"title":mods[i]["title"]}]}
            for i,f in enumerate(fragments)],mods)
        self.assertEqual(merged[0]["source_id"],"WMO")
        self.assertEqual(merged[0]["review_status"],"sentence_max_similarity_only_not_entailment")
        self.assertTrue(all("supporting_sentence_sha256" in row
                            for row in merged[0]["ranked_modules"]))

    def test_no_label_leak_in_source_parser(self):
        data={"source_ledger":{"WMO":{"url":"https://example.org/wmo",
                                     "passages":["Water services support warnings."]}}}
        a=read_snapshot(data)
        self.assertEqual(a[0]["id"],"WMO")
        self.assertNotIn("gold",a[0])
        self.assertEqual(len(a[0]["source_passage_sha256"]),64)

    def test_explicit_gold_is_post_rank_diagnostic_only(self):
        ranking=[{"source_id":"WMO","ranked_modules":[
            {"module_id":"WA-06","rank":1},
            {"module_id":"DR-01","rank":4},
            {"module_id":"AW-03","rank":8},
        ]}]
        metrics=evaluate(ranking,[],{"gold":{"WMO":["WA-06","DR-01"]}})
        self.assertEqual(metrics["endpoint_recall_at_5"],1)
        self.assertEqual(metrics["expected_pairs_queued"],0)
        self.assertIn("not semantic relation precision",metrics["warning"])

if __name__=="__main__":
    unittest.main()
