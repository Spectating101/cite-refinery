"""Source row region transfer: preserve complete samples and abstain on ambiguity."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class OriginalRuledRowRegionExternalAcceptance(unittest.TestCase):
    def test_real_public_fixtures_are_sha_pinned_and_held_for_operator(self):
        result=json.loads((ROOT/'examples/discovery/ruled_row_region_external_acceptance_20261104.json').read_text())
        oracle=json.loads((ROOT/'examples/discovery/ruled_row_region_external_oracle_20261104.json').read_text())
        self.assertEqual(result['schema'],'atlas.original_pdf_row_region_external_acceptance.v1')
        self.assertEqual(result['public_external_fixture_count'],2)
        self.assertEqual(result['preexisting_reference_document_count'],1)
        self.assertFalse(result['external_fixture_selection_blind'])
        self.assertTrue(result['source_bytes_sha_verified_locally'])
        self.assertFalse(result['original_pdf_bytes_committed'])
        self.assertFalse(result['full_unreviewed_source_word_text_committed'])
        self.assertTrue(result['selected_operator_literal_controls_committed'])
        self.assertFalse(result['human_second_reviewer'])
        self.assertFalse(result['table_semantics_verified'])
        self.assertFalse(result['auto_publish'])
        self.assertFalse(result['auto_register_dataset'])
        self.assertEqual(result['trusted_pdfscope_promotions'],0)
        self.assertEqual(result['release_decision'],'HOLD_UNVERIFIED_SOURCE_ROWS_AND_HELDOUT_LAYOUT_AMBIGUITIES')
        for key in ('health','foo','previous_ruled_reference'):
            r=result['cases'][key];s=oracle[key]
            self.assertEqual(r['source_sha256'],s['source_sha256'])
            self.assertEqual(r['original_physical_page'],s['physical_page'])
            self.assertEqual(r['source_column_count'],len(s['column_edges_pdf'])-1)
            self.assertEqual(r['strategy'],s['source_rule_strategy'])
            self.assertEqual(r['trusted_dataset_rows'],0)
            self.assertFalse(r['operator_review_completed'])
            self.assertGreaterEqual(r['source_words_in_operator_region'],r['source_words_assigned'])
            self.assertEqual(r['source_words_ambiguous_or_unassigned'],
                             r['source_words_in_operator_region']-r['source_words_assigned'])

    def test_external_health_grid_witnesses_source_words_but_not_complete_publication(self):
        r=json.loads((ROOT/'examples/discovery/ruled_row_region_external_acceptance_20261104.json').read_text())['cases']['health']
        self.assertEqual((r['source_rule_boundaries'],r['source_row_region_proposals'],
                          r['source_column_count']),(24,23,8))
        self.assertEqual((r['source_words_in_operator_region'],r['source_words_assigned']),(190,190))
        self.assertEqual(r['single_line_rows_needing_review'],23)
        self.assertEqual(r['flagged_empty_or_multiline_rows'],0)
        self.assertEqual(r['source_literal_controls_matched'],5)
        self.assertEqual(r['original_page_literal_control_rows'],5)
        self.assertEqual([x['row_index'] for x in r['sample_control_results']],[0,6,12,18,22])
        self.assertTrue(all(x['literal_source_cell_match'] and x['cell_count']==8
                            for x in r['sample_control_results']))
        self.assertFalse(r['complete_entire_table_across_pages'])
        self.assertFalse(r['authenticated_original_government_source'])

    def test_complex_header_foo_holdout_retains_one_unassigned_source_word(self):
        r=json.loads((ROOT/'examples/discovery/ruled_row_region_external_acceptance_20261104.json').read_text())['cases']['foo']
        self.assertEqual(r['source_row_region_proposals'],6)
        self.assertEqual(r['source_words_in_operator_region'],52)
        self.assertEqual(r['source_words_assigned'],51)
        self.assertEqual(r['source_words_ambiguous_or_unassigned'],1)
        self.assertGreaterEqual(r['flagged_empty_or_multiline_rows'],1)
        self.assertTrue(r['held_on_incomplete_original_word_coverage'])
        self.assertEqual(r['geometry_status'],'ABSTAIN_BOUNDARY_OR_WORD_COVERAGE')

    def test_old_original_pdf_still_proposes_exactly_same_source_grid(self):
        r=json.loads((ROOT/'examples/discovery/ruled_row_region_external_acceptance_20261104.json').read_text())['cases']['previous_ruled_reference']
        prior=json.loads((ROOT/'examples/discovery/original_ruled_cost_table_acceptance_20261103.json').read_text())
        self.assertEqual(r['source_sha256'],prior['original_sha256'])
        self.assertEqual(r['source_row_region_proposals'],5)
        self.assertEqual(r['source_column_count'],3)
        self.assertEqual(r['source_words_assigned'],15)
        self.assertEqual(r['source_words_in_operator_region'],15)
        self.assertEqual(r['source_words_ambiguous_or_unassigned'],0)
        self.assertEqual(r['geometry_status'],'ROW_REGIONS_EXACT_ORIGINAL_WORD_COVERAGE_REVIEW_REQUIRED')
        self.assertEqual(prior['native_crop_matching_perturbations'],1)
        self.assertFalse(r['operator_review_completed'])


if __name__=='__main__':
    unittest.main()
