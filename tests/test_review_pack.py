import unittest

from cite_refinery.problem_case import ProblemCaseWorkspace
from cite_refinery.problem_commons import ProblemCommons, Visibility
from cite_refinery.problem_governance import GateKind, GateStatus, GovernanceRegistry, InterventionEnvelope, Reversibility
from cite_refinery.problem_stages import MethodMaturity, ProblemStage, StageProfile, StageRegistry, UncertaintyLevel
from cite_refinery.review_pack import build_review_pack


RUBRICS = {
    "schema": "problem-commons-rubrics/v0.1",
    "owner_agreement": {"items": ["owner item"], "scoring": "0/1"},
    "reviewer_quality": {"items": ["review item"], "scoring": "0/1"},
    "solver_comprehension": {"items": ["solver item"], "scoring": "0/1"},
}


class ReviewPackTests(unittest.TestCase):
    def setUp(self) -> None:
        commons = ProblemCommons()
        problem = commons.create_problem(
            title="Restricted-source problem",
            observed_condition="A reviewed restricted source reports a recurrent failure.",
            unresolved_core="Determine the binding mechanism.",
            steward="curator",
        )
        problem.add_evidence(
            source="partner",
            locator="restricted:secret-location",
            summary="Recurrent failure observed.",
            confidence="reviewed",
            visibility=Visibility.RESTRICTED,
            provenance={"private_key": "must-not-leak"},
        )
        sub = problem.add_subproblem("Measure", "Freeze a baseline.", "research")

        stages = StageRegistry()
        stages.upsert(StageProfile(
            problem_id=problem.id,
            subproblem_id=sub.id,
            stage=ProblemStage.MEASURE,
            question="How frequent is the failure?",
            epistemic_type="measurement",
            uncertainty=UncertaintyLevel.HIGH,
            method_maturity=MethodMaturity.ADAPTABLE,
            expected_outputs=["baseline"],
            evaluation_method="independent review",
            notes="internal stage note",
            system_routes=["cite", "refinery"],
        ))

        governance = GovernanceRegistry()
        envelope = InterventionEnvelope(
            problem_id=problem.id,
            subproblem_id=sub.id,
            title="Shadow support",
            target_transition="failure -> recovery",
            diagnosis_hypothesis="coordination may be the bottleneck",
            intervention_class="decision support",
            smallest_feasible_change="offline shadow recommendation",
            expected_mechanism="reduce coordination delay",
            reversibility=Reversibility.REVERSIBLE,
            rollback_plan="stop shadow output",
            evidence_refs=["restricted:evidence:1"],
            outcome_metrics=["failure rate"],
            monitoring_plan="compare frozen windows",
        )
        envelope.set_gate(
            GateKind.EVIDENCE,
            GateStatus.SATISFIED,
            requirement="reviewed evidence",
            evidence_refs=["restricted:evidence:2"],
            reviewer="private reviewer identity",
        )
        governance.add(envelope)

        self.problem = problem
        self.workspace = ProblemCaseWorkspace(commons=commons, stages=stages, governance=governance)

    def test_solver_pack_redacts_restricted_locators_and_governance_receipts(self):
        pack = build_review_pack(self.workspace, self.problem.id, audience="solver", rubrics=RUBRICS)
        evidence = pack["problem"]["evidence"][0]
        self.assertIsNone(evidence["locator"])
        self.assertEqual(evidence["provenance"], {})
        self.assertTrue(evidence["redacted"])

        stage = pack["stage_profiles"][0]
        self.assertNotIn("notes", stage)
        self.assertNotIn("system_routes", stage)

        gate = pack["governance"][0]["gates"][0]
        self.assertNotIn("evidence_refs", gate)
        self.assertNotIn("reviewer", gate)
        self.assertEqual(pack["rubric"]["name"], "solver_comprehension")
        self.assertEqual(pack["response"]["item_scores"], [None])

    def test_audience_selects_matching_rubric(self):
        owner = build_review_pack(self.workspace, self.problem.id, audience="owner", rubrics=RUBRICS)
        reviewer = build_review_pack(self.workspace, self.problem.id, audience="reviewer", rubrics=RUBRICS)
        self.assertEqual(owner["rubric"]["name"], "owner_agreement")
        self.assertEqual(reviewer["rubric"]["name"], "reviewer_quality")

    def test_invalid_rubric_schema_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported rubric schema"):
            build_review_pack(self.workspace, self.problem.id, audience="solver", rubrics={"schema": "wrong"})


if __name__ == "__main__":
    unittest.main()
