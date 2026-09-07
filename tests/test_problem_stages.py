import tempfile
import unittest
from pathlib import Path

from cite_refinery.problem_stages import (
    AuthorityLevel,
    MethodMaturity,
    ProblemStage,
    StageProfile,
    StageRegistry,
    UncertaintyLevel,
    WorkMode,
)


class ProblemStageTests(unittest.TestCase):
    def profile(self, **overrides):
        raw = {
            "problem_id": "problem:test-001",
            "subproblem_id": "psub:measure",
            "stage": ProblemStage.MEASURE,
            "question": "How large and recurrent is the observed condition?",
            "epistemic_type": "empirical-estimation",
            "uncertainty": UncertaintyLevel.HIGH,
            "method_maturity": MethodMaturity.ADAPTABLE,
            "expected_outputs": ["frozen baseline"],
            "evaluation_method": "independent reproduction against frozen source data",
        }
        raw.update(overrides)
        return StageProfile(**raw)

    def test_nine_stage_order_is_complete(self):
        self.assertEqual(
            [stage.value for stage in ProblemStage],
            ["observe", "measure", "explain", "design", "build", "test", "deploy", "monitor", "generalize"],
        )

    def test_measure_high_uncertainty_is_empirical_inquiry(self):
        profile = self.profile()
        self.assertEqual(profile.work_mode, WorkMode.EMPIRICAL_INQUIRY)
        systems = [row["system"] for row in profile.route_plan()]
        self.assertIn("cite", systems)
        self.assertIn("refinery", systems)

    def test_established_build_is_known_or_adaptive_practice(self):
        profile = self.profile(
            subproblem_id="psub:build",
            stage=ProblemStage.BUILD,
            epistemic_type="engineering-implementation",
            uncertainty=UncertaintyLevel.LOW,
            method_maturity=MethodMaturity.ESTABLISHED,
            expected_outputs=["working implementation"],
            evaluation_method="integration test",
        )
        self.assertEqual(profile.work_mode, WorkMode.KNOWN_PRACTICE)
        self.assertEqual([row["system"] for row in profile.route_plan()], ["refinery"])

    def test_novel_frontier_work_is_research_frontier(self):
        profile = self.profile(
            stage=ProblemStage.EXPLAIN,
            epistemic_type="causal-mechanism-discovery",
            uncertainty=UncertaintyLevel.FRONTIER,
            method_maturity=MethodMaturity.NOVEL,
        )
        self.assertEqual(profile.work_mode, WorkMode.RESEARCH_FRONTIER)

    def test_deploy_requires_institutional_authority(self):
        profile = self.profile(
            subproblem_id="psub:deploy",
            stage=ProblemStage.DEPLOY,
            epistemic_type="operational-deployment",
            uncertainty=UncertaintyLevel.LOW,
            method_maturity=MethodMaturity.ESTABLISHED,
            authority_level=AuthorityLevel.NONE,
        )
        report = profile.validation()
        self.assertFalse(report.valid)
        self.assertTrue(any("institutional authority" in error for error in report.errors))

        authorized = self.profile(
            subproblem_id="psub:deploy",
            stage=ProblemStage.DEPLOY,
            epistemic_type="operational-deployment",
            uncertainty=UncertaintyLevel.LOW,
            method_maturity=MethodMaturity.ESTABLISHED,
            authority_level=AuthorityLevel.INSTITUTIONAL,
            authority_requirement="Participating municipal authority must explicitly authorize the bounded deployment.",
        )
        report = authorized.validation()
        self.assertTrue(report.valid)
        systems = [row["system"] for row in authorized.route_plan()]
        self.assertIn("external-authority", systems)
        self.assertIn("public-good", systems)

    def test_monitor_routes_back_to_nocturnal(self):
        profile = self.profile(
            subproblem_id="psub:monitor",
            stage=ProblemStage.MONITOR,
            epistemic_type="longitudinal-outcome-observation",
            uncertainty=UncertaintyLevel.MEDIUM,
            method_maturity=MethodMaturity.ESTABLISHED,
        )
        self.assertIn("nocturnal", [row["system"] for row in profile.route_plan()])

    def test_generalize_targets_refinery_and_compounding(self):
        profile = self.profile(
            subproblem_id="psub:generalize",
            stage=ProblemStage.GENERALIZE,
            epistemic_type="capability-generalization",
            uncertainty=UncertaintyLevel.MEDIUM,
            method_maturity=MethodMaturity.ADAPTABLE,
            reuse_target="portable baseline-measurement capability",
        )
        report = profile.validation()
        self.assertTrue(report.valid)
        self.assertIn("refinery", [row["system"] for row in profile.route_plan()])

    def test_authority_is_overlay_not_academic_rank(self):
        profile = self.profile(
            subproblem_id="psub:licensed",
            stage=ProblemStage.TEST,
            epistemic_type="professional-safety-review",
            uncertainty=UncertaintyLevel.MEDIUM,
            method_maturity=MethodMaturity.ESTABLISHED,
            authority_level=AuthorityLevel.QUALIFIED,
            authority_requirement="A licensed domain professional must sign off on the safety review.",
            required_credentials=["licensed professional"],
        )
        self.assertTrue(profile.requires_professional_authority)
        self.assertNotEqual(profile.work_mode.value, "research-frontier")

    def test_registry_roundtrip_and_coverage(self):
        registry = StageRegistry()
        registry.upsert(self.profile())
        registry.upsert(self.profile(
            subproblem_id="psub:build",
            stage=ProblemStage.BUILD,
            epistemic_type="engineering-implementation",
            uncertainty=UncertaintyLevel.LOW,
            method_maturity=MethodMaturity.ESTABLISHED,
            expected_outputs=["implementation"],
            evaluation_method="integration test",
        ))
        coverage = registry.coverage("problem:test-001")
        self.assertEqual(coverage["profiles"], 2)
        self.assertEqual(coverage["stage_counts"]["measure"], 1)
        self.assertEqual(coverage["stage_counts"]["build"], 1)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stages.json"
            registry.save(path)
            loaded = StageRegistry.load(path)
            self.assertEqual(len(loaded.profiles), 2)
            self.assertTrue(loaded.validate_all()["valid"])


if __name__ == "__main__":
    unittest.main()
