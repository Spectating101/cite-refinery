from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import unittest

from cite_refinery.commercial_blind_trial import (
    DEFAULT_BOOK, validate_casebook, source_packet, arm_prompt, get_plan,
    run_trial, validate_candidate,
)


def book():
    return json.loads(DEFAULT_BOOK.read_text(encoding="utf-8"))


class BlindCommercialTrialTests(unittest.TestCase):
    def test_frozen_development_casebook_is_source_equivalent(self):
        cases = validate_casebook(book())["cases"]
        self.assertEqual(len(cases), 4)
        for case in cases:
            shared = source_packet(case)
            self.assertIn(shared, arm_prompt(case, arm="atlas"))
            self.assertIn(shared, arm_prompt(case, arm="control"))
            self.assertNotIn("ATLAS RESEARCH-GATE", arm_prompt(case, arm="control"))
        plan = get_plan(book())
        self.assertEqual(plan["status"], "ready_for_authenticated_opt_in_not_executed")
        self.assertEqual(len(plan["cases"]), 4)
        self.assertTrue(all(
            row["atlas_prompt_chars"] > row["control_prompt_chars"]
            for row in plan["cases"]
        ))

    def test_invalid_casebook_cannot_claim_heldout_or_lose_sources(self):
        a = book()
        a["split"] = "sealed_held_out"
        with self.assertRaisesRegex(ValueError, "evaluation split"):
            validate_casebook(a)
        a = book()
        a["cases"][0]["evidence"][1]["id"] = a["cases"][0]["evidence"][0]["id"]
        with self.assertRaisesRegex(ValueError, "duplicated evidence"):
            validate_casebook(a)
        a = book()
        a["cases"][0]["evidence"] = []
        with self.assertRaisesRegex(ValueError, "2..10"):
            validate_casebook(a)

    def test_equal_source_ids_restricted_to_attributed_packet(self):
        one = book()["cases"][0]
        candidate = {
            "propositions": [{
                "case_id": one["case_id"], "priority": "investigate",
                "buyer_status": "problem_signal",
                "recommended_next_action": "Verify paid contributor eligibility and bug ownership",
                "rationale": "The problem is sourced; payment is not a contract.",
                "risk_flags": ["unverified rate"], "source_ids": ["ofn_issue_14924"],
            }],
            "bridges": [], "open_questions": [],
        }
        self.assertEqual(validate_candidate(candidate, one)["propositions"][0]["priority"], "investigate")
        candidate["propositions"][0]["source_ids"] = ["fabricated_source"]
        with self.assertRaisesRegex(ValueError, "source IDs"):
            validate_candidate(candidate, one)

    def test_real_model_interfaces_blind_arm_names_from_judge(self):
        cases = book()
        calls = []
        def model(prompt, *, provider, model, timeout_seconds):
            calls.append((provider, model, prompt))
            case_id = re.search(r"CASE: ([a-z0-9-]+)", prompt).group(1)
            if "ANALYSIS X (origin hidden)" in prompt:
                self.assertNotIn("ATLAS RESEARCH-GATE OUTPUT", prompt)
                self.assertNotIn("NO PLATFORM OUTPUT", prompt)
                return {"raw": {
                    "propositions": [{"case_id": case_id, "winner": "tie",
                                     "reason": "Neither document alone proves a paying buyer.",
                                     "unsupported_claims_X": [], "unsupported_claims_Y": [],
                                     "next_action_difference": "none"}],
                    "bridges": [], "open_questions": [],
                }}
            source_ids = re.findall(r"\[([a-z][a-z0-9_]+)\]", prompt)
            return {"raw": {
                "propositions": [{
                    "case_id": case_id, "priority": "investigate", "buyer_status": "problem_signal",
                    "recommended_next_action": "Check the real buyer and practical delivery costs",
                    "rationale": "Technical documentation alone cannot establish willingness to pay.",
                    "risk_flags": ["unverified buyer"], "source_ids": source_ids[:1],
                }],
                "bridges": [], "open_questions": [],
            }}
        result = run_trial(
            cases, proposer_provider="antigravity", proposer_model="gemini-3.8-flash-medium",
            judge_provider="antigravity", judge_model="claude-opus-5-5-medium",
            seed=412, max_cases=1, invoke=model,
        )
        self.assertEqual(len(calls), 3)
        self.assertEqual(result["scored_pairs"], 1)
        self.assertEqual(result["pairwise_model_preferences"]["tie"], 1)
        self.assertIsNone(result["authoritative_gold_accuracy"])
        self.assertEqual(set(result["cases"][0]["arms"]), {"atlas", "control"})
        self.assertEqual(
            result["cases"][0]["arms"]["atlas"]["status"],
            "completed",
        )

    def test_same_family_judge_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "distinct model families"):
            run_trial(
                book(), proposer_provider="antigravity", proposer_model="gemini-3.8-flash-medium",
                judge_provider="antigravity", judge_model="gemini-4-argon-medium",
                seed=2, max_cases=1,
            )

    def test_failed_or_unavailable_inference_never_creates_score(self):
        def unavailable(prompt, **kwargs):
            raise RuntimeError("test-only fake failure; do not expose output")
        result = run_trial(
            book(), proposer_provider="antigravity", proposer_model="gemini-3.8-flash-medium",
            judge_provider="antigravity", judge_model="claude-opus-5-5-medium",
            seed=4, max_cases=1, invoke=unavailable,
        )
        self.assertEqual(result["scored_pairs"], 0)
        self.assertEqual(result["cases"][0]["review"]["status"], "not_scored")
        self.assertTrue(all(
            val["status"] == "failed"
            for val in result["cases"][0]["arms"].values()
        ))
        self.assertEqual(result["pairwise_model_preferences"]["atlas"], 0)


if __name__ == "__main__":
    unittest.main()
