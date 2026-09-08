from __future__ import annotations

import json
import math
import re
import statistics
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BASE = "https://opendata.tycg.gov.tw"
ACCIDENT_PID = "d06dd55d-aac7-4b17-9211-82cbf467cc2d"
SIDEWALK_PID = "1de35418-b949-4ace-89a2-cb92714be3eb"
ACCIDENT_114_FALLBACK_RID = "e8a4e4b6-ab84-4365-b612-fd0f38e7c011"
SIDEWALK_FALLBACK_RID = "6a4126e6-e1ee-43e2-b771-e49f6a532c45"
OUT = Path("real-data-output")


def fetch_json(path: str, params: dict[str, Any] | None = None) -> Any:
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "ProblemCommonsV0.1/real-data-probe"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def unwrap_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        out: list[dict[str, Any]] = []
        for item in payload:
            if isinstance(item, dict):
                out.append(item)
            elif isinstance(item, str):
                try:
                    parsed = json.loads(item)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    out.append(parsed)
        return out
    if not isinstance(payload, dict):
        return []
    for key in ("records", "data", "rows", "items"):
        if isinstance(payload.get(key), list):
            return unwrap_rows(payload[key])
    result = payload.get("result")
    if isinstance(result, list):
        return unwrap_rows(result)
    if isinstance(result, dict):
        for key in ("records", "data", "rows", "items"):
            if isinstance(result.get(key), list):
                return unwrap_rows(result[key])
    return []


def resource_rows(pid: str) -> list[dict[str, Any]]:
    payload = fetch_json("/api/v1/resource.info", {"pid": pid})
    rows = unwrap_rows(payload)
    if rows:
        return rows
    if isinstance(payload, dict) and all(k in payload for k in ("rid", "pid")):
        return [payload]
    raise RuntimeError(f"Could not parse resource.info response for {pid}: {type(payload).__name__}")


def choose_resource(resources: list[dict[str, Any]], *, year: str | None, fallback: str) -> dict[str, Any]:
    for row in resources:
        name = str(row.get("name") or row.get("schedule_name") or "")
        fmt = str(row.get("file_format") or row.get("schedule_fomat") or "").upper()
        if year and year in name and (not fmt or "CSV" in fmt):
            return row
    for row in resources:
        if str(row.get("rid")) == fallback:
            return row
    return {"rid": fallback, "name": "fallback resource id"}


def fetch_datastore(rid: str, page_size: int = 1000, max_rows: int = 200000) -> list[dict[str, Any]]:
    all_rows: list[dict[str, Any]] = []
    offset = 0
    while offset < max_rows:
        payload = fetch_json("/api/v1/dataset.datastore", {"rid": rid, "limit": page_size, "offset": offset, "format": "json"})
        rows = unwrap_rows(payload)
        if not rows:
            if offset == 0:
                raise RuntimeError(f"dataset.datastore returned no parseable rows for rid={rid}; payload={str(payload)[:600]}")
            break
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        offset += len(rows)
    return all_rows


def s(value: Any) -> str:
    return "" if value is None else str(value).strip()


def is_missing(value: Any) -> bool:
    return s(value).lower() in {"", "none", "null", "nan", "n/a", "na", "-"}


def numeric(value: Any) -> float | None:
    text = s(value).replace(",", "")
    if not text:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def norm_text(value: Any) -> str:
    text = s(value).replace("臺", "台")
    text = re.sub(r"[\s　,，.。．、()（）\-_/]", "", text)
    return text


SECTION_SUFFIX = re.compile(r"(?:[一二三四五六七八九十百零〇0-9]+段)$")


def road_full(row: dict[str, Any], road_key: str = "Road", section_key: str = "Section") -> str:
    road = norm_text(row.get(road_key))
    section = norm_text(row.get(section_key))
    if section and not section.endswith("段"):
        section += "段"
    return road + section


def road_base(value: Any) -> str:
    return SECTION_SUFFIX.sub("", norm_text(value))


def completeness(rows: list[dict[str, Any]], keys: list[str]) -> dict[str, float]:
    n = max(len(rows), 1)
    return {key: round(sum(not is_missing(r.get(key)) for r in rows) / n, 4) for key in keys}


def describe_numeric(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "min": None, "median": None, "mean": None, "max": None}
    return {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "mean": statistics.mean(values),
        "max": max(values),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    acc_resources = resource_rows(ACCIDENT_PID)
    sw_resources = resource_rows(SIDEWALK_PID)
    acc_resource = choose_resource(acc_resources, year="114", fallback=ACCIDENT_114_FALLBACK_RID)
    sw_resource = choose_resource(sw_resources, year=None, fallback=SIDEWALK_FALLBACK_RID)
    acc_rid = str(acc_resource.get("rid") or ACCIDENT_114_FALLBACK_RID)
    sw_rid = str(sw_resource.get("rid") or SIDEWALK_FALLBACK_RID)

    accidents = fetch_datastore(acc_rid)
    sidewalks = fetch_datastore(sw_rid)

    acc_cols = sorted({k for row in accidents for k in row})
    sw_cols = sorted({k for row in sidewalks for k in row})

    acc_exact_dupes = len(accidents) - len({json.dumps(r, sort_keys=True, ensure_ascii=False) for r in accidents})
    sw_exact_dupes = len(sidewalks) - len({json.dumps(r, sort_keys=True, ensure_ascii=False) for r in sidewalks})

    lons = [numeric(r.get("Longitude")) for r in accidents]
    lats = [numeric(r.get("Latitude")) for r in accidents]
    valid_coords = [
        (lon, lat)
        for lon, lat in zip(lons, lats)
        if lon is not None and lat is not None and 120.8 <= lon <= 121.6 and 24.4 <= lat <= 25.4
    ]

    districts = Counter(s(r.get("Area")) for r in accidents if not is_missing(r.get("Area")))
    accident_types = Counter(s(r.get("Accident_type")) for r in accidents if not is_missing(r.get("Accident_type")))
    loc_types = Counter(s(r.get("location_type")) for r in accidents if not is_missing(r.get("location_type")))

    sw_by_district_full: dict[str, set[str]] = defaultdict(set)
    sw_by_district_base: dict[str, set[str]] = defaultdict(set)
    sw_rows_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in sidewalks:
        district = norm_text(row.get("行政區"))
        full = norm_text(row.get("道路路名"))
        base = road_base(row.get("道路路名"))
        if district and full:
            sw_by_district_full[district].add(full)
            sw_by_district_base[district].add(base)
            sw_rows_by_key[(district, base)].append(row)

    strict_primary = 0
    loose_primary = 0
    loose_either = 0
    eligible_primary = 0
    matched_accident_keys: Counter[tuple[str, str]] = Counter()
    for row in accidents:
        district = norm_text(row.get("Area"))
        primary_road = norm_text(row.get("Road"))
        if not district or not primary_road:
            continue
        eligible_primary += 1
        full = road_full(row)
        base = road_base(row.get("Road"))
        intersection_base = road_base(row.get("Intersection_road"))
        if full in sw_by_district_full[district] or (not norm_text(row.get("Section")) and primary_road in sw_by_district_full[district]):
            strict_primary += 1
        if base in sw_by_district_base[district]:
            loose_primary += 1
            matched_accident_keys[(district, base)] += 1
        if base in sw_by_district_base[district] or (intersection_base and intersection_base in sw_by_district_base[district]):
            loose_either += 1

    duplicate_sw_keys = {key: len(rows) for key, rows in sw_rows_by_key.items() if len(rows) > 1}

    width_fields = ["人行道寬度_最小", "人行道寬度_最大", "道路長度", "人行道長度"]
    sw_numeric = {
        field: describe_numeric([x for x in (numeric(r.get(field)) for r in sidewalks) if x is not None])
        for field in width_fields
    }

    top_joined: list[dict[str, Any]] = []
    for (district, base), count in matched_accident_keys.most_common(25):
        rows = sw_rows_by_key[(district, base)]
        mins = [x for x in (numeric(r.get("人行道寬度_最小")) for r in rows) if x is not None]
        maxs = [x for x in (numeric(r.get("人行道寬度_最大")) for r in rows) if x is not None]
        road_lengths = [x for x in (numeric(r.get("道路長度")) for r in rows) if x is not None]
        top_joined.append({
            "district_normalized": district,
            "road_base_normalized": base,
            "accident_rows_114": count,
            "sidewalk_rows": len(rows),
            "sidewalk_min_width_median": statistics.median(mins) if mins else None,
            "sidewalk_max_width_median": statistics.median(maxs) if maxs else None,
            "listed_road_length_sum": sum(road_lengths) if road_lengths else None,
        })

    summary = {
        "schema": "problem-commons-real-data-probe/v0.1",
        "source": {
            "accident_dataset_pid": ACCIDENT_PID,
            "accident_resource": acc_resource,
            "sidewalk_dataset_pid": SIDEWALK_PID,
            "sidewalk_resource": sw_resource,
        },
        "accidents": {
            "rows": len(accidents),
            "columns": acc_cols,
            "exact_duplicate_rows": acc_exact_dupes,
            "completeness": completeness(accidents, ["Year", "Date", "Time", "Accident_type", "location_type", "Area", "Road", "Section", "Intersection_road", "Longitude", "Latitude"]),
            "coordinate_valid_share": round(len(valid_coords) / max(len(accidents), 1), 4),
            "accident_type_counts": dict(accident_types),
            "top_districts": districts.most_common(20),
            "top_location_types": loc_types.most_common(20),
        },
        "sidewalks": {
            "rows": len(sidewalks),
            "columns": sw_cols,
            "exact_duplicate_rows": sw_exact_dupes,
            "completeness": completeness(sidewalks, ["行政區", "道路路名", "道路長度", "道路寬度_最大", "道路寬度_最小", "人行道長度", "人行道寬度_最大", "人行道寬度_最小"]),
            "numeric_profiles": sw_numeric,
            "normalized_duplicate_road_keys": len(duplicate_sw_keys),
            "rows_on_duplicate_road_keys": sum(duplicate_sw_keys.values()),
        },
        "join": {
            "accident_rows_with_primary_road_and_district": eligible_primary,
            "strict_primary_match_count": strict_primary,
            "strict_primary_match_share": round(strict_primary / max(eligible_primary, 1), 4),
            "base_primary_match_count": loose_primary,
            "base_primary_match_share": round(loose_primary / max(eligible_primary, 1), 4),
            "base_primary_or_intersection_match_count": loose_either,
            "base_primary_or_intersection_match_share": round(loose_either / max(eligible_primary, 1), 4),
            "warning": "Base-name matching intentionally strips section suffixes and can create false-positive corridor matches; it is a sensitivity check, not an accepted join.",
            "top_joined_descriptive_rows": top_joined,
        },
        "problem_commons_interpretation": {
            "supported": [
                "The accident dataset can support descriptive recurrence/location analysis if row-level quality is adequate.",
                "The sidewalk dataset can supply road-level infrastructure context for some named roads if matching coverage is adequate.",
            ],
            "not_supported": [
                "Pedestrian risk cannot be inferred from all A1/A2 accident rows because this local dataset does not identify pedestrian involvement.",
                "Causality cannot be inferred from road-name co-location or sidewalk width.",
                "Exposure is missing: traffic/pedestrian volumes are not supplied by these two datasets.",
                "The sidewalk table has no coordinates/intersection geometry, so spatial joins are not directly available from these two sources.",
            ],
            "decision_rule": "Keep the case in RESEARCHING unless row-level join quality is defensible and a pedestrian-specific/exposure source is added; otherwise reframe from pedestrian intervention to general corridor-data feasibility or retire the corridor hypothesis.",
        },
    }

    (OUT / "taoyuan-real-data-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "taoyuan-top-joined.json").write_text(json.dumps(top_joined, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = []
    report.append("# Taoyuan Mobility Real-Data Probe\n")
    report.append(f"- Accident resource: `{acc_rid}` ({len(accidents):,} rows)")
    report.append(f"- Sidewalk resource: `{sw_rid}` ({len(sidewalks):,} rows)")
    report.append(f"- Valid accident coordinates: {len(valid_coords):,}/{len(accidents):,} ({len(valid_coords)/max(len(accidents),1):.1%})")
    report.append(f"- Strict primary road match: {strict_primary:,}/{eligible_primary:,} ({strict_primary/max(eligible_primary,1):.1%})")
    report.append(f"- Base primary road match: {loose_primary:,}/{eligible_primary:,} ({loose_primary/max(eligible_primary,1):.1%})")
    report.append(f"- Base primary-or-intersection road match: {loose_either:,}/{eligible_primary:,} ({loose_either/max(eligible_primary,1):.1%})")
    report.append("")
    report.append("## Immediate Problem Commons verdict")
    report.append("The data can test whether recurring accident locations can be described and whether some road names can be enriched with sidewalk context. It cannot yet justify a pedestrian-intervention problem: pedestrian involvement and exposure are missing, sidewalk geometry is road-level, and any road-name join is vulnerable to normalization/section ambiguity.")
    report.append("")
    report.append("## What should happen to the Problem Packet")
    report.append("1. Preserve the observed accident recurrence question.")
    report.append("2. Downgrade any pedestrian-specific mechanism from problem statement to unresolved hypothesis.")
    report.append("3. Record join coverage and duplicate-key ambiguity as explicit evidence-quality constraints.")
    report.append("4. Add a pedestrian-specific case-level source and an exposure source before any risk ranking.")
    report.append("5. Require transport/domain review before any intervention language.")
    (OUT / "taoyuan-real-data-report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(json.dumps({
        "accident_rows": len(accidents),
        "sidewalk_rows": len(sidewalks),
        "strict_match_share": summary["join"]["strict_primary_match_share"],
        "base_match_share": summary["join"]["base_primary_match_share"],
        "either_match_share": summary["join"]["base_primary_or_intersection_match_share"],
        "output": str(OUT),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
