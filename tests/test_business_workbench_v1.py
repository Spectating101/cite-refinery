from __future__ import annotations

from contextlib import redirect_stdout
import copy
from datetime import date
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

from cite_refinery.business_workbench import (
    ROOT, SCHEMA, append_event, build_board, digest,
    money, new_ledger, render_board, validate_event,
    validate_ledger, validate_plan,
)
from cite_refinery.business_cli import main as business_cli, private_path

DEMO = ROOT / "examples/atlas_business_workbench_demo_v1.json"


def plan():
    return json.loads(DEMO.read_text(encoding="utf-8"))


def evt(kind, *, case_id="pv-independent-rooftop-performance-audit",
        event_id="event_000001", amount=None, action=None, currency=None):
    obj = {
        "event_id": event_id, "case_id": case_id, "on": "2026-10-23",
        "kind": kind, "note": "Synthetic operator record for a business workbench regression test.",
    }
    if amount is not None:
        obj.update({"amount": amount, "currency": currency or "TWD"})
    if action is not None:
        obj["action"] = action
    return obj


class AtlasBusinessWorkbenchTests(unittest.TestCase):
    def test_real_cases_join_to_existing_evidence_and_competition(self):
        board = build_board(plan())
        self.assertEqual(board["schema"], "cite_refinery.business_board.v1")
        self.assertEqual(len(board["opportunities"]), 4)
        self.assertEqual(board["total"]["validation_budget"], "4000.00")
        self.assertEqual(board["total"]["reported_cost"], "0.00")
        self.assertEqual(board["total"]["reported_payment"], "0.00")
        self.assertTrue(board["private_activity_not_exported"])
        for row in board["opportunities"]:
            self.assertEqual(row["state"], "research_validation_only")
            self.assertIn("buyer_and_budget_unverified", row["commercial_blockers"])
            self.assertIsNone(row["economics"]["independently_verified_revenue"])
            self.assertIsNone(row["economics"]["independently_verified_profit"])
        pv = next(r for r in board["opportunities"] if r["case_id"].startswith("pv-"))
        self.assertEqual(pv["competitive_alternatives"][0]["scope"], "direct")
        self.assertIn("Compare the existing substitutes", pv["next_test"])
        self.assertEqual(pv["economics"]["illustrative_unit_scenario"]["gross_contribution"], "9000")
        self.assertIn("not audited finance", render_board(board).lower())

    def test_reported_payment_never_upgrades_buyer_revenue_or_margin(self):
        p = plan()
        log = new_ledger(p)
        log = append_event(p, log, evt("payment_reported", amount="750.00"))
        row = next(r for r in build_board(p, log)["opportunities"] if r["case_id"].startswith("pv-"))
        self.assertEqual(row["economics"]["reported_payment_unreconciled"], "750.00")
        self.assertIsNone(row["economics"]["independently_verified_revenue"])
        self.assertIsNone(row["economics"]["independently_verified_profit"])
        self.assertEqual(row["buyer_stage"], "none")
        self.assertEqual(row["state"], "research_validation_only")
        self.assertEqual(row["activity_count"], 1)

    def test_budget_and_kill_conditions_prevent_promotion(self):
        p = plan()
        log = new_ledger(p)
        log = append_event(p, log, evt("cost_reported", amount="1100.00", event_id="cost_00001"))
        log = append_event(p, log, evt("cost_reported", amount="1050.00", event_id="cost_00002"))
        board = build_board(p, log)
        pv = next(r for r in board["opportunities"] if r["case_id"].startswith("pv-"))
        self.assertEqual(pv["state"], "stop_validation_budget")
        self.assertEqual(pv["economics"]["reported_cost_unreconciled"], "2150.00")
        self.assertEqual(pv["economics"]["validation_budget_remaining"], "0.00")
        self.assertEqual(board["total"]["reported_cost"], "2150.00")
        log = append_event(p, log, evt("decision", event_id="decision_kill01", action="kill"))
        pv = next(r for r in build_board(p, log)["opportunities"] if r["case_id"].startswith("pv-"))
        self.assertEqual(pv["state"], "kill_by_operator")
        self.assertIn("Stop new work", pv["next_test"])

    def test_unsupported_activity_never_forges_market_claim(self):
        p = plan()
        log = new_ledger(p)
        log = append_event(p, log, evt("buyer_response_reported", event_id="reply_00001"))
        log = append_event(p, log, evt("pilot_result_reported", event_id="pilot_00001"))
        log = append_event(p, log, evt("funding_lead", event_id="grant_00001"))
        pv = next(r for r in build_board(p, log)["opportunities"] if r["case_id"].startswith("pv-"))
        self.assertEqual(pv["reported_buyer_replies"], 1)
        self.assertEqual(pv["reported_pilot_results"], 1)
        self.assertEqual(pv["funding_lead_count_unverified"], 1)
        self.assertEqual(pv["buyer_stage"], "none")
        self.assertEqual(pv["conversion_readiness"], "evidence_lead_only")
        self.assertEqual(pv["economics"]["reported_payment_unreconciled"], "0.00")

    def test_case_and_event_schema_rejects_money_fictions(self):
        p = plan()
        for amount in ["NaN", "Infinity", "-2", "0.001", 1.234]:
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                append_event(p, new_ledger(p), evt("cost_reported", amount=amount))
        for bad in [
            evt("cost_reported", amount="100.00", currency="USD"),
            evt("payment_reported"),
            evt("funding_lead", amount="15000"),
            evt("buyer_contact_reported", action="kill"),
            evt("decision"),
            {**evt("buyer_contact_reported"), "field_not_allowed": "x"},
            {**evt("buyer_contact_reported"), "on": "2026-02-30"},
        ]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                append_event(p, new_ledger(p), bad)
        self.assertEqual(money("0.00", "test"), 0)

    def test_replay_chain_rejects_mutation_reorder_and_identity_collision(self):
        p = plan()
        log = append_event(p, new_ledger(p), evt("buyer_contact_reported", event_id="contact_00001"))
        log = append_event(p, log, evt("funding_lead", event_id="funding_00001"))
        self.assertIs(validate_ledger(p, log), log)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            append_event(p, log, evt("decision", event_id="contact_00001", action="hold"))
        tampered = copy.deepcopy(log)
        tampered["entries"][0]["event"]["note"] = "Falsified answer claims a signed deal."
        with self.assertRaisesRegex(ValueError, "hash chain mismatch"):
            validate_ledger(p, tampered)
        swapped = copy.deepcopy(log)
        swapped["entries"].reverse()
        with self.assertRaisesRegex(ValueError, "hash chain mismatch"):
            validate_ledger(p, swapped)
        wrong_plan = copy.deepcopy(p)
        wrong_plan["opportunities"][0]["validation_budget"] = "900.00"
        with self.assertRaisesRegex(ValueError, "pinned plan"):
            validate_ledger(wrong_plan, log)

    def test_plan_rejects_unreviewed_cases_and_bad_competitive_evidence(self):
        p = plan()
        p["opportunities"][1]["case_id"] = "unknown-phantom-project"
        with self.assertRaisesRegex(ValueError, "Unknown reviewed"):
            validate_plan(p)
        p = plan()
        p["opportunities"][1]["case_id"] = p["opportunities"][0]["case_id"]
        with self.assertRaisesRegex(ValueError, "repeated"):
            validate_plan(p)
        p = plan()
        p["opportunities"][2]["competitive_alternatives"] = [{
            "name": "Fake vendor", "url": "javascript:alert(1)", "scope": "direct",
        }]
        with self.assertRaisesRegex(ValueError, "competitor"):
            validate_plan(p)

    def test_private_cli_init_append_report_and_refuse_overwrite(self):
        p = plan()
        with tempfile.TemporaryDirectory() as d:
            ledger = Path(d) / "private-activity.json"
            ev = Path(d) / "event.json"
            ev.write_text(json.dumps(evt("buyer_contact_reported", event_id="contact_00001")))
            quiet = io.StringIO()
            with redirect_stdout(quiet):
                self.assertEqual(business_cli(["init", "--plan", str(DEMO),
                                               "--ledger", str(ledger)]), 0)
                self.assertEqual(business_cli(["record", "--plan", str(DEMO),
                                               "--ledger", str(ledger), "--event", str(ev)]), 0)
            self.assertEqual(stat.S_IMODE(ledger.stat().st_mode), 0o600)
            self.assertEqual(len(json.loads(ledger.read_text())["entries"]), 1)
            with self.assertRaises(FileExistsError):
                business_cli(["init", "--plan", str(DEMO), "--ledger", str(ledger)])
            with redirect_stdout(quiet):
                self.assertEqual(business_cli(["board", "--plan", str(DEMO),
                                               "--ledger", str(ledger)]), 0)
            self.assertIn("not audited finance", quiet.getvalue().lower())
            with self.assertRaisesRegex(ValueError, "public repository"):
                private_path(str(ROOT / "private_leads.json"))


if __name__ == "__main__":
    unittest.main()
