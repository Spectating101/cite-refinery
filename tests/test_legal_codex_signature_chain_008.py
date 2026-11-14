"""Legal Codex appointment signature hunt: reported document refs, not fake originals."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.app import CiteRefinery
from cite_refinery.semantic import SemanticGraph
from cite_refinery.legal_codex_signature_chain import evaluate, validate, semantic_packet

SEED = Path(__file__).resolve().parents[1] / "examples/legal_codex_signature_chain_008.json"


class SignatureChainTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SEED.read_text(encoding="utf-8"))

    def docs(self):
        return {x["id"]: x for x in self.data["documents"]}

    def reports(self):
        return {x["id"]: x for x in self.data["reports"]}

    def test_ten_distinct_reported_instrument_leads(self):
        result = evaluate(self.data)
        self.assertEqual(result["source_count"], 7)
        self.assertEqual(result["document_locator_count"], 10)
        self.assertEqual(result["report_count"], 12)
        self.assertEqual(result["competing_account_count"], 2)
        self.assertFalse(result["full_signed_2020_appointment_verified"])
        self.assertFalse(result["2020_egov_purchase_order_matched"])
        self.assertFalse(result["publication_authorized"])
        self.assertTrue(all(d["actual_signatory"] is None and
                            d["primary_signed_instrument_verified"] is False and
                            d["specific_package_transaction_verified"] is False
                            for d in result["document_leads"]))

    def test_incomplete_number_four_not_equated_to_june_eighth_decree(self):
        documents = self.docs()
        self.assertEqual(documents["d_kpa_appointment_no4"]["reported_reference"], "4")
        self.assertEqual(documents["d_kpa_appointment_no4"]["reference_status"],
                         "partial_reference_reported")
        self.assertEqual(documents["d_sd_appointment_15004"]["reported_reference"],
                         "15004/C3/KPA/VI/KP/2020")
        self.assertNotEqual(documents["d_kpa_appointment_no4"]["reported_reference"],
                            documents["d_sd_appointment_15004"]["reported_reference"])

    def test_2020_smp_addenda_are_not_2020_sd_order(self):
        docs = self.docs()
        self.assertEqual(docs["d_smp_2020_addendum_one"]["channel"],
                         "smp_2020_directorate_ecatalog")
        self.assertEqual(docs["d_smp_2020_addendum_two"]["document_kind"],
                         "smp_purchase_addendum")
        self.assertEqual(docs["d_sd_june30_purchase"]["reference_status"],
                         "no_reference_found")
        self.assertIsNone(docs["d_sd_june30_purchase"]["reported_reference"])

    def test_judicial_reasoning_and_prosecution_motive_disagreement_preserved(self):
        result = evaluate(self.data)
        entries = {x["id"]: x for x in result["competing_accounts"]}
        self.assertEqual(len(entries["c_replacement_reason"]["accounts"]), 3)
        self.assertIn("court_reasoning_reported", [x["stance"]
                        for x in entries["c_replacement_reason"]["accounts"]])
        self.assertIn("prosecution_allegation", [x["stance"]
                        for x in entries["c_replacement_reason"]["accounts"]])
        self.assertEqual(entries["c_replacement_reason"]["resolution"],
                         "unresolved_pending_original_court_reasoning")
        self.assertTrue(all(not item["court_original_confirmed"]
                            for item in entries["c_replacement_reason"]["accounts"]))

    def test_live_captures_verify_pages_not_signed_documents(self):
        sources = {x["id"]: x for x in self.data["sources"]}
        expected = {"s_pati_response", "s_witness_detik", "s_trial_hukumonline"}
        self.assertEqual({k for k, v in sources.items() if v.get("capture_receipt")}, expected)
        for key in expected:
            receipt = sources[key]["capture_receipt"]
            self.assertEqual(receipt["workflow_run"], 42834469206)
            self.assertEqual(len(receipt["raw_sha256"]), 64)
            self.assertEqual(len(receipt["extracted_sha256"]), 64)
            self.assertFalse(receipt["original_2020_instrument_verified"])
            self.assertFalse(sources[key]["original_legal_document_archived"])

    def test_spoofed_capture_or_truth_upgrade_rejected(self):
        source = next(x for x in self.data["sources"] if x["id"] == "s_pati_response")
        source["capture_receipt"]["raw_sha256"] = "fabricated"
        with self.assertRaisesRegex(ValueError, "capture receipt"):
            validate(self.data)
        source["capture_receipt"]["raw_sha256"] = "a" * 64
        source["capture_receipt"]["original_2020_instrument_verified"] = True
        with self.assertRaisesRegex(ValueError, "overclaimed"):
            validate(self.data)

    def test_fake_named_signatory_rejected(self):
        self.docs()["d_wahyu_replacement"]["actual_signatory"] = "Wahyu Haryadi"
        with self.assertRaisesRegex(ValueError, "not verified"):
            validate(self.data)

    def test_fake_signed_appointment_rejected(self):
        self.docs()["d_wahyu_replacement"]["signed_document_verified"] = True
        with self.assertRaisesRegex(ValueError, "not verified"):
            validate(self.data)

    def test_fake_purchase_id_rejected(self):
        self.data["verified_e_purchase_ids"] = ["2020-XXXX"]
        with self.assertRaisesRegex(ValueError, "unverified signature"):
            validate(self.data)

    def test_2020_smp_addendum_mislabeled_as_sd_order_rejected(self):
        self.docs()["d_smp_2020_addendum_one"]["channel"] = "sd_2020_directorate_ecatalog"
        with self.assertRaisesRegex(ValueError, "SMP addendum"):
            validate(self.data)

    def test_partial_decree_falsely_completed_rejected(self):
        self.docs()["d_kpa_appointment_no4"]["reported_reference"] = "4/C3/FAKE"
        with self.assertRaisesRegex(ValueError, "ambiguous partial"):
            validate(self.data)

    def test_claimed_fiscal_guilt_injection_rejected(self):
        self.reports()["r_prosecution_sd_click"]["legal_guilt_established"] = True
        with self.assertRaisesRegex(ValueError, "guilt upgrade"):
            validate(self.data)

    def test_prosecutor_claim_masquerading_as_court_finding_rejected(self):
        self.reports()["r_prosecution_removed_for_refusal"]["stance"] = "court_reasoning_reported"
        with self.assertRaisesRegex(ValueError, "court finding"):
            validate(self.data)

    def test_bambang_contradiction_cannot_be_declared_resolved(self):
        self.data["conflicts"][0]["resolution"] = "prosecution_won"
        with self.assertRaisesRegex(ValueError, "cannot be adjudicated"):
            validate(self.data)

    def test_source_custody_cannot_be_invented(self):
        self.data["sources"][0]["original_legal_document_archived"] = True
        with self.assertRaisesRegex(ValueError, "invalid source"):
            validate(self.data)

    def test_graph_edges_stay_neutral_with_real_cite_refinery_preview(self):
        packet = semantic_packet(self.data)
        self.assertEqual(len(packet["edges"]), 24)
        self.assertTrue(all(e["status"] == "candidate" for e in packet["edges"]))
        self.assertFalse(any(e["relation"] in {"PAID", "SIGNED", "COLLUDED", "CORRUPTED"}
                             for e in packet["edges"]))
        with tempfile.TemporaryDirectory() as temp:
            app = CiteRefinery(temp)
            project = app.init_project("Chromebook appointment trace", "Original instrument lookup")
            graph = SemanticGraph(app.store)
            preview = graph.preview_packet(project.id, packet)
            self.assertFalse(preview["authority_boundary_warnings"])
            receipt = graph.ingest_packet(project.id, packet,
                                          expected_state_digest=preview["state_digest"])
            self.assertEqual(len(receipt["edge_ids"]), 24)
            self.assertTrue(all(app.store.load()["semantic_edges"][x]["status"] == "candidate"
                                for x in receipt["edge_ids"]))


if __name__ == "__main__":
    unittest.main()
