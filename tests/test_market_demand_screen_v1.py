from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from cite_refinery.market_demand_screen import validate, screen, render
from cite_refinery.business_workbench import ROOT
from cite_refinery.business_cli import main as business_cli
from contextlib import redirect_stdout
import io

SOURCE = ROOT / "research_materials/opportunity_conversion/public_demand_scan_20261024.json"
PLAN = ROOT / "examples/atlas_business_workbench_demo_v1.json"


def fixture():
    return json.loads(SOURCE.read_text(encoding="utf-8"))


class PublicMarketDemandScreenTests(unittest.TestCase):
    def test_real_public_openings_rejected_or_held_on_access_not_budget_size(self):
        board = screen(fixture(), as_of="2026-10-24")
        self.assertEqual(board["schema"], "cite_refinery.public_demand_screen.v1")
        self.assertEqual(len(board["leads"]), 3)
        keyed = {r["lead_id"]: r for r in board["leads"]}
        self.assertEqual(keyed["cognee-mergetober-2026"]["status"], "hold_eligibility")
        self.assertEqual(keyed["taiwan-mod-ai-pm-2026"]["status"], "verify_primary_notice")
        self.assertEqual(keyed["ncku-medical-data-2026"]["status"], "reject_scope_mismatch")
        self.assertEqual(board["pursue_now_count"], 0)
        self.assertEqual(board["verified_contract_count"], 0)
        self.assertIsNone(board["realized_revenue"])
        self.assertFalse(any(x["buyer_contract_verified"] for x in board["leads"]))
        self.assertTrue(all(x["expected_profit"] is None and x["award_probability"] is None
                            for x in board["leads"]))

    def test_deadline_first_and_only_explicit_as_of(self):
        result = screen(fixture(), as_of="2026-11-06")
        self.assertTrue(all(x["status"] == "expired_no_submission" for x in result["leads"]))
        self.assertTrue(all(x["days_until_deadline"] < 0 for x in result["leads"]))
        with self.assertRaisesRegex(ValueError, "as_of"):
            screen(fixture(), as_of="yesterday")

    def test_even_verified_fit_does_not_create_guaranteed_prize(self):
        d = fixture()
        item = d["leads"][0]
        item["eligibility"] = "verified_eligible"
        item["capability_fit"] = "validated"
        result = screen(d, as_of="2026-10-24")
        self.assertEqual(result["leads"][0]["status"], "optional_competition_not_contract")
        self.assertIsNone(result["leads"][0]["expected_profit"])
        self.assertFalse(result["leads"][0]["buyer_contract_verified"])

    def test_primary_buyer_eligibility_and_fit_still_not_signed_contract(self):
        d = fixture()
        item = d["leads"][1]
        item["authority"] = "first_party"
        item["eligibility"] = "verified_eligible"
        item["capability_fit"] = "validated"
        result = screen(d, as_of="2026-10-24")
        self.assertEqual(result["leads"][1]["status"], "eligible_for_manual_diligence_only")
        self.assertIsNone(result["realized_revenue"])
        self.assertEqual(result["verified_contract_count"], 0)
        self.assertEqual(result["pursue_now_count"], 0)

    def test_funded_listing_cannot_be_forged_into_contract_or_profit(self):
        d = fixture()
        d["leads"][1]["commitment_status"] = "signed_customer_contract"
        with self.assertRaisesRegex(ValueError, "cannot declare signed contracting"):
            screen(d, as_of="2026-10-24")
        d = fixture()
        d["leads"][1]["advertised_value"]["amount"] = "NaN"
        with self.assertRaisesRegex(ValueError, "nonnegative finite"):
            validate(d)
        d = fixture()
        d["leads"][0]["advertised_value"]["amount"] = "-100"
        with self.assertRaisesRegex(ValueError, "nonnegative finite"):
            validate(d)
        d = fixture()
        d["leads"][0]["listing_url"] = "http://phishing.local"
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            validate(d)

    def test_ineligible_and_stale_gate_without_pretending_bid(self):
        d = fixture()
        d["leads"][0]["eligibility"] = "ineligible"
        self.assertEqual(screen(d, as_of="2026-10-24")["leads"][0]["status"], "reject_ineligible")
        d = fixture()
        d["leads"][0]["checked_on"] = "2026-10-01"
        self.assertEqual(screen(d, as_of="2026-10-24")["leads"][0]["status"], "verify_primary_notice")

    def test_integrates_into_current_business_cli_without_mutating_records(self):
        output = io.StringIO()
        with redirect_stdout(output):
            business_cli([
                "board", "--plan", str(PLAN),
                "--demand-scan", str(SOURCE), "--as-of", "2026-10-24",
                "--format", "json",
            ])
        result = json.loads(output.getvalue())
        self.assertEqual(len(result["opportunities"]), 4)
        self.assertEqual(len(result["public_demand_screen"]["leads"]), 3)
        self.assertEqual(result["total"]["reported_payment"], "0.00")
        self.assertEqual(result["public_demand_screen"]["pursue_now_count"], 0)
        self.assertIn("No advertised tender budget", render(result["public_demand_screen"]))

if __name__ == "__main__":
    unittest.main()
