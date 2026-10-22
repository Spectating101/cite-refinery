"""Historical actual EA-stage-reading QA, not flood warning accuracy."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from math import nan, inf
import json
import unittest

from cite_refinery.flood_historical_gauge_audit import (
    MEASURE, STATION, audit, from_mirror, main, retrieve_official_window,
)

ROOT = Path(__file__).resolve().parents[1]
MIRROR = ROOT / "research_materials/runtime_trials/flood_20261023/sandford_archived_ea_sample.json"


def event(when, val, measure=MEASURE, station=STATION):
    return {"dateTime": when, "value": val, "measure": measure, "stationReference": station}


class HistoricalGaugeAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads(MIRROR.read_text("utf-8"))

    def test_real_three_archived_stage_readings_never_claim_real_event_accuracy(self):
        report = from_mirror(self.original)
        self.assertEqual(report["selected_stage_unique_finite_readings"], 3)
        self.assertEqual(report["nominal_grid_positions_between_first_and_last"], 4)
        self.assertEqual(report["unseen_slots_in_this_sample_not_verified_operational_outages"], 1)
        self.assertEqual(report["sample_coverage_ratio_not_sensor_uptime"], .75)
        self.assertEqual(len(report["observed_sample_gap_intervals"]), 1)
        self.assertEqual(report["sample_min_mASD"], .062)
        self.assertEqual(report["sample_max_mASD"], .068)
        self.assertEqual(report["sample_median_mASD"], .065)
        self.assertEqual(report["source_provenance"], "third_party_archived_EA_mirror")
        self.assertTrue(report["mirror_absent_slots_are_not_provider_gaps"])
        self.assertFalse(report["operational_risk_threshold_available"])
        self.assertIsNone(report["confirmed_flood_events"])
        self.assertIsNone(report["real_flood_false_alarm_rate"])
        self.assertIsNone(report["real_flood_missed_event_rate"])
        self.assertIsNone(report["public_warning_lead_time_minutes"])
        self.assertFalse(report["safety_or_impact_validated"])

    def test_out_of_order_readings_sorted_and_identical_duplicates_counted(self):
        base = [event("2026-02-07T13:30:00Z", .065),
                event("2026-02-07T13:45:00Z", .062),
                event("2026-02-07T14:15:00Z", .068)]
        readings = [base[2], base[0], base[1], base[0]]
        report = audit(readings, provenance="third_party_archived_EA_mirror")
        self.assertEqual(report["selected_stage_unique_finite_readings"], 3)
        self.assertEqual(report["duplicate_identical_readings_collapsed"], 1)
        self.assertTrue(report["measurements_aligned_to_first_observed_grid"])

    def test_prevents_stage_downstage_and_flow_unit_mixing(self):
        items = [event("2026-02-07T13:30:00Z", .065),
                 event("2026-02-07T13:30:00Z", -0.356,
                       "http://environment.data.gov.uk/flood-monitoring/id/measures/1502TH-level-downstage-i-15_min-mASD"),
                 event("2026-02-07T13:30:00Z", 284.0,
                       "http://environment.data.gov.uk/flood-monitoring/id/measures/3399TH-flow-water-i-15_min-m3_s")]
        result = audit(items, provenance="third_party_archived_EA_mirror")
        self.assertEqual(result["excluded_other_measures"], 2)
        self.assertEqual(result["selected_stage_unique_finite_readings"], 1)
        self.assertEqual(result["units"], "mASD")

    def test_conflicting_same_time_different_level_rejected(self):
        a = event("2026-02-07T13:30:00Z", .065)
        b = dict(a, value=.9)
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            audit([a, b], provenance="third_party_archived_EA_mirror")

    def test_finite_invalid_telemetry_rejected_not_imputed(self):
        a = event("2026-02-07T13:30:00Z", .065)
        for bad in [nan, inf, -inf, "0.99", None, True, 10 ** 1000]:
            with self.subTest(value=str(bad)[:24]):
                b = event("2026-02-07T13:45:00Z", bad)
                report = audit([a, b], provenance="third_party_archived_EA_mirror")
                self.assertEqual(report["invalid_readings_rejected"],
                                 {"nonfinite_or_malformed_readings": 1})
                self.assertEqual(report["selected_stage_unique_finite_readings"], 1)
                self.assertFalse(report["safety_or_impact_validated"])

    def test_utc_timezone_required_and_original_station_identity_enforced(self):
        valid = event("2026-02-07T13:30:00Z", .065)
        with self.assertRaisesRegex(ValueError, "explicit UTC offset"):
            audit([dict(valid, dateTime="2026-02-07T13:30:00")],
                  provenance="third_party_archived_EA_mirror")
        with self.assertRaisesRegex(ValueError, "Station reference"):
            audit([dict(valid, stationReference="OTHER")],
                  provenance="third_party_archived_EA_mirror")
        offset = audit([dict(valid, dateTime="2026-02-07T21:30:00+08:00")],
                       provenance="third_party_archived_EA_mirror")
        self.assertEqual(offset["earliest_observed_utc"], "2026-02-07T13:30:00+00:00")

    def test_frozen_mirror_source_provenance_cannot_be_promoted(self):
        changed = deepcopy(self.original)
        changed["flood_event_labels_present"] = True
        with self.assertRaisesRegex(ValueError, "Expected source-located"):
            from_mirror(changed)
        changed = deepcopy(self.original)
        changed["observations"].pop()
        with self.assertRaisesRegex(ValueError, "sample changed"):
            from_mirror(changed)
        changed = deepcopy(self.original)
        changed["observations"][0]["value"] = 99.0
        with self.assertRaisesRegex(ValueError, "source-bound EA readings altered"):
            from_mirror(changed)
        changed = deepcopy(self.original)
        changed["observations"][0]["mirror_blob"] = "BAD"
        with self.assertRaisesRegex(ValueError, "source-bound EA readings altered"):
            from_mirror(changed)

    def test_live_endpoint_limits_bad_ranges_before_network(self):
        for start, end in [
            ("2026-10-20", "2026-10-24"),
            ("2026-10-24", "2026-10-20"),
            ("2026-13-01", "2026-10-20"),
        ]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                retrieve_official_window(start, end)

    def test_cli_mirror_emits_no_overwrite_non_safety_receipt(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "ea-gauge-audit.json"
            args = ["--archived-mirror", str(MIRROR), "--out", str(out)]
            self.assertEqual(main(args), 0)
            result = json.loads(out.read_text())
            self.assertEqual(result["selected_stage_unique_finite_readings"], 3)
            self.assertTrue(result["no_automatic_warning_output"])
            with self.assertRaisesRegex(ValueError, "overwrite"):
                main(args)


if __name__ == "__main__":
    unittest.main()
