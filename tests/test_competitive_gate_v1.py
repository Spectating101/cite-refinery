"""Tests for Issue #60 Competitive Semantic-Map Gate and cross-family enforcement."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from cite_refinery.competitive_gate import (
    COMPETITIVE_GATE_CASES,
    SCHEMA,
    build_casebook,
    cite_refinery_structural_precheck,
    evaluate_competitive_gate,
    render_markdown,
)
from cite_refinery.external_llm_runtime import model_family, require_distinct_family

ROOT = Path(__file__).resolve().parents[1]


def _perfect_critic_payload() -> dict:
    return {
        "raw": {
            "judgments": [
                {
                    "id": c["id"],
                    "verdict": c["expected_verdict"],
                    "reason": c["rationale_gold"],
                }
                for c in COMPETITIVE_GATE_CASES
            ]
        },
        "duration_ms": 1200,
    }


class CompetitiveGateTests(unittest.TestCase):
    def test_cross_family_enforcement_blocks_same_family_self_grading(self):
        self.assertEqual(model_family("codex", "gpt-6.1-sol"), "gpt")
        self.assertEqual(model_family("antigravity", "claude-opus-5-5-medium"), "claude")
        self.assertEqual(model_family("antigravity", "gemini-4-argon-medium"), "gemini")
        self.assertEqual(
            require_distinct_family("codex", "gpt-6.1-sol", "antigravity", "claude-opus-5-5-medium"),
            ("gpt", "claude"),
        )
        with self.assertRaisesRegex(ValueError, "distinct model families"):
            require_distinct_family("antigravity", "gemini-3.8-flash-medium", "antigravity", "gemini-4-argon-high")
        with self.assertRaisesRegex(ValueError, "distinct model families"):
            require_distinct_family("claude", "claude-3", "antigravity", "claude-sonnet-5-5-medium")

    def test_casebook_covers_ten_cross_domain_and_adversarial_traps(self):
        cb = build_casebook()
        self.assertEqual(cb["case_count"], 10)
        categories = {c["category"] for c in cb["cases"]}
        self.assertIn("inverse_quote_adversarial", categories)
        self.assertIn("same_publisher_fake_independence", categories)
        self.assertIn("unsupported_quantitative_leap", categories)
        self.assertIn("missing_practical_data", categories)
        self.assertIn("stale_mismatched_source_context", categories)
        self.assertIn("accurate_bounded_support", categories)
        # Verify CG04 structural precheck flags same-publisher / same-commit fake independence
        cg04 = next(c for c in cb["cases"] if c["id"] == "CG04")
        pre = cite_refinery_structural_precheck(cg04)
        self.assertIn("same_publisher_or_commit_deduplicated", pre["structural_flags"])

    def test_evaluate_competitive_gate_beats_naive_quote_baseline_and_enforces_cross_family(self):
        reviews = {
            "claude-opus-5-5-medium": _perfect_critic_payload(),
            "claude-sonnet-5-5-medium": _perfect_critic_payload(),
            "gemini-4-argon-medium": _perfect_critic_payload(),
        }
        report = evaluate_competitive_gate(
            proposer_provider="codex",
            proposer_model="gpt-6.1-sol",
            critic_reviews=reviews,
        )
        self.assertEqual(report["schema"], SCHEMA)
        self.assertTrue(report["cross_family_enforced"])
        self.assertEqual(report["critic_families"], ["claude", "gemini"])
        arm_a = report["arm_a_cite_refinery_three_layer"]
        arm_b = report["arm_b_naive_quote_baseline"]
        self.assertEqual(arm_a["exact_label_matches"], 10)
        self.assertEqual(arm_a["unsafe_false_entailments"], 0)
        self.assertEqual(arm_a["adversarial_trap_catch_rate"], "8/8")
        # Naive quote-matching baseline accepts verbatim-quoted inverse/overreach claims
        self.assertGreater(arm_b["unsafe_false_entailments"], 5)
        self.assertLess(arm_b["exact_label_matches"], arm_a["exact_label_matches"])
        md = render_markdown(report)
        self.assertIn("KEEP_CORE_NARROW_CRITICS_ABSORB_OVERLAY_CLIS", md)
        self.assertFalse(report["safety_boundaries"]["sealed_holdout_touched"])
        self.assertFalse(report["safety_boundaries"]["automatic_status_promotion_allowed"])

    def test_same_family_proposer_and_critic_rejected_in_gate(self):
        reviews = {"gemini-4-argon-medium": _perfect_critic_payload()}
        with self.assertRaisesRegex(ValueError, "distinct model families"):
            evaluate_competitive_gate(
                proposer_provider="antigravity",
                proposer_model="gemini-3.8-flash-medium",
                critic_reviews=reviews,
            )

    def test_saved_live_competitive_gate_receipt_is_valid_if_present(self):
        receipt_path = ROOT / "research_materials/opportunity_atlas/competitive_gate_issue60.json"
        if receipt_path.is_file():
            saved = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["schema"], SCHEMA)
            self.assertTrue(saved["cross_family_enforced"])
            self.assertEqual(saved["critic_families"], ["claude", "gemini"])
            self.assertEqual(saved["arm_a_cite_refinery_three_layer"]["unsafe_false_entailments"], 0)
            self.assertGreaterEqual(saved["arm_a_cite_refinery_three_layer"]["exact_label_matches"], 9)


if __name__ == "__main__":
    unittest.main()
