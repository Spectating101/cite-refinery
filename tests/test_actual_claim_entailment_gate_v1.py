"""Source-bound contract tests; injected logits are NOT reported as NLI results."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import math
import unittest

from cite_refinery.actual_claim_entailment_gate import (
    _blind_pairs,_check_source,_softmax,_triage,evaluate,SCHEMA,SWAPS,
)

ROOT=Path(__file__).resolve().parents[1]
CASES=ROOT/"research_materials/runtime_trials/fulltext_dog_20261020/benchmark_cases.json"


class ActualSourceNliGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(CASES.read_text("utf-8"))

    def test_real_existing_21_casebook_keeps_all_four_difficult_labels(self):
        records,by_id=_check_source(self.data)
        self.assertEqual(len(records),21)
        self.assertEqual(len(by_id),21)
        self.assertEqual(sum(x["expected"]=="entailed" for x in records),8)
        self.assertEqual(sum(x["expected"]=="contradicted" for x in records),8)
        self.assertEqual(sum(x["expected"]=="overreach" for x in records),3)
        self.assertEqual(sum(x["expected"]=="unresolved" for x in records),2)

    def test_model_input_pairs_exclude_golds_and_source_id_leak(self):
        pairs,by_id=_blind_pairs(self.data)
        self.assertEqual(len(pairs),25)
        self.assertEqual(len({x["id"] for x in pairs}),25)
        self.assertEqual(len(SWAPS),4)
        self.assertTrue(all(set(x)=={"id","claim","evidence","source_kind",
                                    "source_evidence_sha256"} for x in pairs))
        self.assertEqual(len([p for p in pairs if p["id"].startswith("SWAP-")]),4)
        self.assertNotIn("gold_reason",json.dumps(pairs))
        self.assertNotIn("expected",json.dumps(pairs))
        for identity,source_claim,source_passage in SWAPS:
            pair=next(x for x in pairs if x["id"]==identity)
            self.assertEqual(pair["claim"],by_id[source_claim]["claim"])
            self.assertEqual(pair["evidence"],by_id[source_passage]["evidence"])
            self.assertNotEqual(source_claim,source_passage)

    def test_predeclared_abstention_and_candidate_promotion_boundary(self):
        supported,_=_triage([-3,5,-2])
        contradicted,_=_triage([5,-3,-2])
        uncertain,_=_triage([1,1,1])
        neutral,_=_triage([-3,-3,6])
        self.assertEqual(supported,"candidate_supported_requires_original_source_review")
        self.assertEqual(contradicted,"candidate_contradicted_requires_original_source_review")
        self.assertEqual(uncertain,"abstain_needs_original_source_review")
        self.assertEqual(neutral,"abstain_needs_original_source_review")
        with self.assertRaisesRegex(ValueError,"finite"):
            _softmax([float("nan"),1,2])
        with self.assertRaisesRegex(ValueError,"finite"):
            _softmax([0,1])

    def test_deliberately_unsafe_fake_predictions_are_counted_not_hidden(self):
        # A fake system claiming everything is entailed must visibly incur
        # 13 false candidate approvals: 8 contradictions, 3 overreach,
        # 2 unresolved, plus 4 evidence-swapped negative controls = 17.
        def always_yes(pairs):
            return [[-7,9,-7] for _ in pairs]
        r=evaluate(self.data,infer=always_yes,model_name="TEST_ONLY_ALWAYS_ENTAILS")
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["counts"]["candidate_support"],25)
        self.assertEqual(r["counts"]["unsafe_false_candidate_support"],17)
        self.assertEqual(r["counts"]["true_supported_candidate"],8)
        self.assertEqual(r["counts"]["source_swaps_abstained"],0)
        self.assertEqual(r["counts"]["unresolved_abstained"],0)
        self.assertEqual(r["model_revision"],"injected_test_only")
        self.assertFalse(r["support_or_contradiction_automatically_promoted"])

    def test_testonly_correct_logits_do_not_count_as_verified_science(self):
        def test_only(pairs):
            answer=[]
            original={x["id"]:x for x in self.data["cases"]}
            for p in pairs:
                expected=original.get(p["id"],{}).get("expected")
                answer.append(
                    ([9,-7,-7] if expected=="contradicted" else
                     [-7,9,-7] if expected=="entailed" else
                     [-7,-7,9]))
            return answer
        r=evaluate(self.data,infer=test_only,model_name="TEST_ONLY_LABEL_CONSTRUCTION")
        c=r["counts"]
        self.assertEqual(c["true_supported_candidate"],8)
        self.assertEqual(c["correct_contradiction_candidate"],8)
        self.assertEqual(c["unsafe_false_candidate_support"],0)
        self.assertEqual(c["unresolved_abstained"],2)
        self.assertEqual(c["overreach_abstained"],3)
        self.assertEqual(c["source_swaps_abstained"],4)
        self.assertEqual(r["actual_source_claim_support_independently_human_validated"],False)
        self.assertEqual(r["cross_layer_claims_created"],0)
        self.assertFalse(r["functional_code_suitability_verified"])
        self.assertFalse(r["independent_gold_labels_available"])

    def test_invalid_source_identity_or_gold_regression_rejected(self):
        invalid=deepcopy(self.data)
        invalid["source_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"original article"):
            _check_source(invalid)
        invalid=deepcopy(self.data)
        invalid["cases"][0]["expected"]="overreach"
        with self.assertRaisesRegex(ValueError,"labels"):
            _check_source(invalid)
        invalid=deepcopy(self.data)
        invalid["cases"][1]["id"]="B01"
        with self.assertRaisesRegex(ValueError,"duplicated"):
            _check_source(invalid)
        invalid=deepcopy(self.data)
        invalid["cases"]=invalid["cases"][:-1]
        with self.assertRaisesRegex(ValueError,"incomplete"):
            _check_source(invalid)

    def test_bad_or_incomplete_real_model_outputs_fail_closed(self):
        for fake in (
            lambda p: [[0,1,2]],
            lambda p: [[0,1,float("inf")] for _ in p],
            lambda p: [[0,1] for _ in p],
        ):
            with self.assertRaises(ValueError):
                evaluate(self.data,infer=fake,model_name="TEST_ONLY_BROKEN")

    def test_source_swap_probes_predeclared_without_gold_label_leak(self):
        pairs,_=_blind_pairs(self.data)
        swaps=[x for x in pairs if x["id"].startswith("SWAP-")]
        self.assertEqual([x["id"] for x in swaps],
                         ["SWAP-01","SWAP-02","SWAP-03","SWAP-04"])
        self.assertTrue(all("negative_control" in x["source_kind"] for x in swaps))


if __name__=="__main__":
    unittest.main()
