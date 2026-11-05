"""Offline evidence-receipt schema checks; no PDF download or package install."""
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]

class RealPdfPilotTests(unittest.TestCase):
    def test_real_documents_are_exposed_as_unverified_negative_evidence(self):
        data=json.loads((ROOT/'examples/discovery/real_pdf_operator_pilot_20261103.json').read_text())
        self.assertEqual(data['schema'],'atlas.real_pdf_operator_pilot.v1')
        self.assertEqual(data['authority'],'REVIEW_ONLY')
        self.assertEqual(data['semantic_accuracy'],'NOT_MEASURED')
        self.assertEqual(data['independent_truth_checked_cells'],0)
        self.assertFalse(data['automatic_adoption'])
        self.assertEqual(data['decision'],'HOLD_OPTIONAL_PARSER_NOT_PRODUCTION_READY')
        self.assertEqual(len(data['cases']),5)
        self.assertEqual(len({r['source_sha256'] for r in data['cases']}),5)
        self.assertEqual(sum(r['optional']['status']=='ok' for r in data['cases']),2)
        self.assertEqual(sum(r['optional']['status']=='error' for r in data['cases']),3)
        self.assertTrue(all(r['native']['status']=='ok' for r in data['cases']))
        for r in data['cases']:
            self.assertEqual(len(r['source_sha256']),64)
            self.assertEqual(len(r['selected_physical_pages']),2)
            self.assertTrue(r['source_url'].startswith('https://'))
            for engine in ('native','optional'):
                self.assertEqual(r[engine]['reliability'],'UNVERIFIED_CANDIDATE_OR_SPURIOUS_REGION')

if __name__=='__main__':unittest.main()
