"""Holdout audit is source-specific, labels are never passed to inference."""
from __future__ import annotations

import json
from pathlib import Path
from unittest import TestCase
from scripts.external_semantic_holdout_benchmark_v1 import (
    BENCHMARK_CASES, grade, parse_model_output,
)
from scripts.external_semantic_binary_screen_v1 import run


ROOT=Path(__file__).resolve().parents[1]
GOLD=ROOT/"research_materials/runtime_trials/holdout_20261020/gold_labels.json"


class BlindedSemanticBenchmarkTests(TestCase):
    def test_labels_and_cases_are_separate(self):
        fixture=json.loads(GOLD.read_text())
        self.assertEqual(len(BENCHMARK_CASES),8)
        self.assertEqual(sum(r["supported"] for r in fixture["gold"].values()),4)
        self.assertEqual(set(fixture["gold"]),{x["id"] for x in BENCHMARK_CASES})
        self.assertTrue(fixture["frozen_before_model_inference"])
        for case in BENCHMARK_CASES:
            self.assertNotIn("supported",case)
            self.assertTrue(case["claim"] and case["source"])
        self.assertEqual(len({x["source"] for x in BENCHMARK_CASES}),4)

    def test_binary_classification_counts_fp_fn(self):
        fixture=json.loads(GOLD.read_text())["gold"]
        rows=[{**x,"passage":"The source passage discusses only the described issue."}
              for x in BENCHMARK_CASES]
        response={"results":[{"id":x["id"],"supported":True,"quote":""}
                             for x in BENCHMARK_CASES]}
        data=grade(rows,{"response":json.dumps(response)},fixture)
        self.assertEqual(data["score"]["true_positive"],4)
        self.assertEqual(data["score"]["false_positive"],4)
        self.assertEqual(data["score"]["accuracy_over_8"],.5)

    def test_invalid_outputs_do_not_count_as_correct(self):
        fixture=json.loads(GOLD.read_text())["gold"]
        rows=[{**x,"passage":"Only a test passage."} for x in BENCHMARK_CASES]
        result=grade(rows,{"response":json.dumps({"results":[{"id":"WMO-context","supported":"yes","quote":""}]})},fixture)
        self.assertEqual(result["score"]["missing_or_invalid"],8)
        mapped,error=parse_model_output("not-json")
        self.assertFalse(mapped)
        self.assertIsNotNone(error)

    def test_literal_quote_requires_source_substring(self):
        fixture=json.loads(GOLD.read_text())["gold"]
        rows=[{**x,"passage":"A verifiable description of what this source reports."}
              for x in BENCHMARK_CASES]
        response={"results":[{"id":x["id"],"supported":fixture[x["id"]]["supported"],
                              "quote":"a quotation that is not in the source"}
                             for x in BENCHMARK_CASES]}
        result=grade(rows,{"response":json.dumps(response)},fixture)
        self.assertEqual(result["score"]["false_quotes"],8)
        self.assertEqual(result["score"]["verbatim_supported_quotes"],0)


if __name__=="__main__":
    import unittest; unittest.main()
