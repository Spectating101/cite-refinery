import json
import unittest
from pathlib import Path

from cite_refinery.problem_commons import ProblemStatus, Visibility
from cite_refinery.problem_intake import OwnerConfirmation, OwnerIntake


ROOT = Path(__file__).resolve().parents[1]
LIVE_INTAKE = ROOT / "pilot" / "intake" / "yzu-yongfeng-after-school.v0.1.json"


class ProblemOwnerIntakeTests(unittest.TestCase):
    def test_live_yzu_listing_converts_to_nonpublic_unconfirmed_candidate(self):
        intake = OwnerIntake.load(LIVE_INTAKE)
        report = intake.validation()
        self.assertTrue(report.valid)
        self.assertTrue(any("not been confirmed" in warning for warning in report.warnings))

        packet = intake.to_problem_packet(steward="pilot-curator")
        self.assertEqual(packet.status, ProblemStatus.CANDIDATE)
        self.assertEqual(packet.visibility, Visibility.RESTRICTED)
        self.assertEqual(packet.problem_owner, "")
        self.assertEqual(packet.evidence[0].confidence, "reported")
        self.assertTrue(all(item.status == "proposed_pending_owner_review" for item in packet.subproblems))
        self.assertTrue(any("not yet confirmed" in item for item in packet.disputes_uncertainty))
        self.assertFalse(packet.publishability().publishable)
        self.assertIn("reviewed_evidence", packet.publishability().missing)
        self.assertEqual(packet.authority_decisions, [])
        self.assertEqual(packet.attempts, [])
        self.assertEqual(packet.outcomes, [])

    def test_live_intake_preserves_geography_and_funding_uncertainty(self):
        intake = OwnerIntake.load(LIVE_INTAKE)
        packet = intake.to_problem_packet(steward="pilot-curator")
        self.assertTrue(any("heading says Zhongli" in item for item in packet.constraints))
        self.assertIn("No funding", packet.funding_notes)
        self.assertTrue(any("No funding" in item for item in intake.uncertainties))

    def test_confirmed_owner_requires_confirmation_receipt(self):
        raw = json.loads(LIVE_INTAKE.read_text(encoding="utf-8"))
        raw["owner_confirmation"] = OwnerConfirmation.CONFIRMED.value
        intake = OwnerIntake.from_dict(raw)
        report = intake.validation()
        self.assertFalse(report.valid)
        self.assertTrue(any("owner_confirmation_ref" in error for error in report.errors))
        self.assertTrue(any("owner_confirmed_at" in error for error in report.errors))

    def test_confirmed_owner_can_become_named_problem_owner_but_not_verified_problem(self):
        raw = json.loads(LIVE_INTAKE.read_text(encoding="utf-8"))
        raw["owner_confirmation"] = OwnerConfirmation.CONFIRMED.value
        raw["owner_confirmation_ref"] = "owner-review:example"
        raw["owner_confirmed_at"] = "2026-09-09T00:00:00+08:00"
        intake = OwnerIntake.from_dict(raw)
        self.assertTrue(intake.validation().valid)
        packet = intake.to_problem_packet(steward="pilot-curator")
        self.assertEqual(packet.problem_owner, raw["owner_org"])
        self.assertEqual(packet.status, ProblemStatus.CANDIDATE)
        self.assertFalse(packet.publishability().publishable)

    def test_child_facing_live_work_is_never_opened_by_intake_conversion(self):
        intake = OwnerIntake.load(LIVE_INTAKE)
        packet = intake.to_problem_packet(steward="pilot-curator")
        child_facing = [item for item in packet.subproblems if item.required_credentials]
        self.assertGreaterEqual(len(child_facing), 1)
        self.assertTrue(all(item.status != "open" for item in child_facing))
        self.assertIn("authorizes no direct service", packet.authority_boundary)


if __name__ == "__main__":
    unittest.main()
