"""Functional candidate trials are source-pinned diagnostics, not solution proof."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cite_refinery.app import CiteRefinery
from cite_refinery.functional_component_probes import (
    REVISIONS,SCHEMA,SubprocessProbeRunner,check,aggregate,render_md,_source,
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

    def test_subprocess_probe_runner_records_refinery_runs_and_blocks_promotion(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scratch = root / "scratch"
            scratch.mkdir()
            co2_dir = scratch / "ajlongshanks__co2_esphome"
            co2_dir.mkdir()
            (co2_dir / ".git").mkdir()
            (co2_dir / "co2sensor.yaml").write_text(
                "esphome:\n  name: test\nimage:\n  - file: \"a.png\"\n    id: face_bad\ndisplay:\n  - lambda: |-\n      it.image(0, 0, id(face_good));\n",
                encoding="utf-8",
            )
            flood_dir = scratch / "WeixuanZ__flood-warning-system"
            (flood_dir / "floodsystem").mkdir(parents=True)
            (flood_dir / ".git").mkdir()
            (flood_dir / "floodsystem" / "__init__.py").write_text("", encoding="utf-8")
            (flood_dir / "floodsystem" / "station.py").write_text(
                "class MonitoringStation:\n"
                "    def __init__(self, station_id, measure_id, label, coord, typical_range, river, town):\n"
                "        self.name = label\n"
                "        self.typical_range = typical_range\n"
                "        self.latest_level = None\n"
                "    def relative_water_level(self):\n"
                "        if self.latest_level is None or self.typical_range[1] <= self.typical_range[0]: return None\n"
                "        return (self.latest_level - self.typical_range[0]) / (self.typical_range[1] - self.typical_range[0])\n",
                encoding="utf-8",
            )
            (flood_dir / "floodsystem" / "flood.py").write_text(
                "def stations_level_over_threshold(stations, tol):\n"
                "    out = []\n"
                "    for s in stations:\n"
                "        r = s.relative_water_level()\n"
                "        if r is not None and r > tol: out.append((s, r))\n"
                "    return out\n"
                "def stations_highest_rel_level(stations, N):\n"
                "    valid = [s for s in stations if s.relative_water_level() is not None]\n"
                "    return valid[:N]\n",
                encoding="utf-8",
            )
            for folder, rev in (
                (co2_dir, REVISIONS["ajlongshanks__co2_esphome"]),
                (flood_dir, REVISIONS["WeixuanZ__flood-warning-system"]),
            ):
                import subprocess as sp
                sp.run(["git", "-C", str(folder), "init", "-q"], check=True)
                sp.run(["git", "-C", str(folder), "config", "user.email", "t@example.com"], check=True)
                sp.run(["git", "-C", str(folder), "config", "user.name", "t"], check=True)
                sp.run(["git", "-C", str(folder), "add", "."], check=True)
                sp.run(["git", "-C", str(folder), "commit", "-q", "-m", "fixture"], check=True)
            actual_co2_rev = sp.run(["git", "-C", str(co2_dir), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
            actual_flood_rev = sp.run(["git", "-C", str(flood_dir), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
            app = CiteRefinery(root / "ws")
            project = app.init_project("Probe provenance", "Record subprocess probe runs and block defective promotion")
            runner = SubprocessProbeRunner()
            agg = runner.run_into_project(
                app,
                project.id,
                scratch,
                probes=["flood", "co2"],
                revision_overrides={
                    "ajlongshanks__co2_esphome": actual_co2_rev,
                    "WeixuanZ__flood-warning-system": actual_flood_rev,
                },
            )
            self.assertEqual(len(agg["probes"]), 2)
            for p in agg["probes"]:
                prov = p["refinery_provenance"]
                self.assertTrue(prov["run_id"].startswith("rrun:"))
                self.assertTrue(prov["experiment_id"].startswith("rexp:"))
                self.assertEqual(prov["experiment_verdict"], "failed")
                with self.assertRaises(ValueError):
                    app.promote_capability(project.id, prov["capability_id"], experiment_id=prov["experiment_id"])

if __name__=="__main__":
    unittest.main()
