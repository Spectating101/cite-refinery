import unittest
from scripts.portfolio_calibration_pilot import parse_generated, score_one, SELECTED

class PilotTests(unittest.TestCase):
    def test_pilot_has_mixed_tasks(self):
        self.assertEqual(len(SELECTED),8)
        self.assertEqual(sum(x.endswith("self_description") for x in SELECTED),2)

    def test_markdown_fence_can_be_decoded_but_not_auto_accepted(self):
        data,fenced=parse_generated('```json\n{"a":1}\n```')
        self.assertTrue(fenced)
        self.assertEqual(data["a"],1)

    def test_invalid_independent_approval_is_detected(self):
        task={"id":"demo:adoption","task_kind":"requires_independent_evidence",
              "allowed_evidence_ids":["repo_demo"],"evidence_text":"Demo README"}
        r=score_one(task,'{"id":"demo:adoption","verdict":"self_reported","evidence_id":"repo_demo","quote":"Demo README"}')
        self.assertTrue(r["false_source_approval"])
        self.assertFalse(r["contract_valid"])

    def test_correct_abstention(self):
        task={"id":"demo:adoption","task_kind":"requires_independent_evidence",
              "allowed_evidence_ids":["repo_demo"],"evidence_text":"Demo README"}
        r=score_one(task,'{"id":"demo:adoption","verdict":"insufficient","evidence_id":null,"quote":""}')
        self.assertTrue(r["contract_valid"])

if __name__=="__main__":
    unittest.main()
