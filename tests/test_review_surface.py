import json
from pathlib import Path
import shutil
import subprocess
import unittest

from cite_refinery.problem_case import ProblemCaseWorkspace
from cite_refinery.problem_commons import ProblemCommons, ProblemStatus, SuccessCriterion, Visibility, object_id
from cite_refinery.problem_governance import GovernanceRegistry
from cite_refinery.problem_stages import StageRegistry
from cite_refinery.pilot import PilotLedger
from cite_refinery.review_pack import build_review_pack


class ReviewSurfaceTests(unittest.TestCase):
    def test_review_js_parses_when_node_is_available(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed")
        subprocess.run([node, "--check", "prototype/review.js"], check=True)

    def test_review_html_loads_review_js(self):
        html = Path("prototype/review.html").read_text(encoding="utf-8")
        self.assertIn('script src="review.js"', html)
        self.assertIn('id="packFile"', html)
        self.assertIn('id="rubricItems"', html)
        self.assertIn('id="selectedSubproblem"', html)

    def test_solver_pack_contains_operational_response_fields(self):
        commons = ProblemCommons()
        p = commons.create_problem(
            title="Example",
            observed_condition="A condition exists.",
            unresolved_core="The mechanism remains unknown.",
            steward="curator",
        )
        p.transition(ProblemStatus.RESEARCHING, actor="curator", reason="curate")
        p.authority_boundary = "External authority only."
        p.add_evidence(source="source", locator="restricted:source", summary="Observed.", confidence="reviewed", visibility=Visibility.RESTRICTED)
        p.success_criteria.append(SuccessCriterion(id=object_id("criterion"), metric="x", target="improve", measurement="measure x", falsification="no improvement"))
        p.add_subproblem("Measure", "Measure the condition.", "research")
        workspace = ProblemCaseWorkspace(commons=commons, stages=StageRegistry(), governance=GovernanceRegistry(), pilot=PilotLedger())
        rubrics = {
            "schema": "problem-commons-rubrics/v0.1",
            "owner_agreement": {"items": ["x"], "scoring": "0/1"},
            "reviewer_quality": {"items": ["x"], "scoring": "0/1"},
            "solver_comprehension": {"items": ["x"], "scoring": "0/1"},
        }
        pack = build_review_pack(workspace, p.id, audience="solver", rubrics=rubrics)
        response = pack["response"]
        for key in [
            "selected_subproblem_id",
            "minutes_to_useful_edge",
            "usefulness_rating",
            "serious_attempt",
            "abandoned",
            "abandonment_reason",
            "observer_notes",
            "arm",
        ]:
            self.assertIn(key, response)
        self.assertIsNone(pack["problem"]["evidence"][0]["locator"])
        self.assertEqual(pack["problem"]["evidence"][0]["provenance"], {})


if __name__ == "__main__":
    unittest.main()
