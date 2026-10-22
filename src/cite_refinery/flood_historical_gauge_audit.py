"""Bounded EA-gauge observation audit; NOT flood prediction or alert evaluation.

No operational flood-risk thresholds or validated flood-event labels are present.
Use a fixed-source offline audit; optional short live read is advisory only.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timedelta, timezone
from hashlib import sha256, sha1
from math import isfinite
from pathlib import Path
from statistics import median
import argparse
import json
import urllib.request
import urllib.error

SCHEMA = "cite_refinery.flood_historical_gauge_audit.v1"
MIRROR = "cite_refinery.official_gauge_mirror_three_readings.v1"
STATION = "1502TH"
MEASURE = ("http://environment.data.gov.uk/flood-monitoring/id/measures/"
           "1502TH-level-stage-i-15_min-mASD")
ENDPOINT = ("https://environment.data.gov.uk/flood-monitoring/id/measures/"
            "1502TH-level-stage-i-15_min-mASD/readings")
INTERVAL = 15
MAX_BYTES = 2_000_000
OFFICIAL_ATTRIBUTION = (
    "This uses Environment Agency flood and river level data from the real-time data API (Beta)"
)


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _read_json(path: Path):
    _require(path.is_file() and not path.is_symlink() and
             path.stat().st_size <= MAX_BYTES, "Missing/oversized/linked gauge input")
    return json.loads(path.read_text("utf-8"))


def _instant(stamp):
    _require(isinstance(stamp, str) and len(stamp) < 40 and
             ("+" in stamp or stamp.endswith("Z")),
             "Gauge timestamp requires explicit UTC offset")
    try:
        dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid ISO 8601 gauge timestamp") from exc
    _require(dt.tzinfo is not None, "Gauge timestamp must have timezone")
    return dt.astimezone(timezone.utc)


def _finite_numeric(value):
    if type(value) not in (float, int):
        return None
    try:
        x = float(value)
    except (OverflowError, ValueError):
        return None
    return x if isfinite(x) else None


def audit(readings, *, provenance, nominal_interval_minutes=INTERVAL):
    """Reject wrong-source claims and report only measured telemetry integrity."""
    _require(provenance in {"third_party_archived_EA_mirror", "original_EA_live_endpoint"},
             "Unrecognized gauge dataset authority")
    _require(type(nominal_interval_minutes) is int and
             nominal_interval_minutes == 15, "Unexpected measurement cadence")
    _require(isinstance(readings, list) and 1 <= len(readings) <= 10000,
             "No valid-sized gauge observation payload")
    valid = {}
    invalid = Counter()
    excluded_other_measures = 0
    exact_duplicate_count = 0
    for item in readings:
        _require(isinstance(item, dict), "Gauge readings must be objects")
        measure = item.get("measure")
        if measure != MEASURE:
            excluded_other_measures += 1
            continue
        station = item.get("stationReference")
        _require(station in (None, STATION),
                 "Station reference contradicts pinned measure identity")
        timestamp = _instant(item.get("dateTime"))
        value = _finite_numeric(item.get("value"))
        if value is None:
            invalid["nonfinite_or_malformed_readings"] += 1
            continue
        # Raw values are in mASD. Zero/negative stages may be valid; no
        # assumed geodetic datum, threshold, reference range or hazard limit.
        if timestamp in valid:
            if valid[timestamp] != value:
                raise ValueError("Conflicting station readings at identical event timestamp")
            exact_duplicate_count += 1
            continue
        valid[timestamp] = value
    ordered = sorted(valid.items())
    _require(bool(ordered), "Selected original stage measure has no finite readings")
    first, last = ordered[0][0], ordered[-1][0]
    step = timedelta(minutes=nominal_interval_minutes)
    span = (last - first).total_seconds() / 60
    expected = int(span // nominal_interval_minutes) + 1
    gaps = []
    for (earlier, _), (later, _) in zip(ordered, ordered[1:]):
        delta = int((later - earlier).total_seconds() / 60)
        if delta > nominal_interval_minutes:
            gaps.append({
                "after_utc": earlier.isoformat(),
                "before_utc": later.isoformat(),
                "duration_minutes": delta,
                "nominal_missing_slots": max(0, (delta - 1) // nominal_interval_minutes),
            })
    aligned = all((t - first).total_seconds() % step.total_seconds() == 0
                  for t, _ in ordered)
    values = [v for _, v in ordered]
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    return {
        "schema": SCHEMA,
        "station": STATION, "measure_uri": MEASURE, "units": "mASD",
        "source_provenance": provenance, "official_attribution": OFFICIAL_ATTRIBUTION,
        "input_records": len(readings),
        "selected_stage_unique_finite_readings": len(ordered),
        "excluded_other_measures": excluded_other_measures,
        "duplicate_identical_readings_collapsed": exact_duplicate_count,
        "invalid_readings_rejected": dict(invalid),
        "earliest_observed_utc": first.isoformat(),
        "latest_observed_utc": last.isoformat(),
        "nominal_cadence_minutes": nominal_interval_minutes,
        "measurements_aligned_to_first_observed_grid": aligned,
        "nominal_grid_positions_between_first_and_last": expected,
        "unseen_slots_in_this_sample_not_verified_operational_outages": (
            expected - len(ordered) if aligned else None),
        "sample_coverage_ratio_not_sensor_uptime": (
            len(ordered) / expected if aligned else None),
        "observed_sample_gap_intervals": gaps,
        "sample_min_mASD": min(values),
        "sample_max_mASD": max(values),
        "sample_median_mASD": median(values),
        "sample_max_absolute_successive_change_mASD": (
            max(map(abs, changes)) if changes else None),
        "source_readings_sha256": sha256(json.dumps(readings, sort_keys=True,
                                  separators=(",", ":"), ensure_ascii=False,
                                  allow_nan=True).encode("utf-8")).hexdigest(),
        "confirmed_flood_events": None,
        "verified_issued_warning_or_acknowledgment_events": None,
        "operational_risk_threshold_available": False,
        "real_flood_false_alarm_rate": None,
        "real_flood_missed_event_rate": None,
        "public_warning_lead_time_minutes": None,
        "safety_or_impact_validated": False,
        "no_automatic_warning_output": True,
    }


def from_mirror(fixture):
    _require(fixture.get("schema") == MIRROR
             and fixture.get("station") == STATION
             and fixture.get("measure") == MEASURE
             and fixture.get("flood_event_labels_present") is False
             and fixture.get("warning_issue_or_delivery_records_present") is False
             and fixture.get("typical_range_from_official_station_metadata_present") is False
             and fixture.get("mirror_commit") == "93728ebdfdda41e629091f9e3550ccf8f2f4c58b",
             "Expected source-located unqualified EA mirror sample")
    _require(len(fixture.get("observations", [])) == 3, "Archived gauge mirror sample changed")
    data = []
    for x in fixture["observations"]:
        blob = x.get("mirror_blob")
        _require(isinstance(blob, str) and len(blob) == 40 and
                 all(c in "0123456789abcdef" for c in blob) and
                 x.get("mirror_path", "").startswith("owl_engine/owl_data/2026-02-07/river_levels/"),
                 "Source mirror reading identity invalid")
        data.append({"measure": MEASURE, "stationReference": STATION,
                     "dateTime": x["dateTime"], "value": x["value"]})
    result = audit(data, provenance="third_party_archived_EA_mirror")
    result["source_mirror_commit"] = fixture["mirror_commit"]
    result["original_mirror_blob_ids"] = [x["mirror_blob"] for x in fixture["observations"]]
    result["original_mirror_paths"] = [x["mirror_path"] for x in fixture["observations"]]
    result["mirror_absent_slots_are_not_provider_gaps"] = True
    return result


def verify_archived_mirror_sources(fixture, root: Path):
    """Reopen original third-party mirror bytes and match exact Git blob IDs.

    This verifies the stored mirror's content, NOT the EA provider's historical
    server response; independent upstream-origin verification is unavailable.
    """
    _require(isinstance(fixture, dict) and fixture.get("schema") == MIRROR,
             "Invalid fixed EA mirror fixture")
    observations = fixture.get("observations", [])
    _require(len(observations) == 3, "Expected three fixed archived source files")
    reviewed = []
    for item in observations:
        path = item.get("mirror_path")
        blob = item.get("mirror_blob")
        _require(isinstance(path, str) and path.startswith(
                 "owl_engine/owl_data/2026-02-07/river_levels/")
                 and ".." not in path and path.endswith(".json")
                 and isinstance(blob, str) and len(blob) == 40,
                 "Invalid mirror file locator")
        p = root / path
        _require(p.is_file() and not p.is_symlink() and p.stat().st_size <= 4096,
                 "Original mirror file unavailable")
        raw = p.read_bytes()
        actual_sha = sha1(("blob %d\0" % len(raw)).encode() + raw).hexdigest()
        _require(actual_sha == blob, "Original mirror Git blob mismatch")
        row = json.loads(raw).get("raw_data", {})
        _require(row.get("measure") == MEASURE
                 and row.get("stationReference") == STATION
                 and row.get("dateTime") == item.get("dateTime")
                 and type(row.get("value")) in (int, float)
                 and row["value"] == item.get("value"),
                 "Mirrored original river-level observation disagrees with fixture")
        reviewed.append({"path": path, "verified_git_blob_sha1": actual_sha})
    return reviewed


def retrieve_official_window(start_date, end_date):
    """Fetch a narrow, FIXED official measure; no arbitrary URL or alert commands."""
    from datetime import date
    try:
        start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid official history date range") from exc
    _require(start <= end and 0 <= (end - start).days <= 2,
             "Limit live sample to at most three UTC calendar days")
    url = ENDPOINT + "?startdate=" + start.isoformat() + "&enddate=" + end.isoformat() + "&_limit=1000"
    request = urllib.request.Request(
        url, headers={"Accept": "application/json",
                      "User-Agent": "Cite-Refinery-Offline-Hydrology-Research/1.0"})
    with urllib.request.urlopen(request, timeout=18) as response:
        _require(response.status == 200 and
                 response.headers.get("Content-Type", "").split(";")[0] in
                 ("application/json", "application/ld+json"),
                 "Official gauge API did not return JSON 200")
        raw = response.read(MAX_BYTES + 1)
    _require(len(raw) <= MAX_BYTES, "Official gauge JSON exceeds bounded fetch size")
    payload = json.loads(raw)
    _require(isinstance(payload, dict) and isinstance(payload.get("items"), list),
             "Official EA readings JSON payload malformed")
    report = audit(payload["items"], provenance="original_EA_live_endpoint")
    report["requested_original_endpoint"] = url
    report["window_start_date"] = start.isoformat()
    report["window_end_date"] = end.isoformat()
    report["source_provider_payload_sha256"] = sha256(raw).hexdigest()
    report["response_is_a_snapshot_and_provider_values_may_be_revised"] = True
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    inp = p.add_mutually_exclusive_group(required=True)
    inp.add_argument("--archived-mirror", type=Path)
    inp.add_argument("--official-window", nargs=2, metavar=("START_DATE", "END_DATE"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--mirror-source-root", type=Path,
                   help="Exact pinned external Git checkout used to verify mirror bytes")
    args = p.parse_args(argv)
    _require(not args.out.exists(), "Refusing to overwrite prior gauge audit")
    report = (from_mirror(_read_json(args.archived_mirror))
              if args.archived_mirror else
              retrieve_official_window(*args.official_window))
    if args.mirror_source_root is not None:
        _require(args.archived_mirror is not None,
                 "External mirror verification requires --archived-mirror")
        report["verified_original_mirror_git_blobs"] = verify_archived_mirror_sources(
            _read_json(args.archived_mirror), args.mirror_source_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", "utf-8")
    print(json.dumps({
        "source": report["source_provenance"],
        "observations": report["selected_stage_unique_finite_readings"],
        "flood_event_labels_available": False,
        "operational_detection_accuracy_established": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
