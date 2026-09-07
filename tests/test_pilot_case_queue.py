import json
from pathlib import Path
import unittest


class PilotCaseQueueTests(unittest.TestCase):
    def test_case_queue_references_known_candidate_signals_and_stays_non_public(self):
        signals = json.loads(Path("pilot/candidate_signals.tw.v0.1.json").read_text(encoding="utf-8"))
        queue = json.loads(Path("pilot/case_queue.v0.1.json").read_text(encoding="utf-8"))
        self.assertEqual(queue["schema"], "problem-pilot-case-queue/v0.1")
        known = {item["id"] for item in signals["signals"]}
        self.assertEqual(len(queue["cases"]), 3)
        for case in queue["cases"]:
            self.assertIn(case["signal_id"], known)
            self.assertTrue(case["required_external_reviews"])
            self.assertTrue(case["primary_measures"])
            self.assertTrue(case["stop_conditions"])
            self.assertNotEqual(case["publication_state"], "public")

    def test_taoyuan_lane_does_not_claim_causal_intervention(self):
        queue = json.loads(Path("pilot/case_queue.v0.1.json").read_text(encoding="utf-8"))
        taoyuan = next(item for item in queue["cases"] if item["signal_id"] == "signal:taoyuan-pedestrian-risk-001")
        self.assertIn("non-causal", taoyuan["objective"])
        self.assertTrue(any("join" in item for item in taoyuan["stop_conditions"]))
        self.assertIn("researching", taoyuan["publication_state"])


if __name__ == "__main__":
    unittest.main()
