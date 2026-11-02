"""Offline receipt validation: real originals checked by isolated bwrap worker."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
class PeriodOfflineAcceptance(unittest.TestCase):
    def test_isolated_original_group_receipts_are_readonly_and_pinned(self):
        oracle=json.loads((ROOT/'examples/discovery/operator_reviewed_financial_cells_20261103.json').read_text())
        receipt=json.loads((ROOT/'examples/discovery/isolated_period_context_acceptance_20261103.json').read_text())
        self.assertEqual(receipt['schema'],'atlas.period_context_original_source_acceptance.v1')
        self.assertTrue(receipt['isolated_replay'])
        self.assertFalse(receipt['auto_publish'])
        self.assertFalse(receipt['auto_register_dataset'])
        self.assertFalse(receipt['operator_double_reviewed'])
        self.assertEqual(receipt['authority'],'REVIEW_ONLY_NOT_TRUSTED_CSV')
        self.assertEqual((receipt['document_count'],receipt['checked_cells'],receipt['matched'],receipt['isolated_matched'],receipt['abstained']), (5,40,40,40,0))
        self.assertEqual({c['original_sha256'] for c in receipt['cases']}, {s['sha256'] for s in oracle['sources']})
        for c in receipt['cases']:
            self.assertEqual(c['checked_cells'],8)
            self.assertEqual(c['matched'],8)
            self.assertEqual(len(c['cell_verdicts']),8)
            self.assertIsNotNone(c['isolated'])
            self.assertEqual(c['isolated']['runtime'],'independent_offline_bwrap_seccomp')
            self.assertEqual(c['isolated']['network'],'disabled')
            self.assertEqual(c['isolated']['authority'],'REVIEW_ONLY_NO_TRUSTED_CSV')
            self.assertTrue(c['isolated']['passed'])
            self.assertEqual((c['isolated']['matched'],c['isolated']['abstained']),(8,0))
            self.assertTrue(all(entry['status']=='original_period_witness_match' and all(entry['checks'].values()) for entry in c['cell_verdicts']))

if __name__=='__main__':unittest.main()
