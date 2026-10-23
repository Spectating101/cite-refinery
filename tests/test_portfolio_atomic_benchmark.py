import unittest
from cite_refinery.portfolio_atomic_benchmark import compare, trivial_baseline

class AtomicBaselineTests(unittest.TestCase):
    def test_baseline_can_get_perfect_score_without_model(self):
        tasks=[
            {"id":"a","task_kind":"source_attribution","allowed_evidence_ids":["node"],
             "reference_quote":"original maintainer repository declaration statement",
             "evidence_text":"original maintainer repository declaration statement"},
            {"id":"b","task_kind":"requires_independent_evidence","allowed_evidence_ids":["node"]},
        ]
        model={"results":[{"id":"a","contract_valid":False},{"id":"b","contract_valid":True}]}
        score=compare({"tasks":tasks},model)
        self.assertEqual(score["trivial_baseline_contract_valid"],2)
        self.assertEqual(score["model_contract_valid"],1)
        self.assertFalse(score["benchmark_is_discriminating"])

    def test_baseline_abstains_without_claiming_real_world_negation(self):
        task={"id":"none","task_kind":"requires_independent_evidence"}
        self.assertEqual(trivial_baseline(task)["verdict"],"insufficient")

    def test_missing_model_result_rejected(self):
        with self.assertRaises(AssertionError):
            compare({"tasks":[{"id":"x","task_kind":"requires_independent_evidence"}]},
                    {"results":[]})

if __name__=="__main__":
    unittest.main()
