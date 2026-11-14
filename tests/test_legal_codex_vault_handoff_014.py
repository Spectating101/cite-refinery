"""Milestone 014: custody from a verified vault, never from invented JSON."""
import copy
import json
from pathlib import Path
from unittest.mock import patch
import unittest

from cite_refinery.legal_codex_vault_handoff import (
    evaluate, semantic_packet, validate,
)

SEED=Path(__file__).resolve().parents[1]/"examples/legal_codex_vault_handoff_014.json"


class VaultHandoff014Tests(unittest.TestCase):
    def setUp(self):
        self.seed=json.loads(SEED.read_text(encoding="utf-8"))

    def fake(self, receipts=None, **more):
        return {
            "schema":"nocturnal.legal_codex_vault_review.v1",
            "snapshot_receipts":receipts or [],
            "publication_authorized":False,
            "source_authenticity_certified":False,
            "factual_corrections_adjudicated":False,
            "external_head_anchor_verified":False,
            "head_event_sha256":"a"*64,
            "revision_candidate_count":0,
            "failed_attempt_count":0,
            **more,
        }

    def test_eight_sources_all_uncaptured_by_default(self):
        out=evaluate(self.seed)
        self.assertEqual(out["expected_source_count"],8)
        self.assertEqual(out["verified_byte_source_count"],0)
        self.assertEqual(out["missing_or_untrusted_count"],8)
        self.assertFalse(out["nocturnal_hash_chain_rechecked"])
        self.assertIsNone(out["vault_head_event_sha256"])
        self.assertTrue(all(row["custody_status"]=="not_acquired" for row in out["source_status"]))
        self.assertFalse(out["publication_authorized"])

    def test_source_registry_is_pinned_to_012_and_013(self):
        self.seed["expected_sources"][0]["source_url"]="https://example.com/forged"
        with self.assertRaisesRegex(ValueError,"source list"):
            validate(self.seed)

    def test_full_report_cannot_claim_originals_in_seed(self):
        self.seed["originals_archived_in_fixture"]=True
        with self.assertRaisesRegex(ValueError,"promoted"):
            validate(self.seed)

    def test_independent_editorial_review_cannot_be_inferred(self):
        self.seed["legal_editorial_approval"]=True
        with self.assertRaisesRegex(ValueError,"promoted"):
            validate(self.seed)

    def test_no_case_specific_remedy_inferred_from_uk_scheme(self):
        self.seed["case_specific_remedies_proven"]=True
        with self.assertRaisesRegex(ValueError,"promoted"):
            validate(self.seed)

    def test_publication_not_authorized(self):
        self.seed["publication_authorized"]=True
        with self.assertRaisesRegex(ValueError,"promoted"):
            validate(self.seed)

    def test_altered_reference_period_for_official_report_fails(self):
        x=next(x for x in self.seed["expected_sources"] if x["source_id"]=="s_uk_redress_sep")
        x["reference_date"]="2026-10-30"
        with self.assertRaisesRegex(ValueError,"reporting date"):
            validate(self.seed)

    def test_test_double_receipt_does_not_establish_original_capture(self):
        x=self.seed["expected_sources"][0]
        receipt={
            "source_id":x["source_id"],
            "source_url":x["source_url"],
            "reference_date":x["reference_date"],
            "acquisition_state":"live_nocturnal_loader_rechecked",
            "source_truth_verified":False,
            "raw_sha256":"a"*64,
        }
        out=evaluate(self.seed,vault_root="/fake",verifier=lambda _:self.fake([receipt]))
        self.assertEqual(out["verified_byte_source_count"],0)
        self.assertEqual(out["source_status"][0]["custody_status"],"synthetic_or_untrusted_capture")
        self.assertFalse(out["nocturnal_hash_chain_rechecked"])

    def test_synthetic_source_receipt_is_explicitly_not_custody(self):
        x=self.seed["expected_sources"][0]
        receipt={
            "source_id":x["source_id"],"source_url":x["source_url"],
            "reference_date":x["reference_date"],
            "acquisition_state":"synthetic_test_only",
            "source_truth_verified":False,
            "raw_sha256":"a"*64,
        }
        out=evaluate(self.seed,vault_root="/fake",verifier=lambda _:self.fake([receipt]))
        self.assertEqual(out["verified_byte_source_count"],0)
        self.assertFalse(out["official_claims_independently_verified"])

    def test_wrong_url_or_date_retains_mismatch_status(self):
        x=self.seed["expected_sources"][0]
        receipt={
            "source_id":x["source_id"],"source_url":"https://example.com/other",
            "reference_date":"2026-09-30",
            "acquisition_state":"synthetic_test_only",
        }
        out=evaluate(self.seed,vault_root="/fake",verifier=lambda _:self.fake([receipt]))
        self.assertEqual(out["source_status"][0]["custody_status"],
                         "source_identity_or_reference_period_mismatch")

    def test_reject_overclaimed_vault_authenticity(self):
        with self.assertRaisesRegex(ValueError,"overclaimed"):
            evaluate(self.seed,vault_root="/fake",verifier=lambda _:self.fake(
                [],source_authenticity_certified=True))

    def test_revision_candidates_cannot_become_factual_correction(self):
        out=evaluate(self.seed,vault_root="/fake",verifier=lambda _:self.fake(
            [],revision_candidate_count=3))
        self.assertEqual(out["unreviewed_correction_candidates"],3)
        self.assertFalse(out["factual_corrections_adjudicated"])

    def test_failed_capture_count_is_not_success_count(self):
        out=evaluate(self.seed,vault_root="/fake",verifier=lambda _:self.fake(
            [],failed_attempt_count=5))
        self.assertEqual(out["failed_capture_attempts_logged"],5)
        self.assertEqual(out["verified_byte_source_count"],0)

    def test_graph_only_candidate_custody_and_no_individual_edge(self):
        out=evaluate(self.seed)
        packet=semantic_packet(self.seed,out)
        self.assertEqual(len(packet["nodes"]),16)
        self.assertEqual(len(packet["edges"]),8)
        self.assertTrue(all(e["status"]=="candidate" for e in packet["edges"]))
        self.assertFalse(any(e["relation"] in {
            "PAID", "REMEDIED", "CAUSES", "GUILTY", "LEGAL_RULE_APPLIES"
        } for e in packet["edges"]))

    def test_stale_result_cannot_change_source_graph(self):
        out=evaluate(self.seed)
        mutated=copy.deepcopy(self.seed)
        mutated["as_of"]="2026-11-16"
        with self.assertRaisesRegex(ValueError,"source list|reporting date"):
            semantic_packet(mutated,out)

    def test_real_semantic_graph_preview_and_ingest_never_promotes_custody(self):
        from cite_refinery.app import CiteRefinery
        from cite_refinery.semantic import SemanticGraph
        from tempfile import TemporaryDirectory
        packet=semantic_packet(self.seed,evaluate(self.seed))
        with TemporaryDirectory() as path:
            app=CiteRefinery(path)
            project=app.init_project("Evidence custody baseline",
                                     "All eight source captures awaiting genuine Nocturnal ingestion")
            graph=SemanticGraph(app.store)
            preview=graph.preview_packet(project.id,packet)
            self.assertFalse(preview["authority_boundary_warnings"])
            receipt=graph.ingest_packet(
                project.id,packet,expected_state_digest=preview["state_digest"])
            self.assertEqual(len(receipt["edge_ids"]),8)
            self.assertTrue(all(app.store.load()["semantic_edges"][x]["status"]=="candidate"
                                for x in receipt["edge_ids"]))


if __name__=="__main__":
    unittest.main()
