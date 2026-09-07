import unittest

from cite_refinery.pilot import PilotLedger
from cite_refinery.problem_case import ProblemCaseWorkspace
from cite_refinery.problem_commons import ProblemCommons, ProblemStatus, SuccessCriterion, Visibility, object_id
from cite_refinery.problem_governance import GovernanceRegistry
from cite_refinery.problem_stages import AuthorityLevel, MethodMaturity, ProblemStage, StageProfile, StageRegistry, UncertaintyLevel
from cite_refinery.solver_experiment import CONTROL_ARM, TREATMENT_ARM, assign_arm, build_experiment_pack, summarize_experiment


RUBRICS = {
    "schema": "problem-commons-rubrics/v0.1",
    "owner_agreement": {"items": ["x"], "scoring": "0/1"},
    "reviewer_quality": {"items": ["x"], "scoring": "0/1"},
    "solver_comprehension": {
        "items": [
            "observed condition",
            "uncertainty",
            "contribution",
            "useful output",
            "constraint",
        ],
        "scoring": "0/1",
    },
}


class SolverExperimentTests(unittest.TestCase):
    def setUp(self) -> None:
        commons = ProblemCommons()
        p = commons.create_problem(
            title="Recurring service access failure",
            observed_condition="Users repeatedly fail a documented service transition.",
            unresolved_core="Determine the binding failure mechanism before selecting an intervention.",
            steward="curator",
            domain="public-good",
            geography="Taiwan",
            problem_owner="partner",
        )
        p.transition(ProblemStatus.RESEARCHING, actor="curator", reason="curate")
        p.summary = "Externally grounded access problem."
        p.authority_boundary = "Only the service operator may authorize a real process change."
        p.affected_actors.append("service users")
        p.constraints.extend(["privacy", "preserve appeal path"])
        p.disputes_uncertainty.append("The dominant failure mechanism is not established.")
        p.knowledge_frontier.append("Transition-level cause evidence remains incomplete.")
        p.capability_frontier.append("funnel measurement")
        p.add_evidence(source="aggregate log", locator="restricted:log", summary="Repeated drop-off is present.", confidence="reviewed", visibility=Visibility.RESTRICTED)
        p.success_criteria.append(SuccessCriterion(id=object_id("criterion"), metric="completion", target="improve", measurement="frozen event log", falsification="no improvement"))
        sub = p.add_subproblem("Establish cause baseline", "Measure and classify competing failure causes.", "research", expected_outputs=["baseline", "cause taxonomy"])
        p.transition(ProblemStatus.VERIFIED, actor="curator", reason="reviewed")
        p.transition(ProblemStatus.OPEN, actor="curator", reason="open")

        stages = StageRegistry()
        stages.upsert(StageProfile(
            problem_id=p.id,
            subproblem_id=sub.id,
            stage=ProblemStage.MEASURE,
            question="What is the representative transition-failure rate and cause distribution?",
            epistemic_type="empirical-estimation",
            uncertainty=UncertaintyLevel.HIGH,
            method_maturity=MethodMaturity.ADAPTABLE,
            expected_outputs=["baseline", "cause taxonomy"],
            evaluation_method="independent reproduction",
            authority_level=AuthorityLevel.NONE,
            reuse_target="transition measurement protocol",
        ))
        self.problem = p
        self.workspace = ProblemCaseWorkspace(commons=commons, stages=stages, governance=GovernanceRegistry(), pilot=PilotLedger())

    def test_assignment_counterbalances_repeated_exposure(self):
        first = assign_arm(self.problem.id, "participant-1", sequence_index=0)
        second = assign_arm(self.problem.id, "participant-1", sequence_index=1)
        third = assign_arm(self.problem.id, "participant-1", sequence_index=2)
        self.assertIn(first.arm, {CONTROL_ARM, TREATMENT_ARM})
        self.assertNotEqual(first.arm, second.arm)
        self.assertEqual(first.arm, third.arm)

    def test_control_and_treatment_share_core_facts_but_not_commons_enrichment(self):
        control = build_experiment_pack(self.workspace, self.problem.id, participant_id="p1", forced_arm=CONTROL_ARM, rubrics=RUBRICS)
        treatment = build_experiment_pack(self.workspace, self.problem.id, participant_id="p1", forced_arm=TREATMENT_ARM, rubrics=RUBRICS)

        for field in ["id", "title", "observed_condition", "unresolved_core", "authority_boundary"]:
            self.assertEqual(control["problem"][field], treatment["problem"][field])
        self.assertEqual(control["problem"]["success_criteria"], treatment["problem"]["success_criteria"])
        self.assertEqual(control["response"]["arm"], CONTROL_ARM)
        self.assertEqual(treatment["response"]["arm"], TREATMENT_ARM)
        self.assertEqual(control["stage_profiles"], [])
        self.assertTrue(treatment["stage_profiles"])
        self.assertEqual(control["problem"]["disputes_uncertainty"], [])
        self.assertTrue(treatment["problem"]["disputes_uncertainty"])
        self.assertIsNone(treatment["problem"]["evidence"][0]["locator"])

    def test_report_uses_same_solver_ledger_and_reports_directional_differences(self):
        ledger = PilotLedger()
        pid = self.problem.id
        for index in range(5):
            ledger.record_solver(problem_id=pid, participant_id=f"c{index}", arm=CONTROL_ARM, comprehension_score=0.6, minutes_to_useful_edge=12, usefulness_rating=0.6, serious_attempt=index < 2, coaching_minutes=3)
            ledger.record_solver(problem_id=pid, participant_id=f"t{index}", arm=TREATMENT_ARM, comprehension_score=0.9, minutes_to_useful_edge=7, usefulness_rating=0.85, serious_attempt=index < 4, coaching_minutes=1)
        report = summarize_experiment(ledger.solvers, problem_id=pid)
        self.assertEqual(report["arms"][CONTROL_ARM]["sessions"], 5)
        self.assertEqual(report["arms"][TREATMENT_ARM]["sessions"], 5)
        self.assertAlmostEqual(report["difference_treatment_minus_control"]["comprehension"], 0.3)
        self.assertAlmostEqual(report["difference_treatment_minus_control"]["minutes_to_useful_edge"], -5.0)
        self.assertAlmostEqual(report["difference_treatment_minus_control"]["serious_attempt_rate"], 0.4)
        self.assertEqual(report["warnings"], [])

    def test_small_samples_are_labeled_exploratory(self):
        ledger = PilotLedger()
        ledger.record_solver(problem_id=self.problem.id, participant_id="one", arm=CONTROL_ARM, comprehension_score=1)
        ledger.record_solver(problem_id=self.problem.id, participant_id="two", arm=TREATMENT_ARM, comprehension_score=1)
        report = summarize_experiment(ledger.solvers, problem_id=self.problem.id)
        self.assertTrue(any("exploratory" in item for item in report["warnings"]))


if __name__ == "__main__":
    unittest.main()
