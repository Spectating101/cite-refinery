import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cite_refinery.case_operations import CaseOperations
from cite_refinery.pilot import PilotLedger
from cite_refinery.problem_case import ProblemCaseWorkspace
from cite_refinery.problem_commons import ProblemCommons, ProblemStatus, SuccessCriterion, Visibility, object_id
from cite_refinery.problem_governance import GovernanceRegistry
from cite_refinery.problem_stages import StageRegistry
from cite_refinery.solver_experiment import CONTROL_ARM, TREATMENT_ARM, build_experiment_pack


RUBRICS = {
    "schema": "problem-commons-rubrics/v0.1",
    "owner_agreement": {"items": ["x"], "scoring": "0/1"},
    "reviewer_quality": {"items": ["x"], "scoring": "0/1"},
    "solver_comprehension": {"items": ["a", "b", "c", "d", "e"], "scoring": "0/1"},
}


class SolverExperimentIntegrationTests(unittest.TestCase):
    def _workspace(self):
        commons = ProblemCommons()
        p = commons.create_problem(
            title="Experiment case",
            observed_condition="A real service transition repeatedly fails.",
            unresolved_core="Determine why before selecting an intervention.",
            steward="curator",
            problem_owner="owner",
        )
        p.transition(ProblemStatus.RESEARCHING, actor="curator", reason="curate")
        p.authority_boundary = "External owner authority required."
        p.affected_actors.append("users")
        p.constraints.append("privacy")
        p.knowledge_frontier.append("mechanism unknown")
        p.capability_frontier.append("measurement")
        p.add_evidence(source="log", locator="restricted:log", summary="Repeated failure exists.", confidence="reviewed", visibility=Visibility.RESTRICTED)
        p.success_criteria.append(SuccessCriterion(id=object_id("criterion"), metric="completion", target="improve", measurement="frozen log", falsification="no improvement"))
        sub = p.add_subproblem("Measure baseline", "Measure the transition.", "research", expected_outputs=["baseline"])
        p.transition(ProblemStatus.VERIFIED, actor="curator", reason="reviewed")
        p.transition(ProblemStatus.OPEN, actor="curator", reason="open")
        pilot = PilotLedger()
        workspace = ProblemCaseWorkspace(commons=commons, stages=StageRegistry(), governance=GovernanceRegistry(), pilot=pilot)
        ops = CaseOperations(commons=commons, stages=workspace.stages, governance=workspace.governance, pilot=pilot)
        return workspace, ops, p, sub

    def test_both_arms_ingest_into_same_solver_ledger_with_arm_preserved(self):
        workspace, ops, p, sub = self._workspace()
        for arm, participant, score in [(CONTROL_ARM, "control-1", [1, 0, 1, 1, 1]), (TREATMENT_ARM, "treatment-1", [1, 1, 1, 1, 1])]:
            pack = build_experiment_pack(workspace, p.id, participant_id=participant, forced_arm=arm, rubrics=RUBRICS)
            pack["response"]["item_scores"] = score
            pack["response"]["selected_subproblem_id"] = sub.id
            pack["response"]["minutes_to_useful_edge"] = 10 if arm == CONTROL_ARM else 6
            pack["response"]["serious_attempt"] = True
            ops.ingest_review_pack(pack, participant_id=participant)
        self.assertEqual([row.arm for row in ops.pilot.solvers], [CONTROL_ARM, TREATMENT_ARM])
        self.assertEqual(ops.pilot.solvers[0].comprehension_score, 0.8)
        self.assertEqual(ops.pilot.solvers[1].comprehension_score, 1.0)

    def test_cli_builds_both_arms_from_same_saved_case(self):
        workspace, _, p, _ = self._workspace()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commons = root / "commons.json"
            stages = root / "stages.json"
            governance = root / "governance.json"
            pilot = root / "pilot.json"
            workspace.commons.save(commons)
            workspace.stages.save(stages)
            workspace.governance.save(governance)
            workspace.pilot.save(pilot)
            rubrics = root / "rubrics.json"
            rubrics.write_text(json.dumps(RUBRICS), encoding="utf-8")

            common = [
                sys.executable, "-m", "cite_refinery.experiment_cli",
                "--commons", str(commons), "--stages", str(stages), "--governance", str(governance),
                "--pilot", str(pilot), "--rubrics", str(rubrics),
            ]
            control_path = root / "control.json"
            treatment_path = root / "treatment.json"
            subprocess.run(common + ["build", p.id, "--participant", "p1", "--force-arm", CONTROL_ARM, "--out", str(control_path)], check=True, capture_output=True, text=True)
            subprocess.run(common + ["build", p.id, "--participant", "p2", "--force-arm", TREATMENT_ARM, "--out", str(treatment_path)], check=True, capture_output=True, text=True)
            control = json.loads(control_path.read_text(encoding="utf-8"))
            treatment = json.loads(treatment_path.read_text(encoding="utf-8"))
            self.assertEqual(control["experiment"]["arm"], CONTROL_ARM)
            self.assertEqual(treatment["experiment"]["arm"], TREATMENT_ARM)
            self.assertEqual(control["problem"]["observed_condition"], treatment["problem"]["observed_condition"])
            self.assertEqual(control["stage_profiles"], [])
            self.assertEqual(control["governance"], [])


if __name__ == "__main__":
    unittest.main()
