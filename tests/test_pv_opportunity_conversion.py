from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from cite_refinery.opportunity_conversion import evaluate


CASE = (
    Path(__file__).resolve().parents[1]
    / "research_materials/opportunity_conversion/pv-independent-rooftop-performance-audit.json"
)


def load_case():
    return json.loads(CASE.read_text(encoding="utf-8"))


class IndependentPVAuditOpportunityTests(unittest.TestCase):
    def test_real_sources_do_not_imply_real_buyer_or_underconversion(self):
        report = evaluate(load_case())
        self.assertEqual(report["schema"], "cite_refinery.opportunity_decision.v1")
        self.assertEqual(report["readiness"], "evidence_lead_only")
        self.assertEqual(report["buyer"]["demand_status"], "none")
        self.assertEqual(report["underconversion"]["status"], "not_established")
        self.assertEqual(
            report["conversion_routes"]["self_execution"],
            "conditional_on_license_compliance_review",
        )
        self.assertIn("Interview", report["recommended_next_test"])

    def test_license_is_a_component_candidate_not_deployment_permission(self):
        report = evaluate(load_case())
        self.assertEqual(report["candidate_asset"]["license_state"], "recognized_permissive")
        self.assertFalse(load_case()["compliance"]["deployment_authorized"])
        self.assertEqual(
            report["conversion_routes"]["reuse_as_component"],
            "technical_candidate_requires_integration_and_rights_check",
        )

    def test_price_and_margin_are_only_hypothetical(self):
        report = evaluate(load_case())
        economics = report["unit_economics"]
        self.assertEqual(economics["status"], "illustrative_unit_scenario")
        self.assertEqual(economics["gross_contribution"], "9000")
        self.assertEqual(economics["gross_margin"], "36.00%")
        self.assertEqual(report["readiness"], "evidence_lead_only")
        self.assertIn("Not actual earned profit", economics["limitation"])

    def test_cannot_invent_prospective_buyer_interest_or_budget(self):
        for status in ("expressed_interest", "funded_request", "signed_commitment"):
            with self.subTest(status=status):
                case = copy.deepcopy(load_case())
                case["market"]["demand_status"] = status
                with self.assertRaises(ValueError):
                    evaluate(case)

    def test_missing_license_blocks_reuse_even_with_a_good_fit(self):
        case = copy.deepcopy(load_case())
        case["repository"]["license_status"] = "no_license_detected"
        case["repository"]["license_url"] = None
        report = evaluate(case)
        self.assertEqual(
            report["conversion_routes"]["reuse_as_component"],
            "blocked_until_rights_resolved",
        )
        self.assertEqual(
            report["conversion_routes"]["self_execution"],
            "blocked_until_rights_resolved",
        )


if __name__ == "__main__":
    unittest.main()
