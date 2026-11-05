"""Pinned read-only source-word replay receipt; optional CV never downloaded in CI."""
from __future__ import annotations
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]

class OriginalPdfWordWitnessReceiptTests(unittest.TestCase):
    def test_receipt_is_consistent_with_manual_source_oracle(self):
        oracle=json.loads((ROOT/'examples/discovery/operator_reviewed_financial_cells_20261103.json').read_text())
        receipt=json.loads((ROOT/'examples/discovery/original_pdf_word_witness_20261103.json').read_text())
        self.assertEqual(receipt['schema'],'atlas.original_pdf_word_witness_acceptance.v1')
        self.assertEqual(receipt['document_count'],5)
        self.assertEqual(receipt['selected_cells'],40)
        self.assertEqual(receipt['source_word_matches'],40)
        self.assertEqual(receipt['abstentions'],0)
        self.assertFalse(receipt['trust_promotion'])
        self.assertFalse(receipt['operator_period_group_reviewed'])
        self.assertEqual(receipt['authority'],'REVIEW_ONLY_NO_TRUSTED_EXPORT')
        self.assertEqual({x['source_sha256'] for x in receipt['cases']},{x['sha256'] for x in oracle['sources']})
        for case in receipt['cases']:
            self.assertEqual(case['selected'],8)
            self.assertEqual(case['matched'],8)
            self.assertEqual(len(case['cell_checks']),8)
            for entry in case['cell_checks']:
                self.assertEqual(entry['status'],'source_word_witness_match')
                self.assertEqual(len(entry['checks']),6)
                self.assertTrue(all(entry['checks'].values()))

if __name__=='__main__': unittest.main()
