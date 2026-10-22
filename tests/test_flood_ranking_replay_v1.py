"""Pinned original source replay and safe offline adapter negative cases."""
from __future__ import annotations
import itertools
import math
import os
import shutil
import tempfile
from pathlib import Path
import unittest
from cite_refinery.flood_ranking_adapter import (
    inspect_stations, highest_station_candidates, stations_above_threshold,
)
from cite_refinery.flood_ranking_replay import import_pinned_upstream, replay, ORIGINAL_BLOBS


class Station:
    def __init__(self, sid, level, rng=(0., 1.)):
        self.station_id = sid
        self.latest_level = level
        self.typical_range = rng


def ids(result):
    return [x.station.station_id for x in result.candidates]


class FiniteOnlyRankingTests(unittest.TestCase):
    def test_all_six_input_orders_reject_nan_preserving_highest(self):
        stations = [Station("low", .2), Station("nan", math.nan), Station("high", 1.6)]
        for order in itertools.permutations(stations):
            result = highest_station_candidates(order, 1)
            self.assertEqual(ids(result), ["high"])
            self.assertEqual([x.station_id for x in result.rejected], ["nan"])
            self.assertTrue(result.degraded_input)

    def test_nonfinite_and_malformed_sensor_levels_never_enter_ranking(self):
        invalid = [None, math.nan, math.inf, -math.inf, "1.0", True, 10 ** 1000, complex(1, 0)]
        for level in invalid:
            with self.subTest(level=str(level)[:20]):
                got = inspect_stations([Station("valid", 1.3), Station("invalid", level)])
                self.assertEqual(ids(got), ["valid"])
                self.assertTrue(got.degraded_input)
                self.assertEqual(len(got.rejected), 1)
                self.assertEqual(got.rejected[0].reason, "invalid_or_nonfinite_water_level")

    def test_invalid_ranges_and_overflow_never_produce_risk_score(self):
        bad_ranges = [None, [0., 1.], (0., 0.), (2., 1.), (math.nan, 1.),
                      (0., math.inf), (False, 1.), ("0", 1.), (0.,), (0., 1., 2.)]
        for rng in bad_ranges:
            with self.subTest(range=str(rng)):
                result = inspect_stations([Station("good", .9), Station("bad", 1., rng)])
                self.assertEqual(ids(result), ["good"])
                self.assertEqual(result.rejected[0].station_id, "bad")
                self.assertEqual(result.rejected[0].reason, "invalid_typical_range")
        overflow = inspect_stations([Station("overflow", 1e308, (-1e308, 1e308))])
        self.assertEqual(ids(overflow), [])
        self.assertEqual(overflow.rejected[0].reason, "overflowed_relative_range")

    def test_order_invariance_under_ties_and_valid_ranking(self):
        cases = [Station("z", .8), Station("b", 1.6), Station("a", 1.6), Station("low", -.3)]
        for order in itertools.permutations(cases):
            result = highest_station_candidates(order, 3)
            self.assertEqual(ids(result), ["a", "b", "z"])
            self.assertFalse(result.degraded_input)
        self.assertEqual(ids(highest_station_candidates(cases, 0)), [])
        self.assertEqual(ids(stations_above_threshold(cases, .5)), ["a", "b", "z"])
        self.assertEqual(ids(stations_above_threshold(cases, 1.6)), [])

    def test_duplicate_identifiers_must_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "Repeated station ID"):
            inspect_stations([Station("same", .3), Station("same", 1.7)])

    def test_invalid_parameters_must_fail_closed(self):
        cases = [Station("x", .5)]
        for n in [-1, True, 1., "1"]:
            with self.subTest(n=n), self.assertRaises(ValueError):
                highest_station_candidates(cases, n)
        for tol in [None, math.nan, math.inf, True, "0.5"]:
            with self.subTest(tol=tol), self.assertRaises(ValueError):
                stations_above_threshold(cases, tol)
        with self.assertRaises(TypeError):
            inspect_stations(iter(cases))

    def test_empty_missing_id_and_valid_conservative_degradation(self):
        self.assertEqual(ids(inspect_stations([])), [])
        bad = inspect_stations([Station("", 1.7), Station("valid", .7)])
        self.assertEqual(ids(bad), ["valid"])
        self.assertTrue(bad.degraded_input)
        self.assertEqual(bad.rejected[0].reason, "invalid_station_id")


class PinnedOriginalSourceTests(unittest.TestCase):
    def test_sha_verification_blocks_tamper_before_execution(self):
        root = os.getenv("FLOOD_UPSTREAM_ROOT")
        if not root:
            self.skipTest("No pinned original checkout supplied; adapter tests still run")
        with tempfile.TemporaryDirectory() as td:
            orig = Path(root) / "floodsystem"
            target = Path(td) / "floodsystem"
            target.mkdir()
            for filename in ORIGINAL_BLOBS:
                shutil.copyfile(orig / filename, target / filename)
            (target / "flood.py").write_bytes((target / "flood.py").read_bytes() + b"\n# injected")
            with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
                import_pinned_upstream(Path(td))

    def test_true_pinned_original_nan_failure_and_repair_receipt(self):
        root = os.getenv("FLOOD_UPSTREAM_ROOT")
        if not root:
            self.skipTest("No pinned original checkout supplied; adapter tests still run")
        report = replay(Path(root))
        self.assertEqual(report["input_permutations"], 6)
        self.assertGreaterEqual(report["original_incorrect_top_one"], 1)
        self.assertEqual(report["original_correct_top_one"], 4)
        self.assertEqual(report["adapter_correct_top_one"], 6)
        self.assertEqual(report["adapter_nan_rejections"], 6)
        self.assertTrue(report["finite_only_ranking_preserved"])
        self.assertEqual(report["original_verified_git_blobs"], ORIGINAL_BLOBS)
        self.assertFalse(report["field_or_safety_authority_proven"])
        self.assertTrue(report["no_real_warning_generated"])


if __name__ == "__main__":
    unittest.main()
