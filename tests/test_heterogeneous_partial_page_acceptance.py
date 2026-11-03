"""Partial extraction is not a substitute for original-cell truth or full coverage."""
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]


class PageIsolatedHeterogeneousAcceptance(unittest.TestCase):
    def test_real_original_page_holdout_recovers_pages_but_cannot_promote(self):
        receipt=json.loads((ROOT/'examples/discovery/heterogeneous_partial_page_acceptance_20261103.json').read_text())
        prior=json.loads((ROOT/'examples/discovery/real_pdf_operator_pilot_20261103.json').read_text())
        original={row['id']:row for row in prior['cases']}
        self.assertEqual(receipt['schema'],'atlas.heterogeneous_pdf_partial_page_acceptance.v1')
        self.assertEqual((receipt['document_count'],receipt['requested_pages'],
                          receipt['successful_pages'],receipt['failed_pages']),(5,10,7,3))
        self.assertEqual(receipt['documents_with_any_candidate_page'],5)
        self.assertEqual(receipt['documents_with_all_requested_pages'],2)
        self.assertEqual(receipt['candidate_cells'],131)
        self.assertEqual(receipt['pages_with_table_candidates'],6)
        self.assertFalse(receipt['numeric_cell_truth_checked'])
        self.assertFalse(receipt['auto_publish'])
        self.assertFalse(receipt['auto_register_dataset'])
        self.assertEqual(receipt['release_decision'],'HOLD_INCOMPLETE_COVERAGE_AND_SEMANTIC_REVIEW')
        self.assertEqual(len(receipt['cases']),len(original))
        for case in receipt['cases']:
            self.assertEqual(case['original_sha256'],original[case['source_id']]['source_sha256'])
            self.assertEqual(case['selected_physical_pages'],original[case['source_id']]['selected_physical_pages'])
            self.assertEqual(case['successful_page_count']+case['failed_page_count'],2)
            self.assertEqual(set(case['successful_pages']) | {x['page'] for x in case['failed_pages']},
                set(case['selected_physical_pages']))
            self.assertFalse(set(case['successful_pages']) & {x['page'] for x in case['failed_pages']})
            self.assertEqual(case['candidate_trust'],'UNVERIFIED_PARSER_HYPOTHESES')
            self.assertEqual(sum(x['candidate_cells'] for x in case['successful_page_details']),case['candidate_cell_count'])
            self.assertFalse(case['trusted_csv_export'])
            for failure in case['failed_pages']:
                self.assertIn(failure['error_code'],{
                    'UPSTREAM_TEXT_ALIGNMENT_ERROR','INVALID_EXTRACTED_CELL_GEOMETRY'})
        self.assertEqual({case['source_id'] for case in receipt['cases'] if case['failed_page_count']},
            {'bis138','arxiv2604','arxiv2506'})

if __name__=='__main__':unittest.main()
