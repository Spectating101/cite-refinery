"""Replay PINNED original upstream flood code and repaired lab-only adapter.

Fetch upstream source outside this module using its fixed Git commit; verify all
original blob IDs before executing. This does not modify upstream or issue alerts.
"""
from __future__ import annotations

from hashlib import sha1
from pathlib import Path
import argparse
import importlib
import itertools
import json
import sys

from cite_refinery.flood_ranking_adapter import highest_station_candidates, stations_above_threshold

PINNED_COMMIT = "c1c7facf2c5577a155edd93a0b7279ad7630518c"
ORIGINAL_BLOBS = {
    "flood.py": "467c9813043adef3593ef6dd73c9c7adca2e9618",
    "station.py": "00d963622dda2ec688fec6b6b1d222955e8d9a0e",
    "utils.py": "2ebe58b654041fe461fbf47e99cdc9488e453785",
}


def import_pinned_upstream(root: Path):
    base = root / "floodsystem"
    actual = {}
    for filename, blob in ORIGINAL_BLOBS.items():
        file = base / filename
        if not file.is_file() or file.is_symlink() or file.stat().st_size > 16000:
            raise ValueError("Missing, symlinked or oversized original pinned file: " + filename)
        content = file.read_bytes()
        digest = sha1(("blob %d\0" % len(content)).encode() + content).hexdigest()
        if digest != blob:
            raise ValueError("Upstream Git blob fingerprint mismatch: " + filename)
        actual[filename] = digest
    # Checkout is pinned at a Git SHA; individual blob verification prevents
    # silently running changed code. No upstream source is vendored in our repo.
    for name in list(sys.modules):
        if name == "floodsystem" or name.startswith("floodsystem."):
            raise RuntimeError("Unexpected preloaded floodsystem package")
    sys.path.insert(0, str(root))
    try:
        station = importlib.import_module("floodsystem.station")
        flood = importlib.import_module("floodsystem.flood")
    finally:
        sys.path.pop(0)
    return station.MonitoringStation, flood, actual


def replay(root: Path) -> dict:
    Station, original, fingerprints = import_pinned_upstream(root)

    def station(sid, level, rng=(0.0, 1.0)):
        s = Station(sid, sid, sid, (0.0, 0.0), rng, "test-river", "test-town")
        s.latest_level = level
        return s

    low, bad, high = station("low", .2), station("nonfinite", float("nan")), station("high", 1.6)
    rows = []
    for items in itertools.permutations([low, bad, high]):
        original_top = original.stations_highest_rel_level(items, 1)
        repaired = highest_station_candidates(items, 1)
        above = stations_above_threshold(items, .5)
        rows.append({
            "input_ids": [s.station_id for s in items],
            "original_top_id": original_top[0].station_id if original_top else None,
            "adapter_top_id": repaired.candidates[0].station.station_id,
            "adapter_above_threshold_ids": [c.station.station_id for c in above.candidates],
            "adapter_rejected_ids": [c.station_id for c in repaired.rejected],
            "adapter_degraded_input": repaired.degraded_input,
        })
    problems = [x for x in rows if x["original_top_id"] != "high"]
    if not problems:
        raise AssertionError("Pinned upstream NaN misranking not reproduced on this runtime")
    if not all(x["adapter_top_id"] == "high"
               and x["adapter_above_threshold_ids"] == ["high"]
               and x["adapter_rejected_ids"] == ["nonfinite"]
               and x["adapter_degraded_input"] for x in rows):
        raise AssertionError("Adapter did not reject NaN while preserving high station")
    finite = [station("low", .2), station("high", 1.6), station("medium", .8)]
    finite_original = [x.station_id for x in original.stations_highest_rel_level(finite, 3)]
    finite_adapter = [x.station.station_id for x in highest_station_candidates(finite, 3).candidates]
    if finite_adapter != finite_original:
        raise AssertionError("Adapter broke ranking for finite source inputs")
    return {
        "schema": "cite_refinery.flood_pinned_original_nan_replay.v1",
        "pinned_upstream_commit": PINNED_COMMIT,
        "original_verified_git_blobs": fingerprints,
        "scope": "pinned_original_modules_offline_synthetic_station_fixtures_only",
        "input_permutations": len(rows),
        "original_incorrect_top_one": len(problems),
        "original_correct_top_one": len(rows) - len(problems),
        "adapter_correct_top_one": sum(x["adapter_top_id"] == "high" for x in rows),
        "adapter_nan_rejections": sum(x["adapter_rejected_ids"] == ["nonfinite"] for x in rows),
        "finite_only_ranking_preserved": True,
        "permutations": rows,
        "no_real_warning_generated": True,
        "field_or_safety_authority_proven": False,
        "upstream_modified": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--upstream-root", required=True, type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    if args.out.exists():
        raise ValueError("Refusing to overwrite a prior replay receipt")
    result = replay(args.upstream_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "pinned_upstream_commit", "input_permutations", "original_incorrect_top_one",
        "adapter_correct_top_one", "finite_only_ranking_preserved")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
