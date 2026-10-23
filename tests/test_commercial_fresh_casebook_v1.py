"""Prospective-fresh source packet preflight, with ZERO model calls.

This is analyst-curated and pre-execution. Not a sealed independent gold set.
"""
from __future__ import annotations
import hashlib
import json
import unittest
from cite_refinery.business_workbench import ROOT
from cite_refinery.commercial_blind_trial import (
    arm_prompt, atlas_context, get_plan, source_packet, validate_casebook,
)
from cite_refinery.opportunity_conversion import evaluate

BASE = ROOT / "research_materials/opportunity_conversion"
FILE = BASE / "blind_casebook_prospective_fresh_v1.json"
OLD = BASE / "blind_casebook_development_v1.json"


class FreshCommercialCasebookPreflight(unittest.TestCase):
    def setUp(self):
        self.book = json.loads(FILE.read_text(encoding="utf-8"))

    def test_new_and_old_case_ids_disjoint_with_prospective_label(self):
        old = json.loads(OLD.read_text(encoding="utf-8"))
        self.assertEqual(self.book["split"], "prospective_fresh_not_independently_sealed")
        validate_casebook(self.book)
        self.assertFalse({x["case_id"] for x in self.book["cases"]}
                         & {x["case_id"] for x in old["cases"]})
        self.assertEqual(len(self.book["cases"]), 3)

    def test_each_fresh_case_uses_only_shared_source_urls(self):
        for case in self.book["cases"]:
            with self.subTest(case=case["case_id"]):
                packet = source_packet(case)
                casefile = BASE / (case["case_id"] + ".json")
                source = json.loads(casefile.read_text(encoding="utf-8"))
                source_urls = {x["url"] for x in source["problem"]["sources"]}
                source_urls.update(x["url"] for x in source["market"]["signals"])
                source_urls.update(x["url"] for x in source["upstream"]["signals"])
                source_urls.add(source["repository"]["capability_source"])
                cited = {x["url"] for x in case["evidence"]}
                self.assertEqual(source_urls, cited)
                self.assertIn("CASE:", packet)
                report = evaluate(source)
                self.assertEqual(report["readiness"], "evidence_lead_only")
                self.assertEqual(report["buyer"]["verified_demand_status"], "problem_signal")
                self.assertFalse(report["buyer"]["demand_attestation_valid"])
                self.assertEqual(report["candidate_asset"]["license_state"], "unverified")
                self.assertFalse(report["cross_layer_fit"]["execution_attestation_valid"])
                self.assertTrue(atlas_context(case))
                self.assertEqual(arm_prompt(case, arm="control").count(packet), 1)
                self.assertEqual(arm_prompt(case, arm="atlas").count(packet), 1)

    def test_no_claimed_seal_or_real_model_in_plan(self):
        p = get_plan(self.book)
        self.assertEqual(p["split"], "prospective_fresh_not_independently_sealed")
        self.assertEqual(len(p["cases"]), 3)
        self.assertEqual(p["status"], "ready_for_authenticated_opt_in_not_executed")
        self.assertIn("not independently sealed", p["limitations"][0])
        for row in p["cases"]:
            self.assertEqual(len(row["source_sha256"]), 64)
            self.assertGreater(row["atlas_prompt_chars"], row["control_prompt_chars"])
        self.assertEqual(p["source_casebook_sha256"],
                         hashlib.sha256(json.dumps(self.book, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")).hexdigest())

    def test_forged_holdout_label_and_source_mismatch_rejected(self):
        falsified = json.loads(json.dumps(self.book))
        falsified["split"] = "independently_sealed_test"
        with self.assertRaisesRegex(ValueError, "Unrecognized casebook"):
            validate_casebook(falsified)
        falsified = json.loads(json.dumps(self.book))
        falsified["cases"][0]["evidence"][0]["id"] = "homelab_readme"
        with self.assertRaisesRegex(ValueError, "duplicated"):
            validate_casebook(falsified)


if __name__ == "__main__":
    unittest.main()
