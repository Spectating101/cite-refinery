"""Frozen original source runtime trials and non-authoritative conversion overlay."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import unittest

from cite_refinery.pinned_original_component_trials import (
    PINS,SCHEMA,git_blob,patch_source,_validate,markdown,
)
from cite_refinery.operator_conversion_gate import decide

ROOT=Path(__file__).resolve().parents[1]/"research_materials/opportunity_atlas"
def fixture(name):return json.loads((ROOT/name).read_text(encoding="utf-8"))

class OriginalComponentTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record=fixture("original_component_execution.json")
        cls.snapshot=fixture("operator_github_snapshot.json")
        cls.functional=fixture("functional_component_trials.json")
        cls.repair=fixture("repair_replace_executable_results.json")
        cls.contracts=fixture("reported_issue_source_contracts.json")
        cls.now=datetime.fromisoformat(cls.snapshot["collected_at_utc"])

    def test_pinned_original_functions_executed_not_full_app(self):
        r=self.record
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["original_source_pins"],PINS)
        self.assertEqual(len(r["cases"]),2)
        self.assertTrue(r["limitations"]["actual_original_functions_executed"])
        for k in ("full_angular_app_or_browser_tested","rails_database_or_complete_suite_tested",
                  "all_proposed_repair_requirements_passed","third_party_repository_modified",
                  "published_external_patches","paid_operator_demand_verified",
                  "commercial_conversion_achieved","native_graph_status_promoted",
                  "research_holdout_touched"):
            self.assertFalse(r["limitations"][k])
        self.assertIn("multi-outlier regression",markdown(r))

    def test_ofn_original_reproduced_and_naive_median_is_not_full_fix(self):
        case=self.record["cases"][0]
        self.assertEqual(case["id"],"ofn_canada_map_bounds")
        orig=case["original_execution"]
        candidate=case["temporary_candidate_execution"]
        self.assertTrue(orig["upstream_source_compiled_and_executed"])
        self.assertTrue(candidate["upstream_source_compiled_and_executed"])
        self.assertTrue(orig["all_standard_regressions_pass"])
        self.assertTrue(candidate["all_standard_regressions_pass"])
        self.assertFalse(orig["outlier_regression_pass"])
        self.assertTrue(candidate["outlier_regression_pass"])
        self.assertFalse(candidate["multiple_outliers_regression_pass"])
        self.assertFalse(case["candidate_zoom_and_geographic_bounds_verified"])
        center=next(x for x in orig["validations"] if
                    x["name"]=="four_points_with_bad_geocode_actual_center")
        self.assertEqual(center["actual"],19)
        median=next(x for x in candidate["validations"] if
                    x["name"]=="four_points_with_bad_geocode_actual_center")
        self.assertEqual(median["actual"],50)
        self.assertFalse(orig["full_angular_app_executed"])
        self.assertFalse(candidate["original_application_test_suite_executed"])

    def test_foodsoft_original_ruby_branch_regressions(self):
        case=self.record["cases"][1]
        self.assertEqual(case["id"],"foodsoft_order_quantity_rounding")
        original=case["original_execution"]
        candidate=case["temporary_candidate_execution"]
        self.assertEqual(original["ruby_version"],"3.3.12")
        self.assertEqual(original["case_count"],7)
        self.assertTrue(original["upstream_ruby_helper_loaded_and_executed"])
        self.assertFalse(original["equal_ordered_and_received_precision_regressions_pass"])
        self.assertTrue(candidate["equal_ordered_and_received_precision_regressions_pass"])
        self.assertTrue(original["genuine_difference_regressions_pass"])
        self.assertTrue(candidate["genuine_difference_regressions_pass"])
        self.assertFalse(case["rails_application_integration_verified"])
        self.assertFalse(candidate["rails_app_executed"])
        self.assertFalse(candidate["rails_test_suite_executed"])

    def test_candidate_edit_anchor_requires_inspected_source(self):
        with self.assertRaisesRegex(ValueError,"cannot safely patch"):
            patch_source("openfoodnetwork","something entirely different")
        with self.assertRaisesRegex(ValueError,"cannot safely patch"):
            patch_source("foodsoft","x.round(3) == group_orders_sum_quantity")
        with self.assertRaisesRegex(ValueError,"unverified"):
            patch_source("other_repo","any")
        self.assertEqual(len(git_blob(b"x")),40)
        source="      minimumAngle + (distanceBetweenMinimumAndMaximum / 2)"
        target=patch_source("openfoodnetwork",source)
        self.assertIn("sortedAngles",target)

    def test_manipulated_or_promoted_runtime_rejected(self):
        a,b=[deepcopy(x) for x in self.record["cases"]]
        _validate(a["original_execution"],a["temporary_candidate_execution"],
                  b["original_execution"],b["temporary_candidate_execution"])
        a["temporary_candidate_execution"]["multiple_outliers_regression_pass"]=True
        with self.assertRaisesRegex(ValueError,"known limitations"):
            _validate(a["original_execution"],a["temporary_candidate_execution"],
                      b["original_execution"],b["temporary_candidate_execution"])
        a=self.record["cases"][0]
        x=deepcopy(b["temporary_candidate_execution"])
        x["rails_app_executed"]=True
        with self.assertRaisesRegex(ValueError,"cannot claim"):
            _validate(a["original_execution"],a["temporary_candidate_execution"],
                      b["original_execution"],x)

    def test_conversion_uses_executed_evidence_without_paying_contract(self):
        j=decide(self.snapshot,self.functional,self.repair,self.contracts,
                 now=self.now,original_runtime=self.record)
        lookup={x["id"]:x for x in j["rows"]}
        self.assertEqual(lookup["ofn_canada_map_bounds"]["route"],
                         "complete_viewport_solution_then_integration_test")
        self.assertEqual(lookup["foodsoft_order_quantity_rounding"]["route"],
                         "run_original_app_integration_before_contribution")
        for id in ("ofn_canada_map_bounds","foodsoft_order_quantity_rounding"):
            row=lookup[id]
            self.assertTrue(row["technical"]["source_app_component_runtime_verified"])
            self.assertFalse(row["technical"]["full_original_application_test_suite_executed"])
            self.assertFalse(row["buyer_verified"])
            self.assertFalse(row["paid_work_order_verified"])
        self.assertEqual(j["checks"]["verified_paid_contracts"],0)
        self.assertFalse(j["native_evidence_status_promoted"])

    def test_false_integrated_or_upstream_identity_forbidden(self):
        tampered=deepcopy(self.record)
        tampered["limitations"]["rails_database_or_complete_suite_tested"]=True
        with self.assertRaisesRegex(ValueError,"complete app"):
            decide(self.snapshot,self.functional,self.repair,self.contracts,
                   now=self.now,original_runtime=tampered)
        tampered=deepcopy(self.record)
        tampered["original_source_pins"]["openfoodnetwork"]["blob"]="0"*40
        with self.assertRaisesRegex(ValueError,"mismatches"):
            decide(self.snapshot,self.functional,self.repair,self.contracts,
                   now=self.now,original_runtime=tampered)

if __name__=="__main__":
    unittest.main()
