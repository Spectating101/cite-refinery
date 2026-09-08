import unittest

from cite_refinery.problem_funding import (
    CompensationMode,
    FundingNeed,
    FundingStatus,
)
from cite_refinery.problem_stages import ProblemStage
from cite_refinery.public_good_bridge import (
    ResourceMatchStatus,
    coordination_match_to_commons,
    freeze_invariants,
    funding_need_to_public_good,
    normalized_finding_to_candidate_work,
)


class PublicGoodBridgeTests(unittest.TestCase):
    def test_unknown_funding_projects_without_inventing_amount_or_commitment(self):
        need = FundingNeed(
            problem_id="problem:test-001",
            subproblem_id="sub:measure",
            stage=ProblemStage.MEASURE,
            status=FundingStatus.UNKNOWN,
            compensation_mode=CompensationMode.UNSPECIFIED,
            volunteer_compatible=False,
            currency="TWD",
            target_amount=None,
            minimum_amount=None,
            committed_amount=0,
            expense_categories=["research labor"],
            restrictions=["Do not assume unpaid labor."],
        )
        projection = funding_need_to_public_good(need)
        self.assertEqual(projection.kind, "funding")
        self.assertEqual(projection.priority, "watch")
        self.assertIsNone(projection.amount)
        self.assertIn("unknown", projection.notes)
        self.assertIn("does not establish eligibility", projection.claim_boundary)

    def test_not_required_funding_is_not_projected_as_need(self):
        need = FundingNeed(
            problem_id="problem:test-001",
            subproblem_id="sub:free",
            stage=ProblemStage.BUILD,
            status=FundingStatus.NOT_REQUIRED,
            volunteer_compatible=True,
        )
        with self.assertRaises(ValueError):
            funding_need_to_public_good(need)

    def test_qualified_resource_match_stays_candidate_only(self):
        projection = coordination_match_to_commons(
            problem_id="problem:test-001",
            subproblem_id="sub:measure",
            raw_match={
                "resource_id": "grant:example",
                "status": "qualified_candidate",
                "matched_dimensions": ["support_kind", "geography"],
                "unresolved_dimensions": [],
                "blocking_dimensions": [],
                "evidence_refs": ["source:grant"],
                "reasons": ["Represented dimensions matched."],
            },
        )
        self.assertEqual(projection.status, ResourceMatchStatus.QUALIFIED_CANDIDATE)
        self.assertFalse(projection.funding_commitment)
        self.assertFalse(projection.application_submitted)
        self.assertFalse(projection.authority_granted)
        self.assertIn("not an award", projection.claim_boundary)

    def test_blocked_resource_match_preserves_blocker(self):
        projection = coordination_match_to_commons(
            problem_id="problem:test-001",
            subproblem_id="sub:measure",
            raw_match={
                "resource_id": "grant:closed",
                "status": "blocked",
                "blocking_dimensions": ["application_deadline"],
            },
        )
        self.assertEqual(projection.status, ResourceMatchStatus.BLOCKED)
        self.assertEqual(projection.blocking_dimensions, ["application_deadline"])

    def test_public_good_finding_does_not_auto_classify_commons_stage(self):
        projection = normalized_finding_to_candidate_work(
            problem_id="problem:test-001",
            source_case_id="case:pg-001",
            raw_finding={
                "stage": "access",
                "problem_class": "service_access_gap",
                "priority": "urgent",
                "recommended_action": "Verify the access bottleneck before expanding capacity.",
                "evidence_refs": ["source:a"],
                "human_authority_required": True,
                "structural_candidate": True,
            },
        )
        self.assertEqual(projection.public_good_stage, "access")
        self.assertIsNone(projection.commons_stage)
        self.assertFalse(projection.commons_subproblem_created)
        self.assertFalse(projection.authority_granted)
        self.assertEqual(projection.suggested_title, "Investigate service access gap")

    def test_projection_objects_refuse_escalation_flags(self):
        with self.assertRaises(ValueError):
            coordination_match_to_commons(
                problem_id="problem:test-001",
                subproblem_id="sub:measure",
                raw_match={"resource_id": "grant:x", "status": "funded"},
            )

    def test_freeze_invariants_cover_stage_funding_and_authority(self):
        text = " ".join(freeze_invariants()).lower()
        self.assertIn("work stage", text)
        self.assertIn("funding", text)
        self.assertIn("authority", text)
        self.assertIn("domain constitutions", text)


if __name__ == "__main__":
    unittest.main()
