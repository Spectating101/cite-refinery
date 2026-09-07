import unittest

from cite_refinery.case_operations import CaseOperations
from cite_refinery.pilot import PilotLedger
from cite_refinery.problem_case import ProblemCaseWorkspace
from cite_refinery.problem_commons import ProblemCommons, ProblemStatus, SuccessCriterion, Visibility, object_id
from cite_refinery.problem_governance import GovernanceRegistry
from cite_refinery.problem_stages import StageRegistry
from cite_refinery.review_pack import build_review_pack


RUBRICS = {
    "schema": "problem-commons-rubrics/v0.1",
    "owner_agreement": {"items": ["a", "b", "c", "d", "e"], "scoring": "0/1"},
    "reviewer_quality": {"items": ["a", "b", "c", "d", "e"], "scoring": "0/1"},
    "solver_comprehension": {"items": ["a", "b", "c", "d", "e"], "scoring": "0/1"},
}

POLICY = {
    "schema": "problem-operations-policy/v0.1",
    "require_owner_for_verification": True,
    "require_reviewer_for_verification": True,
    "owner_agreement_min": 0.8,
    "reviewer_score_min": 0.8,
    "solver_comprehension_min": 0.8,
}


class CaseOperationsTests(unittest.TestCase):
    def setUp(self) -> None:
        commons = ProblemCommons()
        self.problem = commons.create_problem(
            title="Operational access failure",
            observed_condition="A verified service pathway repeatedly fails before completion.",
            unresolved_core="Determine which transition is failing and why.",
            steward="curator",
            domain="public-good",
            problem_owner="partner",
        )
        self.problem.transition(ProblemStatus.RESEARCHING, actor="curator", reason="begin curation")
        self.problem.authority_boundary = "Only the partner institution may authorize consequential action."
        self.problem.affected_actors.append("service users")
        self.problem.constraints.append("minimum necessary data")
        self.problem.knowledge_frontier.append("The binding failure mechanism remains uncertain.")
        self.problem.capability_frontier.append("transition measurement")
        self.problem.implementation_pathway.append("shadow evaluation before any field change")
        self.problem.add_evidence(
            source="partner aggregate log",
            locator="restricted:partner-log",
            summary="Repeated transition failure is present in reviewed aggregate records.",
            confidence="reviewed",
            visibility=Visibility.RESTRICTED,
        )
        self.problem.success_criteria.append(
            SuccessCriterion(
                id=object_id("criterion"),
                metric="verified transition completion",
                target="improve relative to frozen baseline",
                measurement="partner-confirmed event log",
                falsification="no improvement or guardrail worsening",
                baseline="frozen pre-intervention period",
                guardrails=["no autonomous denial"],
            )
        )
        self.subproblem = self.problem.add_subproblem(
            "Establish the transition baseline",
            "Measure the failing transition without prescribing a solution.",
            "research",
            skill_tags=["statistics"],
            expected_outputs=["frozen baseline"],
        )
        self.ops = CaseOperations(
            commons=commons,
            stages=StageRegistry(),
            governance=GovernanceRegistry(),
            pilot=PilotLedger(),
        )
        self.workspace = ProblemCaseWorkspace(
            commons=commons,
            stages=self.ops.stages,
            governance=self.ops.governance,
            pilot=self.ops.pilot,
        )

    def _pack(self, audience: str, scores: list[int]):
        pack = build_review_pack(self.workspace, self.problem.id, audience=audience, rubrics=RUBRICS)
        pack["response"]["item_scores"] = scores
        return pack

    def test_reviews_gate_explicit_verification_and_open(self):
        self.ops.start_production(self.problem.id, actor="curator", curator_minutes=75, source_count=3)
        before = self.ops.assess(self.problem.id, policy=POLICY)
        self.assertFalse(before.eligible_for_verification)
        self.assertTrue(any("owner review" in item for item in before.blockers))

        owner = self._pack("owner", [1, 1, 1, 1, 1])
        reviewer = self._pack("reviewer", [1, 1, 1, 1, 0])
        self.ops.ingest_review_pack(owner, participant_id="owner-1")
        self.ops.ingest_review_pack(reviewer, participant_id="reviewer-1")

        ready = self.ops.assess(self.problem.id, policy=POLICY)
        self.assertTrue(ready.eligible_for_verification)
        self.assertEqual(self.problem.status, ProblemStatus.RESEARCHING)
        self.assertEqual(self.problem.authority_decisions, [])

        receipt = self.ops.promote(
            self.problem.id, target="verified", actor="curator", reason="owner and domain review passed pilot gates", policy=POLICY,
        )
        self.assertEqual(self.problem.status, ProblemStatus.VERIFIED)
        self.assertTrue(receipt.problem_sha256)
        self.assertTrue(receipt.pilot_sha256)
        self.assertEqual(self.problem.authority_decisions, [])

        open_assessment = self.ops.assess(self.problem.id, policy=POLICY)
        self.assertTrue(open_assessment.eligible_for_open)
        self.ops.promote(self.problem.id, target="open", actor="curator", reason="bounded contribution path ready", policy=POLICY)
        self.assertEqual(self.problem.status, ProblemStatus.OPEN)
        self.assertEqual(self.problem.authority_decisions, [])

    def test_low_owner_agreement_blocks_verification(self):
        self.ops.start_production(self.problem.id, actor="curator", curator_minutes=50)
        self.ops.ingest_review_pack(self._pack("owner", [1, 0, 0, 0, 0]), participant_id="owner-1")
        self.ops.ingest_review_pack(self._pack("reviewer", [1, 1, 1, 1, 1]), participant_id="reviewer-1")
        assessment = self.ops.assess(self.problem.id, policy=POLICY)
        self.assertFalse(assessment.eligible_for_verification)
        self.assertTrue(any("owner agreement below" in item for item in assessment.blockers))
        with self.assertRaises(ValueError):
            self.ops.promote(self.problem.id, target="verified", actor="curator", reason="should fail", policy=POLICY)

    def test_incomplete_review_is_rejected(self):
        self.ops.start_production(self.problem.id, actor="curator", curator_minutes=30)
        pack = build_review_pack(self.workspace, self.problem.id, audience="owner", rubrics=RUBRICS)
        pack["response"]["item_scores"] = [1, 1, None, 1, 1]
        with self.assertRaises(ValueError):
            self.ops.ingest_review_pack(pack, participant_id="owner-1")

    def test_reviewer_errors_and_reframe_are_measured(self):
        production = self.ops.start_production(self.problem.id, actor="curator", curator_minutes=45)
        pack = self._pack("reviewer", [1, 1, 1, 1, 1])
        pack["response"]["material_errors"] = ["Wrong time scope", "Missing operational constraint"]
        pack["response"]["reframe_required"] = True
        self.ops.ingest_review_pack(pack, participant_id="reviewer-1")
        self.assertEqual(production.correction_count, 2)
        self.assertEqual(production.reframing_count, 1)
        self.assertIn("Wrong time scope", production.notes)

    def test_solver_review_records_conversion_without_mutating_lifecycle(self):
        self.ops.start_production(self.problem.id, actor="curator", curator_minutes=60)
        self.ops.ingest_review_pack(self._pack("owner", [1, 1, 1, 1, 1]), participant_id="owner-1")
        self.ops.ingest_review_pack(self._pack("reviewer", [1, 1, 1, 1, 1]), participant_id="reviewer-1")
        self.ops.promote(self.problem.id, target="verified", actor="curator", reason="reviewed", policy=POLICY)
        self.ops.promote(self.problem.id, target="open", actor="curator", reason="open for solver test", policy=POLICY)

        pack = self._pack("solver", [1, 1, 1, 1, 1])
        pack["response"]["selected_subproblem_id"] = self.subproblem.id
        pack["response"]["minutes_to_useful_edge"] = 7.5
        pack["response"]["usefulness_rating"] = 0.9
        pack["response"]["serious_attempt"] = True
        result = self.ops.ingest_review_pack(pack, participant_id="solver-1")

        self.assertEqual(result.score, 1.0)
        self.assertEqual(len(self.ops.pilot.solvers), 1)
        solver = self.ops.pilot.solvers[0]
        self.assertTrue(solver.serious_attempt)
        self.assertEqual(solver.selected_subproblem_id, self.subproblem.id)
        self.assertEqual(self.problem.status, ProblemStatus.OPEN)
        assessment = self.ops.assess(self.problem.id, policy=POLICY)
        self.assertEqual(assessment.phase, "active_problem")
        self.assertEqual(assessment.serious_attempt_rate, 1.0)

    def test_serious_solver_attempt_requires_known_subproblem(self):
        self.ops.start_production(self.problem.id, actor="curator", curator_minutes=60)
        pack = self._pack("solver", [1, 1, 1, 1, 1])
        pack["response"]["selected_subproblem_id"] = "psub:missing"
        pack["response"]["serious_attempt"] = True
        with self.assertRaises(ValueError):
            self.ops.ingest_review_pack(pack, participant_id="solver-1")


if __name__ == "__main__":
    unittest.main()
