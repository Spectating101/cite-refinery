"""Operator document review can corroborate both conflicting note choices."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class OperatorAssistedReviewReceiptTests(unittest.TestCase):
    def test_two_real_apple_pdfs_have_no_auto_semantic_attribution(self):
        oracle=json.loads((ROOT/'examples/discovery/operator_reviewed_financial_cells_20261103.json').read_text())
        receipt=json.loads((ROOT/'examples/discovery/operator_assisted_pdf_review_20261103.json').read_text())
        self.assertEqual(receipt['schema'],'atlas.operator_assisted_source_review_acceptance.v1')
        self.assertEqual(receipt['authority'],'REVIEW_ONLY_ORIGINAL_SOURCE_OPERATOR_ASSERTIONS')
        self.assertEqual(receipt['documents'],2)
        self.assertEqual(receipt['annotations'],8)
        self.assertEqual(receipt['source_witnesses_recorded'],6)
        self.assertEqual(receipt['unresolved_source_note_choices'],2)
        self.assertEqual(receipt['conflicting_alternative_source_witnesses'],4)
        self.assertEqual(receipt['semantic_note_links_independently_approved'],0)
        self.assertEqual(receipt['trusted_pdfscope_promotions'],0)
        self.assertFalse(receipt['automatic_publishing'])
        self.assertFalse(receipt['automatic_dataset_registration'])
        self.assertFalse(receipt['independent_second_reviewer'])
        self.assertFalse(receipt['publisher_pdf_bytes_committed'])
        self.assertEqual(receipt['decision'],'HOLD_SECOND_REVIEW_REQUIRED')
        digests={entry['id']:entry['sha256'] for entry in oracle['sources']}
        self.assertEqual({row['source_id'] for row in receipt['cases']},{'apple_fy25q1','apple_fy25q4'})
        for row in receipt['cases']:
            self.assertEqual(row['original_sha256'],digests[row['source_id']])
            self.assertEqual(row['source_period_status'],'original_period_witness_match')
            self.assertEqual(row['original_statement_header_witnesses'],2)
            self.assertTrue(row['independent_second_review_completed'] is False)
            self.assertEqual(row['trusted_semantic_link'],'NOT_VERIFIED')
        for source in ('apple_fy25q1','apple_fy25q4'):
            cases={case['case']:case for case in receipt['cases'] if case['source_id']==source}
            self.assertEqual(set(cases),{'unresolved','segment_definition','category_definition','unfootnoted_control'})
            self.assertEqual(cases['unresolved']['review_state'],'unresolved_note_selection')
            self.assertEqual(cases['unresolved']['candidate_note_definitions'],2)
            for alternate in ('segment_definition','category_definition'):
                self.assertEqual(cases[alternate]['review_state'],
                                 'operator_source_witnesses_recorded_second_review_pending')
                self.assertTrue(cases[alternate]['original_definition_witnessed'])
                self.assertEqual(cases[alternate]['candidate_note_definitions'],2)
                self.assertEqual(cases[alternate]['target_id'],cases['unresolved']['target_id'])
            self.assertEqual(cases['unfootnoted_control']['review_state'],
                             'operator_source_witnesses_recorded_second_review_pending')
            self.assertEqual(cases['unfootnoted_control']['operator_decision'],'none')

if __name__=='__main__':unittest.main()
