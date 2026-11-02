"""Offline acceptance receipt and fail-closed semantic-period declaration contract."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class PeriodContextAcceptanceTests(unittest.TestCase):
    def test_original_pdf_group_date_year_period_witness(self):
        oracle=json.loads((ROOT/'examples/discovery/operator_reviewed_financial_cells_20261103.json').read_text())
        receipt=json.loads((ROOT/'examples/discovery/original_pdf_period_context_20261103.json').read_text())
        self.assertEqual(receipt['schema'],'atlas.period_context_original_source_acceptance.v1')
        self.assertEqual(receipt['document_count'],5)
        self.assertEqual(receipt['checked_cells'],40)
        self.assertEqual(receipt['matched'],40)
        self.assertEqual(receipt['abstained'],0)
        self.assertFalse(receipt['operator_double_reviewed'])
        self.assertFalse(receipt['auto_publish'])
        self.assertFalse(receipt['auto_register_dataset'])
        self.assertEqual(receipt['authority'],'REVIEW_ONLY_NOT_TRUSTED_CSV')
        self.assertEqual({x['original_sha256'] for x in receipt['cases']},
                         {x['sha256'] for x in oracle['sources']})
        self.assertEqual({r['kind'] for case in receipt['cases'] for r in case['cell_verdicts']},
                         {'quarter','three_months','nine_months','twelve_months'})
        for case in receipt['cases']:
            self.assertEqual(case['checked_cells'],8)
            self.assertEqual(len(case['cell_verdicts']),8)
            for claim in case['cell_verdicts']:
                self.assertEqual(claim['status'],'original_period_witness_match')
                self.assertEqual(len(claim['checks']),7)
                self.assertTrue(all(claim['checks'].values()))

    def test_multi_period_same_year_requires_distinct_explicit_anchors(self):
        oracle=json.loads((ROOT/'examples/discovery/operator_reviewed_financial_cells_20261103.json').read_text())
        apple=next(s for s in oracle['sources'] if s['id']=='apple_fy25q4')
        self.assertEqual(apple['word_witness_header_contract']['period_key_to_printed_text']['current_quarter'],
                         apple['word_witness_header_contract']['period_key_to_printed_text']['current_full_year'])
        quarters=apple['period_anchor_contracts']['0']
        self.assertNotEqual(quarters['current_quarter']['kind'],quarters['current_full_year']['kind'])
        self.assertNotEqual(quarters['current_quarter']['group_bbox_pdf'],quarters['current_full_year']['group_bbox_pdf'])
        amazon=next(s for s in oracle['sources'] if s['id']=='amazon_2026q3')
        self.assertEqual(amazon['word_witness_header_contract']['period_key_to_printed_text']['current_quarter'],
                         amazon['word_witness_header_contract']['period_key_to_printed_text']['current_nine_months'])
        self.assertNotEqual(amazon['period_anchor_contracts']['0']['current_quarter']['kind'],
                            amazon['period_anchor_contracts']['0']['current_nine_months']['kind'])

if __name__=='__main__':unittest.main()
