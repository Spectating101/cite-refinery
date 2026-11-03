"""Pinned real original PDF crop sensitivity: success at baseline is insufficient."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class RealOriginalCropRobustness(unittest.TestCase):
    def test_source_sha_fixed_stability_denominators_are_not_rewritten(self):
        result=json.loads((ROOT/'examples/discovery/failed_page_native_crop_stability_20261103.json').read_text())
        original=json.loads((ROOT/'examples/discovery/operator_cropped_failed_pdf_pages_20261103.json').read_text())
        pilot=json.loads((ROOT/'examples/discovery/real_pdf_operator_pilot_20261103.json').read_text())
        pins={x['id']:x['source_sha256'] for x in pilot['cases']}
        self.assertEqual(result['schema'],'atlas.original_failed_page_crop_robustness.v1')
        self.assertEqual((result['tested_original_pages'],result['baseline_source_word_matches']), (2,8))
        self.assertEqual((result['total_boundary_perturbations'],result['all_source_words_matched_perturbations'],result['failed_or_abstained_perturbations']),(10,6,4))
        self.assertEqual((result['crop_sensitive_pages'],result['robust_under_tested_crops_pages']),(1,1))
        self.assertEqual(result['perturbation_offsets_pdf_points'],[-5,-2,0,2,5])
        self.assertEqual(result['trusted_pdfscope_promotions'],0)
        self.assertFalse(result['auto_publish'])
        self.assertFalse(result['auto_register_dataset'])
        self.assertFalse(result['independent_human_review'])
        self.assertFalse(result['verified_source_table_completeness'])
        self.assertFalse(result['source_pdf_bytes_committed'])
        self.assertEqual(result['decision'],'HOLD_CROP_SENSITIVITY_AND_UNREVIEWED_SEMANTICS')
        cases={case['source_id']:case for case in result['cases']}
        self.assertEqual(set(cases),{'arxiv2506','arxiv2604'})
        inputs={r['source_id']:r for r in original['table_cases']}
        for name,case in cases.items():
            self.assertEqual(case['original_sha256'],pins[name])
            self.assertEqual(case['physical_page'],inputs[name]['physical_page'])
            self.assertEqual(case['operator_crop_bbox_pdf'],inputs[name]['crop_bbox_pdf'])
            self.assertEqual(case['original_img2table_error_code'],inputs[name]['strict_img2table_error_code'])
            self.assertEqual(case['selected_original_source_cells'],4)
            self.assertEqual(case['baseline_match_count'],4)
            self.assertEqual(len(case['trials']),5)
            self.assertEqual([r['inset_pdf_points'] for r in case['trials']],[-5,-2,0,2,5])
            self.assertEqual(case['successful_perturbations']+case['failed_or_abstained_perturbations'],5)
            self.assertFalse(case['source_table_completeness_verified'])
        sensitive=cases['arxiv2506']
        self.assertEqual(sensitive['successful_perturbations'],1)
        self.assertEqual(sensitive['failed_or_abstained_perturbations'],4)
        self.assertFalse(sensitive['all_tested_crops_match'])
        self.assertEqual(sensitive['review_state'],'CROP_SENSITIVE_OPERATOR_REVIEW_HOLD')
        self.assertEqual([r['status'] for r in sensitive['trials']],[
            'ABSTAIN_CROP_SHAPE_CHANGED','ABSTAIN_CROP_SHAPE_CHANGED',
            'ALL_SELECTED_ORIGINAL_WORDS_MATCH','ABSTAIN_CROP_SHAPE_CHANGED',
            'ABSTAIN_CROP_SHAPE_CHANGED'])
        stable=cases['arxiv2604']
        self.assertEqual(stable['successful_perturbations'],5)
        self.assertEqual(stable['failed_or_abstained_perturbations'],0)
        self.assertTrue(stable['all_tested_crops_match'])
        self.assertEqual(stable['review_state'],'CROP_STABLE_ORIGINAL_SOURCE_WORDS_NOT_SEMANTIC_APPROVAL')

if __name__=='__main__':unittest.main()
