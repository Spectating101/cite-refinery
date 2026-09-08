from __future__ import annotations

import csv
import io
import json
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
ACCIDENT_114_RID = "e8a4e4b6-ab84-4365-b612-fd0f38e7c011"
SIDEWALK_RID = "6a4126e6-e1ee-43e2-b771-e49f6a532c45"
OUT = Path("real-data-output")
UA = {"User-Agent": "ProblemCommonsV0.1/real-data-probe"}


def get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.read()


def get_json(path: str, params: dict[str, Any]) -> Any:
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    return json.loads(get_bytes(url).decode("utf-8-sig"))


def recursive_dicts(node: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(node, dict):
        out.append(node)
        for value in node.values():
            out.extend(recursive_dicts(value))
    elif isinstance(node, list):
        for value in node:
            out.extend(recursive_dicts(value))
    return out


def resource_info(pid: str) -> list[dict[str, Any]]:
    payload = get_json("/api/v1/resource.info", {"pid": pid})
    rows = [d for d in recursive_dicts(payload) if d.get("rid")]
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        unique[str(row["rid"])] = row
    if not unique:
        raise RuntimeError("resource.info returned no object containing rid: " + json.dumps(payload, ensure_ascii=False)[:1200])
    return list(unique.values())


def choose(resources: list[dict[str, Any]], *, fallback_rid: str, year: str | None = None) -> dict[str, Any]:
    if year:
        for row in resources:
            name = str(row.get("name") or row.get("schedule_name") or row.get("file_name") or "")
            if year in name:
                return row
    for row in resources:
        if str(row.get("rid")) == fallback_rid:
            return row
    return {"rid": fallback_rid}


def decode_csv(raw: bytes) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "big5", "cp950"):
        try:
            text = raw.decode(encoding)
            rows = list(csv.DictReader(io.StringIO(text)))
            if rows:
                return rows
        except (UnicodeDecodeError, csv.Error) as exc:
            last_error = exc
    raise RuntimeError(f"could not decode CSV: {last_error}")


def rows_from_resource(resource: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    url = str(resource.get("url") or "")
    if url:
        if url.startswith("/"):
            url = BASE + url
        try:
            return decode_csv(get_bytes(url)), "resource_csv"
        except Exception as exc:
            print(f"CSV route failed for {resource.get('rid')}: {exc}; falling back to datastore")
    rid = str(resource.get("rid"))
    all_rows: list[dict[str, Any]] = []
    offset = 0
    requested = 2000
    for _ in range(2000):
        payload = get_json("/api/v1/dataset.datastore", {"rid": rid, "limit": requested, "offset": offset, "format": "json"})
        candidates: list[list[dict[str, Any]]] = []
        def walk(node: Any) -> None:
            if isinstance(node, list):
                dict_rows = [x for x in node if isinstance(x, dict)]
                if dict_rows:
                    candidates.append(dict_rows)
                for x in node:
                    walk(x)
            elif isinstance(node, dict):
                for x in node.values():
                    walk(x)
        walk(payload)
        rows = max(candidates, key=len) if candidates else []
        if not rows:
            break
        all_rows.extend(rows)
        offset += len(rows)
        if len(all_rows) >= 200000:
            break
    if not all_rows:
        raise RuntimeError("datastore returned no rows: " + json.dumps(payload, ensure_ascii=False)[:1200])
    return all_rows, "datastore"


def text(v: Any) -> str:
    return "" if v is None else str(v).strip()


def missing(v: Any) -> bool:
    return text(v).lower() in {"", "none", "null", "nan", "n/a", "na", "-"}


def num(v: Any) -> float | None:
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text(v).replace(",", ""))
    return float(m.group(0)) if m else None


def norm(v: Any) -> str:
    v = text(v).replace("臺", "台")
    return re.sub(r"[\s　,，.。．、()（）\-_/]", "", v)


SECTION = re.compile(r"[一二三四五六七八九十百零〇0-9]+段$")


def base_road(v: Any) -> str:
    return SECTION.sub("", norm(v))


def full_accident_road(row: dict[str, Any]) -> str:
    road = norm(row.get("Road"))
    section = norm(row.get("Section"))
    if section and not section.endswith("段"):
        section += "段"
    return road + section


def complete(rows: list[dict[str, Any]], keys: list[str]) -> dict[str, float]:
    n = max(len(rows), 1)
    return {k: round(sum(not missing(r.get(k)) for r in rows) / n, 4) for k in keys}


def describe(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "min": None, "median": None, "mean": None, "max": None}
    return {"n": len(values), "min": min(values), "median": statistics.median(values), "mean": statistics.mean(values), "max": max(values)}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    acc_resource = choose(resource_info(ACCIDENT_PID), fallback_rid=ACCIDENT_114_RID, year="114")
    sw_resource = choose(resource_info(SIDEWALK_PID), fallback_rid=SIDEWALK_RID)
    accidents, acc_route = rows_from_resource(acc_resource)
    sidewalks, sw_route = rows_from_resource(sw_resource)

    acc_columns = sorted({k for r in accidents for k in r})
    sw_columns = sorted({k for r in sidewalks for k in r})
    exact_acc_dupes = len(accidents) - len({json.dumps(r, sort_keys=True, ensure_ascii=False) for r in accidents})
    exact_sw_dupes = len(sidewalks) - len({json.dumps(r, sort_keys=True, ensure_ascii=False) for r in sidewalks})

    valid_coords = 0
    for row in accidents:
        lon, lat = num(row.get("Longitude")), num(row.get("Latitude"))
        if lon is not None and lat is not None and 120.8 <= lon <= 121.6 and 24.4 <= lat <= 25.4:
            valid_coords += 1

    sw_full: dict[str, set[str]] = defaultdict(set)
    sw_base: dict[str, set[str]] = defaultdict(set)
    sw_rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in sidewalks:
        district = norm(row.get("行政區"))
        road = norm(row.get("道路路名"))
        base = base_road(row.get("道路路名"))
        if district and road:
            sw_full[district].add(road)
            sw_base[district].add(base)
            sw_rows[(district, base)].append(row)

    eligible = strict = loose = either = 0
    matched: Counter[tuple[str, str]] = Counter()
    for row in accidents:
        district = norm(row.get("Area"))
        road = norm(row.get("Road"))
        if not district or not road:
            continue
        eligible += 1
        full = full_accident_road(row)
        primary_base = base_road(row.get("Road"))
        intersection_base = base_road(row.get("Intersection_road"))
        if full in sw_full[district] or (not norm(row.get("Section")) and road in sw_full[district]):
            strict += 1
        if primary_base in sw_base[district]:
            loose += 1
            matched[(district, primary_base)] += 1
        if primary_base in sw_base[district] or (intersection_base and intersection_base in sw_base[district]):
            either += 1

    duplicate_keys = {k: len(v) for k, v in sw_rows.items() if len(v) > 1}
    top_joined = []
    for (district, road), count in matched.most_common(25):
        rows = sw_rows[(district, road)]
        mins = [x for x in (num(r.get("人行道寬度_最小")) for r in rows) if x is not None]
        maxs = [x for x in (num(r.get("人行道寬度_最大")) for r in rows) if x is not None]
        top_joined.append({
            "district": district,
            "road_base": road,
            "accident_rows_114": count,
            "sidewalk_rows": len(rows),
            "sidewalk_min_width_median": statistics.median(mins) if mins else None,
            "sidewalk_max_width_median": statistics.median(maxs) if maxs else None,
        })

    widths = {}
    for field in ("道路長度", "人行道長度", "人行道寬度_最小", "人行道寬度_最大"):
        widths[field] = describe([x for x in (num(r.get(field)) for r in sidewalks) if x is not None])

    summary = {
        "schema": "problem-commons-real-data-probe/v0.2",
        "source": {
            "accident_pid": ACCIDENT_PID,
            "accident_rid": acc_resource.get("rid"),
            "accident_name": acc_resource.get("name") or acc_resource.get("schedule_name"),
            "accident_fetch_route": acc_route,
            "sidewalk_pid": SIDEWALK_PID,
            "sidewalk_rid": sw_resource.get("rid"),
            "sidewalk_name": sw_resource.get("name") or sw_resource.get("schedule_name"),
            "sidewalk_fetch_route": sw_route,
        },
        "accidents": {
            "rows": len(accidents),
            "columns": acc_columns,
            "exact_duplicate_rows": exact_acc_dupes,
            "completeness": complete(accidents, ["Year", "Date", "Time", "Accident_type", "location_type", "Area", "Road", "Section", "Intersection_road", "Longitude", "Latitude"]),
            "valid_coordinate_share": round(valid_coords / max(len(accidents), 1), 4),
            "accident_type_counts": dict(Counter(text(r.get("Accident_type")) for r in accidents if not missing(r.get("Accident_type")))),
            "district_counts": Counter(text(r.get("Area")) for r in accidents if not missing(r.get("Area"))).most_common(),
            "location_type_counts": Counter(text(r.get("location_type")) for r in accidents if not missing(r.get("location_type"))).most_common(),
        },
        "sidewalks": {
            "rows": len(sidewalks),
            "columns": sw_columns,
            "exact_duplicate_rows": exact_sw_dupes,
            "completeness": complete(sidewalks, ["行政區", "道路路名", "道路長度", "人行道長度", "人行道寬度_最小", "人行道寬度_最大"]),
            "numeric_profiles": widths,
            "duplicate_normalized_district_road_keys": len(duplicate_keys),
            "rows_on_duplicate_keys": sum(duplicate_keys.values()),
        },
        "join": {
            "eligible_accident_rows": eligible,
            "strict_primary_match_count": strict,
            "strict_primary_match_share": round(strict / max(eligible, 1), 4),
            "base_primary_match_count": loose,
            "base_primary_match_share": round(loose / max(eligible, 1), 4),
            "base_primary_or_intersection_match_count": either,
            "base_primary_or_intersection_match_share": round(either / max(eligible, 1), 4),
            "top_joined_descriptive_rows": top_joined,
            "caveat": "Section-stripped matching is a sensitivity check and may create false positives; it is not an accepted production join.",
        },
        "commons_decision": {
            "supported_now": [
                "descriptive recurrence/location analysis of A1/A2 accident rows",
                "road-name enrichment with sidewalk context where matching is defensible",
            ],
            "blocked_now": [
                "pedestrian-specific risk inference: pedestrian involvement is absent from this local corridor file",
                "causal inference from co-location or sidewalk width",
                "risk rates: pedestrian/traffic exposure denominators are absent",
                "intersection geometry joins: sidewalk rows have no coordinates",
            ],
            "recommended_state": "researching",
            "recommended_reframe": "Treat this as a corridor-data feasibility problem until pedestrian-specific and exposure evidence is added; do not publish it as a pedestrian-intervention problem yet.",
        },
    }

    (OUT / "taoyuan-real-data-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "taoyuan-top-joined.json").write_text(json.dumps(top_joined, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = f"""# Taoyuan Mobility Real-Data Probe

- Accident rows: **{len(accidents):,}** via `{acc_route}`
- Sidewalk rows: **{len(sidewalks):,}** via `{sw_route}`
- Valid accident coordinates: **{valid_coords / max(len(accidents), 1):.1%}**
- Strict primary road match: **{strict / max(eligible, 1):.1%}**
- Section-stripped primary match: **{loose / max(eligible, 1):.1%}**
- Section-stripped primary-or-intersection match: **{either / max(eligible, 1):.1%}**
- Sidewalk normalized district-road keys with multiple rows: **{len(duplicate_keys):,}**

## Problem Commons verdict

The live rows can test accident-location recurrence and road-name enrichment. They **cannot yet support the original pedestrian-intervention framing**: this local accident file does not identify pedestrian involvement, neither source supplies a pedestrian/traffic exposure denominator, and the sidewalk table is road-level without coordinates/intersection geometry.

The correct Commons behavior is therefore to keep the case **RESEARCHING**, preserve the empirical corridor question, downgrade pedestrian causation/intervention to an unresolved hypothesis, and require a pedestrian-specific case-level source plus exposure evidence before risk ranking or intervention language.
"""
    (OUT / "taoyuan-real-data-report.md").write_text(report, encoding="utf-8")
    print(json.dumps({"accidents": len(accidents), "sidewalks": len(sidewalks), "strict": summary["join"]["strict_primary_match_share"], "base": summary["join"]["base_primary_match_share"], "either": summary["join"]["base_primary_or_intersection_match_share"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
