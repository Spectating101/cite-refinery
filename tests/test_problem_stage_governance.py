import unittest

from cite_refinery.problem_governance import GateKind, GateStatus, InterventionEnvelope, Reversibility
from cite_refinery.problem_stage_governance import align_stage_and_governance
from cite_refinery.problem_stages import AuthorityLevel, MethodMaturity, ProblemStage, StageProfile, UncertaintyLevel


class StageGovernanceAlignmentTests(unittest.TestCase):
    def envelope(self) -> InterventionEnvelope:
        item = InterventionEnvelope(
            problem_id="problem:x",
            subproblem_id="s1",
            title="Bounded reversible intervention",
            target_transition="a -> b",
            diagnosis_hypothesis="friction causes some failures",
            intervention_class="support",
            smallest_feasible_change="show bounded guidance",
            expected_mechanism="reduce avoidable friction",
            reversibility=Reversibility.REVERSIBLE,
            rollback_plan="disable guidance",
            evidence_refs=["e1"],
            outcome_metrics=["completion", "error"],
            monitoring_plan="monitor completion, error, and guardrails",
        )
        for kind in (GateKind.EVIDENCE, GateKind.SAFETY, GateKind.INTEGRITY, GateKind.RIGHTS, GateKind.DATA_ACCESS, GateKind.REVERSIBILITY):
            item.set_gate(kind, GateStatus.SATISFIED, requirement=kind.value, reviewer="r")
        return item

    def profile(self, stage: ProblemStage, authority: AuthorityLevel = AuthorityLevel.NONE, routes=None) -> StageProfile:
        return StageProfile(
            problem_id="problem:x",
            subproblem_id="s1",
            stage=stage,
            question="What should happen?",
            epistemic_type="test",
            uncertainty=UncertaintyLevel.MEDIUM,
            method_maturity=MethodMaturity.ADAPTABLE,
            expected_outputs=["artifact"],
            evaluation_method="independent review",
            authority_level=authority,
            authority_requirement="required" if authority != AuthorityLevel.NONE else "",
            system_routes=routes or [],
        )

    def test_build_can_align_without_external_authority(self):
        report = align_stage_and_governance(self.profile(ProblemStage.BUILD), self.envelope())
        self.assertTrue(report.valid)

    def test_qualified_design_requires_professional_gate(self):
        profile = self.profile(ProblemStage.DESIGN, AuthorityLevel.QUALIFIED)
        envelope = self.envelope()
        report = align_stage_and_governance(profile, envelope)
        self.assertFalse(report.valid)
        self.assertIn("qualified stage requires a satisfied professional governance gate", report.errors)
        envelope.set_gate(GateKind.PROFESSIONAL, GateStatus.SATISFIED, requirement="licensed review", reviewer="professional")
        self.assertTrue(align_stage_and_governance(profile, envelope).valid)

    def test_test_stage_requires_test_ready_governance(self):
        profile = self.profile(ProblemStage.TEST)
        envelope = self.envelope()
        envelope.set_gate(GateKind.RIGHTS, GateStatus.PENDING)
        report = align_stage_and_governance(profile, envelope)
        self.assertFalse(report.valid)
        self.assertTrue(any("rights gate pending" in x for x in report.errors))

    def test_deploy_stage_requires_both_institutional_stage_authority_and_deploy_ready_envelope(self):
        envelope = self.envelope()
        profile = self.profile(ProblemStage.DEPLOY, AuthorityLevel.REVIEW)
        report = align_stage_and_governance(profile, envelope)
        self.assertFalse(report.valid)
        self.assertIn("deploy stage requires institutional stage authority", report.errors)

        profile = self.profile(ProblemStage.DEPLOY, AuthorityLevel.INSTITUTIONAL)
        envelope.mark_test_ready()
        envelope.record_test(evaluator="reviewer", scope="shadow", passed=True, summary="pass")
        envelope.authorize_handoff(authority_actor="institution", authority_scope="bounded pilot", decision="authorized", receipt_ref="public:auth")
        report = align_stage_and_governance(profile, envelope)
        self.assertTrue(report.valid)


if __name__ == "__main__":
    unittest.main()
