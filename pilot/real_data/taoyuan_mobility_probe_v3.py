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
ACCIDENT_114_RID = "e8a4e4b6-ab84-4365-b612-fd0f38e7c011"
SIDEWALK_PID = "1de35418-b949-4ace-89a2-cb92714be3eb"
SIDEWALK_RID = "6a4126e6-e1ee-43e2-b771-e49f6a532c45"
ANNUAL_COUNT_PID = "2bc7f575-acaf-436c-a6ca-be8af3cf19f2"
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
        raise RuntimeError("resource.info returned no rid for " + pid + ": " + json.dumps(payload, ensure_ascii=False)[:1200])
    return list(unique.values())


def choose(resources: list[dict[str, Any]], *, fallback_rid: str | None = None, year: str | None = None) -> dict[str, Any]:
    if year:
        for row in resources:
            name = str(row.get("name") or row.get("schedule_name") or row.get("file_name") or "")
            if year in name:
                return row
    if fallback_rid:
        for row in resources:
            if str(row.get("rid")) == fallback_rid:
                return row
        return {"rid": fallback_rid}
    return resources[-1]


def decode_csv(raw: bytes) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "big5", "cp950"):
        try:
            rows = list(csv.DictReader(io.StringIO(raw.decode(encoding))))
            if rows:
                return rows
        except (UnicodeDecodeError, csv.Error) as exc:
            last_error = exc
    raise RuntimeError(f"could not decode CSV: {last_error}")


def resource_rows(resource: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    url = str(resource.get("url") or "")
    if url:
        if url.startswith("/"):
            url = BASE + url
        try:
            return decode_csv(get_bytes(url)), "resource_csv"
        except Exception as exc:
            print(f"CSV route failed rid={resource.get('rid')}: {exc}; falling back to datastore")
    rid = str(resource.get("rid"))
    all_rows: list[dict[str, Any]] = []
    offset = 0
    for _ in range(2000):
        payload = get_json("/api/v1/dataset.datastore", {"rid": rid, "limit": 2000, "offset": offset, "format": "json"})
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
        raise RuntimeError("datastore returned no rows for " + rid)
    return all_rows, "datastore"


def text(v: Any) -> str:
    return "" if v is None else str(v).strip()


def missing(v: Any) -> bool:
    return text(v).lower() in {"", "none", "null", "nan", "n/a", "na", "-"}


def num(v: Any) -> float | None:
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text(v).replace(",", ""))
    return float(m.group(0)) if m else None


def norm(v: Any) -> str:
    return re.sub(r"[\s　,，.。．、()（）\-_/]", "", text(v).replace("臺", "台"))


SECTION = re.compile(r"[一二三四五六七八九十百零〇0-9]+段$")


def base_road(v: Any) -> str:
    return SECTION.sub("", norm(v))


def full_accident_road(row: dict[str, Any]) -> str:
    road = norm(row.get("Road"))
    section = norm(row.get("Section"))
    if section and not section.endswith("段"):
        section += "段"
    return road + section


def row_key(row: dict[str, Any]) -> str:
    return json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def dedupe(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], Counter[str]]:
    counts: Counter[str] = Counter(row_key(r) for r in rows)
    first: dict[str, dict[str, Any]] = {}
    for row in rows:
        first.setdefault(row_key(row), row)
    return list(first.values()), counts


def complete(rows: list[dict[str, Any]], keys: list[str]) -> dict[str, float]:
    n = max(len(rows), 1)
    return {k: round(sum(not missing(r.get(k)) for r in rows) / n, 4) for k in keys}


def quantiles(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    values = sorted(values)
    def q(p: float) -> float:
        idx = (len(values) - 1) * p
        lo = int(idx)
        hi = min(lo + 1, len(values) - 1)
        f = idx - lo
        return values[lo] * (1 - f) + values[hi] * f
    return {"n": len(values), "min": values[0], "p50": q(.5), "p95": q(.95), "p99": q(.99), "mean": statistics.mean(values), "max": values[-1]}


def join_stats(accidents: list[dict[str, Any]], sidewalks: list[dict[str, Any]]) -> dict[str, Any]:
    sw_full: dict[str, set[str]] = defaultdict(set)
    sw_base: dict[str, set[str]] = defaultdict(set)
    sw_rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in sidewalks:
        district = norm(row.get("行政區")); road = norm(row.get("道路路名")); base = base_road(row.get("道路路名"))
        if district and road:
            sw_full[district].add(road); sw_base[district].add(base); sw_rows[(district, base)].append(row)
    eligible = strict = loose = either = 0
    matched: Counter[tuple[str, str]] = Counter()
    for row in accidents:
        district = norm(row.get("Area")); road = norm(row.get("Road"))
        if not district or not road:
            continue
        eligible += 1
        full = full_accident_road(row); primary = base_road(row.get("Road")); intersection = base_road(row.get("Intersection_road"))
        if full in sw_full[district] or (not norm(row.get("Section")) and road in sw_full[district]):
            strict += 1
        if primary in sw_base[district]:
            loose += 1; matched[(district, primary)] += 1
        if primary in sw_base[district] or (intersection and intersection in sw_base[district]):
            either += 1
    top = []
    for (district, road), count in matched.most_common(20):
        rows = sw_rows[(district, road)]
        mins = [x for x in (num(r.get("人行道寬度_最小")) for r in rows) if x is not None]
        maxs = [x for x in (num(r.get("人行道寬度_最大")) for r in rows) if x is not None]
        top.append({"district": district, "road_base": road, "distinct_accident_rows_114": count, "sidewalk_rows": len(rows), "sidewalk_min_width_median": statistics.median(mins) if mins else None, "sidewalk_max_width_median": statistics.median(maxs) if maxs else None})
    return {"eligible": eligible, "strict_count": strict, "strict_share": round(strict/max(eligible,1),4), "base_count": loose, "base_share": round(loose/max(eligible,1),4), "either_count": either, "either_share": round(either/max(eligible,1),4), "top_joined": top}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    acc_resource = choose(resource_info(ACCIDENT_PID), fallback_rid=ACCIDENT_114_RID, year="114")
    sw_resource = choose(resource_info(SIDEWALK_PID), fallback_rid=SIDEWALK_RID)
    count_resource = choose(resource_info(ANNUAL_COUNT_PID), year="114")
    raw_acc, acc_route = resource_rows(acc_resource)
    sidewalks, sw_route = resource_rows(sw_resource)
    annual_counts, count_route = resource_rows(count_resource)
    distinct_acc, multiplicities = dedupe(raw_acc)

    aggregate_total = int(sum(num(r.get("count")) or 0 for r in annual_counts))
    mult_dist = Counter(multiplicities.values())
    duplicated_unique_rows = sum(1 for n in multiplicities.values() if n > 1)
    max_mult = max(multiplicities.values()) if multiplicities else 0

    coord_valid = sum(1 for r in distinct_acc if (lambda lon,lat: lon is not None and lat is not None and 120.8 <= lon <= 121.6 and 24.4 <= lat <= 25.4)(num(r.get("Longitude")), num(r.get("Latitude"))))
    join_raw = join_stats(raw_acc, sidewalks)
    join_distinct = join_stats(distinct_acc, sidewalks)

    sidewalk_profiles = {}
    anomaly_rows: dict[str, list[dict[str, Any]]] = {}
    thresholds = {"道路長度": 50000.0, "人行道長度": 50000.0, "人行道寬度_最小": 20.0, "人行道寬度_最大": 20.0}
    for field, threshold in thresholds.items():
        vals = [x for x in (num(r.get(field)) for r in sidewalks) if x is not None]
        sidewalk_profiles[field] = quantiles(vals) | {"zero_share": round(sum(x == 0 for x in vals)/max(len(vals),1),4), "above_plausibility_threshold": sum(x > threshold for x in vals), "threshold": threshold}
        bad = []
        for r in sidewalks:
            value = num(r.get(field))
            if value is not None and value > threshold:
                bad.append({"行政區": text(r.get("行政區")), "道路路名": text(r.get("道路路名")), field: value})
        anomaly_rows[field] = sorted(bad, key=lambda x: x[field], reverse=True)[:10]

    sw_key_counts = Counter((norm(r.get("行政區")), base_road(r.get("道路路名"))) for r in sidewalks if norm(r.get("行政區")) and base_road(r.get("道路路名")))
    sw_dup_keys = {k: v for k,v in sw_key_counts.items() if v > 1}

    coord_groups: dict[tuple[str,str], list[dict[str, Any]]] = defaultdict(list)
    for r in distinct_acc:
        lon, lat = text(r.get("Longitude")), text(r.get("Latitude"))
        if lon and lat:
            coord_groups[(lon,lat)].append(r)
    hotspots = []
    for (lon,lat), rows in sorted(coord_groups.items(), key=lambda kv: len(kv[1]), reverse=True)[:20]:
        roads = Counter((text(r.get("Area")), text(r.get("Road")), text(r.get("Intersection_road"))) for r in rows)
        district, road, intersection = roads.most_common(1)[0][0]
        hotspots.append({"longitude": lon, "latitude": lat, "distinct_accident_rows_114": len(rows), "district": district, "road": road, "intersection_road": intersection, "A1": sum(text(r.get("Accident_type"))=="A1" for r in rows), "A2": sum(text(r.get("Accident_type"))=="A2" for r in rows)})

    reconciliation = {
        "raw_corridor_rows": len(raw_acc),
        "distinct_full_rows": len(distinct_acc),
        "official_annual_time_table_total": aggregate_total,
        "distinct_minus_official": len(distinct_acc) - aggregate_total,
        "raw_minus_official": len(raw_acc) - aggregate_total,
        "exact_duplicate_rows_removed": len(raw_acc) - len(distinct_acc),
        "unique_row_patterns_repeated": duplicated_unique_rows,
        "maximum_exact_multiplicity": max_mult,
        "multiplicity_distribution": dict(sorted(mult_dist.items())),
        "grain_assessment": "confirmed_distinct_full_row_as_incident_proxy" if len(distinct_acc) == aggregate_total else "unresolved",
    }

    summary = {
        "schema": "problem-commons-real-data-probe/v0.3",
        "sources": {"corridor": {"pid": ACCIDENT_PID, "rid": acc_resource.get("rid"), "route": acc_route}, "sidewalk": {"pid": SIDEWALK_PID, "rid": sw_resource.get("rid"), "route": sw_route}, "annual_count": {"pid": ANNUAL_COUNT_PID, "rid": count_resource.get("rid"), "route": count_route}},
        "reconciliation": reconciliation,
        "distinct_accidents": {"rows": len(distinct_acc), "completeness": complete(distinct_acc, ["Year","Date","Time","Accident_type","location_type","Area","Road","Section","Intersection_road","Longitude","Latitude"]), "valid_coordinate_share": round(coord_valid/max(len(distinct_acc),1),4), "A1": sum(text(r.get("Accident_type"))=="A1" for r in distinct_acc), "A2": sum(text(r.get("Accident_type"))=="A2" for r in distinct_acc), "district_counts": Counter(text(r.get("Area")) for r in distinct_acc).most_common()},
        "sidewalk_quality": {"rows": len(sidewalks), "profiles": sidewalk_profiles, "anomaly_examples": anomaly_rows, "duplicate_normalized_district_road_keys": len(sw_dup_keys), "rows_on_duplicate_normalized_keys": sum(sw_dup_keys.values())},
        "join_raw": join_raw,
        "join_distinct": join_distinct,
        "exact_coordinate_recurrence": hotspots,
        "commons_update": {
            "new_findings": ["Raw 2025 corridor export contains extensive exact duplication and must not be treated as incident grain without reconciliation.", "Independent annual-count data can validate whether exact full-row deduplication recovers the intended accident-event count.", "Sidewalk infrastructure measurements contain extreme values that require validation/outlier handling before any association analysis.", "Road-name joins cover only part of accident records and become materially more permissive when road-section information is stripped."],
            "still_blocked": ["Pedestrian-specific corridor attribution is not available in the corridor file.", "Exposure denominators are absent.", "Road-level sidewalk records do not locate intersection geometry.", "No causal intervention claim is supported."],
            "recommended_status": "researching",
        },
    }
    (OUT / "taoyuan-real-data-v3-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "taoyuan-hotspots-v3.json").write_text(json.dumps(hotspots, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = f"""# Taoyuan real-data probe V0.3 — grain reconciliation

## Accident grain
- Raw corridor rows: **{len(raw_acc):,}**
- Distinct full rows: **{len(distinct_acc):,}**
- Independent official 2025 annual-count total: **{aggregate_total:,}**
- Exact duplicate rows removed: **{len(raw_acc)-len(distinct_acc):,}**
- Reconciliation: **{reconciliation['grain_assessment']}**

## Distinct-row join coverage
- Strict district + road/section: **{join_distinct['strict_share']:.1%}**
- Section-stripped primary road: **{join_distinct['base_share']:.1%}**
- Section-stripped primary-or-intersection road: **{join_distinct['either_share']:.1%}**

## Sidewalk measurement integrity
- Normalized district-road keys with >1 row: **{len(sw_dup_keys):,}**
- Road length >50 km: **{sidewalk_profiles['道路長度']['above_plausibility_threshold']}** rows
- Sidewalk length >50 km: **{sidewalk_profiles['人行道長度']['above_plausibility_threshold']}** rows
- Minimum sidewalk width >20 m: **{sidewalk_profiles['人行道寬度_最小']['above_plausibility_threshold']}** rows
- Maximum sidewalk width >20 m: **{sidewalk_profiles['人行道寬度_最大']['above_plausibility_threshold']}** rows

## Commons consequence
The real case now has an explicit data-quality stage before hotspot interpretation. Raw corridor rows cannot be counted directly, permissive road normalization cannot be treated as a verified join, and sidewalk measurements require plausibility review. Even if recurrence is real, pedestrian-specific risk and intervention remain blocked until party-level pedestrian evidence and exposure are added.
"""
    (OUT / "taoyuan-real-data-v3-report.md").write_text(report, encoding="utf-8")
    print(json.dumps({"raw": len(raw_acc), "distinct": len(distinct_acc), "official": aggregate_total, "grain": reconciliation["grain_assessment"], "strict": join_distinct["strict_share"], "base": join_distinct["base_share"], "either": join_distinct["either_share"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
