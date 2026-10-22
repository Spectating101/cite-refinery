"""Reproducible independent-map evaluation preparation over the real frozen corpus."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from cite_refinery.three_map_capability_packet import (
    SCHEMA, PREDICTIONS, RESULT, build_packet, score, main,
)
from test_standalone_workspace_pilot_v1 import OfflineStandalonePilotTests

ROOT = Path(__file__).resolve().parents[1]


class ThreeMapCapabilityPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OfflineStandalonePilotTests.setUpClass()
        cls.pilot = OfflineStandalonePilotTests.pilot

    def test_120_challenges_sample_60_real_source_records_without_holdout(self):
        tasks, references = build_packet(self.pilot)
        self.assertEqual(tasks["schema"], SCHEMA)
        self.assertEqual(len(tasks["questions"]), 120)
        self.assertEqual(len(references["anchors"]), 120)
        self.assertEqual(len(references["historical_development_pairs"]), 10)
        self.assertEqual({x["layer"] for x in tasks["questions"]},
                         {"practical", "academic", "implementation"})
        self.assertEqual(sum(references["selection_by_layer_and_group"]["practical"].values()), 20)
        self.assertEqual(sum(references["selection_by_layer_and_group"]["academic"].values()), 20)
        self.assertEqual(sum(references["selection_by_layer_and_group"]["implementation"].values()), 20)
        self.assertEqual(len({r["selected_source_card_id"]
                              for r in references["anchors"]}), 60)
        self.assertGreaterEqual(
            len(references["implementation_selected_source_stages"]), 2)
        self.assertEqual(sum(references["implementation_selected_source_stages"].values()), 20)
        self.assertEqual(sum(references["implementation_full_corpus_source_stages"].values()), 1290)
        self.assertEqual(len({q["task_id"] for q in tasks["questions"]}), 120)
        self.assertTrue(references["no_sealed_holdout_or_private_nocturnal_material_used"])
        self.assertFalse(references["independent_answer_quality_gold_available"])
        self.assertFalse(references["cross_layer_match_or_commercial_validation_performed"])
        self.assertTrue(all(q["gold_status"] == "not_independently_adjudicated"
                            and "selected_source_card_id" not in q
                            for q in tasks["questions"]))

    def test_frozen_10_development_pairs_are_diagnostic_not_blind_accuracy(self):
        _, refs = build_packet(self.pilot)
        probes = refs["historical_development_pairs"]
        self.assertEqual(sum(x["literal_hit"] for x in probes), 10)
        self.assertEqual(sum(x["paraphrase_hit"] for x in probes), 0)
        self.assertTrue(all(x["label_origin"].endswith("not_blind_gold")
                            for x in probes))

    def test_sampling_is_deterministic_but_seed_changes_selected_sources(self):
        q, r = build_packet(self.pilot)
        self.assertEqual((q, r), build_packet(self.pilot))
        alternate, alt_reference = build_packet(self.pilot, seed="different-precommitted-seed")
        self.assertNotEqual(q["baseline_sha256"], alternate["baseline_sha256"])
        self.assertNotEqual([x["selected_source_card_id"] for x in r["anchors"]],
                            [x["selected_source_card_id"] for x in alt_reference["anchors"]])

    def test_refuses_mutated_frozen_source_counts_and_holdout_leak(self):
        altered = deepcopy(self.pilot)
        altered["original_data"]["academic_sealed_holdout_not_imported"] = 0
        with self.assertRaisesRegex(ValueError, "safety or evidence authority"):
            build_packet(altered)
        altered = deepcopy(self.pilot)
        altered["cards"][0]["source_body"] = "Private forbidden contents"
        with self.assertRaisesRegex(ValueError, "holdout leaked"):
            build_packet(altered)
        altered = deepcopy(self.pilot)
        altered["by_layer"]["implementation"] = 1289
        with self.assertRaisesRegex(ValueError, "frozen"):
            build_packet(altered)

    def test_results_are_diagnostic_only_no_fabricated_gold(self):
        tasks, refs = build_packet(self.pilot)
        anchor = refs["anchors"][0]
        good = {
            "schema": PREDICTIONS, "baseline_sha256": tasks["baseline_sha256"],
            "responses": [
                {"task_id": anchor["task_id"],
                 "retrieved_card_ids": [anchor["selected_source_card_id"]],
                 "abstained": False},
            ],
        }
        report = score(tasks, refs, good)
        layer = tasks["questions"][0]["layer"]
        self.assertEqual(report["schema"], RESULT)
        self.assertEqual(report["total_submitted"], 1)
        self.assertEqual(report["by_layer"][layer]["developer_selected_anchor_hits"], 1)
        self.assertFalse(report["answer_grounding_or_entailment_scored"])
        self.assertFalse(report["technical_feasibility_independently_verified"])
        self.assertFalse(report["competitive_superiority_claim_allowed"])
        self.assertEqual(sum(v["missing"] for v in report["by_layer"].values()), 119)
        with self.assertRaisesRegex(ValueError, "unpinned"):
            score(tasks, refs, dict(good, baseline_sha256="bad"))
        duplicate = dict(good, responses=good["responses"] * 2)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            score(tasks, refs, duplicate)
        invalid = deepcopy(good)
        invalid["responses"][0]["retrieved_card_ids"] = ["practical:reported_case:fake"]
        with self.assertRaisesRegex(ValueError, "Unknown or wrong-layer"):
            score(tasks, refs, invalid)

    def test_offline_cli_writes_original_packet_without_overwrite(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            pilot = root / "pilot.json"
            pilot.write_text(json.dumps(self.pilot), encoding="utf-8")
            out = root / "packet"
            self.assertEqual(main(["--pilot", str(pilot), "--out-dir", str(out)]), 0)
            tasks = json.loads((out / "questions.json").read_text())
            refs = json.loads((out / "reviewer-reference.json").read_text())
            self.assertEqual(len(tasks["questions"]), 120)
            self.assertEqual(len(refs["historical_development_pairs"]), 10)
            with self.assertRaisesRegex(ValueError, "overwrite"):
                main(["--pilot", str(pilot), "--out-dir", str(out)])


if __name__ == "__main__":
    unittest.main()
