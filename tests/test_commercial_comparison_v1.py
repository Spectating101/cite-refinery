from __future__ import annotations

import unittest

from cite_refinery.commercial_comparison import run_benchmark, render


class CommercialComparisonTests(unittest.TestCase):
    def test_equal_evidence_three_cases_are_correctly_gated(self):
        result = run_benchmark()
        self.assertEqual(result["total_checks"], 18)
        self.assertEqual(result["atlas_correct"], 18)
        self.assertEqual(result["baseline_correct"], 18)
        self.assertEqual(len(result["cases"]), 3)
        self.assertIn("not_independent_agent_trial", result["kind"])

    def test_no_claim_of_agent_advantage_from_unblinded_easy_cases(self):
        report = render(run_benchmark()).lower()
        self.assertIn("not a demonstrated atlas advantage", report)
        self.assertIn("not blinded or independent", report)
        self.assertIn("no matched tokens", report)

    def test_caller_supplied_fake_reviewed_contract_currently_passes_status_gate(self):
        # Negative capability receipt: public issue URL mislabeled as signed deal.
        # A future strict source verifier should cause this test to be changed
        # to demand external receipts and reject the forged classification.
        result = run_benchmark()
        red = result["adversarial"]
        self.assertFalse(red["expected_funded_or_signed_buyer"])
        self.assertTrue(red["unsafe_trust_in_caller_metadata"])
        self.assertEqual(
            red["atlas_readiness"],
            "candidate_for_paid_pilot_subject_to_contract_and_rights",
        )


if __name__ == "__main__":
    unittest.main()
