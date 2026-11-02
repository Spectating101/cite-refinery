"""Reject false positive adoption conclusions from heterogeneous parser replays."""
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]


class HeterogeneousPdfRegression(unittest.TestCase):
    def test_unfamiliar_document_failure_rate_is_retained(self):
        data=json.loads((ROOT/'examples/discovery/heterogeneous_pdf_regression_replay_20261103.json').read_text())
        prior=json.loads((ROOT/'examples/discovery/real_pdf_operator_pilot_20261103.json').read_text())
        prior_by_id={c['id']:c for c in prior['cases']}
        self.assertEqual(len(data),5)
        self.assertEqual({d['source_id'] for d in data},set(prior_by_id))
        self.assertEqual(sum(d['status']=='executed' for d in data),2)
        self.assertEqual(sum(d['status']=='error' for d in data),3)
        for entry in data:
            self.assertEqual(entry['sha256'],prior_by_id[entry['source_id']]['source_sha256'])
            self.assertEqual(entry['selected_pages'],prior_by_id[entry['source_id']]['selected_physical_pages'])
            self.assertGreater(entry['seconds'],0)
            self.assertEqual(entry['status']=='executed',prior_by_id[entry['source_id']]['optional']['status']=='ok')
            if entry['status']=='error':
                self.assertIsNone(entry['tables_detected'])
                self.assertEqual(entry['error']['type'],'ValueError')

if __name__=='__main__':unittest.main()
