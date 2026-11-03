"""Pinned original hetero source evidence separates shape and truth/provenance."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class HeterogeneousFinancialCandidateQuality(unittest.TestCase):
    def test_sanitized_source_cell_replay_preserves_all_untrusted_gates(self):
        result=json.loads((ROOT/'examples/discovery/heterogeneous_source_cell_quality_20261103.json').read_text())
        oracle=json.loads((ROOT/'examples/discovery/heterogeneous_original_source_cell_oracle_20261103.json').read_text())
        pilot=json.loads((ROOT/'examples/discovery/real_pdf_operator_pilot_20261103.json').read_text())
        original={x['id']:x for x in pilot['cases']}
        self.assertEqual(result['schema'],'atlas.heterogeneous_source_cell_quality_acceptance.v1')
        self.assertEqual(result['documents'],5)
        self.assertEqual(result['table_regions_triaged'],7)
        self.assertEqual(result['candidate_rows_triaged'],33)
        self.assertEqual(result['shape_reviewable_rows'],8)
        self.assertEqual(result['abstained_candidate_rows'],25)
        self.assertEqual(result['candidate_cells_total'],131)
        self.assertEqual(result['shape_reviewable_rows']+result['abstained_candidate_rows'],result['candidate_rows_triaged'])
        self.assertEqual(result['trusted_data_promotions'],0)
        self.assertFalse(result['actual_second_human_adjudication'])
        self.assertFalse(result['primary_issuer_source_verified'])
        self.assertFalse(result['auto_publish'])
        self.assertFalse(result['auto_register_dataset'])
        self.assertFalse(result['source_file_bytes_committed'])
        self.assertEqual(result['decision'],'HOLD_UNVERIFIED_LAYOUTS_SECONDARY_SOURCE_AND_FAILED_PAGES')
        for case in result['cases']:
            self.assertEqual(case['original_sha256'],original[case['source_id']]['source_sha256'])
            self.assertEqual(case['selected_pages'],original[case['source_id']]['selected_physical_pages'])
            for table in case['table_shape_diagnostics']:
                self.assertEqual(table['row_count'],table['shape_reviewable_rows']+table['abstained_rows'])
                self.assertEqual(len(table['outcomes']),table['row_count'])
                self.assertTrue(all(a in {'source_verification_required_not_approved',
                    'abstain_missing_selected_cells','abstain_flattened_multiline_cells',
                    'abstain_axis_ticks_or_not_single_label',
                    'abstain_non_atomic_currency_or_number'} for a in table['outcomes']))
        source=result['manual_source_cell_acceptance']
        self.assertEqual(source['source_id'],'arxiv2506')
        self.assertEqual(source['page'],oracle['physical_page'])
        self.assertEqual(source['original_sha256'],oracle['source_sha256'])
        self.assertEqual(source['reviewed_cells'],8)
        self.assertEqual(source['source_word_matches'],6)
        self.assertEqual(source['source_word_abstentions'],2)
        self.assertFalse(source['publisher_original_verified'])
        self.assertFalse(source['trusted_financial_export'])
        self.assertEqual(source['provenance']['classification'],
            'SECONDARY_REPRODUCED_ISSUER_FACT_SHEET_IN_RESEARCH_ARTICLE')
        self.assertFalse(source['provenance']['trusted_primary_financial_data'])
        by_id={x['id']:x for x in source['source_label_and_value_flags']}
        self.assertEqual(set(by_id),{x['id'] for x in oracle['source_cells']})
        for row in by_id.values():
            self.assertEqual(len(row['checks']),6)
            if row['id'] in ('manulife-05','manulife-06'):
                self.assertEqual(row['status'],'abstain_word_or_geometry_mismatch')
                self.assertFalse(row['checks']['label_candidate_match'])
                self.assertTrue(row['checks']['label_original_word_match'])
                self.assertTrue(row['checks']['value_original_word_match'])
            else:
                self.assertEqual(row['status'],'source_word_witness_match')
                self.assertTrue(all(row['checks'].values()))

if __name__=='__main__':unittest.main()
