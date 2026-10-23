"""Adversarial tests for portfolio candidate decision scoring."""
import unittest
from cite_refinery.portfolio_decision_eval import evaluate, EvaluationError


class DecisionEvalTests(unittest.TestCase):
    def setUp(self):
        self.tasks = [
            {"id": "physical", "gold": "insufficient", "family": "hardware",
             "allowed_evidence_ids": ["readme-1"],
             "evidence_urls": ["https://github.com/Spectating101/hardware-splicer"]},
            {"id": "CI", "gold": "supported", "family": "software",
             "allowed_evidence_ids": ["run-1"],
             "evidence_urls": ["https://github.com/Spectating101/cite-refinery/actions"]},
            {"id": "claim", "gold": "refuted", "family": "research",
             "allowed_evidence_ids": ["correction-1"], "evidence_urls": []}
        ]
        self.answers = [
            {"id": "physical", "verdict": "insufficient", "evidence_ids": [],
             "rationale": "No independent bench receipt is available."},
            {"id": "CI", "verdict": "supported", "evidence_ids": ["run-1"],
             "rationale": "A workflow execution receipt supports this claim."},
            {"id": "claim", "verdict": "refuted", "evidence_ids": ["correction-1"],
             "rationale": "The supplied correction contradicts the claim."}
        ]

    def test_clean_scoring(self):
        result = evaluate(self.tasks, self.answers)
        self.assertTrue(result["release_gate_pass"])
        self.assertEqual(result["accuracy"], 1)
        self.assertEqual(result["insufficient_abstention_rate"], 1)

    def test_unanswerable_question_nearest_neighbor_is_not_proof(self):
        self.answers[0]["verdict"] = "supported"
        self.answers[0]["evidence_ids"] = ["readme-1"]
        result = evaluate(self.tasks, self.answers)
        self.assertEqual(result["false_approval_count"], 1)
        self.assertFalse(result["release_gate_pass"])

    def test_valid_gold_with_unknown_evidence_does_not_pass(self):
        self.answers[1]["evidence_ids"] = ["private-worktree-claim"]
        result = evaluate(self.tasks, self.answers)
        self.assertEqual(result["source_scope_violation_count"], 1)
        self.assertEqual(result["unsupported_positive_count"], 1)
        self.assertFalse(result["release_gate_pass"])

    def test_positive_without_citation_does_not_pass(self):
        self.answers[1]["evidence_ids"] = []
        self.assertEqual(evaluate(self.tasks, self.answers)
                         ["unsupported_positive_count"], 1)

    def test_missing_answer_is_not_silently_abstained(self):
        with self.assertRaisesRegex(EvaluationError, "Missing"):
            evaluate(self.tasks, self.answers[:-1])

    def test_private_source_url_is_rejected(self):
        self.tasks[0]["evidence_urls"] = ["file:///home/operator/private-repo"]
        with self.assertRaisesRegex(EvaluationError, "nonpublic"):
            evaluate(self.tasks, self.answers)

    def test_duplicate_candidate_ids_rejected(self):
        with self.assertRaisesRegex(EvaluationError, "duplicate"):
            evaluate(self.tasks, self.answers + [self.answers[0]])

    def test_refutation_of_unknown_is_not_valid_abstention(self):
        self.answers[0]["verdict"] = "refuted"
        result = evaluate(self.tasks, self.answers)
        self.assertEqual(result["insufficient_abstention_rate"], 0)
        self.assertFalse(result["release_gate_pass"])


if __name__ == "__main__":
    unittest.main()
