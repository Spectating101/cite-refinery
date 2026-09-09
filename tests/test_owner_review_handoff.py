"""Regression tests for the boundary between an issued pack and a returned review."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from cite_refinery.intake_review import build_intake_owner_review_pack, validate_owner_review_response
from cite_refinery.problem_intake import IntakeMode, OwnerIntake

ROOT = Path(__file__).resolve().parents[1]


def issued_pack():
    intake = OwnerIntake.load(ROOT / 'pilot/intake/yzu-yongfeng-after-school.v0.1.json')
    return build_intake_owner_review_pack(
        intake, intake.to_problem_packet(steward='test-curator'),
        rubrics=json.loads((ROOT / 'pilot/rubrics.v0.1.json').read_text()),
    )


def completed_pack():
    pack = issued_pack()
    pack['response'].update(
        disposition='confirm', source_still_current=True,
        owner_identity_and_role_correct=True, item_scores=[1] * 5,
    )
    return pack


class OwnerReviewValidationTests(unittest.TestCase):
    def test_valid_draft_and_completed_response(self):
        self.assertEqual(validate_owner_review_response(issued_pack()), [])
        self.assertEqual(validate_owner_review_response(completed_pack()), [])

    def test_review_does_not_define_its_own_allowed_dispositions(self):
        pack = completed_pack()
        pack['allowed_dispositions'].append('deploy')
        pack['response']['disposition'] = 'deploy'
        self.assertTrue(validate_owner_review_response(pack))

    def test_scores_are_binary_integers_not_booleans_strings_or_null_on_completion(self):
        for value in (True, False, '1', 2, -1, 0.5, None, {}, float('nan')):
            with self.subTest(value=value):
                pack = completed_pack()
                pack['response']['item_scores'][0] = value
                self.assertTrue(validate_owner_review_response(pack))

    def test_actual_booleans_are_required(self):
        for field in ('source_still_current', 'owner_identity_and_role_correct', 'reframe_required'):
            pack = completed_pack()
            pack['response'][field] = 'false'
            self.assertTrue(validate_owner_review_response(pack))

    def test_unknown_duplicate_and_conflicting_work_choices_rejected(self):
        for case in ('unknown', 'duplicate', 'conflict'):
            with self.subTest(case=case):
                pack = completed_pack()
                key = pack['problem']['candidate_work'][0]['subproblem_id']
                pack['response']['acceptable_work_subproblem_ids'] = [key]
                if case == 'unknown':
                    pack['response']['acceptable_work_subproblem_ids'] = ['psub:nonexistent']
                elif case == 'duplicate':
                    pack['response']['acceptable_work_subproblem_ids'].append(key)
                else:
                    pack['response']['unacceptable_work_subproblem_ids'] = [key]
                self.assertTrue(validate_owner_review_response(pack))

    def test_confirm_cannot_say_need_stale_wrong_owner_or_reframe_required(self):
        for field, value in [('source_still_current', False),
                             ('owner_identity_and_role_correct', False), ('reframe_required', True)]:
            pack = completed_pack()
            pack['response'][field] = value
            self.assertTrue(validate_owner_review_response(pack))

    def test_empty_rubric_cannot_make_completion_vacuously_valid(self):
        pack = completed_pack()
        pack['rubric']['items'] = []
        pack['response']['item_scores'] = []
        self.assertTrue(validate_owner_review_response(pack))

    def test_identity_mismatch_and_duplicate_candidate_ids_rejected(self):
        pack = completed_pack()
        pack['problem_id'] = 'problem:other'
        self.assertTrue(validate_owner_review_response(pack))
        pack = completed_pack()
        pack['problem']['candidate_work'].append(deepcopy(pack['problem']['candidate_work'][0]))
        self.assertTrue(validate_owner_review_response(pack))

    def test_malformed_containers_return_errors_not_tracebacks(self):
        for value in (None, [], 'bad', 12, {'schema': 'problem-owner-intake-review/v0.1'}):
            self.assertTrue(validate_owner_review_response(value))
        for field in ('response', 'rubric', 'problem', 'allowed_dispositions'):
            for bad in (None, 'bad', 17, []):
                pack = completed_pack()
                pack[field] = bad
                self.assertTrue(validate_owner_review_response(pack))

    def test_missing_response_fields_or_escalation_fields_are_rejected(self):
        pack = completed_pack()
        del pack['response']['funding_or_resource_notes']
        self.assertTrue(validate_owner_review_response(pack))
        pack = completed_pack()
        pack['response']['authority_granted'] = True
        self.assertTrue(validate_owner_review_response(pack))

    def test_institutional_source_locator_does_not_escape_in_review_pack(self):
        intake = OwnerIntake.load(ROOT / 'pilot/intake/yzu-yongfeng-after-school.v0.1.json')
        intake.intake_mode = IntakeMode.INSTITUTIONAL_BATCH
        intake.source_ref = 'internal:staff-only-location'
        # Round trip through the actual constructor as the CLI does.
        intake = OwnerIntake.from_dict(intake.to_dict())
        packet = intake.to_problem_packet(steward='test-curator')
        pack = build_intake_owner_review_pack(intake, packet,
            rubrics=json.loads((ROOT / 'pilot/rubrics.v0.1.json').read_text()))
        self.assertNotIn('internal:staff-only-location', json.dumps(pack))

class OwnerReviewReturnTests(unittest.TestCase):
    def test_completion_gate_distinguishes_valid_draft_from_return(self):
        self.assertTrue(validate_owner_review_response(issued_pack(), require_complete=True))
        self.assertEqual(validate_owner_review_response(completed_pack(), require_complete=True), [])

    def test_return_binds_to_actual_issued_content_not_just_problem_id(self):
        original = issued_pack()
        returned = deepcopy(original)
        returned['response'] = completed_pack()['response']
        self.assertEqual(validate_owner_review_response(returned, expected_pack=original), [])
        for key in ('problem', 'rubric', 'instructions', 'potential_owner', 'source_ref'):
            changed = deepcopy(returned)
            if key == 'problem':
                changed[key]['observed_condition'] += ' Changed after issue.'
            elif key == 'rubric':
                changed[key]['items'][0] = 'A substituted easier question.'
            elif key == 'instructions':
                changed[key].append('Additional instruction.')
            else:
                changed[key] += ' altered'
            self.assertTrue(validate_owner_review_response(changed, expected_pack=original), key)

    def test_receipt_is_non_mutating_and_never_claims_identity_authority_or_funding(self):
        from cite_refinery.owner_review_contract import build_owner_review_receipt
        original = issued_pack()
        returned = deepcopy(original)
        returned['response'] = completed_pack()['response']
        before = deepcopy((original, returned))
        receipt = build_owner_review_receipt(original, returned, actor='test-curator', receipt_ref='test:local-return')
        self.assertEqual(receipt['status'], 'pending-curator-decision')
        for key in ('respondent_identity_verified', 'owner_confirmation_applied', 'work_opened', 'funding_committed', 'authority_granted'):
            self.assertIs(receipt[key], False)
        self.assertEqual((original, returned), before)
        receipt['response']['owner_notes'] = 'not the input'
        self.assertNotEqual(receipt['response']['owner_notes'], returned['response']['owner_notes'])

    def test_each_final_disposition_has_a_safe_followup(self):
        from cite_refinery.owner_review_contract import build_owner_review_receipt
        for disposition in ('confirm', 'reframe', 'stale', 'already-resolved', 'decline'):
            original = issued_pack()
            returned = deepcopy(original)
            returned['response'] = completed_pack()['response']
            returned['response'].update(disposition=disposition,
                source_still_current=disposition != 'stale', reframe_required=disposition == 'reframe',
                owner_notes='AUTOMATED TEST: no actual owner response.')
            receipt = build_owner_review_receipt(original, returned, actor='test', receipt_ref='test:receipt')
            self.assertTrue(receipt['next_action'])
            self.assertFalse(receipt['work_opened'])

    def test_cli_writes_private_receipt_and_refuses_overwrite_or_tampered_context(self):
        from cite_refinery.intake_cli import main
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); original = issued_pack(); returned = deepcopy(original)
            returned['response'] = completed_pack()['response']
            (root / 'issued.json').write_text(json.dumps(original))
            (root / 'returned.json').write_text(json.dumps(returned))
            args = ['record-owner-review', str(root / 'returned.json'), '--original', str(root / 'issued.json'),
                    '--actor', 'test-curator', '--receipt-ref', 'test:receipt', '--out', str(root / 'receipt.json')]
            self.assertEqual(main(args), 0)
            receipt_bytes = (root / 'receipt.json').read_bytes()
            self.assertEqual(main(args), 2)
            self.assertEqual((root / 'receipt.json').read_bytes(), receipt_bytes)
            self.assertEqual((root / 'receipt.json').stat().st_mode & 0o777, 0o600)
            returned['problem']['title'] += ' unreviewed edit'
            (root / 'returned.json').write_text(json.dumps(returned))
            args[-1] = str(root / 'bad-receipt.json')
            self.assertEqual(main(args), 2)
            self.assertFalse((root / 'bad-receipt.json').exists())

    def test_cli_rejects_malformed_json_shapes_without_traceback(self):
        from cite_refinery.intake_cli import main
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'bad.json'
            for value in (None, [], 'bad'):
                path.write_text(json.dumps(value))
                self.assertEqual(main(['validate-owner-review', str(path)]), 2)

    def test_single_file_renderer_escapes_untrusted_script_delimiters(self):
        from cite_refinery.owner_review_page import render_owner_review_page
        pack = issued_pack()
        payload = '</script><script>globalThis.pwned=true</script>'
        pack['problem']['title'] = payload
        page = render_owner_review_page(pack)
        self.assertNotIn(payload, page)
        self.assertIn('\\u003c/script\\u003e', page)
        self.assertIn("connect-src 'none'".replace("'", '&#x27;'), page)
        self.assertNotIn('src="review.js"', page)
        self.assertNotIn('href="styles.css"', page)
        self.assertIn('id="preloadedReview"', page)

    def test_single_file_and_source_paths_must_differ(self):
        from cite_refinery.intake_cli import main
        source = ROOT / 'pilot/intake/yzu-yongfeng-after-school.v0.1.json'
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'same.html'
            self.assertEqual(main(['owner-review', str(source), '--steward', 'test', '--out', str(out), '--html-out', str(out)]), 2)
            self.assertFalse(out.exists())

    def test_missing_assets_are_reported_not_silently_omitted(self):
        from cite_refinery.owner_review_page import render_owner_review_page
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, 'review assets not found'):
                render_owner_review_page(issued_pack(), assets_dir=td)


if __name__ == '__main__':
    unittest.main()
