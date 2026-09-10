import copy
import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.contribution_handoff import ContributorWorkspace, ParticipationBasis, canonical_hash
from cite_refinery.contribution_revision import ContributionRevisionWorkspace, validate_revision_submission
from cite_refinery.contribution_revision_cli import main as revision_main
from cite_refinery.contribution_review import (
    ContributionReview,
    project_review_into_commons,
    project_revision_review_into_commons,
)
from cite_refinery.contribution_review_cli import main as review_main
from cite_refinery.problem_commons import ProblemCommons, ProblemPacket, ProblemStatus, Subproblem, Visibility


class ContributionRevisionTests(unittest.TestCase):
    def brief(self):
        problem_id = "problem:revision-test"
        subproblem_id = "sub:revision-test"
        return {
            "id": f"project:{problem_id}:{subproblem_id}",
            "problem_id": problem_id,
            "subproblem_id": subproblem_id,
            "title": "Analyze a bounded revision question",
            "problem_title": "Synthetic revision test",
            "description": "Produce a reproducible analysis and revise it without erasing review history.",
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
            self.brief(), contributor_ref="contributor:alice", workspace_id="contribution:revision-001"
        )
        workspace.activate(basis=ParticipationBasis.VOLUNTEER)
        workspace.set_work(
            method_scope="Run a reproducible descriptive check against the frozen sample.",
            produced_outputs=["analysis notebook"],
            blockers=["denominator definition needs reviewer confirmation"],
            notes="Initial bounded pass.",
        )
        workspace.add_artifact(
            title="Analysis notebook",
            kind="notebook",
            locator="file:///private/original-analysis.ipynb",
            sha256_value="sha256:" + "a" * 64,
            artifact_id="artifact:revision-original",
        )
        submission = workspace.submit()
        return workspace, submission

    def commons(self):
        commons = ProblemCommons()
        packet = ProblemPacket(
            id="problem:revision-test",
            title="Synthetic revision test",
            observed_condition="A bounded data-quality question remains unresolved.",
            unresolved_core="Determine what the data support without overstating the result.",
            steward="curator:test",
            status=ProblemStatus.OPEN,
            visibility=Visibility.PUBLIC,
            subproblems=[Subproblem(
                id="sub:revision-test",
                title="Analyze a bounded revision question",
                description="Produce a reproducible analysis and preserve limitations.",
                kind="analysis",
            )],
        )
        commons.problems[packet.id] = packet
        return commons, packet

    def review(self, submission, verdict="revise", **kwargs):
        defaults = {
            "reviewer_ref": "reviewer:bob",
            "summary": "The submission is bounded but needs one explicit correction.",
            "strengths": ["reproducible artifact"],
            "limitations": ["denominator remains underspecified"],
            "revision_requirements": ["define and justify the denominator"] if verdict == "revise" else [],
        }
        defaults.update(kwargs)
        return ContributionReview.from_submission(submission, verdict=verdict, **defaults)

    def seed_revise(self):
        workspace, submission = self.submitted()
        trigger = self.review(submission, "revise")
        commons, packet = self.commons()
        project_review_into_commons(commons, workspace, submission, trigger)
        return workspace, submission, trigger, commons, packet

    def revised_submission(self, parent_submission, trigger_review, *, note="Defined denominator against the frozen eligible population."):
        workspace = ContributionRevisionWorkspace.from_revise(parent_submission, trigger_review.to_dict())
        workspace.set_work(
            method_scope="Run the frozen-sample descriptive check with an explicit eligible-population denominator.",
            blockers=[],
            notes=note,
        )
        submission = workspace.submit(parent_submission=parent_submission, trigger_review=trigger_review.to_dict())
        return workspace, submission

    def test_revision_workspace_preserves_parent_and_requires_a_change(self):
        original_workspace, parent_submission = self.submitted()
        trigger = self.review(parent_submission, "revise")
        frozen_parent = copy.deepcopy(parent_submission)

        revision = ContributionRevisionWorkspace.from_revise(parent_submission, trigger.to_dict())
        self.assertEqual(revision.root_workspace_id, original_workspace.id)
        self.assertEqual(revision.parent_workspace_id, original_workspace.id)
        self.assertEqual(revision.revision_number, 1)
        self.assertEqual(revision.parent_submission_hash, canonical_hash(parent_submission))
        self.assertEqual(revision.trigger_review_hash, canonical_hash(trigger.to_dict()))
        self.assertEqual(revision.revision_requirements, ["define and justify the denominator"])

        report = revision.validation(
            parent_submission=parent_submission,
            trigger_review=trigger.to_dict(),
            require_submittable=True,
        )
        self.assertFalse(report.valid)
        self.assertTrue(any("must change contributor work" in item for item in report.errors))

        with self.assertRaisesRegex(ValueError, "submitted workspace is immutable"):
            original_workspace.set_work(notes="silently rewrite the original")

        revision.set_work(notes="Explicitly define the denominator in the revised analysis.")
        revised = revision.submit(parent_submission=parent_submission, trigger_review=trigger.to_dict())
        self.assertEqual(parent_submission, frozen_parent)
        self.assertNotEqual(revised["work_hash"], revised["base_work_hash"])
        self.assertEqual(revised["parent_submission_hash"], canonical_hash(parent_submission))
        self.assertEqual(revised["trigger_review_hash"], canonical_hash(trigger.to_dict()))
        with self.assertRaisesRegex(ValueError, "must be active to edit"):
            revision.set_work(notes="post-submit mutation")

    def test_revision_requires_exact_revise_trigger(self):
        _, parent_submission = self.submitted()
        accept = self.review(parent_submission, "accept")
        with self.assertRaisesRegex(ValueError, "revise verdict"):
            ContributionRevisionWorkspace.from_revise(parent_submission, accept.to_dict())

        trigger = self.review(parent_submission, "revise")
        tampered_parent = copy.deepcopy(parent_submission)
        tampered_parent["notes"] = "changed after review"
        with self.assertRaisesRegex(ValueError, "exact parent submission"):
            ContributionRevisionWorkspace.from_revise(tampered_parent, trigger.to_dict())

    def test_revision_review_updates_same_attempt_and_preserves_boundaries(self):
        _, parent_submission, trigger, commons, packet = self.seed_revise()
        revision, revised_submission = self.revised_submission(parent_submission, trigger)
        revision.remove_artifact("artifact:revision-original") if False else None
        revision_review = self.review(
            revised_submission,
            "accept",
            summary="The requested denominator clarification is now explicit and bounded.",
            limitations=["acceptance remains scoped to the submitted analysis"],
        )

        receipt = project_revision_review_into_commons(
            commons,
            revision,
            revised_submission,
            revision_review,
            parent_submission=parent_submission,
            trigger_review=trigger.to_dict(),
        )
        self.assertTrue(receipt["changed"])
        self.assertEqual(receipt["revision_number"], 1)
        self.assertEqual(receipt["attempt_id"], "pattempt:revision-001")
        self.assertEqual(receipt["attempt_review_id"], "pareview:revision-001:r1")
        self.assertEqual(receipt["attempt_status"], "accepted")
        self.assertEqual(len(packet.attempts), 1)
        self.assertEqual(packet.attempts[0].status.value, "accepted")
        self.assertEqual(len(packet.attempt_reviews), 2)
        self.assertEqual([item.id for item in packet.attempt_reviews], ["pareview:revision-001", "pareview:revision-001:r1"])
        self.assertEqual(packet.status, ProblemStatus.OPEN)
        self.assertEqual(packet.outcomes, [])
        self.assertEqual(packet.authority_decisions, [])
        self.assertNotIn("file:///private/original-analysis.ipynb", json.dumps(packet.public_snapshot()))

    def test_revision_projection_is_idempotent_but_changed_review_is_not(self):
        _, parent_submission, trigger, commons, packet = self.seed_revise()
        revision, revised_submission = self.revised_submission(parent_submission, trigger)
        review = self.review(revised_submission, "accept", review_id="contribreview:revision-accept")

        first = project_revision_review_into_commons(
            commons, revision, revised_submission, review,
            parent_submission=parent_submission, trigger_review=trigger.to_dict(),
        )
        second = project_revision_review_into_commons(
            commons, revision, revised_submission, review,
            parent_submission=parent_submission, trigger_review=trigger.to_dict(),
        )
        self.assertTrue(first["changed"])
        self.assertFalse(second["changed"])
        self.assertEqual(len(packet.attempts), 1)
        self.assertEqual(len(packet.attempt_reviews), 2)

        changed_review = self.review(
            revised_submission,
            "accept",
            review_id="contribreview:revision-accept-2",
            summary="Different review text for the same revised submission.",
        )
        with self.assertRaisesRegex(ValueError, "different review"):
            project_revision_review_into_commons(
                commons, revision, revised_submission, changed_review,
                parent_submission=parent_submission, trigger_review=trigger.to_dict(),
            )

    def test_second_revision_round_reuses_attempt_and_stale_replay_fails(self):
        _, parent_submission, trigger, commons, packet = self.seed_revise()
        revision1, submission1 = self.revised_submission(parent_submission, trigger, note="First revision clarifies denominator.")
        review1 = self.review(
            submission1,
            "revise",
            reviewer_ref="reviewer:carol",
            summary="Denominator is clear; sensitivity treatment still needs revision.",
            revision_requirements=["add a bounded sensitivity check"],
        )
        project_revision_review_into_commons(
            commons, revision1, submission1, review1,
            parent_submission=parent_submission, trigger_review=trigger.to_dict(),
        )
        self.assertEqual(packet.attempts[0].status.value, "active")

        revision2 = ContributionRevisionWorkspace.from_revise(submission1, review1.to_dict())
        revision2.set_work(notes="Second revision adds the requested bounded sensitivity check.")
        submission2 = revision2.submit(parent_submission=submission1, trigger_review=review1.to_dict())
        review2 = self.review(
            submission2,
            "accept",
            reviewer_ref="reviewer:dana",
            summary="The requested sensitivity check is present and scoped.",
            limitations=["review remains limited to this contribution"],
        )
        receipt2 = project_revision_review_into_commons(
            commons, revision2, submission2, review2,
            parent_submission=submission1, trigger_review=review1.to_dict(),
        )
        self.assertEqual(receipt2["revision_number"], 2)
        self.assertEqual(receipt2["attempt_status"], "accepted")
        self.assertEqual(len(packet.attempts), 1)
        self.assertEqual(
            [item.id for item in packet.attempt_reviews],
            ["pareview:revision-001", "pareview:revision-001:r1", "pareview:revision-001:r2"],
        )

        with self.assertRaisesRegex(ValueError, "later or conflicting"):
            project_revision_review_into_commons(
                commons, revision1, submission1, review1,
                parent_submission=parent_submission, trigger_review=trigger.to_dict(),
            )

    def test_tampered_revision_lineage_fails_before_canonical_mutation(self):
        _, parent_submission, trigger, commons, packet = self.seed_revise()
        revision, revised_submission = self.revised_submission(parent_submission, trigger)
        review = self.review(revised_submission, "accept")
        before = copy.deepcopy(packet.to_dict())
        tampered_parent = copy.deepcopy(parent_submission)
        tampered_parent["notes"] = "tampered after review"

        with self.assertRaisesRegex(ValueError, "lineage"):
            project_revision_review_into_commons(
                commons, revision, revised_submission, review,
                parent_submission=tampered_parent, trigger_review=trigger.to_dict(),
            )
        self.assertEqual(packet.to_dict(), before)

    def test_cli_revision_round_trip(self):
        original_workspace, parent_submission, trigger, commons, _ = self.seed_revise()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            parent_path = root / "submission-v0.json"
            trigger_path = root / "review-v0.json"
            revision_workspace_path = root / "revision-r1.json"
            revision_submission_path = root / "submission-r1.json"
            revision_review_path = root / "review-r1.json"
            state_path = root / "commons.json"
            receipt_path = root / "projection-r1.json"

            parent_path.write_text(json.dumps(parent_submission, indent=2) + "\n", encoding="utf-8")
            trigger_path.write_text(json.dumps(trigger.to_dict(), indent=2) + "\n", encoding="utf-8")
            commons.save(state_path)

            self.assertEqual(revision_main([
                "init", str(parent_path), "--trigger-review", str(trigger_path), "--out", str(revision_workspace_path),
            ]), 0)
            self.assertEqual(revision_main([
                "validate", str(revision_workspace_path), "--parent-submission", str(parent_path),
                "--trigger-review", str(trigger_path), "--submittable",
            ]), 2)
            self.assertEqual(revision_main([
                "set-work", str(revision_workspace_path),
                "--method-scope", "Re-run the frozen analysis with the denominator explicitly defined.",
                "--notes", "Addresses the review requirement.",
            ]), 0)
            self.assertEqual(revision_main([
                "submit", str(revision_workspace_path), "--parent-submission", str(parent_path),
                "--trigger-review", str(trigger_path), "--submission-out", str(revision_submission_path),
            ]), 0)
            self.assertEqual(review_main([
                "create-revision", str(revision_submission_path), "--workspace", str(revision_workspace_path),
                "--parent-submission", str(parent_path), "--trigger-review", str(trigger_path),
                "--reviewer-ref", "reviewer:carol", "--verdict", "accept",
                "--summary", "The requested revision is present.",
                "--limitation", "No Problem-level outcome is inferred.", "--out", str(revision_review_path),
            ]), 0)
            self.assertEqual(review_main([
                "validate-revision", str(revision_review_path), "--submission", str(revision_submission_path),
                "--workspace", str(revision_workspace_path), "--parent-submission", str(parent_path),
                "--trigger-review", str(trigger_path),
            ]), 0)
            self.assertEqual(review_main([
                "project-revision", str(revision_review_path), "--submission", str(revision_submission_path),
                "--workspace", str(revision_workspace_path), "--parent-submission", str(parent_path),
                "--trigger-review", str(trigger_path), "--state", str(state_path),
                "--receipt-out", str(receipt_path),
            ]), 0)

            loaded = ProblemCommons.load(state_path)
            packet = loaded.get(original_workspace.problem_id)
            self.assertEqual(len(packet.attempts), 1)
            self.assertEqual(packet.attempts[0].status.value, "accepted")
            self.assertEqual(len(packet.attempt_reviews), 2)
            self.assertTrue(receipt_path.exists())
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["revision_number"], 1)
            self.assertEqual(receipt["attempt_review_id"], "pareview:revision-001:r1")

    def test_existing_revision_receipt_blocks_state_mutation(self):
        _, parent_submission, trigger, commons, packet = self.seed_revise()
        revision, revised_submission = self.revised_submission(parent_submission, trigger)
        review = self.review(revised_submission, "accept")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            parent_path = root / "submission-v0.json"
            trigger_path = root / "review-v0.json"
            workspace_path = root / "revision-r1.json"
            submission_path = root / "submission-r1.json"
            review_path = root / "review-r1.json"
            state_path = root / "commons.json"
            receipt_path = root / "projection-r1.json"

            parent_path.write_text(json.dumps(parent_submission, indent=2) + "\n", encoding="utf-8")
            trigger_path.write_text(json.dumps(trigger.to_dict(), indent=2) + "\n", encoding="utf-8")
            revision.dump(workspace_path)
            submission_path.write_text(json.dumps(revised_submission, indent=2) + "\n", encoding="utf-8")
            review_path.write_text(json.dumps(review.to_dict(), indent=2) + "\n", encoding="utf-8")
            commons.save(state_path)
            receipt_path.write_text("preserve me\n", encoding="utf-8")
            before = copy.deepcopy(packet.to_dict())

            self.assertEqual(review_main([
                "project-revision", str(review_path), "--submission", str(submission_path),
                "--workspace", str(workspace_path), "--parent-submission", str(parent_path),
                "--trigger-review", str(trigger_path), "--state", str(state_path),
                "--receipt-out", str(receipt_path),
            ]), 2)

            loaded = ProblemCommons.load(state_path)
            self.assertEqual(loaded.get("problem:revision-test").to_dict(), before)
            self.assertEqual(receipt_path.read_text(encoding="utf-8"), "preserve me\n")


if __name__ == "__main__":
    unittest.main()
