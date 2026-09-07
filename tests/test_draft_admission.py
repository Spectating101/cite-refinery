import json
from pathlib import Path
import unittest

from cite_refinery.case_operations import CaseOperations
from cite_refinery.draft_admission import admit_draft_packet
from cite_refinery.pilot import PilotLedger
from cite_refinery.problem_commons import ProblemCommons, ProblemStatus, Visibility
from cite_refinery.problem_governance import GovernanceRegistry
from cite_refinery.problem_stages import StageRegistry


class DraftAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ops = CaseOperations(
            commons=ProblemCommons(),
            stages=StageRegistry(),
            governance=GovernanceRegistry(),
            pilot=PilotLedger(),
        )
        self.taoyuan = json.loads(Path("pilot/drafts/taoyuan-mobility.candidate.v0.1.json").read_text(encoding="utf-8"))

    def test_real_taoyuan_draft_enters_only_as_researching_nonpublic_case(self):
        packet, receipt, duplicates = admit_draft_packet(self.ops, self.taoyuan, actor="pilot-curator")
        self.assertEqual(packet.id, "problem:taoyuan-mobility-candidate-001")
        self.assertEqual(packet.status, ProblemStatus.RESEARCHING)
        self.assertEqual(packet.visibility, Visibility.RESTRICTED)
        self.assertEqual(packet.attempts, [])
        self.assertEqual(packet.authority_decisions, [])
        self.assertEqual(packet.outcomes, [])
        self.assertEqual(self.ops.commons.list_public(), [])
        self.assertEqual(duplicates, [])
        self.assertEqual(receipt.action, "draft-import")
        self.assertTrue(receipt.problem_sha256)
        self.assertIn("do-not-publish-before-curation", packet.tags)

        assessment = self.ops.assess(packet.id, policy={
            "schema": "problem-operations-policy/v0.1",
            "require_owner_for_verification": True,
            "require_reviewer_for_verification": True,
            "owner_agreement_min": 0.8,
            "reviewer_score_min": 0.8,
            "solver_comprehension_min": 0.8,
        })
        self.assertEqual(assessment.phase, "curation")
        self.assertFalse(assessment.eligible_for_verification)
        self.assertTrue(any("production" in item for item in assessment.blockers))
        self.assertTrue(any("reviewed_evidence" in item for item in assessment.blockers))

    def test_draft_admission_rejects_public_or_advanced_state(self):
        public = dict(self.taoyuan)
        public["visibility"] = "public"
        with self.assertRaises(ValueError):
            admit_draft_packet(self.ops, public, actor="curator")

        opened = dict(self.taoyuan)
        opened["status"] = "open"
        with self.assertRaises(ValueError):
            admit_draft_packet(self.ops, opened, actor="curator")

    def test_draft_admission_rejects_embedded_authority_outcome_or_attempt(self):
        with_authority = dict(self.taoyuan)
        with_authority["authority_decisions"] = [{
            "id": "pauth:x", "problem_id": self.taoyuan["id"], "actor": "x", "scope": "x", "decision": "authorized"
        }]
        with self.assertRaises(ValueError):
            admit_draft_packet(self.ops, with_authority, actor="curator")

        with_outcome = dict(self.taoyuan)
        with_outcome["outcomes"] = [{
            "id": "poutcome:x", "problem_id": self.taoyuan["id"], "summary": "x", "observed_change": "x"
        }]
        with self.assertRaises(ValueError):
            admit_draft_packet(self.ops, with_outcome, actor="curator")

        with_attempt = dict(self.taoyuan)
        with_attempt["attempts"] = [{
            "id": "pattempt:x", "problem_id": self.taoyuan["id"], "title": "x", "contributor": "x",
            "subproblem_ids": ["sub:validate-data"], "status": "active"
        }]
        with self.assertRaises(ValueError):
            admit_draft_packet(self.ops, with_attempt, actor="curator")

    def test_duplicate_draft_requires_explicit_override(self):
        first, _, _ = admit_draft_packet(self.ops, self.taoyuan, actor="curator")
        second_payload = dict(self.taoyuan)
        second_payload["id"] = "problem:taoyuan-mobility-candidate-duplicate"
        with self.assertRaises(ValueError):
            admit_draft_packet(self.ops, second_payload, actor="curator")
        second, _, duplicates = admit_draft_packet(self.ops, second_payload, actor="curator", allow_duplicate=True)
        self.assertEqual(second.id, "problem:taoyuan-mobility-candidate-duplicate")
        self.assertTrue(any(problem_id == first.id for problem_id, _ in duplicates))


if __name__ == "__main__":
    unittest.main()
