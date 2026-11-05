"""Pinned original source-page results; chart-only source never becomes a dataset."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class FailedOriginalPageRecovery(unittest.TestCase):
    def test_source_sha_and_selected_source_words_stay_review_only(self):
        receipt=json.loads((ROOT/"examples/discovery/failed_page_native_crop_acceptance_20261103.json").read_text())
        oracle=json.loads((ROOT/"examples/discovery/operator_cropped_failed_pdf_pages_20261103.json").read_text())
        original=json.loads((ROOT/"examples/discovery/real_pdf_operator_pilot_20261103.json").read_text())
        pins={x["id"]:x for x in original["cases"]}
        expected={x["source_id"]:x for x in oracle["table_cases"]}
        expected[oracle["chart_case"]["source_id"]]=oracle["chart_case"]
        self.assertEqual(receipt["schema"],"atlas.failed_page_operator_cropped_native_recovery.v1")
        self.assertEqual(receipt["original_selected_failed_pages"],3)
        self.assertEqual(receipt["original_img2table_errors_still_reproduced"],3)
        self.assertEqual(receipt["cropped_native_pages_attempted"],2)
        self.assertEqual(receipt["chart_only_original_pages_held"],1)
        self.assertEqual(receipt["operator_selected_cells_checked"],8)
        self.assertEqual(receipt["source_word_matches"],8)
        self.assertEqual(receipt["source_word_abstentions"],0)
        self.assertEqual(receipt["trusted_source_values_promoted"],0)
        for key in ("auto_publish","auto_register_dataset",
                    "verified_original_table_semantics","independent_human_adjudication",
                    "default_img2table_parser_repaired","original_pdf_bytes_committed"):
            self.assertFalse(receipt[key])
        self.assertEqual(receipt["release_decision"],
            "HOLD_OPERATOR_SCOPED_RECOVERY_IS_NOT_DEFAULT_PARSER_FIX")
        self.assertEqual(len(receipt["cases"]),3)
        for case in receipt["cases"]:
            source=pins[case["source_id"]]
            operator=expected[case["source_id"]]
            self.assertEqual(case["original_sha256"],source["source_sha256"])
            self.assertIn(case["physical_page"],source["selected_physical_pages"])
            self.assertEqual(case["original_img2table_error_code"],
                             operator["strict_img2table_error_code"])
            self.assertEqual(case["trusted_values"],0)
            if case["source_id"]=="bis138":
                self.assertTrue(case["original_caption_verified"])
                self.assertFalse(case["native_fallback_attempted"])
                self.assertEqual(case["page_outcome"],"CHART_ONLY_HOLD_NO_TABLE_RECONSTRUCTION")
                self.assertEqual(case["source_word_matches"],0)
            else:
                self.assertTrue(case["native_fallback_attempted"])
                self.assertEqual(case["operator_crop_bbox_pdf"],operator["crop_bbox_pdf"])
                self.assertEqual(case["native_profile"],operator["profile"])
                self.assertEqual(case["source_word_matches"],4)
                self.assertEqual(case["original_source_cells_checked"],4)
                self.assertEqual(case["source_word_abstentions"],0)
                self.assertFalse(case["word_verifier_separate_library_from_detector"])
                self.assertFalse(case["operator_table_context_independently_adjudicated"])
                self.assertEqual(len(case["original_word_and_geometry_checks"]),4)
                for x in case["original_word_and_geometry_checks"]:
                    self.assertEqual(x["status"],"native_original_word_witness_match")
                    self.assertEqual(len(x["checks"]),6)
                    self.assertTrue(all(x["checks"].values()))

    def test_source_operator_crops_are_manual_not_all_observations(self):
        o=json.loads((ROOT/"examples/discovery/operator_cropped_failed_pdf_pages_20261103.json").read_text())
        self.assertEqual(o["schema"],"atlas.operator_cropped_failed_pdf_pages.v1")
        self.assertEqual({x["source_id"] for x in o["table_cases"]},{"arxiv2506","arxiv2604"})
        self.assertEqual(o["chart_case"]["source_id"],"bis138")
        self.assertEqual(sum(len(x["selected"]) for x in o["table_cases"]),8)
        self.assertEqual(o["release_decision"],"HOLD_NO_AUTOMATIC_DATASET_PROMOTION")


if __name__=="__main__":unittest.main()
