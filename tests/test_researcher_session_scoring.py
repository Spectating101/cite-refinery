"""Adversarial tests for the independent researcher task scoring instrument."""
import unittest

from scripts.score_researcher_sessions import SCHEMA, TASKS, score_session


def sample():
    choices = {
        "dog_national_survey": "decline_not_significant",
        "dog_talea_capability": "not_demonstrated",
        "dog_shoushan_scope": "local_model_not_national_proof",
        "dog_policy_outcome": "policy_intent_not_verified_effect",
    }
    return {
        "schema": SCHEMA,
        "case": "taiwan-free-roaming-dogs-survey-management",
        "session_id": "synthetic-fixture-only",
        "mode": "independent",
        "tasks": [
            {
                "task_id": key,
                "choice": choices[key],
                "evidence_node_keys": sorted(rubric["required_keys"]),
                "source_domains": sorted(rubric["required_domains"]),
                "elapsed_seconds": 60,
                "used_hint": False,
            }
            for key, rubric in TASKS.items()
        ],
    }


class SessionScoringTests(unittest.TestCase):
    def test_synthetic_perfect_fixture_not_claimed_human(self):
        report = score_session(sample())
        self.assertEqual(report["source_grounded_unassisted_tasks"], 4)
        self.assertEqual(report["total_elapsed_seconds"], 240)
        self.assertIn("not independently verified", report["limitations"][0])

    def test_correct_guess_without_evidence_is_not_success(self):
        s = sample()
        s["tasks"][0]["evidence_node_keys"] = []
        self.assertEqual(score_session(s)["source_grounded_unassisted_tasks"], 3)

    def test_missing_primary_source_is_not_success(self):
        s = sample()
        s["tasks"][1]["source_domains"] = []
        self.assertEqual(score_session(s)["source_grounded_unassisted_tasks"], 3)

    def test_assistance_excludes_independent_success(self):
        s = sample()
        s["tasks"][0]["used_hint"] = True
        self.assertEqual(score_session(s)["source_grounded_unassisted_tasks"], 3)
        s["mode"] = "automated"
        self.assertEqual(score_session(s)["source_grounded_unassisted_tasks"], 0)

    def test_false_policy_effectiveness_is_wrong(self):
        s = sample()
        s["tasks"][3]["choice"] = "verified_effect"
        r = score_session(s)
        self.assertEqual(r["correct_choices"], 3)
        self.assertEqual(r["source_grounded_unassisted_tasks"], 3)

    def test_duplicate_task_rejected(self):
        s = sample()
        s["tasks"][1] = s["tasks"][0].copy()
        with self.assertRaises(ValueError):
            score_session(s)

    def test_invalid_time_and_hint_rejected(self):
        s = sample()
        s["tasks"][0]["elapsed_seconds"] = -1
        with self.assertRaises(ValueError):
            score_session(s)
        s = sample()
        s["tasks"][0]["used_hint"] = "false"
        with self.assertRaises(ValueError):
            score_session(s)

    def test_wrong_case_and_schema_rejected(self):
        for field, value in (("case", "other"), ("schema", "v0")):
            s = sample()
            s[field] = value
            with self.assertRaises(ValueError):
                score_session(s)


if __name__ == "__main__":
    unittest.main()
