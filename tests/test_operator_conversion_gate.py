"""External problem reports, executable repairs, and business authority stay distinct."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import unittest

from cite_refinery.operator_conversion_gate import decide,markdown,CASES
from cite_refinery.reported_issue_contracts import evaluate_source,CASES as SOURCE_CASES

ROOT=Path(__file__).resolve().parents[1]/"research_materials/opportunity_atlas"
def load(name):
    return json.loads((ROOT/name).read_text(encoding="utf-8"))

class OperatorConversionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot=load("operator_github_snapshot.json")
        cls.functional=load("functional_component_trials.json")
        cls.repair=load("repair_replace_executable_results.json")
        cls.contracts=load("reported_issue_source_contracts.json")
        cls.time=datetime.fromisoformat(cls.snapshot["collected_at_utc"])

    def evaluation(self,snapshot=None,functional=None,repair=None,contracts=None,now=None):
        return decide(
            snapshot if snapshot is not None else self.snapshot,
            functional if functional is not None else self.functional,
            repair if repair is not None else self.repair,
            contracts if contracts is not None else self.contracts,
            now=now if now is not None else self.time,
        )

    def test_real_github_snapshot_routes_and_no_paid_proof(self):
        report=self.evaluation()
        self.assertEqual(report["schema"],"cite_refinery.operator_conversion_gate.v1")
        self.assertEqual(len(report["rows"]),5)
        self.assertEqual(len(CASES),5)
        self.assertEqual(report["checks"]["source_backed_open_public_issues"],2)
        self.assertEqual(report["checks"]["scratch_only_technical_repairs"],2)
        self.assertEqual(report["checks"]["verified_paid_contracts"],0)
        self.assertEqual(report["checks"]["verified_revenue"],0)
        self.assertEqual(report["checks"]["approved_external_reuse_or_contribution"],0)
        by_id={x["id"]:x for x in report["rows"]}
        self.assertEqual(by_id["ofn_canada_map_bounds"]["route"],
                         "reproduce_public_maintainer_issue")
        self.assertEqual(by_id["foodsoft_order_quantity_rounding"]["route"],
                         "reproduce_public_maintainer_issue")
        self.assertEqual(by_id["co2_yaml_and_license"]["route"],
                         "license_and_deployment_blocked")
        self.assertEqual(by_id["flood_nan_priority"]["route"],
                         "propose_opt_in_upstream_contribution")
        self.assertEqual(by_id["lfp_positive_gate_fee"]["route"],
                         "propose_opt_in_upstream_contribution")
        self.assertEqual(len(by_id["co2_yaml_and_license"]["source_issue_urls"]),1)
        self.assertIn("/pull/1",by_id["co2_yaml_and_license"]["source_issue_urls"][0])
        for row in report["rows"]:
            self.assertFalse(row["buyer_verified"])
            self.assertFalse(row["paid_work_order_verified"])
            self.assertFalse(row["maintainer_permission_or_interest_verified"])
            self.assertFalse(row["license_rights_review_completed"])
            self.assertFalse(row["commercial_unit_economics_verified"])
            self.assertFalse(row["economic_capture_realized"])
        self.assertFalse(report["native_evidence_status_promoted"])
        self.assertFalse(report["research_holdout_touched"])
        self.assertIn("not a revenue pipeline",markdown(report))

    def test_two_source_pinned_issue_analogs_not_original_apps(self):
        report=self.evaluation()
        by={x["id"]:x for x in report["rows"]}
        for name in ("ofn_canada_map_bounds","foodsoft_order_quantity_rounding"):
            tech=by[name]["technical"]
            self.assertEqual(tech["status"],"source_pinned_arithmetic_analog_requires_runtime_test")
            self.assertFalse(tech["original_application_executed"])
            self.assertFalse(tech["deployed_fit_verified"])
            self.assertTrue(tech["synthetic_result_reproduced"])
            self.assertEqual(len(tech["source_blob_sha"]),40)
        source_by={r["id"]:r for r in self.contracts["cases"]}
        m=source_by["ofn_canada_map_bounds"]["reproduction"]
        self.assertEqual(m["without_outlier_latitude"],51)
        self.assertEqual(m["with_outlier_latitude"],19)
        v=source_by["foodsoft_order_quantity_rounding"]["reproduction"]
        self.assertEqual(v["rounded_order_quantity"],"1.308")
        self.assertFalse(v["asymmetric_original_equality"])
        self.assertTrue(v["symmetrically_rounded_equality"])

    def test_issue_closed_or_stale_does_not_make_current_demand(self):
        snapshot=deepcopy(self.snapshot)
        snapshot["repositories"]["foodcoops/foodsoft"]["issues"]["1368"]["state"]="closed"
        report=self.evaluation(snapshot=snapshot)
        row=next(x for x in report["rows"] if x["id"]=="foodsoft_order_quantity_rounding")
        self.assertFalse(row["public_maintainer_issue_open"])
        self.assertEqual(row["route"],"research_candidate_unready")
        self.assertEqual(report["checks"]["source_backed_open_public_issues"],1)
        report=self.evaluation(now=self.time+timedelta(days=15))
        self.assertTrue(report["source_snapshot_stale"])
        self.assertEqual(report["checks"]["source_backed_open_public_issues"],0)
        self.assertTrue(all(row["route"]=="refresh_public_source_before_contact"
                            for row in report["rows"]))
        self.assertFalse(report["native_evidence_status_promoted"])

    def test_wrong_issue_pr_and_tampered_source_blocked(self):
        snapshot=deepcopy(self.snapshot)
        snapshot["repositories"]["openfoodfoundation/openfoodnetwork"]["issues"]["14924"]["url"]=(
            "https://github.com/openfoodfoundation/openfoodnetwork/pull/14924")
        with self.assertRaisesRegex(ValueError,"independent issue"):
            self.evaluation(snapshot=snapshot)
        contracts=deepcopy(self.contracts)
        contracts["cases"][0]["source_git_blob_sha"]="0"*40
        with self.assertRaisesRegex(ValueError,"source-checked issue"):
            self.evaluation(contracts=contracts)
        contracts=deepcopy(self.contracts)
        contracts["commercial_revenue_verified"]=True
        with self.assertRaisesRegex(ValueError,"promoted"):
            self.evaluation(contracts=contracts)
        snapshot=deepcopy(self.snapshot)
        snapshot["collected_at_utc"]=(self.time+timedelta(days=2)).isoformat()
        with self.assertRaisesRegex(ValueError,"future"):
            self.evaluation(snapshot=snapshot)
        with self.assertRaisesRegex(ValueError,"timezone"):
            self.evaluation(now=datetime(2026,10,21))

    def test_tampered_local_repair_and_repo_identity_rejected(self):
        repair=deepcopy(self.repair)
        repair["domains"][0]["upstream_source_sha"]="0"*40
        with self.assertRaisesRegex(ValueError,"revision"):
            self.evaluation(repair=repair)
        snapshot=deepcopy(self.snapshot)
        snapshot["repositories"]["WeixuanZ/flood-warning-system"]["full_name"]="someoneelse/project"
        with self.assertRaisesRegex(ValueError,"exact public repository"):
            self.evaluation(snapshot=snapshot)

    def test_source_anchor_guard_rejects_made_up_original(self):
        spec=SOURCE_CASES[0]
        with self.assertRaisesRegex(ValueError,"not anchored"):
            evaluate_source(spec,"No referenced code tokens appear in this description.")

if __name__=="__main__":
    unittest.main()
