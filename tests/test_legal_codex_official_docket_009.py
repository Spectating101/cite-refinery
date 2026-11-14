"""Milestone 009: official directory metadata is not original procurement proof."""
import copy
import json
from pathlib import Path
import unittest

from cite_refinery.legal_codex_docket_registry import evaluate, validate, semantic_packet

SEED = Path(__file__).resolve().parents[1] / "examples/legal_codex_official_docket_009.json"


class OfficialDocketTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SEED.read_text(encoding="utf-8"))

    def test_registry_corroborates_two_only(self):
        result = evaluate(self.data)
        self.assertEqual(result["verified_official_directory_listing_count"], 2)
        self.assertEqual(result["reported_but_unlocated_docket_count"], 1)
        self.assertEqual(result["listed_pdf_download_count"], 2)
        self.assertEqual(result["pdf_files_obtained"], 0)
        self.assertFalse(result["2020_ppk_appointment_verified"])
        self.assertFalse(result["2020_sd_purchase_order_matched"])
        self.assertFalse(result["publication_authorized"])

    def test_sri_docket_remains_report_only(self):
        sri = next(x for x in self.data["cases"] if x["id"] == "case_sri_149")
        self.assertIsNone(sri["registry_url"])
        sri["registry_status"] = "official_listing_indexed"
        with self.assertRaises(ValueError):
            validate(self.data)

    def test_source_cannot_be_third_party_disguised_as_court(self):
        self.data["cases"][0]["registry_url"] = "https://fake.mahkamahagung.go.id/direktori/putusan/example.html"
        with self.assertRaisesRegex(ValueError, "official court directory provenance"):
            validate(self.data)

    def test_pdf_listed_is_not_pdf_acquired(self):
        self.data["cases"][0]["pdf_bytes_obtained"] = True
        with self.assertRaisesRegex(ValueError, "illegally promoted"):
            validate(self.data)

    def test_pdf_hash_not_fabricated(self):
        self.data["cases"][1]["pdf_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "illegally promoted"):
            validate(self.data)

    def test_cross_case_exhibit_reference_is_not_joint_liability(self):
        edge = self.data["cross_case_references"][0]
        edge["joint_criminal_liability_proved"] = True
        with self.assertRaisesRegex(ValueError, "cross-case linkage"):
            validate(self.data)

    def test_cross_case_exhibit_reference_is_not_shared_order(self):
        self.data["cross_case_references"][0]["common_purchase_order_proved"] = True
        with self.assertRaisesRegex(ValueError, "cross-case linkage"):
            validate(self.data)

    def test_cross_case_reference_is_cited_to_originating_official_case(self):
        self.data["cross_case_references"][0]["source_url"] = self.data["cases"][0]["registry_url"]
        with self.assertRaisesRegex(ValueError, "cross-case citation"):
            validate(self.data)

    def test_semantic_graph_is_candidate_only(self):
        packet = semantic_packet(self.data)
        self.assertEqual(len(packet["nodes"]), 3)
        self.assertEqual(len(packet["edges"]), 1)
        self.assertTrue(all(e["status"] == "candidate" for e in packet["edges"]))
        self.assertFalse(any(e["relation"] in ("SIGNED", "PAID", "COLLUDED", "CORRUPTED")
                             for e in packet["edges"]))
        self.assertTrue(all(n["provenance"]["ppk_appointment_verified"] is False
                            for n in packet["nodes"]))


if __name__ == "__main__":
    unittest.main()
