"""Pinned post-holdout calibration: exact original PDF SHA and no trust upgrade."""
import hashlib,json
from pathlib import Path
import unittest

EXAMPLES=Path(__file__).resolve().parents[1]/'examples/discovery'
def read(name):return json.loads((EXAMPLES/name).read_text())

class TabulaOriginalGeometryRecovery(unittest.TestCase):
    def test_four_calibrated_originals_and_one_still_blocked_without_rewriting_baseline(self):
        x=read('tabula_original_geometry_recovery_20261105.json')
        original=read('tabula_engine_holdout_first_pass_20261104.json')
        prior_geometry=read('tabula_original_geometry_blockers_20261104.json')
        self.assertEqual(x['schema'],'atlas.tabula_original_source_affine_recovery.v1')
        self.assertEqual(x['original_first_pass_sha256'],
                         hashlib.sha256((EXAMPLES/'tabula_engine_holdout_first_pass_20261104.json').read_bytes()).hexdigest())
        self.assertEqual(x['previously_geometry_blocked_sources'],5)
        self.assertEqual(x['sources_with_verified_affine_calibration'],4)
        self.assertEqual(x['new_original_source_candidate_rows'],255)
        self.assertEqual(x['new_strict_source_review_rows'],30)
        self.assertEqual(x['new_blocked_candidate_rows'],225)
        self.assertEqual(x['new_real_private_review_sheets'],1)
        self.assertEqual(x['still_inconsistent_parser_geometry_source'],'argentina_diputados_voting_record.pdf')
        self.assertTrue(x['original_source_geometry_proof_replayed'])
        self.assertTrue(x['old_first_pass_metrics_unchanged'])
        self.assertTrue(x['not_prospective_on_frozen_cohort'])
        self.assertFalse(x['auto_publish'])
        self.assertFalse(x['auto_register_dataset'])
        self.assertFalse(x['original_PDF_or_full_review_rows_committed'])
        self.assertEqual(x['trusted_pdfscope_promotions'],0)
        self.assertEqual(x['trusted_dataset_rows'],0)
        self.assertEqual(x['operator_actions_submitted'],0)
        self.assertEqual(x['real_independent_reviewers'],0)
        self.assertEqual(x['release_state'],'HOLD_GEOMETRY_RECOVERED_NOT_HUMAN_SEMANTICS_APPROVED')
        refs={v['filename']:v for v in original['cases']}
        blockers={v['source_file']:v for v in prior_geometry['cases']}
        self.assertEqual(len(x['cases']),4)
        observed={
            'rotated_page.pdf':(90,40,30,10),
            'schools.pdf':(90,76,0,76),
            'Publication_of_award_of_Bids_for_Transport_Sector__August_2016.pdf':(90,49,0,49),
            'should_detect_rulings.pdf':(0,90,0,90)}
        for case in x['cases']:
            filename=case['source_file']
            self.assertIn(filename,observed)
            rotation,rows,ready,blocked=observed.pop(filename)
            self.assertEqual(case['original_sha256'],refs[filename]['original_sha256'])
            self.assertTrue(blockers[filename]['engine_hybrid_error'])
            self.assertEqual((case['original_rotation'],
                              case['candidate_rows_on_calibrated_page'],
                              case['strict_review_ready_rows'],case['blocked_candidate_rows']),
                             (rotation,rows,ready,blocked))
            self.assertGreaterEqual(case['independent_unique_word_anchors'],20)
            self.assertEqual(case['source_word_boxes_with_exact_mapping'],
                             case['independent_unique_word_anchors'])
            self.assertEqual(case['max_source_word_box_residual_pdf'],0)
            self.assertEqual(case['operator_actions_submitted'],0)
            self.assertEqual(case['human_second_review_approvals'],0)
            self.assertEqual(case['trusted_rows'],0)
        self.assertFalse(observed)
        self.assertEqual(sum(c['rows_with_all_literal_original_word_cells'] for c in x['cases']),174)
        self.assertTrue(next(c for c in x['cases'] if c['source_file']=='rotated_page.pdf')
                        ['private_source_review_sheet_created'])
        self.assertTrue(next(c for c in x['cases'] if c['source_file']=='should_detect_rulings.pdf')
                        ['original_cropbox_is_offset'])
        self.assertFalse(any(c['private_source_review_sheet_created'] for c in x['cases']
            if c['source_file']!='rotated_page.pdf'))
    def test_frozen_historical_candidate_denominators_unchanged(self):
        original=read('tabula_engine_holdout_first_pass_20261104.json')
        queue=read('tabula_operator_review_queue_20261104.json')
        self.assertEqual(original['primary_candidate_rows'],325)
        self.assertEqual(queue['original_source_witnessed_review_rows'],68)
        self.assertEqual(queue['blocked_from_operator_review'],257)
        self.assertEqual(original['primary_engine_errors_or_timeouts'],5)
if __name__=='__main__':unittest.main()
