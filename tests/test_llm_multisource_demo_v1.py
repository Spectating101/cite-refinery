"""End-to-end source-backed GPT-6 semantic demonstration, not model benchmark.

Frozen generated response and same-model critique. Tests verify that the
existing Cite-Refinery machinery consumes actual model-authored structured
reasoning, keeps uncertain bridges unresolved, and does not accept source
claims automatically.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery import CiteRefinery,SemanticGraph
from cite_refinery.external_llm_reasoner import (
    make_input,inspect_answer,inspect_second_pass,
)
from cite_refinery.external_llm_packets import llm_review_packet

FIXTURE=Path(__file__).resolve().parents[1]/"research_materials/runtime_trials/llm_multisource_20261020"


def load(name):
    return json.loads((FIXTURE/name).read_text(encoding="utf-8"))


class LLMRealSourceDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources=load("sources.json")
        cls.modules=load("modules.json")
        cls.initial=make_input(cls.sources,cls.modules)
        cls.answer=load("gpt6_semantic_generation.json")
        cls.inspected=inspect_answer(cls.initial,cls.answer)
        cls.critical=inspect_second_pass(cls.initial,cls.inspected,load("gpt6_self_critique.json"))
        cls.packet=llm_review_packet(cls.initial,cls.inspected,cls.critical)

    def test_genuinely_separate_primary_sources(self):
        manifest=load("source_manifest.json")
        self.assertEqual(len(manifest),3)
        self.assertEqual({s["origin_type"] for s in self.sources},{
            "peer_reviewed_academic_article","official_program_guidance",
            "official_institutional_public_health",
        })
        self.assertTrue(all(x["retrieval_status"]==200 and
                            len(x["raw_page_sha256"])==64 and
                            len(x["selected_excerpts_sha256"])==64 for x in manifest))
        self.assertEqual(len(self.modules),5)
        self.assertTrue(all(s["url"].startswith("https://") for s in self.sources))

    def test_atomized_investigation_does_not_promote_source_claims(self):
        self.assertEqual(len(self.inspected["propositions"]),11)
        self.assertEqual(len(self.inspected["bridges"]),9)
        self.assertEqual(len(self.inspected["open_questions"]),4)
        self.assertEqual(len(self.inspected["rejected"]),0)
        self.assertTrue(all(p["review_status"]=="direct_source_quote_candidate_unverified_entailment"
                            for p in self.inspected["propositions"]))
        self.assertEqual(len(self.packet["nodes"]),23)
        self.assertEqual(len(self.packet["edges"]),40)
        self.assertEqual(Counter(n["layer"] for n in self.packet["nodes"]),{"neutral":23})
        self.assertEqual(Counter(e["status"] for e in self.packet["edges"]),
                         {"candidate":39,"unresolved":1})
        self.assertEqual(self.packet["conversion_metadata"]["verified_effectiveness_claims"],0)

    def test_same_model_critique_downgrades_weak_interpretation(self):
        self.assertEqual(Counter(x["reviewer_verdict"] for x in self.critical["propositions"]),
                         {"entailed":9,"partially_supported":2})
        self.assertEqual(Counter(x["reviewer_verdict"] for x in self.critical["bridges"]),
                         {"plausible":8,"uncertain":1})
        uncertain=[e for e in self.packet["edges"] if e["status"]=="unresolved"]
        self.assertEqual(len(uncertain),1)
        self.assertEqual(uncertain[0]["provenance"]["second_pass_verdict"],"uncertain")

    def test_true_quote_can_support_a_false_interpretation(self):
        injected=load("adversarial_quote_matched_wrong_claim.json")
        report=inspect_answer(self.initial,injected)
        self.assertEqual(len(report["propositions"]),1)
        critique=inspect_second_pass(self.initial,report,load("adversarial_critique.json"))
        self.assertEqual(critique["propositions"][0]["reviewer_verdict"],"contradicted")
        self.assertEqual(critique["propositions"][0]["authority"],"NONE_ACCEPTED")

    def test_isolated_project_ingest_and_replay(self):
        with TemporaryDirectory() as folder:
            app=CiteRefinery(folder)
            p=app.init_project("Three source LLM review","Dog population vs rabies")
            g=SemanticGraph(app.store)
            receipt=g.ingest_packet(p.id,self.packet)
            snapshot=app.store.load()
            receipt2=g.ingest_packet(p.id,self.packet)
            self.assertEqual(receipt["id"],receipt2["id"])
            self.assertEqual(app.store.load(),snapshot)
            self.assertEqual(len(receipt["edge_ids"]),40)
            self.assertEqual(len(receipt["node_ids"]),23)

    def test_bundled_html_demo_references_exact_review_data(self):
        viewer=(FIXTURE/"interactive_graph.html").read_text(encoding="utf-8")
        self.assertIn("cytoscape(",viewer)
        self.assertIn("dataset.graphReady='true'",viewer)
        self.assertIn("edge[status=",viewer)
        self.assertIn("../../../src/cite_refinery/vendor/cytoscape.min.js",viewer)
        self.assertNotIn("https://cdn.",viewer)


if __name__=="__main__":
    unittest.main()
