import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.contribution_cli import main as contribution_main
from cite_refinery.contribution_handoff import (
    ContributorWorkspace,
    ContributionState,
    ParticipationBasis,
    canonical_hash,
)


def brief(**overrides):
    raw = {
        "id": "project:problem:demo:sub:one",
        "problem_id": "problem:demo",
        "subproblem_id": "sub:one",
        "title": "Validate a bounded data transformation",
        "problem_title": "Demo problem",
        "description": "Produce a reproducible transformation and document the result.",
        "stage": "build",
        "work_mode": "adaptive-practice",
        "effort": "8-12 hours",
        "skill_tags": ["python"],
        "required_credentials": [],
        "expected_outputs": ["reproducible script", "validation note"],
        "authority_requirement": "review",
        "compensation_mode": "paid-project",
        "volunteer_compatible": False,
        "funding_status": "funded",
        "funding_readiness": "ready",
        "currency": "TWD",
        "minimum_amount": 3000,
        "target_amount": 5000,
        "committed_amount": 5000,
        "funding_gap": 0,
        "eligible_instruments": [],
        "in_kind_needs": [],
        "expense_categories": ["labor"],
        "funding_restrictions": [],
        "implementation_budget_owner": "demo owner",
        "maintenance_budget_owner": "",
        "warnings": [],
    }
    raw.update(overrides)
    return raw


class ContributorWorkspaceTests(unittest.TestCase):
    def test_workspace_binds_exact_project_brief(self):
        source = brief()
        workspace = ContributorWorkspace.from_project_brief(source, contributor_ref="private:solver-1", workspace_id="contribution:demo")
        self.assertEqual(workspace.project_brief_hash, canonical_hash(source))
        self.assertEqual(workspace.state, ContributionState.DRAFT)
        self.assertTrue(workspace.validation().valid)
        workspace.project_brief["description"] = "tampered"
        report = workspace.validation()
        self.assertFalse(report.valid)
        self.assertTrue(any("issued brief hash" in item for item in report.errors))

    def test_active_work_requires_explicit_valid_participation_basis(self):
        workspace = ContributorWorkspace.from_project_brief(brief(), contributor_ref="private:solver-1")
        with self.assertRaises(ValueError):
            workspace.activate(basis=ParticipationBasis.VOLUNTEER)
        self.assertEqual(workspace.state, ContributionState.DRAFT)
        workspace.activate(basis=ParticipationBasis.COMPENSATED)
        self.assertEqual(workspace.state, ContributionState.ACTIVE)

    def test_compensated_work_is_blocked_when_funding_is_not_ready(self):
        workspace = ContributorWorkspace.from_project_brief(
            brief(funding_status="seeking", funding_readiness="blocked", committed_amount=0, funding_gap=5000),
            contributor_ref="private:solver-1",
        )
        with self.assertRaises(ValueError):
            workspace.activate(basis="compensated")

    def test_academic_credit_requires_explicit_arrangement_note(self):
        workspace = ContributorWorkspace.from_project_brief(brief(), contributor_ref="private:solver-1")
        with self.assertRaises(ValueError):
            workspace.activate(basis="academic-credit")
        workspace.activate(basis="academic-credit", participation_note="Approved independent-study credit path; curator must retain the external approval reference separately.")
        self.assertEqual(workspace.participation_basis, ParticipationBasis.ACADEMIC_CREDIT)

    def test_submission_requires_method_output_and_material_artifact(self):
        workspace = ContributorWorkspace.from_project_brief(brief(), contributor_ref="private:solver-1")
        workspace.activate(basis="compensated")
        with self.assertRaises(ValueError):
            workspace.submit()
        workspace.set_work(method_scope="Run the frozen transformation on the supplied fixture and compare row counts.", produced_outputs=["Transformation script completed"])
        with self.assertRaises(ValueError):
            workspace.submit()
        workspace.add_artifact(title="transform.py", kind="code", locator="private-artifact:transform.py")
        submission = workspace.submit()
        self.assertEqual(workspace.state, ContributionState.SUBMITTED)
        self.assertEqual(submission["schema"], "problem-contribution-submission/v0.1")
        self.assertIn("independent review", submission["claims_boundary"])
        self.assertNotIn("accepted", submission)
        self.assertNotIn("outcome", submission)
        self.assertNotIn("authority", submission)

    def test_submitted_workspace_is_immutable(self):
        workspace = ContributorWorkspace.from_project_brief(brief(), contributor_ref="private:solver-1")
        workspace.activate(basis="compensated")
        workspace.set_work(method_scope="Method", produced_outputs=["Output"])
        workspace.add_artifact(title="result.txt", kind="analysis", locator="private:result")
        workspace.submit()
        with self.assertRaises(ValueError):
            workspace.set_work(notes="change after submission")
        with self.assertRaises(ValueError):
            workspace.add_artifact(title="late.txt", kind="analysis", locator="private:late")

    def test_valid_sha256_is_preserved_and_invalid_digest_rejected(self):
        workspace = ContributorWorkspace.from_project_brief(brief(), contributor_ref="private:solver-1")
        digest = "sha256:" + "a" * 64
        artifact = workspace.add_artifact(title="artifact", kind="data", locator="private:data", sha256_value=digest)
        self.assertEqual(artifact.sha256, digest)
        with self.assertRaises(ValueError):
            workspace.add_artifact(title="bad", kind="data", locator="private:bad", sha256_value="sha256:xyz")

    def test_cli_round_trip_creates_workspace_and_submission(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            brief_path = root / "brief.json"
            workspace_path = root / "workspace.json"
            artifact_path = root / "result.txt"
            submission_path = root / "submission.json"
            brief_path.write_text(json.dumps(brief()), encoding="utf-8")
            artifact_path.write_text("material result", encoding="utf-8")

            self.assertEqual(contribution_main(["init", str(brief_path), "--contributor-ref", "private:solver-1", "--out", str(workspace_path)]), 0)
            self.assertEqual(contribution_main(["activate", str(workspace_path), "--basis", "compensated"]), 0)
            self.assertEqual(contribution_main(["set-work", str(workspace_path), "--method-scope", "Execute and verify the fixture", "--produced-output", "Verified result"]), 0)
            self.assertEqual(contribution_main(["artifact-add", str(workspace_path), "--title", "result.txt", "--kind", "analysis", "--file", str(artifact_path)]), 0)
            self.assertEqual(contribution_main(["validate", str(workspace_path), "--submittable"]), 0)
            self.assertEqual(contribution_main(["submit", str(workspace_path), "--submission-out", str(submission_path)]), 0)

            workspace = json.loads(workspace_path.read_text(encoding="utf-8"))
            submission = json.loads(submission_path.read_text(encoding="utf-8"))
            self.assertEqual(workspace["state"], "submitted")
            self.assertTrue(workspace["artifacts"][0]["sha256"].startswith("sha256:"))
            self.assertEqual(submission["workspace_id"], workspace["id"])
            self.assertEqual(submission["project_brief_hash"], workspace["project_brief_hash"])


if __name__ == "__main__":
    unittest.main()
