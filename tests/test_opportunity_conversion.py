from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from cite_refinery.opportunity_conversion import evaluate
from cite_refinery.opportunity_cli import render

ROOT = Path(__file__).resolve().parents[1] / "research_materials/opportunity_conversion"


def fixture(name="foodsoft-food-coop-deployment"):
    return json.loads((ROOT / (name + ".json")).read_text(encoding="utf-8"))


class ConversionCaseTests(unittest.TestCase):
    def test_three_real_cases_are_unproven_not_fake_arbitrage(self):
        expected = {
            "foodsoft-food-coop-deployment": "conditional_on_license_compliance_review",
            "food-rescue-mvp-partner-audit": "blocked_until_rights_resolved",
            "ofn-paid-contributor-route": "conditional_on_license_compliance_review",
        }
        for name, route in expected.items():
            with self.subTest(name=name):
                result = evaluate(fixture(name))
                self.assertEqual(result["conversion_routes"]["self_execution"], route)
                self.assertEqual(result["readiness"], "evidence_lead_only")
                self.assertEqual(result["underconversion"]["status"], "not_established")
                self.assertEqual(result["unit_economics"]["status"], "not_estimated")
                self.assertIn("not a proven", render(result).lower())

    def test_contractor_and_maintainer_are_distinct_revenue_routes(self):
        foodsoft = evaluate(fixture())
        ofn = evaluate(fixture("ofn-paid-contributor-route"))
        self.assertIn("community_contribution", foodsoft["conversion_routes"]["maintainer_service"])
        self.assertIn("paid_contributor", ofn["conversion_routes"]["maintainer_service"])
        self.assertIn("application", ofn["recommended_next_test"])

    def test_no_unlicensed_self_execution_or_reuse(self):
        food = evaluate(fixture("food-rescue-mvp-partner-audit"))
        self.assertEqual(food["conversion_routes"]["reuse_as_component"], "blocked_until_rights_resolved")
        self.assertIn("license/permission", food["recommended_next_test"])

    def test_invalid_or_unproven_evidence_disallowed(self):
        for field, value in [("demand_status", "expressed_interest")]:
            source = fixture()
            source["market"][field] = value
            with self.subTest(stage=value), self.assertRaisesRegex(ValueError, "demand stage requires"):
                evaluate(source)
        bad = fixture()
        bad["market"]["demand_status"] = "signed_commitment"
        with self.assertRaisesRegex(ValueError, "funded demand"):
            evaluate(bad)
        bad["market"]["demand_status"] = "funded_request"
        bad["market"]["signals"][0]["status"] = "reviewed"
        with self.assertRaisesRegex(ValueError, "funded demand"):
            evaluate(bad)

    def test_repo_slug_and_capability_reference_must_match(self):
        source = fixture()
        source["repository"]["slug"] = "unrelated/repository"
        with self.assertRaisesRegex(ValueError, "disagree"):
            evaluate(source)
        source = fixture()
        source["repository"]["capability_source"] = "https://example.org/fake-readme"
        with self.assertRaisesRegex(ValueError, "inside"):
            evaluate(source)

    def test_positive_license_requires_in_repo_evidence(self):
        source = fixture("food-rescue-mvp-partner-audit")
        source["repository"]["license_status"] = "recognized_permissive"
        with self.assertRaisesRegex(ValueError, "license evidence"):
            evaluate(source)
        source = fixture()
        source["repository"]["license_url"] = "https://example.org/fake-license"
        with self.assertRaisesRegex(ValueError, "belong"):
            evaluate(source)

    def test_permission_and_deployment_are_explicit(self):
        source = fixture()
        source["compliance"]["deployment_authorized"] = True
        with self.assertRaisesRegex(ValueError, "rights review"):
            evaluate(source)
        source = fixture()
        source["upstream"]["engagement"] = "direct_permission"
        with self.assertRaisesRegex(ValueError, "direct upstream permission"):
            evaluate(source)
        source = fixture()
        source["upstream"]["paid_contribution_invitation"] = True
        self.assertRaises(ValueError, evaluate, source)

    def test_hypothetical_economics_never_claim_revenue(self):
        source = fixture()
        source["unit_economics"] = {"basis": "hypothetical", "currency": "TWD",
                                   "price_per_unit": "25000", "cost_per_unit": "15000"}
        result = evaluate(source)
        self.assertEqual(result["unit_economics"]["gross_contribution"], "10000")
        self.assertEqual(result["unit_economics"]["gross_margin"], "40.00%")
        self.assertEqual(result["unit_economics"]["status"], "illustrative_unit_scenario")
        self.assertEqual(result["readiness"], "evidence_lead_only")
        for raw in ["nan", -1, "Infinity"]:
            bad = copy.deepcopy(source)
            bad["unit_economics"]["cost_per_unit"] = raw
            self.assertRaises(ValueError, evaluate, bad)
        source["unit_economics"]["basis"] = "verified_contract"
        with self.assertRaisesRegex(ValueError, "actual reference"):
            evaluate(source)

    def test_no_cross_case_identity_collapse(self):
        left = fixture()
        right = fixture("ofn-paid-contributor-route")
        self.assertNotEqual(evaluate(left)["input_sha256"], evaluate(right)["input_sha256"])
        self.assertEqual(evaluate(left), evaluate(left))

    def test_missing_problem_sources_fail_closed(self):
        source = fixture()
        source["problem"]["sources"] = []
        with self.assertRaisesRegex(ValueError, "source"):
            evaluate(source)


if __name__ == "__main__":
    unittest.main()
