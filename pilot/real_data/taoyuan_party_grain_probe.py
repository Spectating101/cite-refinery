from __future__ import annotations

import csv
import io
import json
import re
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

BASE = "https://opendata.tycg.gov.tw"
PARTY_PID = "08d560b5-7cf2-4909-8a02-da39c74d8b09"
CORRIDOR_PID = "d06dd55d-aac7-4b17-9211-82cbf467cc2d"
OUT = Path("real-data-output")
UA = {"User-Agent": "ProblemCommonsV0.1/party-grain-probe"}


def get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.read()


def get_json(path: str, params: dict[str, Any]) -> Any:
    return json.loads(get_bytes(BASE + path + "?" + urllib.parse.urlencode(params)).decode("utf-8-sig"))


def dicts(node: Any) -> list[dict[str, Any]]:
    out = []
    if isinstance(node, dict):
        out.append(node)
        for v in node.values(): out.extend(dicts(v))
    elif isinstance(node, list):
        for v in node: out.extend(dicts(v))
    return out


def resource(pid: str, year: str = "114") -> dict[str, Any]:
    payload = get_json("/api/v1/resource.info", {"pid": pid})
    rows = []
    seen = set()
    for row in dicts(payload):
        rid = row.get("rid")
        if rid and str(rid) not in seen:
            seen.add(str(rid)); rows.append(row)
    if not rows: raise RuntimeError(f"no resources for {pid}")
    for row in rows:
        name = str(row.get("name") or row.get("schedule_name") or "")
        if year in name: return row
    return rows[-1]


def decode_csv(raw: bytes) -> list[dict[str, Any]]:
    for enc in ("utf-8-sig", "utf-8", "big5", "cp950"):
        try:
            rows = list(csv.DictReader(io.StringIO(raw.decode(enc))))
            if rows: return rows
        except UnicodeDecodeError:
            pass
    raise RuntimeError("CSV decode failed")


def rows(resource: dict[str, Any]) -> list[dict[str, Any]]:
    url = str(resource.get("url") or "")
    if url.startswith("/"): url = BASE + url
    if url:
        return decode_csv(get_bytes(url))
    raise RuntimeError("resource has no direct URL")


def text(v: Any) -> str:
    return "" if v is None else str(v).strip()


def number(v: Any) -> int | None:
    m = re.search(r"\d+", text(v))
    return int(m.group()) if m else None


def main() -> None:
    OUT.mkdir(exist_ok=True)
    party_resource = resource(PARTY_PID)
    corridor_resource = resource(CORRIDOR_PID)
    party = rows(party_resource)
    corridor = rows(corridor_resource)

    rank_field = next((k for k in party[0] if "順位" in k), None)
    action_field = next((k for k in party[0] if "行動狀態" in k), None)
    vehicle_major = next((k for k in party[0] if "使用車種_大類別" in k), None)
    vehicle_minor = next((k for k in party[0] if "使用車種_子類別" in k), None)
    district_field = next((k for k in party[0] if "市區鄉鎮名稱" in k), None)
    if not rank_field:
        raise RuntimeError("party resource missing rank field; columns=" + repr(list(party[0])))

    ranks = Counter(text(r.get(rank_field)) for r in party)
    numeric_ranks = Counter(number(r.get(rank_field)) for r in party if number(r.get(rank_field)) is not None)
    first_party_rows = numeric_ranks.get(1, 0)
    action_counts = Counter(text(r.get(action_field)) for r in party) if action_field else Counter()
    vehicle_major_counts = Counter(text(r.get(vehicle_major)) for r in party) if vehicle_major else Counter()
    districts = Counter(text(r.get(district_field)) for r in party) if district_field else Counter()

    corridor_keys = Counter(json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(",", ":")) for r in corridor)
    distinct_corridor = len(corridor_keys)
    corridor_mult = Counter(corridor_keys.values())

    result = {
        "schema": "problem-commons-party-grain-probe/v0.1",
        "party_source": {"pid": PARTY_PID, "rid": party_resource.get("rid"), "name": party_resource.get("name") or party_resource.get("schedule_name")},
        "corridor_source": {"pid": CORRIDOR_PID, "rid": corridor_resource.get("rid"), "name": corridor_resource.get("name") or corridor_resource.get("schedule_name")},
        "counts": {
            "party_rows": len(party),
            "corridor_rows": len(corridor),
            "distinct_corridor_full_rows": distinct_corridor,
            "first_party_rows": first_party_rows,
            "party_minus_corridor": len(party)-len(corridor),
            "first_party_minus_distinct_corridor": first_party_rows-distinct_corridor,
        },
        "party_columns": list(party[0]),
        "party_rank_field": rank_field,
        "party_rank_counts": dict(ranks),
        "numeric_party_rank_counts": dict(sorted(numeric_ranks.items())),
        "corridor_exact_multiplicity_distribution": dict(sorted(corridor_mult.items())),
        "top_action_statuses": action_counts.most_common(30),
        "top_vehicle_major": vehicle_major_counts.most_common(20),
        "district_counts_party_rows": districts.most_common(),
        "grain_test": {
            "party_total_matches_corridor_total": len(party) == len(corridor),
            "first_party_matches_distinct_corridor": first_party_rows == distinct_corridor,
            "interpretation": "If both equalities hold, the strongest parsimonious explanation is that the corridor export is at party-record grain after party attributes were projected away; identical location rows must not be deduplicated as data errors. If only approximate, exclusions or source transformations require further reconciliation."
        }
    }
    (OUT / "taoyuan-party-grain-summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({"party": len(party), "corridor": len(corridor), "first_party": first_party_rows, "distinct_corridor": distinct_corridor, "rank_counts": dict(sorted(numeric_ranks.items()))}, ensure_ascii=False))


if __name__ == "__main__": main()
