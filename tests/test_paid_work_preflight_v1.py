from __future__ import annotations

import copy
import io
import json
from pathlib import Path
import unittest
from contextlib import redirect_stdout

from cite_refinery.paid_work_preflight import validate, evaluate, render
from cite_refinery.business_workbench import ROOT

FILE = ROOT / "research_materials/opportunity_conversion/paid_work_original_issues_20261024.json"


def original():
    return json.loads(FILE.read_text(encoding="utf-8"))


class PublicPaidWorkPreflightTests(unittest.TestCase):
    def test_five_original_issues_have_no_confirmed_claimable_income(self):
        result = evaluate(original(), as_of="2026-10-24")
        self.assertEqual(result["schema"], "cite_refinery.paid_work_preflight_report.v1")
        self.assertEqual(len(result["listings"]), 5)
        d = {r["lead_id"]: r for r in result["listings"]}
        self.assertEqual(d["claude-builders-hook-3"]["gate"], "reject_payment_discrepancy")
        self.assertEqual(d["tt-metal-56290-closed"]["gate"], "reject_closed_issue")
        self.assertEqual(d["tt-metal-56908-assigned"]["gate"], "reject_already_assigned")
        self.assertEqual(d["sybil-intel-b580-216"]["gate"], "hold_hardware_validation")
        self.assertEqual(d["solana-pay-kit-354-unpaid"]["gate"], "reject_no_payment_offer")
        self.assertIsNone(d["solana-pay-kit-354-unpaid"]["nominal_bounty"])
        self.assertEqual(result["ready_to_code_count"], 0)
        self.assertIsNone(result["actual_earnings"])
        self.assertEqual(result["verified_paid_contract_count"], 0)
        self.assertTrue(all(not row["recommended_work_start"] for row in result["listings"]))
        self.assertTrue(all(row["expected_value"] is None for row in result["listings"]))

    def test_aggregate_proxy_is_not_a_payout_or_competitor_pr_count(self):
        result = evaluate(original(), as_of="2026-10-24")
        row = result["listings"][0]
        self.assertEqual(row["competition_proxy_issue_comments"], 1886)
        self.assertIn("not a count of competing PRs", row["competition_proxy_limitation"])
        self.assertEqual(row["nominal_bounty"]["amount"], "100.00")
        self.assertIn("contingent_advertised", row["nominal_bounty"]["value_type"])
        self.assertIsNone(row["recorded_earned_income"])

    def test_stale_primary_claims_cannot_be_pursued(self):
        data = original()
        row = data["listings"][0]
        row["payment_claim_disputed"] = False
        row["last_checked_on"] = "2026-09-01"
        out = evaluate(data, as_of="2026-10-24")
        self.assertEqual(out["listings"][0]["gate"], "hold_refresh_original_issue")

    def test_even_invented_payment_approval_does_not_trigger_work(self):
        data = original()
        row = data["listings"][3]
        row.update({
            "hardware": "none", "technical_fit": "documented",
            "payment_state": "independently_confirmed", "payout_rail_checked": True,
            "operator_can_receive_payout": True, "claimed_status": "unclaimed",
            "payment_claim_disputed": False,
        })
        result = evaluate(data, as_of="2026-10-24")
        # Even user-authored claims that all preconditions pass can only
        # allow manual review; the software cannot contact or claim work.
        self.assertEqual(result["listings"][3]["gate"], "manual_claim_review_only")
        self.assertFalse(result["listings"][3]["recommended_work_start"])
        self.assertEqual(result["ready_to_code_count"], 0)

    def test_mirror_urls_cannot_be_original_issue_evidence(self):
        d = original()
        d["listings"][0]["original_issue_url"] = (
            "https://github.com/zhangjiayang6835-cyber/bounty-plaza/issues/1216"
        )
        with self.assertRaisesRegex(ValueError, "not in evidence"):
            validate(d)
        d = original()
        d["listings"][1]["original_issue_url"] = "https://bountyos.rovidev.com/en/github-bounty-board/"
        with self.assertRaisesRegex(ValueError, "DIRECT original"):
            validate(d)

    def test_money_and_source_integrity_guard(self):
        invalids = [
            {"advertised_amount": "-100"},
            {"advertised_amount": "NaN"},
            {"payment_state": "independently_confirmed", "sources": [
                "https://github.com/claude-builders-bounty/claude-builders-bounty/issues/3",
            ]},
            {"issue_comment_count": -3},
            {"payout_rail_checked": "true"},
        ]
        for bad in invalids:
            d = original()
            d["listings"][0].update(bad)
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate(d)
        d = original()
        d["listings"][-1]["advertised_amount"] = "0.01"
        with self.assertRaisesRegex(ValueError, "must not invent"):
            validate(d)

    def test_markdown_does_not_assume_paid_outcomes(self):
        content = render(evaluate(original(), as_of="2026-10-24"))
        self.assertIn("USD 100.00", content)
        self.assertIn("none", content)
        self.assertIn("No payout", content)
        self.assertNotIn("guaranteed USD", content)


if __name__ == "__main__":
    unittest.main()
