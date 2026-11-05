"""Pinned original PDF operator queue and source geometry blockers; no decisions."""
import hashlib,json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]/'examples/discovery'

def load(name):
    return json.loads((ROOT/name).read_text())


class OperatorReviewQueueSourceAcceptance(unittest.TestCase):
    def test_12_first_pages_and_325_rows_never_drop_blocked_denominator(self):
        queue=load('tabula_operator_review_queue_20261104.json')
        first=load('tabula_engine_holdout_first_pass_20261104.json')
        manifest=load('tabula_engine_holdout_preregistration_20261104.json')
        self.assertEqual(queue['schema'],'atlas.original_pdf_operator_review_pilot.v1')
        self.assertEqual(queue['source_manifest_sha256'],
            hashlib.sha256((ROOT/'tabula_engine_holdout_preregistration_20261104.json').read_bytes()).hexdigest())
        self.assertEqual(queue['frozen_first_pass_sha256'],
            hashlib.sha256((ROOT/'tabula_engine_holdout_first_pass_20261104.json').read_bytes()).hexdigest())
        self.assertEqual(queue['original_first_pages_attempted'],12)
        self.assertEqual(queue['original_candidate_rows'],325)
        self.assertEqual(queue['original_source_witnessed_review_rows'],68)
        self.assertEqual(queue['blocked_from_operator_review'],257)
        self.assertEqual(queue['private_review_sheets_created'],3)
        self.assertEqual(queue['original_candidates_failing_engine'],5)
        self.assertEqual(queue['operator_actions_submitted'],0)
        self.assertEqual(queue['real_independent_reviewers'],0)
        self.assertEqual(queue['trusted_pdfscope_promotions'],0)
        self.assertEqual(queue['trusted_dataset_rows'],0)
        self.assertFalse(queue['source_pdf_and_review_text_committed'])
        self.assertFalse(queue['auto_publish'])
        self.assertFalse(queue['auto_register_dataset'])
        self.assertEqual(queue['release_state'],'HOLD_OPERATOR_AND_SECOND_REVIEW_MISSING')
        self.assertEqual(len(queue['cases']),12)
        self.assertEqual({x['source_file'] for x in queue['cases']},
                         {x['filename'] for x in manifest['files']})
        source={x['filename']:x for x in first['cases']}
        for case in queue['cases']:
            base=source[case['source_file']]
            self.assertEqual(case['original_sha256'],base['original_sha256'])
            self.assertEqual(case['first_pass_candidate_rows'],
                             base['engines']['hybrid']['candidate_rows'])
            self.assertEqual(case['operator_ready_rows']+case['blocked_review_rows'],
                             case['first_pass_candidate_rows'])
            self.assertEqual(case['reviewer_actions_submitted'],0)
            self.assertEqual(case['trusted_rows'],0)
            if case['review_sheet_created']:
                self.assertEqual(case['state'],'UNREVIEWED_OPERATOR_BUNDLE')
                self.assertEqual(len(case['source_packet_digest_sha256']),64)
                self.assertGreater(case['operator_ready_rows'],0)
        reviewable={x['source_file']:x['operator_ready_rows'] for x in queue['cases']
                    if x['operator_ready_rows']}
        self.assertEqual(reviewable,{'MultiColumn.pdf':44,
                                     'spanning_cells.pdf':21,
                                     'jpeg2000.pdf':3})
        self.assertEqual(next(x for x in queue['cases'] if x['source_file']=='twotables.pdf')
                         ['blocked_review_rows'],54)

    def test_geometry_errors_are_original_sha_pinned_and_not_bypassed(self):
        record=load('tabula_original_geometry_blockers_20261104.json')
        baseline=load('tabula_engine_holdout_first_pass_20261104.json')
        self.assertEqual(record['schema'],'atlas.original_pdf_geometry_blockers.v1')
        self.assertEqual(record['checked_original_first_pages'],12)
        self.assertEqual(record['frozen_primary_engine_errors'],5)
        self.assertEqual(record['rotation_blockers'],3)
        self.assertEqual(record['cropbox_or_bbox_blockers'],1)
        self.assertEqual(record['other_candidate_geometry_errors'],1)
        self.assertEqual(record['unverified_source_transformations_applied'],0)
        self.assertEqual(record['source_qualified_for_trusted_use'],0)
        self.assertFalse(record['auto_publish'])
        self.assertEqual(record['state'],'HOLD_SEPARATE_CALIBRATION_REQUIRED')
        src={x['filename']:x for x in baseline['cases']}
        for x in record['cases']:
            self.assertEqual(x['original_sha256'],src[x['source_file']]['original_sha256'])
            self.assertFalse(x['original_coordinate_calibration_approved'])
        rotated={x['source_file'] for x in record['cases']
                 if x['reason']=='ROTATED_ORIGINAL_PAGE_REQUIRES_CALIBRATION'}
        self.assertEqual(rotated,{'rotated_page.pdf','schools.pdf',
            'Publication_of_award_of_Bids_for_Transport_Sector__August_2016.pdf'})
        cropped=[x for x in record['cases']
                 if x['reason']=='OFFSET_OR_CROPPED_ORIGINAL_PAGE_REQUIRES_CALIBRATION']
        self.assertEqual([x['source_file'] for x in cropped],['should_detect_rulings.pdf'])
        self.assertEqual(next(x['source_file'] for x in record['cases']
            if x['reason']=='CAMELOT_TABLE_ROW_OR_CELL_GEOMETRY_INCONSISTENT'),
                         'argentina_diputados_voting_record.pdf')


if __name__=='__main__':unittest.main()
