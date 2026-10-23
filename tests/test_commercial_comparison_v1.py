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

    def test_direct_competitor_does_not_currently_change_conversion_verdict(self):
        # Negative capability receipt: the conversion evaluator does not
        # consume an independently documented, equivalent existing service.
        import copy
        import json
        from cite_refinery.commercial_comparison import CASE_ROOT, atlas_decision
        source = json.loads(
            (CASE_ROOT / "pv-independent-rooftop-performance-audit.json").read_text(encoding="utf-8")
        )
        with_alternative = copy.deepcopy(source)
        with_alternative["competitive_alternatives"] = [{
            "name": "Solargis PV Performance Assessment",
            "url": "https://www.solargis.com/services/pv-performance-assessment",
            "documented_overlap": "Third-party PV output assessment, P50/P90 model comparison, loss analysis",
            "status": "official_provider_description",
        }]
        plain = atlas_decision(source)
        with_competitor = atlas_decision(with_alternative)
        # The record hash changes, but commercial verdict does not.
        self.assertNotEqual(plain["input_sha256"], with_competitor["input_sha256"])
        for key in ("readiness", "next_test", "funded_or_signed_buyer"):
            self.assertEqual(plain[key], with_competitor[key])

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
