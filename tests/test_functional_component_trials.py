"""Functional candidate trials are source-pinned diagnostics, not solution proof."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cite_refinery.functional_component_probes import (
    REVISIONS,SCHEMA,check,aggregate,render_md,_source,
)
from cite_refinery.functional_three_layer_overlay import build,markdown

ROOT=Path(__file__).resolve().parents[1]/"research_materials/opportunity_atlas"

def load(name):
    return json.loads((ROOT/name).read_text(encoding="utf-8"))

class FunctionalityTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trials=load("functional_component_trials.json")
        cls.graph=load("three_layer_unified_atlas.json")
        cls.semantic=load("academic_semantic_review_queue.json")
        cls.overlay=load("functional_three_layer_overlay.json")

    def test_original_upstream_snapshot_evidence_and_scope(self):
        j=self.trials
        self.assertEqual(j["schema"],SCHEMA)
        self.assertEqual(len(j["probes"]),3)
        self.assertEqual(j["test_case_counts"],
                         {"pass":6,"fail":7,"blocked":1,"not_tested":3})
        self.assertFalse(j["graph_status_promotion_allowed"])
        self.assertFalse(j["technical_fit_confirmed"])
        self.assertFalse(j["commercial_eligibility_confirmed"])
        self.assertFalse(j["development_source_holdout_touched"])
        for row in j["probes"]:
            self.assertIn(row["source"]["git_commit"],REVISIONS.values())
            self.assertIn("github:",row["asset_id"])
            self.assertTrue(row["cases"])
            self.assertTrue(all(c["claim_authority"]==
                 "synthetic_code_or_static_configuration_probe_only" for c in row["cases"]))
        self.assertIn("No external code is copied",render_md(j))

    def test_recycling_positive_cost_invariant_fails_for_three_methods(self):
        row=next(p for p in self.trials["probes"] if
                 "EverBatt" in p["asset_id"])
        selected=[r for r in row["cases"] if r["name"].endswith("positive_fee_accounting")]
        self.assertEqual(len(selected),3)
        for r in selected:
            self.assertEqual(r["status"],"fail")
            self.assertEqual(r["expected"]["profit_reduction_usd"],10_000_000)
            self.assertEqual(r["actual"]["actual_profit_reduction_usd"],0)
        income=[r for r in row["cases"] if r["name"].endswith("negative_gate_fee_income")]
        self.assertEqual(len(income),3)
        self.assertTrue(all(r["status"]=="pass" and
            r["actual"]["profit_increase_usd"]==20_000_000 for r in income))

    def test_flood_nan_risk_and_co2_invalid_yaml_not_rebranded_success(self):
        flood=next(p for p in self.trials["probes"] if "flood-warning" in p["asset_id"])
        bad=next(x for x in flood["cases"] if x["name"]=="nonfinite_sensor_level_is_excluded")
        self.assertEqual(bad["status"],"fail")
        self.assertTrue(bad["actual"]["nan_in_ranked_stations"])
        misorder=next(x for x in flood["cases"] if
                      x["name"]=="nonfinite_station_corrupts_top_one_ordering")
        self.assertEqual(misorder["status"],"fail")
        self.assertEqual(misorder["actual"]["top_one"],["low"])
        self.assertEqual(misorder["expected"]["top_one"],["high2"])
        co2=next(p for p in self.trials["probes"] if "co2_esphome" in p["asset_id"])
        self.assertEqual(next(x for x in co2["cases"] if x["name"]=="esphome_yaml_syntax")["status"],"fail")
        self.assertEqual(next(x for x in co2["cases"] if x["name"]=="display_image_identifiers")["actual"]["undeclared_image_ids"],["face_good"])
        self.assertEqual(next(x for x in co2["cases"] if x["name"]=="licensing_provenance")["status"],"blocked")
        self.assertEqual(next(x for x in co2["cases"] if x["name"]=="firmware_compile_and_sensor_calibration")["status"],"not_tested")

    def test_exact_identity_overlay_and_no_authority_escalation(self):
        overlay=build(self.graph,self.trials,semantic_review=self.semantic)
        self.assertEqual(overlay["schema"],"cite_refinery.functional_three_layer_overlay.v1")
        self.assertEqual(overlay["counts"]["practical_academic_implementation_paths_tested"],3)
        self.assertEqual(overlay["counts"]["candidate_paths_with_reproduced_component_defects"],3)
        self.assertEqual(overlay["counts"]["candidate_paths_with_full_tech_validation"],0)
        self.assertEqual(overlay["counts"]["confirmed_buyers"],0)
        self.assertTrue(all(not x["graph_transition_authorized"]
                            and not x["end_to_end_functionality_verified"]
                            and not x["research_entailment_approved"] for x in overlay["linked_trials"]))
        self.assertEqual(overlay,self.overlay)
        self.assertIn("Conversion gate",markdown(overlay))

    def test_tampered_links_and_fake_promotions_rejected(self):
        bad=deepcopy(self.trials)
        bad["probes"][0]["asset_id"]="github:invented/no-repo"
        with self.assertRaisesRegex(ValueError,"existing technical"):
            build(self.graph,bad,semantic_review=self.semantic)
        bad=deepcopy(self.trials)
        bad["technical_fit_confirmed"]=True
        with self.assertRaisesRegex(ValueError,"promoted"):
            build(self.graph,bad,semantic_review=self.semantic)
        bad=deepcopy(self.trials)
        bad["probes"][1]["cases"][0]["status"]="verified_commercial_fit"
        with self.assertRaisesRegex(ValueError,"unreviewed"):
            build(self.graph,bad,semantic_review=self.semantic)
        bad=deepcopy(self.graph)
        bad["edges"]=[x for x in bad["edges"] if not (x["from"]=="mechanism:flood_warning_to_impact" and
                    x["to"]=="github:WeixuanZ/flood-warning-system")]
        with self.assertRaisesRegex(ValueError,"no exact candidate"):
            build(bad,self.trials)

    def test_source_pin_requires_exact_git_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);folder=root/"WeixuanZ__flood-warning-system"
            folder.mkdir();(folder/".git").mkdir()
            with patch("cite_refinery.functional_component_probes.subprocess.run") as subprocess_call:
                subprocess_call.return_value.stdout="0"*40
                with self.assertRaisesRegex(ValueError,"revision changed"):
                    _source(root,"WeixuanZ__flood-warning-system")

    def test_bounded_status_and_distinct_asset_invariants(self):
        with self.assertRaisesRegex(ValueError,"invalid test status"):
            check("fake","Any requirement","qualified")
        invalid=deepcopy(self.trials["probes"])
        invalid.append(deepcopy(invalid[0]))
        with self.assertRaisesRegex(ValueError,"duplicate asset"):
            aggregate(invalid)
        with self.assertRaisesRegex(ValueError,"bounded"):
            aggregate([])

if __name__=="__main__":
    unittest.main()
