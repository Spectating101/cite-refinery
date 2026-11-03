"""Pinned original-vector source rows are complete only inside explicit rules."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class RuledCostTableOriginalSourceAcceptance(unittest.TestCase):
    def test_manually_scoped_full_table_words_are_separate_from_native_crop_stability(self):
        receipt=json.loads((ROOT/'examples/discovery/original_ruled_cost_table_acceptance_20261103.json').read_text())
        oracle=json.loads((ROOT/'examples/discovery/original_ruled_cost_table_oracle_20261103.json').read_text())
        pilot=json.loads((ROOT/'examples/discovery/real_pdf_operator_pilot_20261103.json').read_text())
        stability=json.loads((ROOT/'examples/discovery/failed_page_native_crop_stability_20261103.json').read_text())
        source=next(x for x in pilot['cases'] if x['id']==oracle['source_id'])
        original_stability=next(x for x in stability['cases'] if x['source_id']==oracle['source_id'])
        self.assertEqual(receipt['schema'],'atlas.original_ruled_cost_table_completeness.v1')
        self.assertEqual(receipt['original_sha256'],source['source_sha256'])
        self.assertEqual(receipt['original_sha256'],oracle['original_sha256'])
        self.assertEqual(receipt['original_physical_page'],oracle['original_physical_page'])
        self.assertEqual(receipt['source_rule_region_pdf'],oracle['ruled_source_bbox_pdf'])
        self.assertEqual(receipt['column_edges_pdf'],oracle['operator_source_column_edges_pdf'])
        self.assertEqual(receipt['original_vector_horizontal_row_boundaries'],6)
        self.assertEqual((receipt['bounded_original_ruled_table_rows'],receipt['bounded_original_ruled_table_columns']),(5,3))
        self.assertEqual(receipt['original_words_in_ruled_region'],15)
        self.assertTrue(receipt['all_original_words_assigned_to_one_cell'])
        self.assertEqual(receipt['source_rows_exact_word_inventory'],5)
        self.assertTrue(receipt['bounded_original_table_complete_from_original_rules'])
        self.assertEqual(receipt['operator_selected_native_crop_parser_rows'],5)
        self.assertEqual(receipt['operator_selected_native_crop_parser_cells'],15)
        self.assertEqual(len(receipt['operator_native_candidate_row_exactness']),5)
        self.assertTrue(all(x['parser_source_row_exact_match'] for x in receipt['operator_native_candidate_row_exactness']))
        self.assertEqual(receipt['original_native_numeric_word_witnesses'],4)
        self.assertEqual(receipt['original_native_numeric_word_abstentions'],0)
        self.assertEqual(receipt['native_crop_matching_perturbations'],original_stability['successful_perturbations'])
        self.assertEqual(receipt['native_crop_perturbations_tested'],original_stability['perturbation_count'])
        self.assertFalse(receipt['native_crop_boundary_stability_verified'])
        self.assertTrue(receipt['complete_only_within_explicit_vector_rulings'])
        self.assertFalse(receipt['original_document_semantics_independently_reviewed'])
        self.assertFalse(receipt['table_prices_current_or_market_verified'])
        self.assertFalse(receipt['auto_publish'])
        self.assertFalse(receipt['auto_register_dataset'])
        self.assertEqual(receipt['trusted_pdfscope_promotions'],0)
        self.assertEqual(receipt['decision'],'HOLD_CROP_FRAGILITY_AND_INDEPENDENT_SEMANTICS_REVIEW')

if __name__=='__main__':unittest.main()
