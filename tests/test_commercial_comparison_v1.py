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

    def test_direct_competitor_changes_next_test_but_not_buyer_or_readiness(self):
        # Competing services must change the proposed research action, but
        # they do not conjure a buyer or a paid engagement.
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
            "scope": "direct",
        }]
        plain = atlas_decision(source)
        with_competitor = atlas_decision(with_alternative)
        self.assertNotEqual(plain["input_sha256"], with_competitor["input_sha256"])
        self.assertNotEqual(plain["next_test"], with_competitor["next_test"])
        self.assertEqual(with_competitor["next_test"], "verify_competitive_advantage")
        self.assertEqual(plain["readiness"], with_competitor["readiness"])
        self.assertFalse(with_competitor["funded_or_signed_buyer"])

    def test_caller_supplied_fake_reviewed_contract_now_fails_status_gate(self):
        # Source labels and issue URLs are not authorized contract receipts.
        result = run_benchmark()
        red = result["adversarial"]
        self.assertFalse(red["expected_funded_or_signed_buyer"])
        self.assertFalse(red["unsafe_trust_in_caller_metadata"])
        self.assertEqual(red["atlas_readiness"], "evidence_lead_only")


if __name__ == "__main__":
    unittest.main()
