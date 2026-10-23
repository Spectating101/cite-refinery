"""Offline structural QA for REAL-model retrieval experiment (no fake model score)."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import unittest

from cite_refinery.actual_semantic_retrieval_replay import (
    SCHEMA, MODEL, ABSTENTION_CHALLENGES, _document, _vectors, run,
)
from test_standalone_workspace_pilot_v1 import OfflineStandalonePilotTests


def fake_embed(texts):
    """Test-only deterministic numeric vectors, never a semantic benchmark."""
    import numpy as np
    result = np.zeros((len(texts), 128), dtype=np.float32)
    for i, text in enumerate(texts):
        words = text.lower().split()
        for word in words:
            idx = int.from_bytes(sha256(word.encode("utf-8")).digest()[:2], "big") % 128
            result[i, idx] += 1.0
        if not words:
            result[i, 0] = 1
    return result


class ActualSemanticRetrievalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OfflineStandalonePilotTests.setUpClass()
        cls.pilot = OfflineStandalonePilotTests.pilot

    def test_all_original_1497_cards_and_10_historical_pairs_remain_unchanged(self):
        result = run(self.pilot, embed=fake_embed, model_id="TEST_NO_SEMANTIC_MODEL")
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["records_by_layer"], {
            "practical": 57, "academic": 150, "implementation": 1290
        })
        self.assertEqual(len(result["all_probes"]), 23)
        self.assertEqual(result["development_probe_stats"]["literal"]
                         ["browser_selected_target_retrieved"], 10)
        self.assertEqual(result["development_probe_stats"]["paraphrase"]
                         ["browser_selected_target_retrieved"], 0)
        for v in ("literal", "paraphrase"):
            self.assertEqual(result["development_probe_stats"][v]
                             ["selected_development_probes"], 10)
            self.assertTrue(0 <= result["development_probe_stats"][v]
                            ["embedding_target_recall_at_1"] <= 10)
            self.assertTrue(0 <= result["development_probe_stats"][v]
                            ["embedding_target_recall_at_5"] <= 10)
        self.assertFalse(result["passage_level_entailment_measured"])
        self.assertFalse(result["independent_blind_gold_or_fair_competitor_test"])
        self.assertFalse(result["browser_frontend_semantic_search_deployed"])
        self.assertFalse(result["can_claim_intelligence_product_ready"])
        self.assertEqual(result["validated_cross_layer_semantic_claims"], 0)
        self.assertEqual(result["embedding_package_version"], "injected_test_embedder")

    def test_all_three_safety_questions_return_candidates_but_are_not_answers(self):
        result = run(self.pilot, embed=fake_embed, model_id="TEST_NO_SEMANTIC_MODEL")
        negatives = [x for x in result["all_probes"]
                     if x["variant"] == "unanswerable_safety_prompt"]
        self.assertEqual(len(negatives), 3)
        self.assertEqual({x["layer"] for x in negatives},
                         {x[0] for x in ABSTENTION_CHALLENGES})
        self.assertTrue(all(x["expected_safe_answer_status"] ==
                            "insufficient_validated_sources" for x in negatives))
        self.assertTrue(all(x["retriever_automatically_abstained"] is False
                            and x["ranked_document_is_not_evidence_of_answerability"]
                            for x in negatives))
        self.assertEqual(result["automatic_safe_abstentions"], 0)
        self.assertEqual(result["actual_semantic_answers_generated"], 0)

    def test_no_hidden_ids_or_gold_in_embedded_document(self):
        c=self.pilot["cards"][0]
        txt=_document(c)
        self.assertTrue(c["title"] in txt)
        self.assertNotIn(c["id"], txt)
        self.assertFalse(any(url in txt for url in c["urls"]))
        self.assertLessEqual(len(txt), 1400)

    def test_fails_closed_if_original_holdout_or_private_source_leaks(self):
        tampered=deepcopy(self.pilot)
        tampered["original_data"]["academic_sealed_holdout_not_imported"]=0
        with self.assertRaisesRegex(ValueError,"safety or evidence authority"):
            run(tampered,embed=fake_embed)
        tampered=deepcopy(self.pilot)
        tampered["cards"][0]["source_body"]="SECRET unapproved source"
        with self.assertRaisesRegex(ValueError,"holdout leaked"):
            run(tampered,embed=fake_embed)
        tampered=deepcopy(self.pilot)
        tampered["cards"][2]["layer"]="practical" if tampered["cards"][2]["layer"]=="academic" else "academic"
        with self.assertRaisesRegex(ValueError,"Layer record totals"):
            run(tampered,embed=fake_embed)

    def test_rejects_false_embedding_and_nonfinite_vectors(self):
        import numpy as np
        with self.assertRaisesRegex(ValueError,"dimensions"):
            _vectors(["source"],lambda texts:np.zeros((2,128),dtype=np.float32))
        with self.assertRaisesRegex(ValueError,"norm"):
            _vectors(["source"],lambda texts:np.zeros((1,128),dtype=np.float32))
        with self.assertRaisesRegex(ValueError,"NaN"):
            _vectors(["source"],lambda texts:np.full((1,128),np.nan,dtype=np.float32))
        with self.assertRaisesRegex(ValueError,"Invalid"):
            _vectors([""], fake_embed)


if __name__ == "__main__":
    unittest.main()
