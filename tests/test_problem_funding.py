import tempfile
import unittest
from pathlib import Path

from cite_refinery.problem_commons import ProblemPacket, Subproblem
from cite_refinery.problem_funding import (
    CompensationMode,
    FundingNeed,
    FundingReadiness,
    FundingRegistry,
    FundingStatus,
    build_project_brief,
)
from cite_refinery.problem_stages import (
    AuthorityLevel,
    MethodMaturity,
    ProblemStage,
    StageProfile,
    UncertaintyLevel,
)


class ProblemFundingTests(unittest.TestCase):
    def need(self, **overrides):
        raw = {
            "problem_id": "problem:test-001",
            "subproblem_id": "sub:measure",
            "stage": ProblemStage.MEASURE,
            "status": FundingStatus.SEEKING,
            "compensation_mode": CompensationMode.STIPEND,
            "volunteer_compatible": False,
            "currency": "TWD",
            "minimum_amount": 30000,
            "target_amount": 80000,
            "committed_amount": 0,
            "eligible_instruments": ["microgrant", "research grant"],
            "in_kind_needs": ["field equipment"],
            "expense_categories": ["field labor", "travel"],
        }
        raw.update(overrides)
        return FundingNeed(**raw)

    def packet(self):
        return ProblemPacket(
            id="problem:test-001",
            title="Investigate a real problem",
            observed_condition="A recurring condition is observed.",
            unresolved_core="Determine what is driving the recurrence.",
            steward="pilot curator",
            subproblems=[
                Subproblem(
                    id="sub:measure",
                    title="Measure recurrence",
                    description="Build a defensible baseline before intervention claims.",
                    kind="research",
                    effort="1-2 weeks",
                    skill_tags=["statistics", "data-engineering"],
                    expected_outputs=["validated baseline"],
                )
            ],
        )

    def stage(self):
        return StageProfile(
            problem_id="problem:test-001",
            subproblem_id="sub:measure",
            stage=ProblemStage.MEASURE,
            question="How large and recurrent is the condition?",
            epistemic_type="empirical-estimation",
            uncertainty=UncertaintyLevel.HIGH,
            method_maturity=MethodMaturity.ADAPTABLE,
            expected_outputs=["validated baseline"],
            evaluation_method="independent reproduction",
            authority_level=AuthorityLevel.NONE,
        )

    def test_unfunded_nonvolunteer_work_is_blocked(self):
        need = self.need()
        self.assertEqual(need.readiness, FundingReadiness.BLOCKED)
        self.assertEqual(need.funding_gap, 80000)
        self.assertEqual(need.minimum_gap, 30000)

    def test_minimum_commitment_can_make_work_ready(self):
        need = self.need(status=FundingStatus.PARTIAL, committed_amount=30000)
        self.assertEqual(need.readiness, FundingReadiness.READY)
        self.assertEqual(need.funding_gap, 50000)

    def test_partial_commitment_below_minimum_is_partial(self):
        need = self.need(status=FundingStatus.PARTIAL, committed_amount=10000)
        self.assertEqual(need.readiness, FundingReadiness.PARTIAL)
        self.assertEqual(need.minimum_gap, 20000)

    def test_unknown_plan_never_implies_free_labor(self):
        brief = build_project_brief(self.packet(), "sub:measure", stage_profile=self.stage())
        self.assertFalse(brief.volunteer_compatible)
        self.assertEqual(brief.funding_readiness, FundingReadiness.UNKNOWN.value)
        self.assertTrue(any("do not assume" in warning for warning in brief.warnings))

    def test_project_brief_combines_work_and_funding(self):
        need = self.need(status=FundingStatus.PARTIAL, committed_amount=10000)
        brief = build_project_brief(
            self.packet(),
            "sub:measure",
            stage_profile=self.stage(),
            funding_need=need,
        )
        self.assertEqual(brief.stage, "measure")
        self.assertEqual(brief.work_mode, "empirical-inquiry")
        self.assertEqual(brief.compensation_mode, "stipend")
        self.assertEqual(brief.funding_readiness, "partial")
        self.assertEqual(brief.funding_gap, 70000)
        self.assertIn("microgrant", brief.eligible_instruments)
        self.assertEqual(brief.expected_outputs, ["validated baseline"])

    def test_conflicting_volunteer_contract_is_invalid(self):
        need = self.need(compensation_mode=CompensationMode.VOLUNTEER, volunteer_compatible=False)
        report = need.validation()
        self.assertFalse(report.valid)
        self.assertTrue(any("conflicts" in error for error in report.errors))

    def test_deployment_warns_without_budget_owner(self):
        need = self.need(
            stage=ProblemStage.DEPLOY,
            status=FundingStatus.SEEKING,
            compensation_mode=CompensationMode.PAID_PROJECT,
            minimum_amount=100000,
            target_amount=500000,
        )
        report = need.validation()
        self.assertTrue(report.valid)
        self.assertTrue(any("implementation budget owner" in warning for warning in report.warnings))

    def test_registry_roundtrip_and_coverage(self):
        registry = FundingRegistry()
        registry.upsert(self.need())
        registry.upsert(self.need(
            subproblem_id="sub:build",
            stage=ProblemStage.BUILD,
            status=FundingStatus.PARTIAL,
            compensation_mode=CompensationMode.PAID_PROJECT,
            minimum_amount=50000,
            target_amount=120000,
            committed_amount=50000,
        ))
        coverage = registry.coverage("problem:test-001")
        self.assertEqual(coverage["plans"], 2)
        self.assertEqual(coverage["known_target_total"], 200000)
        self.assertEqual(coverage["committed_total"], 50000)
        self.assertEqual(coverage["readiness"]["blocked"], 1)
        self.assertEqual(coverage["readiness"]["ready"], 1)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "funding.json"
            registry.dump(path)
            loaded = FundingRegistry.load(path)
            self.assertEqual(len(loaded.needs), 2)
            self.assertEqual(loaded.get("problem:test-001", "sub:measure").target_amount, 80000)


if __name__ == "__main__":
    unittest.main()
