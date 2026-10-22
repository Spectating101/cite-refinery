"""First three-map opportunity: authentic archived flood records, no promotion."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from cite_refinery.flood_evidence_dossier import (
    ASSET, READING, SCHEMA, SOURCE_COMMIT, WHO, build_dossier, main,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "research_materials"
ALIGN = BASE / "runtime_trials/cross_layer_20261020/flood_candidate.json"
TRIAL = BASE / "opportunity_atlas/functional_component_trials.json"
QUEUE = BASE / "opportunity_atlas/conversion_qualification_with_positive_and_negative_trials_v1.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class FloodOpportunityDossierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.alignment = load(ALIGN)
        cls.trials = load(TRIAL)
        cls.queue = load(QUEUE)

    def test_original_three_map_receipts_reconcile_without_promoting_deployment(self):
        out = build_dossier(self.alignment, self.trials, self.queue)
        self.assertEqual(out["schema"], SCHEMA)
        self.assertEqual(out["source_reconciliation"]["practical"]["original_id"], WHO)
        self.assertEqual(out["source_reconciliation"]["academic"]["original_id"], READING)
        tech = out["source_reconciliation"]["implementation"]
        self.assertEqual(tech["asset_id"], ASSET)
        self.assertEqual(tech["original_source_commit"], SOURCE_COMMIT)
        self.assertEqual(tech["synthetic_test_counts"],
                         {"pass": 3, "fail": 2, "not_tested": 1})
        self.assertFalse(tech["live_field_execution_verified"])
        self.assertEqual(out["decision"]["status"],
                         "LAB_ONLY_FALSIFICATION_PRIORITY_NO_DEPLOYMENT_RECOMMENDATION")
        self.assertFalse(out["decision"]["automatic_cross_layer_promotion"])
        self.assertFalse(out["decision"]["funding_or_value_established"])
        self.assertFalse(out["decision"]["underconversion_established"])
        self.assertFalse(out["decision"]["field_use_authorized"])
        self.assertEqual(len(out["framework"]["four_pillars"]), 4)
        self.assertEqual(len(out["alternative_candidates"]), 3)
        self.assertTrue(all(x["status"] == "unqualified_development_candidate"
                            and not x["actual_integration_verified"]
                            for x in out["alternative_candidates"]))
        self.assertEqual(len(out["source_artifacts_fingerprint_sha256"]), 64)
        self.assertEqual(out, build_dossier(self.alignment, self.trials, self.queue))

    def test_rejects_promoted_practical_outcome_or_distorted_source_identity(self):
        changed = deepcopy(self.alignment)
        changed["alignments"][0]["outcome_verified"] = True
        with self.assertRaisesRegex(ValueError, "incorrectly promoted"):
            build_dossier(changed, self.trials, self.queue)
        changed = deepcopy(self.alignment)
        changed["alignments"][0]["perspectives"]["program"][0]["source_url"] = (
            "https://some-other-source.invalid")
        with self.assertRaisesRegex(ValueError, "identity or caveat"):
            build_dossier(changed, self.trials, self.queue)

    def test_rejects_removed_or_patched_critical_upstream_failure(self):
        changed = deepcopy(self.trials)
        flood = next(x for x in changed["probes"] if x["asset_id"] == ASSET)
        bad = next(x for x in flood["cases"]
                   if x["name"] == "nonfinite_station_corrupts_top_one_ordering")
        bad["status"] = "pass"
        with self.assertRaisesRegex(ValueError, "fixture results changed"):
            build_dossier(self.alignment, changed, self.queue)
        changed = deepcopy(self.trials)
        flood = next(x for x in changed["probes"] if x["asset_id"] == ASSET)
        flood["source"]["git_commit"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "source and execution authority"):
            build_dossier(self.alignment, changed, self.queue)

    def test_rejects_unverified_alternative_as_suddenly_validated(self):
        changed = deepcopy(self.queue)
        changed["independently_qualified_high_quality_assets"] = 1
        with self.assertRaisesRegex(ValueError, "falsely credited"):
            build_dossier(self.alignment, self.trials, changed)
        changed = deepcopy(self.queue)
        match = next(x for x in changed["rows"] if x["asset_ids"] == [
            "github:TheWillMiller/river-wise", "github:sdmlua/FIMserv"])
        match["proposed_recombination_tested"] = True
        with self.assertRaisesRegex(ValueError, "validation authority"):
            build_dossier(self.alignment, self.trials, changed)

    def test_cli_creates_reproducible_non_overwriting_machine_dossier(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "flood-evidence.json"
            cmd = ["--cross-layer-alignment", str(ALIGN),
                   "--functional-trials", str(TRIAL),
                   "--conversion-queue", str(QUEUE),
                   "--out", str(p)]
            self.assertEqual(main(cmd), 0)
            got = json.loads(p.read_text("utf-8"))
            self.assertEqual(got["source_reconciliation"]["implementation"]
                             ["synthetic_test_counts"]["fail"], 2)
            with self.assertRaisesRegex(ValueError, "overwrite"):
                main(cmd)


if __name__ == "__main__":
    unittest.main()
