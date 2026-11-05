"""Pin negative acceptance: repeated printed footnotes are not source links."""
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]


class OriginalFootnoteMarkerHoldout(unittest.TestCase):
    def test_real_publisher_footnote_marker_reuse_forces_review(self):
        report=json.loads((ROOT/'examples/discovery/real_pdf_footnote_ambiguity_20261103.json').read_text())
        oracle=json.loads((ROOT/'examples/discovery/operator_reviewed_financial_cells_20261103.json').read_text())
        self.assertEqual(report['schema'],'atlas.real_pdf_footnote_marker_holdout.v1')
        self.assertEqual(report['source_count'],4)
        self.assertEqual(report['ambiguous_reused_markers'],2)
        self.assertEqual(report['single_printed_definition_manual_review'],2)
        self.assertEqual(report['semantic_links_verified'],0)
        self.assertEqual(report['automatic_acceptances'],0)
        self.assertEqual(report['authority'],'REVIEW_ONLY_NO_AUTO_FOOTNOTE_LINK')
        self.assertEqual(report['status'],'HOLD_FOOTNOTE_SEMANTIC_LINK_UNVERIFIED')
        sha={x['id']:x['sha256'] for x in oracle['sources']}
        for case in report['cases']:
            self.assertEqual(case['original_source_sha256'],sha[case['source_id']])
            self.assertEqual(case['semantic_note_link'],'NOT_VERIFIED')
            self.assertEqual(case['authority'],'REVIEW_ONLY_NEVER_AUTO_LINK_FOOTNOTE')
            if case['source_id'].startswith('apple_'):
                self.assertEqual(case['candidate_definition_count'],2)
                self.assertEqual(case['status'],'abstain_ambiguous_reused_marker')
            else:
                self.assertEqual(case['candidate_definition_count'],1)
                self.assertEqual(case['status'],'single_printed_definition_requires_manual_link_review')


if __name__=='__main__':unittest.main()
