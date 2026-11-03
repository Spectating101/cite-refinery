"""Public acceptance stores blank-invitation metadata, no reviewer choices."""
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]


class BlindReviewInvitationReadiness(unittest.TestCase):
    def test_pinned_real_pdf_blind_packets_are_private_and_not_completed(self):
        result=json.loads((ROOT/'examples/discovery/blind_review_invitations_20261103.json').read_text())
        oracle=json.loads((ROOT/'examples/discovery/operator_reviewed_financial_cells_20261103.json').read_text())
        self.assertEqual(result['schema'],'atlas.blind_original_pdf_review_invitations.v1')
        self.assertEqual(result['source_count'],2)
        self.assertEqual(result['invitation_count'],4)
        self.assertEqual(result['actual_independent_human_reviewer_count'],0)
        self.assertEqual(result['source_semantics_independently_adjudicated'],0)
        self.assertFalse(result['source_pdf_bytes_committed'])
        self.assertFalse(result['review_session_secrets_committed'])
        self.assertFalse(result['auto_publish'])
        self.assertFalse(result['auto_register_dataset'])
        self.assertEqual(result['status'],'INVITATIONS_PREPARED_AWAITING_SEPARATE_HUMAN_REVIEWS')
        originals={s['id']:s for s in oracle['sources']}
        for item in result['cases']:
            original=originals[item['source_id']]
            self.assertEqual(original['sha256'],item['original_source_sha256'])
            self.assertEqual(original['url'],item['official_publisher_url'])
            self.assertEqual(item['empty_review_invitations_created'],2)
            self.assertEqual(item['operator_annotations_submitted'],0)
            self.assertFalse(item['second_human_review_completed'])
            self.assertFalse(item['private_review_session_ids_committed'])
        # No secret session IDs or local private packet paths in the public receipt.
        text=json.dumps(result)
        self.assertNotIn('\"review_session_id\":',text)
        self.assertNotIn('private-blind-review-invites',text)

if __name__=='__main__':unittest.main()
