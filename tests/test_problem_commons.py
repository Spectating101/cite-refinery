import unittest

from cite_refinery.problem_commons import (
    EvidenceRef,
    ProblemCommons,
    ProblemStatus,
    SuccessCriterion,
)


class ProblemCommonsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.commons = ProblemCommons()
        self.problem = self.commons.create_problem(
            title="Recurring shelter food-access interruption",
            observed_condition="Some shelters report intermittent access to appropriate food supply.",
            unresolved_core="Determine whether the binding constraint is supply, matching, transport, or verification.",
            steward="pilot-curator",
            domain="animal-welfare",
        )

    def make_publishable(self) -> None:
        self.problem.authority_boundary = "Any field intervention requires the participating shelter/operator to approve it."
        self.problem.affected_actors = ["shelters", "animals", "donors", "transport operators"]
        self.problem.constraints = ["food safety", "transport time", "privacy of partner data"]
        self.problem.knowledge_frontier = ["Need evidence on whether interruptions are supply-side or access-side."]
        self.problem.capability_frontier = ["routing", "inventory ingestion"]
        self.problem.evidence.append(
            EvidenceRef(
                id="evidence:1",
                source="partner interview",
                locator="restricted:interview-001",
                summary="Partner reports repeated food-access interruptions.",
                confidence="reviewed",
            )
        )
        self.problem.success_criteria.append(
            SuccessCriterion(
                id="criterion:1",
                metric="interruption frequency",
                target="lower than frozen baseline",
                measurement="partner-confirmed monthly interruption log",
                falsification="no reduction or increased safety incidents",
            )
        )
        self.problem.add_subproblem("Map interruptions", "Establish baseline frequency and causes.", "research")

    def test_candidate_is_not_publishable_without_evidence_and_success(self) -> None:
        report = self.problem.publishability()
        self.assertFalse(report.publishable)
        self.assertIn("evidence", report.missing)
        self.assertIn("success_criteria", report.missing)
        self.assertIn("authority_boundary", report.missing)

    def test_publishable_problem_can_open_and_accept_attempt(self) -> None:
        self.make_publishable()
        self.problem.transition(ProblemStatus.RESEARCHING, actor="curator", reason="begin curation")
        self.problem.transition(ProblemStatus.VERIFIED, actor="reviewer", reason="evidence and scope reviewed")
        self.problem.transition(ProblemStatus.OPEN, actor="reviewer", reason="publish for attempts")
        subproblem_id = self.problem.subproblems[0].id
        attempt = self.problem.start_attempt(
            title="Baseline interruption audit",
            contributor="student-team-a",
            subproblem_ids=[subproblem_id],
        )
        self.assertEqual(attempt.problem_id, self.problem.id)
        self.assertEqual(len(self.problem.attempts), 1)
        self.assertEqual(self.commons.list_public()[0].id, self.problem.id)

    def test_invalid_lifecycle_jump_is_rejected(self) -> None:
        self.make_publishable()
        with self.assertRaisesRegex(ValueError, "invalid transition"):
            self.problem.transition(ProblemStatus.DEPLOYED, actor="x", reason="skip everything")

    def test_unknown_subproblem_cannot_be_claimed(self) -> None:
        self.make_publishable()
        self.problem.transition(ProblemStatus.RESEARCHING, actor="curator", reason="start")
        self.problem.transition(ProblemStatus.VERIFIED, actor="reviewer", reason="review")
        self.problem.transition(ProblemStatus.OPEN, actor="reviewer", reason="publish")
        with self.assertRaisesRegex(ValueError, "unknown subproblem"):
            self.problem.start_attempt(title="bad", contributor="x", subproblem_ids=["psub:missing"])

    def test_resolved_problem_can_reopen_when_outcome_recurs(self) -> None:
        self.make_publishable()
        for status in [
            ProblemStatus.RESEARCHING,
            ProblemStatus.VERIFIED,
            ProblemStatus.OPEN,
            ProblemStatus.PILOTING,
            ProblemStatus.DEPLOYED,
            ProblemStatus.MONITORING,
            ProblemStatus.RESOLVED,
        ]:
            self.problem.transition(status, actor="reviewer", reason=f"advance to {status.value}")
        self.problem.record_outcome(
            summary="Interruption returned after initial improvement.",
            observed_change="Two new interruptions observed.",
            evidence_refs=["nocturnal:matter:001"],
            disposition="recurrence",
        )
        revision = self.problem.transition(ProblemStatus.OPEN, actor="steward", reason="recurrence observed")
        self.assertEqual(revision.from_status, "resolved")
        self.assertEqual(self.problem.status, ProblemStatus.OPEN)


if __name__ == "__main__":
    unittest.main()
