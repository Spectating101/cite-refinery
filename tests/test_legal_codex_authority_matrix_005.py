"""Fail-closed dated office authority tests. These never identify a perpetrator."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from cite_refinery.legal_codex_authority_matrix import evaluate, validate

DATA = (Path(__file__).resolve().parents[1] /
        "examples/legal_codex_procurement_authority_2018_2021.json")


class ProcurementAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads(DATA.read_text(encoding="utf-8"))

    def by_id(self, output):
        return {x["decision_id"]: x for x in output["decisions"]}

    def test_2018_vs_2021_role_article_changes(self):
        results = self.by_id(evaluate(self.bundle))
        old = results["q_2020_chrome_spec"]
        self.assertEqual(len(old["possible_statutory_roles"]), 1)
        self.assertEqual(old["possible_statutory_roles"][0]["article"], "Pasal 11(1)(b)")
        self.assertEqual(old["possible_statutory_roles"][0]["statutory_role"], "PPK")
        new = results["q_2021_hps"]
        self.assertEqual(len(new["possible_statutory_roles"]), 1)
        self.assertEqual(new["possible_statutory_roles"][0]["article"], "Pasal 11(1)(e)")
        self.assertTrue(all(x["actual_authority_holder"] is None for x in results.values()))

    def test_2021_year_does_not_hide_amendment_boundary(self):
        results = self.by_id(evaluate(self.bundle))
        q = results["q_2021_reused_study"]
        self.assertEqual(q["version_uncertainty"], "amendment_boundary_intersects_date")
        self.assertEqual({x["article"] for x in q["possible_statutory_roles"]},
                         {"Pasal 11(1)(b)", "Pasal 11(1)(c)"})

    def test_person_assignments_are_zero(self):
        result = evaluate(self.bundle)
        self.assertEqual(result["appointment_records_verified"], 0)
        self.assertEqual(result["identity_assignments_inferred"], 0)
        self.assertFalse(result["publication_authorized"])
        self.assertTrue(all(row["person_officially_linked_to_procurement"] is False
                            and row["legal_violation_established"] is False
                            for row in result["decisions"]))

    def test_invented_kpa_person_assignment_is_blocked(self):
        self.bundle["person_assignments"] = [{
            "name": "Example government official", "role": "PPK",
            "claimed_appointment": "unknown",
        }]
        with self.assertRaisesRegex(ValueError, "signed appointment"):
            validate(self.bundle)

    def test_missing_supplier_selection_role_abstains(self):
        x = self.by_id(evaluate(self.bundle))["q_vendor_selection"]
        self.assertEqual(x["possible_statutory_roles"], [])
        self.assertEqual(x["version_uncertainty"], "no_matching_candidate_rule")

    def test_amendment_cannot_be_applied_to_2020(self):
        old = self.by_id(evaluate(self.bundle))["q_2020_chrome_spec"]
        self.assertNotIn("r21_ppk_spec",
                         [x["role_rule_id"] for x in old["possible_statutory_roles"]])

    def test_fabricated_statute_capture_rejected(self):
        self.bundle["legal_sources"][0]["original_bytes_captured"] = True
        with self.assertRaisesRegex(ValueError, "original source capture"):
            validate(self.bundle)

    def test_fabricated_named_authority_rejected(self):
        self.bundle["decision_questions"][0]["named_authority_holder"] = "a named defendant"
        with self.assertRaisesRegex(ValueError, "named authority"):
            validate(self.bundle)

    def test_unsupported_legal_scope_rejected(self):
        self.bundle["role_rules"][0]["scope"] = "all_ministry_decisions_automatically"
        with self.assertRaisesRegex(ValueError, "unsupported statutory scope"):
            validate(self.bundle)

    def test_calendar_precision_checked(self):
        self.bundle["decision_questions"][1]["event_date_precision"] = "day"
        with self.assertRaises(ValueError):
            validate(self.bundle)

    def test_date_order_does_not_depend_on_question_order(self):
        expected = evaluate(self.bundle)
        self.bundle["decision_questions"].reverse()
        self.assertEqual(expected, evaluate(self.bundle))


if __name__ == "__main__":
    unittest.main()
