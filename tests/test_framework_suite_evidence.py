"""Scoped framework evidence must never turn into a full app or business claim."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import json
import unittest

from cite_refinery.framework_suite_evidence import SCHEMA,karma,rspec,markdown
from cite_refinery.operator_conversion_gate import decide

BASE=Path(__file__).resolve().parents[1]/"research_materials/opportunity_atlas"
def read(name):return json.loads((BASE/name).read_text())

class ScopedIntegrationEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=read("framework_scoped_integration.json")
        cls.snap=read("operator_github_snapshot.json")
        cls.func=read("functional_component_trials.json")
        cls.repairs=read("repair_replace_executable_results.json")
        cls.issues=read("reported_issue_source_contracts.json")
        cls.original=read("original_component_execution.json")
        cls.now=datetime.fromisoformat(cls.snap["collected_at_utc"])

    def gate(self,source=None):
        return decide(self.snap,self.func,self.repairs,self.issues,now=self.now,
                      original_runtime=self.original,
                      framework_evidence=source if source is not None else self.report)

    def test_original_vs_patch_evidence_is_distinct(self):
        obj=self.report
        self.assertEqual(obj["schema"],SCHEMA)
        a=obj["open_food_network"];b=obj["foodsoft"]
        self.assertEqual(a["original"],{"tests":14,"failed":4,
            "original_jasmine_spec_included":True,"headless_browser_executed":True,
            "full_frontend_app_tested":False})
        self.assertEqual(a["local_candidate"]["failed"],0)
        self.assertEqual(a["original_repo_jasmine_examples"],9)
        self.assertEqual(a["new_geographic_jasmine_examples"],5)
        self.assertFalse(a["proposed_geographic_bounds_implemented_in_product_config"])
        self.assertFalse(a["production_zoom_and_viewport_verified"])
        self.assertFalse(a["candidate_complete_application_fix"])
        self.assertEqual(b["original"]["tests"],9)
        self.assertEqual(b["original"]["failed"],3)
        self.assertEqual(b["local_candidate"]["failed"],0)
        self.assertTrue(b["BigDecimal_realistic_conversion_1_7_over_1_3"])
        self.assertFalse(b["real_Rails_OrderArticle_models_used"])
        self.assertFalse(b["upstream_Rails_RSpec_suite_completed"])
        self.assertFalse(b["candidate_complete_application_fix"])
        self.assertEqual(obj["evidence"]["scoped_framework_examples_executed"],46)
        self.assertEqual(obj["evidence"]["original_source_expected_failures"],7)
        self.assertEqual(obj["evidence"]["local_candidate_failures"],0)
        self.assertFalse(obj["evidence"]["complete_Rails_or_Angular_application_suite_run"])
        self.assertFalse(obj["evidence"]["third_party_repo_modified"])
        self.assertFalse(obj["evidence"]["commercial_contract_or_revenue_verified"])
        self.assertFalse(obj["evidence"]["native_graph_status_promoted"])
        self.assertFalse(obj["evidence"]["research_holdout_touched"])
        self.assertIn("full Angular frontend",markdown(obj))

    def test_karma_and_rspec_require_real_runners(self):
        with self.assertRaisesRegex(ValueError,"browser Karma"):
            karma("14 of 14 SUCCESS")
        with self.assertRaisesRegex(ValueError,"nine original"):
            karma("Chrome Headless Executed 3 of 3 SUCCESS")
        with self.assertRaisesRegex(ValueError,"RSpec"):
            rspec({"summary":{"example_count":9,"failure_count":0},"examples":[]})

    def test_conversion_routes_acknowledge_frameworks_but_not_product_fit(self):
        out=self.gate()
        rows={x["id"]:x for x in out["rows"]}
        self.assertEqual(rows["ofn_canada_map_bounds"]["route"],
                         "wire_region_and_zoom_settings_then_test_full_map")
        self.assertEqual(rows["foodsoft_order_quantity_rounding"]["route"],
                         "run_full_Rails_model_and_precision_policy_tests")
        for key in ("ofn_canada_map_bounds","foodsoft_order_quantity_rounding"):
            tech=rows[key]["technical"]
            self.assertEqual(tech["status"],"original_scoped_framework_tests_executed_full_app_blocked")
            self.assertTrue(tech["source_app_component_runtime_verified"])
            self.assertFalse(tech["full_application_test_suite_executed"])
            self.assertFalse(tech["candidate_applicability_verified"])
            self.assertFalse(rows[key]["buyer_verified"])
            self.assertFalse(rows[key]["paid_work_order_verified"])
        self.assertEqual(out["checks"]["verified_paid_contracts"],0)
        self.assertFalse(out["native_evidence_status_promoted"])

    def test_false_full_app_and_tampered_source_rejected(self):
        fake=deepcopy(self.report)
        fake["evidence"]["complete_Rails_or_Angular_application_suite_run"]=True
        with self.assertRaisesRegex(ValueError,"scoped framework"):
            self.gate(fake)
        fake=deepcopy(self.report)
        fake["source_checks"]["openfoodnetwork"]["blob"]="0"*40
        with self.assertRaisesRegex(ValueError,"source identity"):
            self.gate(fake)
        fake=deepcopy(self.report)
        fake["foodsoft"]["local_candidate"]["failed"]=1
        with self.assertRaisesRegex(ValueError,"incomplete"):
            self.gate(fake)
        fake=deepcopy(self.report)
        fake["open_food_network"]["candidate_complete_application_fix"]=True
        with self.assertRaisesRegex(ValueError,"incomplete"):
            self.gate(fake)

if __name__=="__main__":
    unittest.main()
