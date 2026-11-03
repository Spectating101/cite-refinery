"""The untouched holdout is immutable evidence, not a retrospective success sample."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest
from scripts.score_locked_pdf_holdout_20261104 import normalize, gold_row_text

ROOT=Path(__file__).resolve().parents[1]


class ProspectiveExternalPDFHoldout(unittest.TestCase):
    def load(self,name):
        return json.loads((ROOT/'examples/discovery'/name).read_text())

    def test_all_16_locked_cases_present_and_no_publisher_authority(self):
        manifest=self.load('ruled_pdf_holdout_preregistration_20261104.json')
        result=self.load('ruled_pdf_untouched_holdout_baseline_20261104.json')
        self.assertEqual(manifest['upstream_commit'],result['upstream_git_commit'])
        self.assertEqual(result['locked_engine_commit'][:7],'2f5bd7f')
        self.assertEqual(len(manifest['selected_source_files']),16)
        self.assertEqual((result['intent_to_test_pages'],result['attempted_pages']),(16,16))
        self.assertEqual((result['source_pages_with_row_proposals'],
                          result['source_pages_abstained'],result['source_pages_errors']),(6,9,1))
        self.assertEqual(result['total_source_row_proposals'],68)
        self.assertEqual({x['filename'] for x in result['cases']},
                         {x['filename'] for x in manifest['selected_source_files']})
        self.assertFalse(result['original_pdf_bytes_committed'])
        self.assertFalse(result['original_pdf_full_row_proposals_committed'])
        self.assertEqual(result['trusted_pdfscope_promotions'],0)
        self.assertFalse(result['auto_publish'])
        self.assertFalse(result['auto_register_dataset'])
        self.assertTrue(result['all_failures_kept_in_denominator'])
        self.assertEqual(result['independently_scored_row_pages'],0)
        self.assertTrue(result['precision_unknown_without_independent_oracle'])
        for x in result['cases']:
            self.assertEqual(len(x['original_sha256']),64)
            self.assertEqual(x['physical_page'],1)
            self.assertEqual(x['trusted_published_rows'],0)
            self.assertIsNone(x['row_precision'])
            self.assertIsNone(x['row_recall'])
            self.assertIsNone(x['externally_verified_true_positive_rows'])
        self.assertEqual([x['filename'] for x in result['cases'] if x['scan_status']=='ERROR_NO_SOURCE_AUTHORITY'],['vertical_header.pdf'])
        self.assertEqual([x['error_type'] for x in result['cases'] if x.get('error_type')],['ValueError'])

    def test_third_party_upstream_expected_rows_do_not_cover_all_16(self):
        baseline=self.load('ruled_pdf_untouched_holdout_baseline_20261104.json')
        score=self.load('ruled_pdf_untouched_holdout_scoring_20261104.json')
        self.assertEqual(score['source_manifest_sha256'],baseline['manifest_sha256'])
        self.assertEqual(score['source_upstream_git_commit'],baseline['upstream_git_commit'])
        self.assertEqual(score['pages_with_upstream_expected_row_assertions'],6)
        self.assertEqual(score['pages_without_comparable_upstream_expected_row_assertions'],10)
        self.assertEqual(len(score['unscored_filenames']),10)
        self.assertEqual((score['exact_normalized_row_tp'],score['exact_normalized_row_fp'],score['exact_normalized_row_fn']),(10,0,97))
        self.assertEqual(score['scored_row_precision_conditional'],1.0)
        self.assertAlmostEqual(score['scored_row_recall_conditional'],10/107,places=12)
        self.assertTrue(score['metric_not_full_corpus_or_global_accuracy'])
        self.assertTrue(score['third_party_parser_tests_not_independent_human_adjudication'])
        self.assertTrue(score['unscored_candidate_rows_not_assumed_true'])
        self.assertEqual(score['trusted_dataset_promotions'],0)
        self.assertFalse(score['auto_publish'])
        allscored={x['filename']:x for x in score['scored_cases']}
        self.assertEqual(len(allscored),6)
        self.assertEqual(allscored['multiple_tables.pdf']['expected_upstream_test_rows'],10)
        self.assertEqual(allscored['multiple_tables.pdf']['exact_normalized_row_tp'],10)
        self.assertEqual(allscored['multiple_tables.pdf']['exact_normalized_row_fn'],0)
        for fn in ('vertical_header.pdf','background_lines_1.pdf','edge_tol.pdf','column_span_2.pdf','detect_vertical_false.pdf'):
            self.assertEqual(allscored[fn]['exact_normalized_row_tp'],0)
            self.assertGreater(allscored[fn]['exact_normalized_row_fn'],0)
        self.assertEqual(sum(x['exact_normalized_row_tp'] for x in score['scored_cases']),10)
        self.assertEqual(sum(x['exact_normalized_row_fn'] for x in score['scored_cases']),97)
        self.assertEqual(score['release_decision'],'HOLD_LOW_RECALL_AND_UNKNOWN_GOLD')

    def test_strict_row_normalization_does_not_fuzzy_match_nonidentical_rows(self):
        self.assertEqual(normalize('  Vgvhgh   Hj   Hj  Hj '),'vgvhgh hj hj hj')
        self.assertNotEqual(normalize('Net  income  866'),normalize('Net  earnings  866'))
        self.assertNotEqual(normalize('Newbusiness'),normalize('New business'))
        self.assertEqual(gold_row_text(['Trtrt','H','Gh']), 'trtrt h gh')
        with self.assertRaises(ValueError):
            gold_row_text(['foo',None])


if __name__=='__main__':unittest.main()
