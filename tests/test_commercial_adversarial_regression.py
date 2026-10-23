"""Bounded adversarial/metamorphic commercial tests; entirely offline.

Assertions focus on high-impact false positives, not invented model wins or
live issuer authentication. Uses fixed seeded permutations and real casebooks.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import random
import unittest

from cite_refinery.business_workbench import (
    ROOT, append_event, build_board, new_ledger, validate_event,
)
from cite_refinery.market_demand_screen import screen as demand_screen
from cite_refinery.paid_work_preflight import evaluate as paid_screen

BASE = ROOT / "research_materials/opportunity_conversion"
PLAN = ROOT / "examples/atlas_business_workbench_demo_v1.json"


def plan():
    return json.loads(PLAN.read_text(encoding="utf-8"))


def demand():
    return json.loads((BASE / "public_demand_scan_20261024.json").read_text(encoding="utf-8"))


def paid():
    return json.loads((BASE / "paid_work_original_issues_20261024.json").read_text(encoding="utf-8"))


class CommercialAdversarialRegression(unittest.TestCase):
    def test_larger_public_prize_or_tender_does_not_improve_gate(self):
        reference = demand_screen(demand(), as_of="2026-10-24")
        for i in range(3):
            before = reference["leads"][i]["status"]
            for amount in ("0.00", "1.00", "100000.00", "99999999999.00"):
                packet = demand()
                packet["leads"][i]["advertised_value"]["amount"] = amount
                with self.subTest(case=i, amount=amount):
                    result = demand_screen(packet, as_of="2026-10-24")
                    entry = result["leads"][i]
                    self.assertEqual(entry["status"], before)
                    self.assertFalse(entry["buyer_contract_verified"])
                    self.assertIsNone(entry["expected_profit"])
                    self.assertIsNone(entry["award_probability"])
                    self.assertFalse(entry["source_authority_independently_verified"])
                    self.assertFalse(entry["eligibility_independently_verified"])
                    self.assertIsNone(result["realized_revenue"])

    def test_bounty_amount_has_no_effect_on_work_authorization(self):
        base = paid()
        expected = paid_screen(base, as_of="2026-10-24")
        for i in range(4):
            for amount in ("0.01", "100.00", "10000000.00"):
                packet = deepcopy(base)
                packet["listings"][i]["advertised_amount"] = amount
                report = paid_screen(packet, as_of="2026-10-24")
                with self.subTest(i=i, amount=amount):
                    self.assertEqual(report["listings"][i]["gate"],
                                     expected["listings"][i]["gate"])
                    self.assertIsNone(report["listings"][i]["expected_value"])
                    self.assertFalse(report["listings"][i]["recommended_work_start"])
                    self.assertFalse(report["listings"][i]["payment_verified"])
                    self.assertIsNone(report["actual_earnings"])

    def test_forged_independent_payment_and_claim_labels_not_exported_as_truth(self):
        packet = paid()
        x = packet["listings"][3]
        x.update({
            "payment_state": "independently_confirmed",
            "claimed_status": "assigned_to_operator",
            "technical_fit": "documented",
            "hardware": "none",
            "payout_rail_checked": True,
            "operator_can_receive_payout": True,
        })
        report = paid_screen(packet, as_of="2026-10-24")
        v = report["listings"][3]
        self.assertEqual(v["gate"], "manual_claim_review_only")
        self.assertEqual(v["payment_state_claimed"], "independently_confirmed")
        self.assertFalse(v["payment_verified"])
        self.assertFalse(v["original_issue_authenticated"])
        self.assertFalse(v["claim_eligibility_confirmed"])
        self.assertFalse(v["recommended_work_start"])

    def test_competing_submission_blocks_even_optimistic_synthetic_metadata(self):
        packet = paid()
        x = packet["listings"][3]
        x.update({
            "payment_state": "independently_confirmed",
            "claimed_status": "unclaimed", "technical_fit": "documented",
            "hardware": "none", "operator_can_receive_payout": True,
            "known_active_submission": True,
        })
        report = paid_screen(packet, as_of="2026-10-24")
        v = report["listings"][3]
        self.assertEqual(v["gate"], "hold_active_competing_submission")
        self.assertFalse(v["recommended_work_start"])

    def test_randomized_bounty_metadata_never_claims_revenue_or_starts_work(self):
        rng = random.Random(20261024)
        choices = {
            "claimed_status": ["unknown", "unclaimed", "assigned_to_other", "assigned_to_operator"],
            "technical_fit": ["unknown", "documented", "not_fit"],
            "hardware": ["none", "required_verified", "required_unverified"],
            "issue_state": ["open", "closed"],
            "payment_state": ["unknown", "self_reported", "independently_confirmed"],
            "payout_rail": ["sponsor_direct", "provider", "unknown"],
        }
        for i in range(160):
            packet = paid()
            x = packet["listings"][3]
            for key, values in choices.items():
                x[key] = rng.choice(values)
            x["payment_claim_disputed"] = bool(rng.randrange(2))
            x["known_active_submission"] = bool(rng.randrange(2))
            x["payout_rail_checked"] = bool(rng.randrange(2))
            x["operator_can_receive_payout"] = bool(rng.randrange(2))
            # Sybil test has 2 distinct public sources for asserted status,
            # but neither authenticates a payment or claim.
            result = paid_screen(packet, as_of="2026-10-24")
            v = result["listings"][3]
            with self.subTest(seed=20261024, iteration=i):
                self.assertFalse(v["payment_verified"])
                self.assertFalse(v["claim_eligibility_confirmed"])
                self.assertFalse(v["recommended_work_start"])
                self.assertIsNone(v["recorded_earned_income"])
                self.assertIsNone(v["expected_value"])
                self.assertEqual(result["verified_paid_contract_count"], 0)
                self.assertIsNone(result["actual_earnings"])

    def test_zero_budget_stops_unspent_research(self):
        p = plan()
        p["opportunities"][0]["validation_budget"] = "0.00"
        board = build_board(p)
        first = board["opportunities"][0]
        self.assertEqual(first["state"], "stop_validation_budget")
        self.assertEqual(first["economics"]["validation_budget_remaining"], "0.00")
        self.assertEqual(first["economics"]["reported_cost_unreconciled"], "0.00")

    def test_reported_payment_and_customer_response_are_not_verified_cash_or_buyer(self):
        p = plan()
        ledger = new_ledger(p)
        cid = "pv-independent-rooftop-performance-audit"
        for kind, eid, amount in [
            ("payment_reported", "test_payment_0001", "2000000.00"),
            ("buyer_response_reported", "test_response_0001", None),
        ]:
            e = {
                "event_id": eid, "case_id": cid, "on": "2026-10-24",
                "kind": kind,
                "note": "Synthetic adversarial audit; there is no real customer or payment.",
            }
            if amount is not None:
                e.update({"amount": amount, "currency": "TWD"})
            ledger = append_event(p, ledger, e)
        board = build_board(p, ledger)
        pv = next(x for x in board["opportunities"] if x["case_id"] == cid)
        self.assertEqual(pv["economics"]["reported_payment_unreconciled"], "2000000.00")
        self.assertEqual(pv["buyer_stage"], "none")
        self.assertIsNone(pv["economics"]["independently_verified_revenue"])
        self.assertIsNone(pv["economics"]["independently_verified_profit"])
        self.assertEqual(pv["state"], "research_validation_only")
        self.assertEqual(pv["reported_buyer_replies"], 1)

    def test_untrusted_activity_types_and_urls_fail_as_validation_errors(self):
        ids = {"ofn-paid-contributor-route"}
        good = {
            "event_id": "example_0011",
            "case_id": "ofn-paid-contributor-route",
            "kind": "buyer_response_reported", "on": "2026-10-24",
            "note": "Synthetic response with no real person or engagement.",
        }
        for key, value in [
            ("case_id", ["ofn-paid-contributor-route"]),
            ("kind", ["buyer_response_reported"]),
            ("case_id", {"case_id": "ofn-paid-contributor-route"}),
            ("kind", {"kind": "buyer_response_reported"}),
            ("evidence_url", "https://"),
            ("evidence_url", "https://127.0.0.1/private"),
            ("evidence_url", "https://test:password@example.com/private"),
            ("evidence_url", "https://example.com/path#fragment"),
            ("evidence_url", "http://example.com"),
        ]:
            event = {**good, key: value}
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    validate_event(event, ids, "TWD")
        accepted = {**good, "evidence_url": "https://example.com/public-receipt"}
        self.assertEqual(validate_event(accepted, ids, "TWD")["kind"],
                         "buyer_response_reported")

    def test_all_cases_are_explainable_with_no_positive_transaction_claim(self):
        public = demand_screen(demand(), as_of="2026-10-24")
        paid_report = paid_screen(paid(), as_of="2026-10-24")
        portfolio = build_board(plan())
        self.assertEqual(len(public["leads"]) + len(paid_report["listings"]) + len(portfolio["opportunities"]), 12)
        self.assertTrue(all(row["reason_codes"] for row in public["leads"]))
        self.assertTrue(all(row["risk_codes"] for row in paid_report["listings"]))
        self.assertTrue(all(row["commercial_blockers"] for row in portfolio["opportunities"]))
        self.assertEqual(public["verified_contract_count"], 0)
        self.assertEqual(paid_report["verified_paid_contract_count"], 0)
        self.assertEqual(portfolio["total"]["reported_payment"], "0.00")


if __name__ == "__main__":
    unittest.main()
