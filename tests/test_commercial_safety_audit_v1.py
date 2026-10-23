"""Independent-of-model-judge, offline sanity checks for frozen commercial trial."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from cite_refinery.business_workbench import ROOT
from cite_refinery.commercial_blind_trial import RESULT, source_packet
from cite_refinery.commercial_guardrails import digest
from cite_refinery.commercial_safety_audit import audit_trial, validate_rubric

BASE = ROOT / "research_materials/opportunity_conversion"
BOOK = BASE / "blind_casebook_prospective_fresh_v1.json"
RULES = BASE / "fresh_safety_rubric_v1.json"


def sources():
    return json.loads(BOOK.read_text(encoding="utf-8")), json.loads(RULES.read_text(encoding="utf-8"))


def candidate(case, *, priority, status, cite):
    return {
        "propositions": [{
            "case_id": case["case_id"], "priority": priority,
            "buyer_status": status,
            "recommended_next_action": "Do not claim this bounty without owner authorization and payment verification",
            "rationale": "Original issue state and proof of buyer commitment are not sufficient for contract recognition.",
            "risk_flags": ["No verified buyer", "No authenticated payment"],
            "source_ids": cite,
        }],
        "bridges": [],
        "open_questions": ["Are current assignment and issuer funding independently authenticated?"],
    }


def synthetic_receipt(book, rules):
    items = []
    for case, rule in zip(book["cases"], rules["cases"]):
        payload = candidate(case, priority=rule["allowed_priorities"][0],
                            status="problem_signal", cite=rule["must_cite_ids"])
        items.append({
            "case_id": case["case_id"],
            "source_sha256": hashlib.sha256(source_packet(case).encode("utf-8")).hexdigest(),
            "source_ids": [x["id"] for x in case["evidence"]],
            "arms": {
                "atlas": {"status": "completed", "response": deepcopy(payload)},
                "control": {"status": "completed", "response": deepcopy(payload)},
            },
            "review": {"status": "model_judged_not_human_gold",
                       "preferred_arm": "atlas"},
        })
    return {
        "schema": RESULT, "split": book["split"],
        "casebook_sha256": digest(book), "scored_pairs": len(items), "cases": items,
        "synthetic_test_fixture_not_real_inference": True,
    }


class FrozenCommercialSafetyAuditTests(unittest.TestCase):
    def setUp(self):
        self.book, self.rules = sources()
        self.receipt = synthetic_receipt(self.book, self.rules)

    def test_frozen_rubric_with_direct_original_issue_links(self):
        self.assertEqual(validate_rubric(self.book, self.rules), self.rules)
        self.assertEqual(len(self.rules["cases"]), 3)
        for case, rule in zip(self.book["cases"], self.rules["cases"]):
            evidence = {row["url"] for row in case["evidence"]}
            self.assertIn(rule["original_issue_url"], evidence)
            self.assertEqual(rule["max_buyer_status"], "problem_signal")
            self.assertIn("reject", rule["allowed_priorities"])

    def test_safe_structured_decisions_still_not_income_or_gold(self):
        out = audit_trial(self.book, self.rules, self.receipt)
        self.assertEqual(out["arms_audited"], 6)
        self.assertEqual(out["counts"], {"safe": 6, "unsafe": 0, "unscored": 0})
        self.assertEqual(out["rubric_authority"], "researcher_authored_original_issue_snapshot_not_independently_adjudicated")
        self.assertIsNone(out["independent_human_gold_accuracy"])
        self.assertIsNone(out["verified_customer_revenue"])
        self.assertIsNone(out["comparative_model_superiority"])
        # The test fixture is deliberately marked synthetic; never infer a model win.
        self.assertNotIn("model_win_rate", out)

    def test_hallucinated_funded_customer_is_flagged_despite_model_judge_win(self):
        r = deepcopy(self.receipt)
        for row in r["cases"]:
            row["arms"]["atlas"]["response"]["propositions"][0]["buyer_status"] = "funded_or_signed"
        result = audit_trial(self.book, self.rules, r)
        self.assertEqual(result["counts"]["unsafe"], 3)
        self.assertEqual(result["counts"]["safe"], 3)
        self.assertTrue(all("unsupported_buyer_commitment" in x["atlas"]["violations"]
                            for x in result["cases"]))
        self.assertIsNone(result["comparative_model_superiority"])

    def test_closed_and_claimed_issues_cannot_be_promoted_to_pilot(self):
        r = deepcopy(self.receipt)
        for idx in (1, 2):
            r["cases"][idx]["arms"]["atlas"]["response"]["propositions"][0]["priority"] = "pursue_pilot"
        out = audit_trial(self.book, self.rules, r)
        self.assertEqual(out["counts"]["unsafe"], 2)
        self.assertTrue(all("unsafe_priority_for_original_issue_status_or_assignment"
                            in out["cases"][i]["atlas"]["violations"] for i in (1, 2)))

    def test_citing_readme_instead_of_original_issuer_is_not_sufficient(self):
        r = deepcopy(self.receipt)
        for row in r["cases"]:
            row["arms"]["atlas"]["response"]["propositions"][0]["source_ids"] = [row["source_ids"][-1]]
        out = audit_trial(self.book, self.rules, r)
        self.assertEqual(out["counts"]["unsafe"], 3)
        self.assertTrue(all("pivotal_original_issue_not_cited" in x["atlas"]["violations"]
                            for x in out["cases"]))

    def test_failed_model_arm_is_unscored_not_loss_or_safe(self):
        r = deepcopy(self.receipt)
        r["cases"][0]["arms"]["atlas"] = {"status": "failed", "error_type": "LLMUnavailable"}
        result = audit_trial(self.book, self.rules, r)
        self.assertEqual(result["counts"], {"safe": 5, "unsafe": 0, "unscored": 1})
        self.assertEqual(result["cases"][0]["atlas"]["status"], "unscored")
        self.assertIsNone(result["comparative_model_superiority"])

    def test_reject_tampering_source_hash_casebook_and_case_order(self):
        bad = deepcopy(self.receipt)
        bad["cases"][0]["source_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "source fingerprint"):
            audit_trial(self.book, self.rules, bad)
        bad = deepcopy(self.receipt)
        bad["casebook_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "frozen source"):
            audit_trial(self.book, self.rules, bad)
        bad = deepcopy(self.receipt)
        bad["cases"].reverse()
        with self.assertRaisesRegex(ValueError, "exact frozen prefix"):
            audit_trial(self.book, self.rules, bad)

    def test_bad_rubric_cannot_relax_closed_or_assigned_constraints(self):
        for index in (1, 2):
            altered = deepcopy(self.rules)
            altered["cases"][index]["allowed_priorities"].append("pursue_pilot")
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "cannot be actionable"):
                validate_rubric(self.book, altered)
        altered = deepcopy(self.rules)
        altered["authority"] = "independent_expert_gold"
        with self.assertRaisesRegex(ValueError, "researcher authorship"):
            validate_rubric(self.book, altered)
        altered = deepcopy(self.rules)
        altered["cases"][0]["must_cite_ids"] = ["invented"]
        with self.assertRaisesRegex(ValueError, "frozen packet"):
            validate_rubric(self.book, altered)
        for key, malformed in (("must_cite_ids", [["nested"]]), ("allowed_priorities", [{"key": "investigate"}])):
            altered = deepcopy(self.rules)
            altered["cases"][0][key] = malformed
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_rubric(self.book, altered)

    def test_partial_receipt_audited_without_inventing_other_cases(self):
        r = deepcopy(self.receipt)
        r["cases"] = r["cases"][:1]
        r["scored_pairs"] = 1
        result = audit_trial(self.book, self.rules, r)
        self.assertEqual(result["cases_audited"], 1)
        self.assertEqual(result["arms_audited"], 2)
        self.assertEqual(result["counts"], {"safe": 2, "unsafe": 0, "unscored": 0})


if __name__ == "__main__":
    unittest.main()
