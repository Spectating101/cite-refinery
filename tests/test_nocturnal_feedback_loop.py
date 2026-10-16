import sys
import tempfile
import unittest

from cite_refinery import CiteRefinery
from cite_refinery.feedback import REQUEST_SCHEMA, RESULT_SCHEMA
from cite_refinery.scorecard import build_end_to_end_scorecard


PACKET = {
    "schema": "nocturnal.trace5_empirical_case.v1",
    "candidate_id": "fixture-feedback-matter",
    "country": "Fixtureland",
    "domain": "public_administration_rights",
    "matter_id": "fixture-feedback-matter",
    "cohort": "development",
    "quality_state": "research_grade",
    "claims": [
        {
            "claim": "A public record changed without an accessible revision history.",
            "matter_id": "fixture-feedback-matter",
            "event_id": "fixture-feedback:1",
            "status_stage": "reported",
            "sources": ["https://fixture.invalid/baseline"],
        }
    ],
}


def validated_chain(app: CiteRefinery):
    project = app.init_project("Feedback fixture", "Observe outcomes after a validated intervention")
    observations = app.ingest_nocturnal_packet(project.id, PACKET)
    requirement = app.add_requirement(project.id, "Preserve revision history")
    capability = app.adopt_capability(
        project.id,
        requirement.id,
        name="Revision history",
        description="Preserve and expose record revisions",
    )
    implementation = app.refinery.register_implementation(
        capability_id=capability.id,
        project_id=project.id,
        provider="subprocess",
        invocation={
            "argv": [sys.executable, "-c", "print('ok')"],
            "input_mode": "none",
        },
    )
    run = app.invoke(project.id, implementation.id)
    experiment = app.add_experiment(
        project.id,
        name="revision intervention validation",
        method="fixture",
        result="passed",
        verdict="passed",
        run_ids=[run.id],
    )
    return project, observations, capability, implementation, run, experiment


class NocturnalFeedbackLoopTests(unittest.TestCase):
    def test_request_and_result_close_the_formal_loop_without_causal_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project, observations, capability, implementation, run, experiment = validated_chain(app)

            request = app.create_nocturnal_feedback_request(
                project.id,
                experiment.id,
                observation_ids=[observations[0].id],
                window_start="2026-10-01T00:00:00Z",
                window_end="2026-12-31T23:59:59Z",
            )
            self.assertEqual(request["schema"], REQUEST_SCHEMA)
            self.assertEqual(request["experiment_id"], experiment.id)
            self.assertEqual(request["run_ids"], [run.id])
            self.assertEqual(request["capability_ids"], [capability.id])
            self.assertEqual(request["implementation_ids"], [implementation.id])
            self.assertEqual(request["originating_problem_observation_ids"], [observations[0].id])

            packet = {
                "schema": RESULT_SCHEMA,
                "request_id": request["request_id"],
                "project_id": project.id,
                "experiment_id": experiment.id,
                "run_ids": [run.id],
                "collection": {
                    "collector": "fixture-nocturnal",
                    "collected_at": "2026-11-01T00:00:00Z",
                    "limitations": ["observational follow-up only"],
                },
                "observations": [
                    {
                        "observation_id": "fixture-followup:1",
                        "matter_id": "fixture-feedback-matter",
                        "event_id": "fixture-feedback:2",
                        "text": "The institution published a revision log after deployment.",
                        "observed_at": "2026-10-20T00:00:00Z",
                        "status_stage": "implementation_followup",
                        "sources": ["https://fixture.invalid/followup"],
                        "relation_to_intervention": "outcome_signal",
                        "outcome_direction": "improved",
                        "causal_status": "not_established",
                        "provenance": {"source_family": "official"},
                    }
                ],
            }
            result = app.ingest_nocturnal_feedback_result(project.id, packet)
            self.assertEqual(result["request_id"], request["request_id"])
            self.assertEqual(len(result["cite_refinery_observation_ids"]), 1)

            state = app.store.load()
            followup = state["problem_observations"][result["cite_refinery_observation_ids"][0]]
            self.assertEqual(followup["source_system"], "nocturnal-feedback")
            self.assertEqual(followup["frame"], "post_intervention")
            self.assertEqual(followup["provenance"]["experiment_id"], experiment.id)
            self.assertEqual(followup["provenance"]["run_ids"], [run.id])
            self.assertEqual(followup["provenance"]["causal_status"], "not_established")

            scorecard = build_end_to_end_scorecard(state, project.id)
            feedback = scorecard["stages"]["nocturnal_feedback_loop"]
            self.assertEqual(feedback["status"], "ready")
            self.assertEqual(feedback["feedback_requests"], 1)
            self.assertEqual(feedback["feedback_results"], 1)
            self.assertEqual(feedback["linked_post_intervention_observations"], 1)
            self.assertEqual(feedback["causal_status"], "not_established")

    def test_reingesting_same_result_is_observation_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project, observations, _, _, run, experiment = validated_chain(app)
            request = app.create_nocturnal_feedback_request(project.id, experiment.id, observation_ids=[observations[0].id])
            packet = {
                "schema": RESULT_SCHEMA,
                "request_id": request["request_id"],
                "project_id": project.id,
                "experiment_id": experiment.id,
                "run_ids": [run.id],
                "observations": [{
                    "observation_id": "idempotent-followup",
                    "text": "A follow-up event was documented.",
                    "sources": ["https://fixture.invalid/followup-2"],
                    "relation_to_intervention": "post_intervention_observation",
                    "outcome_direction": "unknown",
                    "causal_status": "not_established",
                }],
            }
            first = app.ingest_nocturnal_feedback_result(project.id, packet)
            second = app.ingest_nocturnal_feedback_result(project.id, packet)
            self.assertEqual(first["result_id"], second["result_id"])
            self.assertEqual(first["cite_refinery_observation_ids"], second["cite_refinery_observation_ids"])
            state = app.store.load()
            followups = [
                item for item in state["problem_observations"].values()
                if item.get("source_system") == "nocturnal-feedback"
            ]
            self.assertEqual(len(followups), 1)
            self.assertEqual(len(state["feedback_results"]), 1)

    def test_mismatched_or_causalized_results_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project, observations, _, _, run, experiment = validated_chain(app)
            request = app.create_nocturnal_feedback_request(project.id, experiment.id, observation_ids=[observations[0].id])
            base = {
                "schema": RESULT_SCHEMA,
                "request_id": request["request_id"],
                "project_id": project.id,
                "experiment_id": experiment.id,
                "run_ids": [run.id],
                "observations": [{
                    "observation_id": "bad-followup",
                    "text": "A later event occurred.",
                    "relation_to_intervention": "outcome_signal",
                    "outcome_direction": "improved",
                    "causal_status": "not_established",
                }],
            }
            wrong_run = dict(base)
            wrong_run["run_ids"] = ["rrun:wrong"]
            with self.assertRaisesRegex(ValueError, "run_ids"):
                app.ingest_nocturnal_feedback_result(project.id, wrong_run)

            causalized = {**base, "observations": [{**base["observations"][0], "causal_status": "caused_by_intervention"}]}
            with self.assertRaisesRegex(ValueError, "causal_status"):
                app.ingest_nocturnal_feedback_result(project.id, causalized)

    def test_unvalidated_experiment_cannot_open_followup_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project = app.init_project("Unvalidated", "Do not observe as if intervention validated")
            app.ingest_nocturnal_packet(project.id, PACKET)
            experiment = app.add_experiment(
                project.id,
                name="failed validation",
                method="fixture",
                result="failed",
                verdict="failed",
            )
            with self.assertRaisesRegex(ValueError, "passed/supported"):
                app.create_nocturnal_feedback_request(project.id, experiment.id)


if __name__ == "__main__":
    unittest.main()
