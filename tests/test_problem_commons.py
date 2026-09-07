import tempfile
import unittest
from pathlib import Path

from cite_refinery.problem_commons import (
    AttemptStatus,
    EvidenceRef,
    ProblemCommons,
    ProblemSignal,
    ProblemStatus,
    SuccessCriterion,
    Visibility,
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
            problem_owner="participating shelter network",
        )

    def make_publishable(self) -> None:
        self.problem.authority_boundary = "Any field intervention requires participating operators to approve it."
        self.problem.affected_actors = ["shelters", "animals", "donors", "transport operators"]
        self.problem.constraints = ["food safety", "transport time", "partner-data privacy"]
        self.problem.knowledge_frontier = ["Need evidence on whether interruptions are supply-side or access-side."]
        self.problem.capability_frontier = ["routing", "inventory ingestion"]
        self.problem.implementation_pathway = ["shadow recommendation", "operator review", "reversible pilot"]
        self.problem.evidence.append(EvidenceRef(id="evidence:1", source="partner interview", locator="restricted:interview-001", summary="Partner reports repeated food-access interruptions.", confidence="reviewed", visibility=Visibility.RESTRICTED))
        self.problem.success_criteria.append(SuccessCriterion(id="criterion:1", metric="interruption frequency", target="lower than frozen baseline", measurement="partner-confirmed monthly interruption log", falsification="no reduction or increased safety incidents"))
        self.problem.add_subproblem("Map interruptions", "Establish baseline frequency and causes.", "research", skill_tags=["statistics", "survey design"], interest_tags=["animal welfare"])

    def open_problem(self):
        self.make_publishable()
        self.problem.transition(ProblemStatus.RESEARCHING, actor="curator", reason="begin curation")
        self.problem.transition(ProblemStatus.VERIFIED, actor="reviewer", reason="reviewed")
        self.problem.transition(ProblemStatus.OPEN, actor="reviewer", reason="publish")

    def test_candidate_is_not_publishable_without_evidence_and_success(self):
        report = self.problem.publishability()
        self.assertFalse(report.publishable)
        self.assertIn("evidence", report.missing)
        self.assertIn("reviewed_evidence", report.missing)
        self.assertIn("success_criteria", report.missing)

    def test_open_requires_decomposition(self):
        self.make_publishable()
        self.problem.subproblems.clear()
        self.problem.transition(ProblemStatus.RESEARCHING, actor="x", reason="research")
        self.problem.transition(ProblemStatus.VERIFIED, actor="x", reason="verify")
        with self.assertRaisesRegex(ValueError, "decomposition"):
            self.problem.transition(ProblemStatus.OPEN, actor="x", reason="open")

    def test_open_problem_accepts_attempt(self):
        self.open_problem()
        attempt = self.problem.start_attempt(title="Baseline interruption audit", contributor="student-team-a", subproblem_ids=[self.problem.subproblems[0].id])
        self.assertEqual(attempt.status, AttemptStatus.ACTIVE)
        self.assertEqual(self.commons.list_public()[0].id, self.problem.id)

    def test_attempt_requires_explicit_subproblem(self):
        self.open_problem()
        with self.assertRaisesRegex(ValueError, "at least one"):
            self.problem.start_attempt(title="vague", contributor="x")

    def test_pilot_requires_accepted_attempt(self):
        self.open_problem()
        with self.assertRaisesRegex(ValueError, "accepted"):
            self.problem.transition(ProblemStatus.PILOTING, actor="x", reason="too early")
        attempt = self.problem.start_attempt(title="Audit", contributor="x", subproblem_ids=[self.problem.subproblems[0].id])
        self.problem.update_attempt_status(attempt.id, AttemptStatus.SUBMITTED)
        self.problem.review_attempt(attempt.id, reviewer="reviewer", verdict="accept")
        self.problem.transition(ProblemStatus.PILOTING, actor="reviewer", reason="accepted attempt")
        self.assertEqual(self.problem.status, ProblemStatus.PILOTING)

    def test_deployment_requires_authority(self):
        self.open_problem()
        attempt = self.problem.start_attempt(title="Audit", contributor="x", subproblem_ids=[self.problem.subproblems[0].id])
        self.problem.update_attempt_status(attempt.id, AttemptStatus.SUBMITTED)
        self.problem.review_attempt(attempt.id, reviewer="reviewer", verdict="accept")
        self.problem.transition(ProblemStatus.PILOTING, actor="reviewer", reason="pilot")
        with self.assertRaisesRegex(ValueError, "authority"):
            self.problem.transition(ProblemStatus.DEPLOYED, actor="x", reason="deploy")
        self.problem.authorize(actor="operator", scope="bounded pilot", decision="authorized")
        self.problem.transition(ProblemStatus.DEPLOYED, actor="operator", reason="authorized")
        self.assertEqual(self.problem.status, ProblemStatus.DEPLOYED)

    def test_public_snapshot_redacts_restricted_locators(self):
        self.open_problem()
        snapshot = self.problem.public_snapshot()
        self.assertIsNone(snapshot["evidence"][0]["locator"])
        self.assertTrue(snapshot["evidence"][0]["redacted"])

    def test_matching_is_transparent_and_credential_gated(self):
        self.open_problem()
        self.problem.add_subproblem("Clinical nutrition review", "Review species-specific nutrition constraints.", "domain", skill_tags=["veterinary nutrition"], required_credentials=["licensed veterinarian"])
        matches = self.problem.match_contributions(skills=["statistics", "survey design"], interests=["animal welfare"])
        self.assertEqual(matches[0].title, "Map interruptions")
        gated = next(x for x in matches if x.title == "Clinical nutrition review")
        self.assertTrue(gated.missing_credentials)

    def test_roundtrip_persistence(self):
        self.open_problem()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "commons.json"
            self.commons.save(path)
            loaded = ProblemCommons.load(path)
            packet = loaded.get(self.problem.id)
            self.assertEqual(packet.status, ProblemStatus.OPEN)
            self.assertEqual(packet.evidence[0].visibility, Visibility.RESTRICTED)

    def test_signal_preserves_origin_reference(self):
        signal = ProblemSignal(id="signal:1", source_system="nocturnal", source_ref="matter:42", title="Observed recurring interruption", observed_condition="A condition recurred over multiple periods.")
        packet = self.commons.create_from_signal(signal, steward="curator")
        self.assertEqual(packet.external_refs[0].system, "nocturnal")

    def test_duplicate_candidates_surface_overlap(self):
        other = self.commons.create_problem(title="Shelter food access interruption", observed_condition="Shelters report intermittent food access and transport problems.", unresolved_core="Determine whether transport or supply is the binding constraint.", steward="x")
        dupes = self.commons.duplicate_candidates(other, threshold=0.15)
        self.assertTrue(any(pid == self.problem.id for pid, _ in dupes))

    def test_resolved_problem_can_reopen_after_recurrence(self):
        self.open_problem()
        attempt = self.problem.start_attempt(title="Audit", contributor="x", subproblem_ids=[self.problem.subproblems[0].id])
        self.problem.update_attempt_status(attempt.id, AttemptStatus.SUBMITTED)
        self.problem.review_attempt(attempt.id, reviewer="reviewer", verdict="accept")
        self.problem.transition(ProblemStatus.PILOTING, actor="reviewer", reason="pilot")
        self.problem.authorize(actor="operator", scope="pilot", decision="authorized")
        self.problem.transition(ProblemStatus.DEPLOYED, actor="operator", reason="deploy")
        self.problem.transition(ProblemStatus.MONITORING, actor="operator", reason="monitor")
        self.problem.transition(ProblemStatus.RESOLVED, actor="reviewer", reason="resolved")
        self.problem.record_outcome(summary="Interruption returned.", observed_change="Two new interruptions observed.", evidence_refs=["nocturnal:matter:001"], disposition="recurrence")
        self.problem.transition(ProblemStatus.OPEN, actor="steward", reason="recurrence")
        self.assertEqual(self.problem.status, ProblemStatus.OPEN)


if __name__ == "__main__":
    unittest.main()
