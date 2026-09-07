import tempfile
import unittest
from pathlib import Path

from cite_refinery.pilot import PilotLedger


class PilotLedgerTests(unittest.TestCase):
    def test_report_separates_problem_production_solver_adoption_and_reuse(self) -> None:
        ledger = PilotLedger()
        ledger.record_production(
            problem_id="problem:1",
            curator_minutes=90,
            source_count=4,
            correction_count=1,
            owner_agreement=0.9,
            reviewer_score=0.8,
            publishable=True,
        )
        ledger.record_solver(
            problem_id="problem:1",
            participant_id="participant:a",
            comprehension_score=0.8,
            minutes_to_useful_edge=7,
            coaching_minutes=0,
            selected_subproblem_id="psub:1",
            serious_attempt=True,
        )
        ledger.record_adoption(
            problem_id="problem:1",
            attempt_id="attempt:1",
            accepted_for_review=True,
            accepted_for_pilot=True,
            pilot_authorized=True,
            deployed=True,
            maintenance_owner_identified=True,
            outcome_observed=True,
        )
        ledger.record_reuse(
            source_problem_id="problem:1",
            target_problem_id="problem:2",
            asset_type="capability",
            asset_ref="rcap:1",
            search_minutes=10,
            adaptation_minutes=20,
            estimated_rebuild_minutes=100,
        )
        report = ledger.report()
        self.assertEqual(report.problem_records, 1)
        self.assertEqual(report.serious_attempt_rate, 1.0)
        self.assertEqual(report.deployment_rate, 1.0)
        self.assertEqual(report.total_net_reuse_minutes_saved, 70)

    def test_failed_reuse_counts_search_and_adaptation_as_negative_cost(self) -> None:
        ledger = PilotLedger()
        record = ledger.record_reuse(
            source_problem_id="problem:1",
            target_problem_id="problem:2",
            asset_type="method",
            asset_ref="method:1",
            search_minutes=15,
            adaptation_minutes=25,
            estimated_rebuild_minutes=90,
            successful=False,
        )
        self.assertEqual(record.net_minutes_saved, -40)
        self.assertEqual(ledger.report().total_net_reuse_minutes_saved, -40)

    def test_adoption_cannot_claim_deployment_without_authority(self) -> None:
        ledger = PilotLedger()
        with self.assertRaisesRegex(ValueError, "pilot_authorized"):
            ledger.record_adoption(problem_id="problem:1", attempt_id="attempt:1", deployed=True)

    def test_outcome_requires_deployment(self) -> None:
        ledger = PilotLedger()
        with self.assertRaisesRegex(ValueError, "deployed"):
            ledger.record_adoption(
                problem_id="problem:1",
                attempt_id="attempt:1",
                pilot_authorized=True,
                outcome_observed=True,
            )

    def test_pilot_ledger_round_trip(self) -> None:
        ledger = PilotLedger()
        ledger.record_production(problem_id="problem:1", curator_minutes=45, publishable=False, blocker_codes=["owner_missing"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pilot.json"
            ledger.save(path)
            loaded = PilotLedger.load(path)
        self.assertEqual(len(loaded.production), 1)
        self.assertEqual(loaded.production[0].blocker_codes, ["owner_missing"])

    def test_fraction_metrics_are_bounded(self) -> None:
        ledger = PilotLedger()
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            ledger.record_solver(problem_id="problem:1", participant_id="p", comprehension_score=1.2)


if __name__ == "__main__":
    unittest.main()
