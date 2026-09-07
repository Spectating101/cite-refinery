import tempfile
import unittest
from pathlib import Path

from cite_refinery.problem_governance import (
    EnvelopeState,
    GateKind,
    GateStatus,
    GovernanceRegistry,
    InterventionEnvelope,
    Reversibility,
)


class ProblemGovernanceTests(unittest.TestCase):
    def make_envelope(self) -> InterventionEnvelope:
        envelope = InterventionEnvelope(
            problem_id="problem:service-1",
            subproblem_id="design-1",
            title="Reversible support intervention",
            target_transition="request -> completed submission",
            diagnosis_hypothesis="Some failures are avoidable information friction.",
            intervention_class="information support",
            smallest_feasible_change="Provide bounded guidance without deciding eligibility.",
            expected_mechanism="Clearer guidance reduces avoidable incomplete submissions.",
            reversibility=Reversibility.REVERSIBLE,
            rollback_plan="Disable support and restore existing workflow.",
            evidence_refs=["evidence:1"],
            outcome_metrics=["completion rate", "incorrect submission rate"],
            monitoring_plan="Monitor completion, errors, burden, and guardrails.",
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
        return envelope

    def test_test_readiness_requires_non_authority_hard_gates(self):
        envelope = self.make_envelope()
        self.assertTrue(envelope.readiness("test").ready)
        envelope.set_gate(GateKind.RIGHTS, GateStatus.PENDING)
        readiness = envelope.readiness("test")
        self.assertFalse(readiness.ready)
        self.assertIn("rights gate pending", readiness.blockers)

    def test_professional_gate_is_separate_and_blocking_when_present(self):
        envelope = self.make_envelope()
        envelope.set_gate(GateKind.PROFESSIONAL, GateStatus.PENDING, requirement="licensed reviewer required")
        self.assertFalse(envelope.readiness("test").ready)
        envelope.set_gate(GateKind.PROFESSIONAL, GateStatus.SATISFIED, requirement="licensed reviewer required", reviewer="licensed-professional")
        self.assertTrue(envelope.readiness("test").ready)

    def test_deploy_requires_passed_test_and_external_authority(self):
        envelope = self.make_envelope()
        envelope.mark_test_ready()
        envelope.record_test(evaluator="independent-reviewer", scope="shadow", passed=True, summary="No guardrail breach.", evidence_refs=["test:evidence:1"])
        readiness = envelope.readiness("deploy")
        self.assertFalse(readiness.ready)
        self.assertTrue(any("authority" in item for item in readiness.blockers))

        envelope.authorize_handoff(authority_actor="service-operator", authority_scope="bounded reversible pilot", decision="authorized", receipt_ref="public:auth:1")
        self.assertTrue(envelope.readiness("deploy").ready)
        envelope.mark_deploy_ready()
        envelope.mark_handed_off()
        self.assertEqual(envelope.state, EnvelopeState.HANDED_OFF)

    def test_guardrail_breach_prevents_deploy_readiness(self):
        envelope = self.make_envelope()
        envelope.mark_test_ready()
        envelope.record_test(evaluator="reviewer", scope="shadow", passed=True, summary="Metric improved but guardrail breached.", guardrail_breaches=["due-process path hidden"])
        envelope.authorize_handoff(authority_actor="operator", authority_scope="pilot", decision="authorized", receipt_ref="public:auth:2")
        readiness = envelope.readiness("deploy")
        self.assertFalse(readiness.ready)
        self.assertIn("no passed test receipt without guardrail breach", readiness.blockers)

    def test_denied_authority_blocks_handoff(self):
        envelope = self.make_envelope()
        envelope.mark_test_ready()
        envelope.record_test(evaluator="reviewer", scope="shadow", passed=True, summary="Pass")
        envelope.authorize_handoff(authority_actor="operator", authority_scope="pilot", decision="denied", receipt_ref="public:deny:1")
        readiness = envelope.readiness("deploy")
        self.assertFalse(readiness.ready)
        self.assertIn("authority gate failed", readiness.blockers)

    def test_irreversible_intervention_warns_and_still_needs_explicit_gates(self):
        envelope = self.make_envelope()
        envelope.reversibility = Reversibility.IRREVERSIBLE
        envelope.rollback_plan = ""
        readiness = envelope.readiness("test")
        self.assertTrue(readiness.ready)
        self.assertTrue(any("irreversible" in warning for warning in readiness.warnings))

    def test_roundtrip_registry(self):
        registry = GovernanceRegistry()
        envelope = self.make_envelope()
        registry.add(envelope)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "governance.json"
            registry.save(path)
            loaded = GovernanceRegistry.load(path)
            copy = loaded.get(envelope.id)
            self.assertEqual(copy.public_good_ref, "public-good:case:1")
            self.assertEqual(copy.gate(GateKind.SAFETY).status, GateStatus.SATISFIED)


if __name__ == "__main__":
    unittest.main()
