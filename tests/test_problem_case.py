import unittest

from cite_refinery.pilot import PilotLedger
from cite_refinery.problem_case import ProblemCaseWorkspace
from cite_refinery.problem_commons import ProblemCommons, ProblemStatus, SuccessCriterion, Visibility
from cite_refinery.problem_governance import (
    GateKind,
    GateStatus,
    GovernanceRegistry,
    InterventionEnvelope,
    Reversibility,
)
from cite_refinery.problem_stages import (
    AuthorityLevel,
    MethodMaturity,
    ProblemStage,
    StageProfile,
    StageRegistry,
    UncertaintyLevel,
)


class ProblemCaseWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.commons = ProblemCommons()
        self.stages = StageRegistry()
        self.governance = GovernanceRegistry()
        self.pilot = PilotLedger()
        self.problem = self.commons.create_problem(
            title="Recurring access interruption",
            observed_condition="Operators report repeated access interruptions.",
            unresolved_core="Determine the binding mechanism and test the smallest reversible response.",
            steward="curator",
            domain="public-good",
            problem_owner="operator",
        )
        self.problem.authority_boundary = "External operator retains consequential authority."
        self.problem.affected_actors = ["operators", "beneficiaries"]
        self.problem.constraints = ["rights", "safety", "reversibility"]
        self.problem.knowledge_frontier = ["Mechanism remains uncertain."]
        self.problem.capability_frontier = ["measurement", "routing"]
        self.problem.implementation_pathway = ["shadow test", "operator review", "bounded pilot"]
        self.problem.add_evidence(
            source="operator record",
            locator="restricted:record",
            summary="Repeated interruptions observed.",
            confidence="reviewed",
            visibility=Visibility.RESTRICTED,
        )
        self.problem.success_criteria.append(
            SuccessCriterion(
                id="criterion:1",
                metric="interruption rate",
                target="lower than baseline",
                measurement="frozen operator log",
                falsification="no reduction or guardrail harm",
            )
        )
        self.sub = self.problem.add_subproblem(
            "Bounded intervention",
            "Test a reversible intervention against the verified bottleneck.",
            "validation",
            expected_outputs=["test receipt"],
        )
        self.problem.transition(ProblemStatus.RESEARCHING, actor="curator", reason="curate")
        self.problem.transition(ProblemStatus.VERIFIED, actor="reviewer", reason="verified")
        self.problem.transition(ProblemStatus.OPEN, actor="reviewer", reason="open")

    def workspace(self) -> ProblemCaseWorkspace:
        return ProblemCaseWorkspace(
            commons=self.commons,
            stages=self.stages,
            governance=self.governance,
            pilot=self.pilot,
        )

    def stage(self, stage: ProblemStage, authority: AuthorityLevel = AuthorityLevel.NONE) -> StageProfile:
        profile = StageProfile(
            problem_id=self.problem.id,
            subproblem_id=self.sub.id,
            stage=stage,
            question="Can the bounded intervention improve the verified transition?",
            epistemic_type="bounded-intervention",
            uncertainty=UncertaintyLevel.MEDIUM,
            method_maturity=MethodMaturity.ADAPTABLE,
            expected_outputs=["test receipt"],
            evaluation_method="frozen shadow test",
            authority_level=authority,
            authority_requirement="Operator authorization required." if authority != AuthorityLevel.NONE else "",
        )
        self.stages.upsert(profile)
        return profile

    def envelope(self) -> InterventionEnvelope:
        envelope = InterventionEnvelope(
            problem_id=self.problem.id,
            subproblem_id=self.sub.id,
            title="Bounded reversible response",
            target_transition="interruption -> restored access",
            diagnosis_hypothesis="access coordination is the binding constraint",
            intervention_class="operator-reviewed coordination support",
            smallest_feasible_change="shadow recommendation only",
            expected_mechanism="reduce coordination delay",
            reversibility=Reversibility.REVERSIBLE,
            rollback_plan="stop recommendations and revert to existing workflow",
            evidence_refs=["pevidence:1"],
            outcome_metrics=["interruption rate"],
            monitoring_plan="compare frozen baseline and post-test operator logs",
            public_good_ref="public-good:case:1",
        )
        for kind in (
            GateKind.EVIDENCE,
            GateKind.SAFETY,
            GateKind.INTEGRITY,
            GateKind.RIGHTS,
            GateKind.DATA_ACCESS,
            GateKind.REVERSIBILITY,
        ):
            envelope.set_gate(kind, GateStatus.SATISFIED, requirement=f"{kind.value} reviewed", reviewer="reviewer")
        self.governance.add(envelope)
        return envelope

    def test_snapshot_surfaces_missing_stage_and_solver(self):
        snapshot = self.workspace().snapshot(self.problem.id)
        self.assertEqual(snapshot.stage_coverage_rate, 0.0)
        self.assertTrue(any("classify remaining contribution paths" in x for x in snapshot.next_actions))
        self.assertTrue(any("independent solver" in x for x in snapshot.next_actions))

    def test_deploy_stage_without_governance_is_invalid(self):
        self.stage(ProblemStage.DEPLOY, AuthorityLevel.INSTITUTIONAL)
        report = self.workspace().validate(self.problem.id)
        self.assertFalse(report.valid)
        self.assertTrue(any("requires a governance envelope" in x for x in report.errors))

    def test_unknown_stage_subproblem_is_invalid(self):
        self.stages.upsert(
            StageProfile(
                problem_id=self.problem.id,
                subproblem_id="missing",
                stage=ProblemStage.MEASURE,
                question="What is happening?",
                epistemic_type="measurement",
                uncertainty=UncertaintyLevel.HIGH,
                method_maturity=MethodMaturity.ADAPTABLE,
                expected_outputs=["baseline"],
                evaluation_method="independent review",
            )
        )
        report = self.workspace().validate(self.problem.id)
        self.assertFalse(report.valid)
        self.assertTrue(any("unknown subproblem" in x for x in report.errors))

    def test_complete_joined_case_records_outcome_and_reuse(self):
        self.stage(ProblemStage.DEPLOY, AuthorityLevel.INSTITUTIONAL)
        envelope = self.envelope()
        envelope.record_test(
            evaluator="independent reviewer",
            scope="shadow test",
            passed=True,
            summary="Pre-specified test passed without guardrail breach.",
            evidence_refs=["test:1"],
        )
        envelope.authorize_handoff(
            authority_actor="operator",
            authority_scope="bounded reversible pilot",
            decision="authorized",
            receipt_ref="authority:1",
        )
        envelope.mark_deploy_ready()

        attempt = self.problem.start_attempt(
            title="Run bounded response",
            contributor="solver",
            subproblem_ids=[self.sub.id],
        )
        self.problem.update_attempt_status(attempt.id, "submitted")
        self.problem.review_attempt(attempt.id, reviewer="reviewer", verdict="accept")
        self.problem.transition(ProblemStatus.PILOTING, actor="reviewer", reason="accepted attempt")
        self.problem.authorize(actor="operator", scope="bounded reversible pilot", decision="authorized", receipt_ref="authority:1")
        self.problem.transition(ProblemStatus.DEPLOYED, actor="operator", reason="authorized deployment")
        self.problem.transition(ProblemStatus.MONITORING, actor="operator", reason="observe outcome")
        self.problem.record_outcome(
            summary="Interruption rate decreased during the observed window.",
            observed_change="lower interruption rate",
            evidence_refs=["outcome:1"],
            attribution="not_established",
        )
        self.pilot.record_reuse(
            source_problem_id=self.problem.id,
            target_problem_id="problem:later-case",
            asset_type="protocol",
            asset_ref="refinery:protocol:1",
            search_minutes=10,
            adaptation_minutes=20,
            estimated_rebuild_minutes=90,
        )

        workspace = self.workspace()
        report = workspace.validate(self.problem.id)
        snapshot = workspace.snapshot(self.problem.id)
        bundle = workspace.bundle(self.problem.id)

        self.assertTrue(report.valid)
        self.assertTrue(snapshot.milestones["test_recorded"])
        self.assertTrue(snapshot.milestones["authority_recorded"])
        self.assertTrue(snapshot.milestones["deployed"])
        self.assertTrue(snapshot.milestones["outcome_observed"])
        self.assertTrue(snapshot.milestones["reuse_observed"])
        self.assertEqual(snapshot.outbound_reuse, 1)
        self.assertEqual(bundle["schema"], "problem-case/v0.1")
        self.assertEqual(bundle["pilot"]["reuse_outbound"][0]["net_minutes_saved"], 60)


if __name__ == "__main__":
    unittest.main()
