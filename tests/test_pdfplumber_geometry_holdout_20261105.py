"""Untouched external geometry-corpus acceptance: count failures and unknown gold."""
import hashlib,json
from collections import Counter
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]/'examples/discovery'

def load(name):
    return json.loads((ROOT/name).read_text())

class FreshPdfplumberGeometryHoldout(unittest.TestCase):
    def test_all_first_pages_and_source_bytes_pinned(self):
        manifest=load('pdfplumber_geometry_holdout_preregistration_20261105.json')
        result=load('pdfplumber_geometry_first_pass_20261105.json')
        self.assertEqual(result['schema'],'atlas.pdfplumber_original_geometry_external_first_pass.v1')
        self.assertEqual(manifest['schema'],'atlas.pdfplumber_new_geometry_holdout_preregistration.v1')
        self.assertEqual(result['locked_manifest_sha256'],hashlib.sha256(
            (ROOT/'pdfplumber_geometry_holdout_preregistration_20261105.json').read_bytes()).hexdigest())
        self.assertEqual(result['frozen_research_drive_source_commit'][:7],'4e3dabe')
        self.assertEqual(result['original_source_repository_commit'],manifest['upstream_commit'])
        self.assertEqual(result['engine_mode'],'camelot-py-1.0.9-hybrid-fixed')
        self.assertTrue(manifest['pdf_bytes_not_opened_or_downloaded_before_commit'])
        self.assertEqual(len(manifest['cases']),12)
        self.assertEqual(result['original_first_page_cases_locked'],12)
        self.assertEqual(result['original_first_page_cases_attempted'],12)
        self.assertEqual(result['original_pdfs_sha_pinned'],12)
        self.assertEqual({x['filename'] for x in result['cases']},
                         {x['filename'] for x in manifest['cases']})
        self.assertTrue(result['first_pass_never_tuned_to_selected_sources'])
        self.assertTrue(result['not_independent_human_blind_review'])
        self.assertTrue(result['source_extraction_normalization_only'])
        self.assertFalse(result['original_pdf_bytes_or_source_rows_committed'])
        for case in result['cases']:
            self.assertEqual(len(case['original_source_sha256']),64)
            self.assertEqual(case['download_status'],'EXACT_UPSTREAM_BYTES_ACQUIRED')
            self.assertEqual(case['worker_status'],'WORKER_COMPLETED_WITH_HOLD_RECEIPT')
            self.assertEqual(case['physical_page'],1)
            self.assertEqual(case['trusted_rows'],0)
            self.assertGreater(case['original_pdf_word_count'],0)
            self.assertLessEqual(case['strict_review_ready_rows'],case['candidate_rows'])

    def test_failures_are_not_dropped_or_promoted(self):
        result=load('pdfplumber_geometry_first_pass_20261105.json')
        self.assertEqual(result['worker_source_errors_or_timeouts'],10)
        self.assertEqual(result['source_pages_with_calibrated_word_proof'],6)
        self.assertEqual(result['source_pages_with_candidate_rows'],2)
        self.assertEqual(result['candidate_rows_total'],88)
        self.assertEqual(result['strict_review_ready_rows_total'],3)
        self.assertEqual(result['blocked_source_rows_total'],85)
        self.assertEqual(result['structural_rows_untrusted_total'],85)
        self.assertFalse(result['external_published_row_gold_available'])
        self.assertIsNone(result['row_precision'])
        self.assertIsNone(result['row_recall'])
        self.assertEqual(result['trusted_rows'],0)
        self.assertFalse(result['auto_publish'])
        self.assertFalse(result['auto_register_dataset'])
        errors=[x for x in result['cases'] if x.get('status')=='ERROR_HELD_NO_TRUSTED_ROWS']
        self.assertEqual(len(errors),10)
        self.assertEqual(Counter(x['error_stage'] for x in errors),
                         Counter({'SOURCE_PDF_NORMALIZATION':6,'FIXED_CAMELOT_HYBRID':4}))
        self.assertTrue(all(x['error_type']=='ValueError' for x in errors))
        self.assertTrue(all(x['candidate_rows']==0 and x['strict_review_ready_rows']==0 for x in errors))

    def test_two_rotated_source_candidates_still_have_limited_original_witnesses(self):
        r=load('pdfplumber_geometry_first_pass_20261105.json')
        success={x['filename']:x for x in r['cases'] if x['candidate_rows']}
        self.assertEqual(set(success),{'issue-461-example.pdf','senate-expenditures.pdf'})
        self.assertEqual((success['issue-461-example.pdf']['candidate_rows'],
                          success['issue-461-example.pdf']['strict_review_ready_rows'],
                          success['issue-461-example.pdf']['blocked_source_rows']),(27,3,24))
        self.assertEqual((success['senate-expenditures.pdf']['candidate_rows'],
                          success['senate-expenditures.pdf']['strict_review_ready_rows'],
                          success['senate-expenditures.pdf']['blocked_source_rows']),(61,0,61))
        self.assertEqual(success['issue-461-example.pdf']['original_rotation'],90)
        self.assertEqual(success['senate-expenditures.pdf']['original_rotation'],90)
        self.assertEqual(sum(x.get('empty_or_merged_source_slots',0) for x in success.values()),240)
        self.assertEqual(sum(x.get('multiline_source_cell_groups',0) for x in success.values()),2)
        self.assertEqual(sum(x['candidate_rows'] for x in success.values()),88)
        for x in success.values():
            self.assertGreaterEqual(x['unique_original_word_box_anchors'],20)
            self.assertEqual(x['verified_original_word_box_anchors'],
                             x['unique_original_word_box_anchors'])
            self.assertEqual(x['max_source_word_box_residual_pdf'],0.0)

    def test_historical_tabula_first_pass_not_rewritten(self):
        prior=load('tabula_engine_holdout_first_pass_20261104.json')
        old_review=load('tabula_operator_review_queue_20261104.json')
        self.assertEqual(prior['primary_candidate_rows'],325)
        self.assertEqual(prior['primary_engine_errors_or_timeouts'],5)
        self.assertEqual(old_review['original_source_witnessed_review_rows'],68)
        self.assertEqual(old_review['blocked_from_operator_review'],257)

if __name__=='__main__':unittest.main()
