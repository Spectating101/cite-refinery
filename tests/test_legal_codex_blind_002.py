"""Blinded mechanism retrieval and Nocturnal capture bridge acceptance.

Fixture outcomes appear only in assertions, never in the retriever input.
Nocturnal loader is deliberately simulated: test passes do NOT establish that
a real live source has been archived or independently authenticated.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.legal_codex_blind import prepare_questions, retrieve
from cite_refinery.legal_codex_nocturnal import evaluate_captures, verified_passage

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "examples/legal_codex_benchmark_001.json"
LIBRARY = ROOT / "examples/legal_codex_candidate_library_001.json"


class BlindRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.seed = json.loads(SEED.read_text(encoding="utf-8"))
        self.library = json.loads(LIBRARY.read_text(encoding="utf-8"))

    def test_three_domain_blind_top_one_without_answer_keys(self):
        questions = prepare_questions(self.seed)
        self.assertTrue(all(set(q) == {
            "case_id", "problem_statement", "anchor_date"} for q in questions))
        output = retrieve(questions, self.library)
        expected = {
            "wangwang": "m_animal_welfare",
            "horizon": "m_criminal_review",
            "dutch_benefits": "m_gdpr_article22",
        }
        self.assertFalse(output["answer_keys_seen_by_retriever"])
        for case in output["results"]:
            self.assertEqual(case["ranked_candidates"][0]["candidate_id"],
                             expected[case["case_id"]])
            self.assertFalse(case["publication_authorized"])
            self.assertIsNone(case["causal_effect"])

    def test_post_incident_law_is_not_retroactively_available(self):
        output = retrieve(prepare_questions(self.seed), self.library)
        dutch = next(c for c in output["results"]
                     if c["case_id"] == "dutch_benefits")
        self.assertNotIn("m_later_ai_act", [x["candidate_id"]
                                           for x in dutch["ranked_candidates"]])
        self.assertIn("m_later_ai_act", [x["candidate_id"]
                                        for x in dutch["excluded_after_incident"]])

    def test_answer_leak_into_question_fails(self):
        q = prepare_questions(self.seed)
        q[0]["expected_match"] = "m_animal_welfare"
        with self.assertRaisesRegex(ValueError, "leaked"):
            retrieve(q, self.library)

    def test_answer_leak_into_candidate_fails(self):
        self.library[0]["addresses"] = ["animal_cruelty_protection_gap"]
        with self.assertRaisesRegex(ValueError, "leakage"):
            retrieve(prepare_questions(self.seed), self.library)

    def test_decoy_does_not_replace_relevant_candidate(self):
        self.library.reverse()
        output = retrieve(prepare_questions(self.seed), self.library)
        self.assertEqual([x["ranked_candidates"][0]["candidate_id"]
                          for x in output["results"]],
                         ["m_gdpr_article22", "m_criminal_review",
                          "m_animal_welfare"] if sorted(x["case_id"] for x in output["results"]) !=
                         [x["case_id"] for x in output["results"]] else [
                          "m_gdpr_article22", "m_criminal_review",
                          "m_animal_welfare"])

    def test_empty_overlap_abstains(self):
        questions = [{"case_id": "negative", "problem_statement":
                      "Galactic telescope launch trajectory delta ion engine",
                      "anchor_date": "2022-01-01"}]
        output = retrieve(questions, self.library)
        self.assertEqual(output["results"][0]["ranked_candidates"], [])


class NocturnalBridgeTests(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads(SEED.read_text(encoding="utf-8"))
        self.source = self.bundle["sources"][0]
        self.case_id = "example-case"
        self.capture_id = "cap-" + "a" * 24
        self.proposal_id = "prop-" + "b" * 24

    def loader(self, *, state_dir, case_id, capture_id):
        return {
            "schema": "nocturnal_source_capture.v2",
            "case_id": case_id, "capture_id": capture_id,
            "source_url": self.source["url"], "http_status": 200,
            "raw_sha256": "1" * 64, "extracted_sha256": "2" * 64,
            "constraints": {
                "tls_hostname_verified": True,
                "injected_test_fetcher": False,
                "source_authenticity_established": False,
                "publication_authorized": False,
            },
            "proposals": [{
                "proposal_id": self.proposal_id,
                "extraction_method": "unicode_verbatim_sentence_v2",
                "quote": self.source["excerpt"],
                "text_sha256": "2" * 64,
            }],
        }

    def check(self, loader=None):
        return verified_passage(
            self.source, state_dir="unmounted-test-only",
            case_id=self.case_id, capture_id=self.capture_id,
            proposal_id=self.proposal_id, loader=loader or self.loader)

    def test_receipt_proves_no_more_than_archive_integrity(self):
        receipt = self.check()
        self.assertEqual(receipt["integrity"], "nocturnal_loader_rechecked")
        self.assertEqual(receipt["source_authenticity"], "not_established")
        self.assertEqual(receipt["claim_truth"], "not_adjudicated")
        self.assertFalse(receipt["publication_authorized"])

    def test_capture_not_from_live_tls_is_rejected(self):
        def tampered(**kw):
            x = self.loader(**kw)
            x["constraints"]["injected_test_fetcher"] = True
            x["constraints"]["tls_hostname_verified"] = False
            return x
        with self.assertRaisesRegex(ValueError, "live TLS"):
            self.check(tampered)

    def test_capture_other_source_is_rejected(self):
        def tampered(**kw):
            x = self.loader(**kw)
            x["source_url"] = "https://example.org/different"
            return x
        with self.assertRaisesRegex(ValueError, "source URL"):
            self.check(tampered)

    def test_capture_changed_quote_is_rejected(self):
        def tampered(**kw):
            x = self.loader(**kw)
            x["proposals"][0]["quote"] = "An unrelated paragraph."
            return x
        with self.assertRaisesRegex(ValueError, "excerpt not found"):
            self.check(tampered)

    def test_nocturnal_recheck_does_not_authorize_publication(self):
        ref = [{
            "source_id": self.source["id"], "state_dir": "unmounted-test-only",
            "case_id": self.case_id, "capture_id": self.capture_id,
            "proposal_id": self.proposal_id,
        }]
        result = evaluate_captures(self.bundle, ref, loader=self.loader)
        self.assertEqual(result["source_integrity"]["checked_sources"], 1)
        self.assertFalse(result["source_integrity"]["live_verification"])
        self.assertFalse(result["publication_authorized"])
        self.assertTrue(all(c["causal_effect"] is None for c in result["cases"]))

    def test_unknown_source_rejected(self):
        ref = [{
            "source_id": "fabricated", "state_dir": "unmounted-test-only",
            "case_id": self.case_id, "capture_id": self.capture_id,
            "proposal_id": self.proposal_id,
        }]
        with self.assertRaisesRegex(ValueError, "unknown"):
            evaluate_captures(self.bundle, ref, loader=self.loader)


if __name__ == "__main__":
    unittest.main()
