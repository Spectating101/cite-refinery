import copy
import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.contribution_handoff import ContributorWorkspace, ParticipationBasis
from cite_refinery.contribution_review import (
    ContributionReview,
    ContributionVerdict,
    project_review_into_commons,
    validate_submission_snapshot,
)
from cite_refinery.contribution_review_cli import main as review_main
from cite_refinery.problem_commons import ProblemCommons, ProblemPacket, ProblemStatus, Subproblem, Visibility


class ContributionReviewTests(unittest.TestCase):
    def brief(self):
        problem_id = "problem:review-test"
        subproblem_id = "sub:review-test"
        return {
            "id": f"project:{problem_id}:{subproblem_id}",
            "problem_id": problem_id,
            "subproblem_id": subproblem_id,
            "title": "Analyze a bounded data-quality question",
            "problem_title": "Synthetic review test",
            "description": "Produce a reproducible analysis and preserve limitations.",
            "stage": "measure",
            "work_mode": "empirical-inquiry",
            "effort": "4-8 hours",
            "skill_tags": ["python"],
            "required_credentials": [],
            "expected_outputs": ["reproducible analysis"],
            "authority_requirement": "review only; no deployment authority",
            "compensation_mode": "volunteer",
            "volunteer_compatible": True,
            "funding_status": "not-required",
            "funding_readiness": "not-required",
            "currency": "TWD",
            "minimum_amount": None,
            "target_amount": None,
            "committed_amount": 0.0,
            "funding_gap": None,
            "eligible_instruments": [],
            "in_kind_needs": [],
            "expense_categories": [],
            "funding_restrictions": [],
            "implementation_budget_owner": "",
            "maintenance_budget_owner": "",
            "warnings": [],
        }

    def submitted(self):
        workspace = ContributorWorkspace.from_project_brief(
            self.brief(), contributor_ref="contributor:alice", workspace_id="contribution:test-001"
        )
        workspace.activate(basis=ParticipationBasis.VOLUNTEER)
        workspace.set_work(
            method_scope="Run a reproducible descriptive check against the frozen sample.",
            produced_outputs=["analysis notebook"],
            blockers=["no external exposure denominator"],
        )
        workspace.add_artifact(
            title="Analysis notebook", kind="notebook", locator="artifact://analysis.ipynb",
            sha256_value="sha256:" + "a" * 64, artifact_id="artifact:test-001",
        )
        submission = workspace.submit()
        return workspace, submission

    def commons(self, *, status=ProblemStatus.OPEN):
        commons = ProblemCommons()
        packet = ProblemPacket(
            id="problem:review-test",
            title="Synthetic review test",
            observed_condition="A bounded data-quality question remains unresolved.",
            unresolved_core="Determine what the data support without overstating the result.",
            steward="curator:test",
            status=status,
            visibility=Visibility.PUBLIC if status == ProblemStatus.OPEN else Visibility.RESTRICTED,
            subproblems=[Subproblem(
                id="sub:review-test", title="Analyze a bounded data-quality question",
                description="Produce a reproducible analysis and preserve limitations.", kind="analysis",
            )],
        )
        commons.problems[packet.id] = packet
        return commons, packet

    def review(self, submission, verdict="accept", **kwargs):
        defaults = {
            "reviewer_ref": "reviewer:bob",
            "summary": "The submission is internally consistent for the stated scope.",
            "strengths": ["reproducible artifact"],
            "limitations": ["does not establish causal effect"],
            "revision_requirements": ["clarify denominator"] if verdict == "revise" else [],
        }
        defaults.update(kwargs)
        return ContributionReview.from_submission(submission, verdict=verdict, **defaults)

    def test_accept_projects_one_canonical_attempt_without_outcome_or_authority(self):
        workspace, submission = self.submitted()
        review = self.review(submission, "accept")
        commons, packet = self.commons()
        receipt = project_review_into_commons(commons, workspace, submission, review)
        self.assertTrue(receipt["changed"])
        self.assertEqual(receipt["attempt_status"], "accepted")
        self.assertEqual(len(packet.attempts), 1)
        self.assertEqual(packet.attempts[0].id, "pattempt:test-001")
        self.assertEqual(packet.attempts[0].status.value, "accepted")
        self.assertEqual(packet.attempts[0].artifact_refs, ["artifact://analysis.ipynb"])
        self.assertEqual(len(packet.attempt_reviews), 1)
        self.assertEqual(packet.attempt_reviews[0].id, "pareview:test-001")
        self.assertEqual(packet.status, ProblemStatus.OPEN)
        self.assertEqual(packet.outcomes, [])
        self.assertEqual(packet.authority_decisions, [])

    def test_revise_returns_canonical_attempt_to_active(self):
        workspace, submission = self.submitted()
        review = self.review(submission, "revise")
        commons, packet = self.commons()
        receipt = project_review_into_commons(commons, workspace, submission, review)
        self.assertEqual(receipt["attempt_status"], "active")
        self.assertEqual(packet.attempts[0].status.value, "active")
        self.assertIn("revision-required", receipt["next_action"])

    def test_reject_preserves_rejected_attempt(self):
        workspace, submission = self.submitted()
        review = self.review(submission, "reject")
        commons, packet = self.commons()
        receipt = project_review_into_commons(commons, workspace, submission, review)
        self.assertEqual(receipt["attempt_status"], "rejected")
        self.assertEqual(packet.attempts[0].status.value, "rejected")
        self.assertEqual(packet.outcomes, [])

    def test_identical_projection_is_idempotent(self):
        workspace, submission = self.submitted()
        review = self.review(submission, "accept")
        commons, packet = self.commons()
        first = project_review_into_commons(commons, workspace, submission, review)
        second = project_review_into_commons(commons, workspace, submission, review)
        self.assertTrue(first["changed"])
        self.assertFalse(second["changed"])
        self.assertEqual(len(packet.attempts), 1)
        self.assertEqual(len(packet.attempt_reviews), 1)

    def test_conflicting_replay_is_rejected(self):
        workspace, submission = self.submitted()
        commons, packet = self.commons()
        project_review_into_commons(commons, workspace, submission, self.review(submission, "accept"))
        conflicting = self.review(submission, "reject")
        with self.assertRaisesRegex(ValueError, "different review"):
            project_review_into_commons(commons, workspace, submission, conflicting)
        self.assertEqual(len(packet.attempts), 1)
        self.assertEqual(len(packet.attempt_reviews), 1)

    def test_same_verdict_with_different_review_content_is_not_treated_as_idempotent(self):
        workspace, submission = self.submitted()
        first_review = self.review(submission, "accept", review_id="contribreview:first")
        commons, packet = self.commons()
        project_review_into_commons(commons, workspace, submission, first_review)
        changed_review = self.review(
            submission,
            "accept",
            review_id="contribreview:second",
            summary="A materially different review narrative for the same submission.",
        )
        with self.assertRaisesRegex(ValueError, "different review"):
            project_review_into_commons(commons, workspace, submission, changed_review)
        self.assertEqual(len(packet.attempts), 1)
        self.assertEqual(len(packet.attempt_reviews), 1)

    def test_tampered_submission_is_rejected_before_projection(self):
        workspace, submission = self.submitted()
        tampered = copy.deepcopy(submission)
        tampered["produced_outputs"] = ["different claim"]
        commons, packet = self.commons()
        self.assertTrue(validate_submission_snapshot(tampered, workspace=workspace))
        review = self.review(submission, "accept")
        with self.assertRaisesRegex(ValueError, "submission/workspace validation failed"):
            project_review_into_commons(commons, workspace, tampered, review)
        self.assertEqual(packet.attempts, [])

    def test_reviewer_cannot_equal_contributor(self):
        _, submission = self.submitted()
        review = self.review(submission, "accept", reviewer_ref="contributor:alice")
        report = review.validation(submission)
        self.assertFalse(report.valid)
        self.assertTrue(any("differ from contributor_ref" in item for item in report.errors))

    def test_revise_requires_actionable_revision_requirement(self):
        _, submission = self.submitted()
        review = self.review(submission, "revise", revision_requirements=[])
        report = review.validation(submission)
        self.assertFalse(report.valid)
        self.assertTrue(any("revision requirement" in item for item in report.errors))

    def test_projection_requires_problem_attempt_lifecycle_to_be_open(self):
        workspace, submission = self.submitted()
        review = self.review(submission, "accept")
        commons, packet = self.commons(status=ProblemStatus.RESEARCHING)
        with self.assertRaisesRegex(ValueError, "attempts require"):
            project_review_into_commons(commons, workspace, submission, review)
        self.assertEqual(packet.attempts, [])
        self.assertEqual(packet.attempt_reviews, [])

    def test_cli_create_validate_and_project_round_trip(self):
        workspace, submission = self.submitted()
        commons, _ = self.commons()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            workspace_path = root / "workspace.json"
            submission_path = root / "submission.json"
            review_path = root / "review.json"
            state_path = root / "commons.json"
            receipt_path = root / "projection.json"
            workspace.dump(workspace_path)
            submission_path.write_text(json.dumps(submission, indent=2) + "\n", encoding="utf-8")
            commons.save(state_path)

            self.assertEqual(review_main([
                "create", str(submission_path), "--workspace", str(workspace_path),
                "--reviewer-ref", "reviewer:bob", "--verdict", "accept",
                "--summary", "Bounded analysis is acceptable for its stated scope.",
                "--limitation", "No causal conclusion.", "--out", str(review_path),
            ]), 0)
            self.assertEqual(review_main([
                "validate", str(review_path), "--submission", str(submission_path),
                "--workspace", str(workspace_path),
            ]), 0)
            self.assertEqual(review_main([
                "project", str(review_path), "--submission", str(submission_path),
                "--workspace", str(workspace_path), "--state", str(state_path),
                "--receipt-out", str(receipt_path),
            ]), 0)

            loaded = ProblemCommons.load(state_path)
            packet = loaded.get("problem:review-test")
            self.assertEqual(len(packet.attempts), 1)
            self.assertEqual(packet.attempts[0].status.value, "accepted")
            self.assertEqual(packet.outcomes, [])
            self.assertTrue(receipt_path.exists())
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["attempt_status"], "accepted")
            self.assertIn("review_hash", receipt)

    def test_existing_receipt_blocks_projection_before_state_mutation(self):
        workspace, submission = self.submitted()
        review = self.review(submission, "accept")
        commons, _ = self.commons()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            workspace_path = root / "workspace.json"
            submission_path = root / "submission.json"
            review_path = root / "review.json"
            state_path = root / "commons.json"
            receipt_path = root / "projection.json"
            workspace.dump(workspace_path)
            submission_path.write_text(json.dumps(submission, indent=2) + "\n", encoding="utf-8")
            review_path.write_text(json.dumps(review.to_dict(), indent=2) + "\n", encoding="utf-8")
            commons.save(state_path)
            receipt_path.write_text("do not overwrite\n", encoding="utf-8")

            self.assertEqual(review_main([
                "project", str(review_path), "--submission", str(submission_path),
                "--workspace", str(workspace_path), "--state", str(state_path),
                "--receipt-out", str(receipt_path),
            ]), 2)

            loaded = ProblemCommons.load(state_path)
            packet = loaded.get("problem:review-test")
            self.assertEqual(packet.attempts, [])
            self.assertEqual(packet.attempt_reviews, [])
            self.assertEqual(receipt_path.read_text(encoding="utf-8"), "do not overwrite\n")


if __name__ == "__main__":
    unittest.main()
