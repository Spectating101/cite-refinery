"""Do not confuse three LLM opinions with three verified experiments."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from cite_refinery.cross_model_evidence_check import compare,markdown

ROOT=Path(__file__).resolve().parents[1]/"research_materials/opportunity_atlas"

def trials():
    return json.loads((ROOT/"functional_component_trials.json").read_text(encoding="utf-8"))

def review(verdict="reproduced_accounting_defect",expected=-10_000_000,observed=0):
    return {
        "defect_verdict":verdict,
        "expected_positive_fee_profit_delta_usd":expected,
        "actual_positive_fee_profit_delta_usd":observed,
        "scope_boundary":"Synthetic accounting review only, not a commercial plant profitability finding."
    }

class CrossModelEvidenceCheckTests(unittest.TestCase):
    def test_saved_real_bounded_reviews_are_non_authoritative(self):
        saved=json.loads((ROOT/"multimodel_fee_review.json").read_text())
        self.assertEqual(saved["schema"],"cite_refinery.cross_model_evidence_diagnostic.v1")
        self.assertEqual(saved["distinct_model_families"],["claude","gemini"])
        self.assertEqual(len(saved["model_reviews"]),3)
        self.assertTrue(saved["all_reviews_agree_with_executed_reference"])
        self.assertEqual(saved["reference_expected_delta_usd"],-10_000_000)
        self.assertEqual(saved["reference_observed_delta_usd"],0)
        self.assertFalse(saved["native_graph_status_promoted"])
        self.assertFalse(saved["research_holdout_touched"])
        self.assertTrue(all(not x["model_is_independent_executor"] for x in saved["model_reviews"]))
        self.assertIn("same provider family",markdown(saved))

    def test_disagreement_not_majority_promoted(self):
        names={
            "gemini-4-argon-medium":review(),
            "claude-opus-5-5-medium":review(verdict="no_defect"),
            "claude-sonnet-5-5-medium":review(expected=5),
        }
        result=compare(trials(),names)
        self.assertEqual(sum(x["diagnostic_agreement"] for x in result["model_reviews"]),1)
        self.assertFalse(result["all_reviews_agree_with_executed_reference"])
        self.assertFalse(result["native_graph_status_promoted"])

    def test_wrong_or_guessed_model_rejected(self):
        with self.assertRaisesRegex(ValueError,"catalog"):
            compare(trials(),{"gemini-4-argon":review(),"claude-opus-5-5-medium":review()})

    def test_source_invariant_required(self):
        t=trials()
        for probe in t["probes"]:
            if "EverBatt" in probe["asset_id"]:
                for case in probe["cases"]:
                    if case["name"]=="direct_positive_fee_accounting":
                        case["status"]="not_tested"
        with self.assertRaisesRegex(ValueError,"actually exercised"):
            compare(t,{"gemini-4-argon-medium":review(),"claude-opus-5-5-medium":review()})
        t=trials();t["graph_status_promotion_allowed"]=True
        with self.assertRaisesRegex(ValueError,"promoted"):
            compare(t,{"gemini-4-argon-medium":review(),"claude-opus-5-5-medium":review()})

if __name__=="__main__":
    unittest.main()
