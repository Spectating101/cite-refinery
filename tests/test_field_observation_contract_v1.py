"""No real animals are in the field contract test fixtures."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from cite_refinery.field_observation_contract import SCHEMA,assess,digest
from cite_refinery.field_observation_synthetic import synthetic_pilot,incomplete_pilot,build_examples

class FieldObservationTests(unittest.TestCase):
    def setUp(self):
        self.complete=synthetic_pilot()
    def test_complete_synthetic_input_passes_format_but_never_causal_identification(self):
        result=assess(self.complete)
        self.assertTrue(result["synthetic"])
        self.assertEqual(result["visit_count"],4)
        self.assertEqual(result["site_count"],1)
        self.assertEqual(result["detection_event_count"],24)
        self.assertEqual(result["independent_observer_counts"]["both"],12)
        self.assertEqual(result["test_status"]["T3"],"conditional_data_quality_review_only")
        self.assertEqual(result["test_status"]["T2"],"data_elements_available_requires_external_design_review")
        self.assertFalse(result["statistically_identified_mechanism"])
        self.assertFalse(result["g_zero_estimated"])
        self.assertFalse(result["field_protocol_approved"])
        self.assertFalse(result["human_privacy_fields_present"])
    def test_degraded_measurement_fails_closed(self):
        result=assess(incomplete_pilot())
        self.assertEqual(result["test_status"]["T3"],"not_ready_for_detection_model")
        self.assertEqual(result["test_status"]["T2"],"unresolved_data_gap")
        self.assertIn("observer_independence_or_blinding_not_verified",result["warnings"])
        self.assertIn("uncertain_or_low_confidence_double_detection_match",result["warnings"])
    def test_reject_private_field_and_contact_data_anywhere(self):
        for scope in ("root","visit","detection","origin"):
            x=deepcopy(self.complete)
            row={"root":x,"visit":x["visits"][0],
                 "detection":x["detections"][0],
                 "origin":x["origin_evidence"][0]}[scope]
            row["gps"]="24.9900,121.0000"
            with self.subTest(scope=scope),self.assertRaises(ValueError):
                assess(x)
    def test_require_observer_matching_rules(self):
        x=deepcopy(self.complete)
        x["detections"][0]["observed_a"]=False
        x["detections"][0]["observed_b"]=False
        with self.assertRaisesRegex(ValueError,"Undetected"):
            assess(x)
        x=deepcopy(self.complete)
        x["detections"][0]["match_status"]="not_applicable"
        with self.assertRaisesRegex(ValueError,"Double detection"):
            assess(x)
        x=deepcopy(self.complete)
        x["detections"][3]["match_status"]="confirmed"
        with self.assertRaisesRegex(ValueError,"Single observer"):
            assess(x)
    def test_refuse_claimed_origins_without_consent_or_corroboration(self):
        x=deepcopy(self.complete)
        x["origin_evidence"][0]["evidence_kind"]="deidentified_voluntary_report"
        with self.assertRaisesRegex(ValueError,"consent"):
            assess(x)
        x=deepcopy(self.complete)
        x["origin_evidence"][0]["corroborated"]=False
        report=assess(x)
        self.assertEqual(report["test_status"]["T2"],"unresolved_data_gap")
        self.assertIn("uncorroborated_origin_labels",report["warnings"])
    def test_duplicate_claimed_origin_event_is_rejected(self):
        data=deepcopy(self.complete)
        data["origin_evidence"].append(deepcopy(data["origin_evidence"][0]))
        with self.assertRaisesRegex(ValueError,"duplicate origin evidence"):
            assess(data)

    def test_dates_dedup_effort_and_invalid_numbers(self):
        x=deepcopy(self.complete)
        x["visits"][0]["survey_day"]="2026-02-30"
        with self.assertRaises(ValueError):assess(x)
        x=deepcopy(self.complete)
        x["visits"][1]["visit_id"]=x["visits"][0]["visit_id"]
        with self.assertRaisesRegex(ValueError,"Duplicate visit"):
            assess(x)
        x=deepcopy(self.complete)
        x["detections"][0]["event_code"]=x["detections"][1]["event_code"]
        with self.assertRaisesRegex(ValueError,"Duplicate detection"):
            assess(x)
        x=deepcopy(self.complete)
        x["detections"][0]["distance_m"]=float("nan")
        with self.assertRaisesRegex(ValueError,"finite"):
            assess(x)
        x=deepcopy(self.complete)
        x["visits"][0]["actual_effort_km"]=0
        with self.assertRaisesRegex(ValueError,"Positive detections"):
            assess(x)
    def test_repeated_survey_scope_matters(self):
        x=deepcopy(self.complete)
        for visit in x["visits"]:
            visit["round_id"]="only_round"
        report=assess(x)
        self.assertEqual(report["test_status"]["T3"],"not_ready_for_detection_model")
        self.assertIn("insufficient_repeated_rounds_per_site",report["warnings"])
    def test_bundle_generation_is_deterministic_and_never_field_empirical(self):
        with TemporaryDirectory() as td:
            m=build_examples(td)
            self.assertTrue(m["synthetic_observations.json"]["synthetic"])
            self.assertEqual(m["synthetic_missing_quality.json"]["status"]["T2"],"unresolved_data_gap")
            for name in ("synthetic_observations.json","synthetic_missing_quality.json"):
                raw=json.loads((Path(td)/name).read_text())
                self.assertEqual(raw["schema"],SCHEMA)
                self.assertTrue(raw["synthetic"])
                self.assertEqual(digest(raw),digest(json.loads(json.dumps(raw))))
            prior=(Path(td)/"manifest.json").read_bytes()
            build_examples(td)
            self.assertEqual(prior,(Path(td)/"manifest.json").read_bytes())

if __name__=="__main__":unittest.main()
