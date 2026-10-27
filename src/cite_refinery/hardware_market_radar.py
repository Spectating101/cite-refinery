"""Offline, provenance-limited hardware market radar for Cite–Refinery.

Catalog + case queue + dated source observations + explicit HS/external capability
manifest → reproducible comparison board. It DOES NOT scrape, infer sales, rank
ROI, validate supplier compatibility, or authorize purchases/robot control.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
OBS_SCHEMA = "cite_refinery.hardware_market_observations.v1"
CAP_SCHEMA = "cite_refinery.hardware_capability_manifest.v1"
SUP_SCHEMA = "cite_refinery.hardware_supplier_candidates.v1"
REPORT_SCHEMA = "cite_refinery.hardware_market_radar.v1"
IDENT = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{2,89}$")
MARKETS = {"ID", "TW", "GLOBAL"}
KINDS = {"local_offer", "global_reference", "buyer_claim", "supplier_candidate"}
STATES = {"public_listing_unverified", "historical_reference", "operator_report_unverified"}
MATURITY = {"repo_implemented_unverified_physical", "draft_unmerged", "external_candidate"}
DAY = re.compile(r"20\d\d-\d\d-\d\d$")
TAG = re.compile(r"^[a-z][a-z0-9_]{2,49}$")


def _day(raw: Any, name: str) -> date:
    if not isinstance(raw, str) or not DAY.fullmatch(raw):
        raise ValueError(name + " requires ISO date")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(name + " has impossible date") from exc


def _url(raw: Any) -> str:
    if not isinstance(raw, str) or len(raw) > 2048:
        raise ValueError("Attribution requires a bounded HTTPS URL")
    p = urlsplit(raw)
    if (p.scheme != "https" or not p.hostname or p.username or p.password
            or p.fragment or p.hostname in {"localhost", "127.0.0.1", "::1"}):
        raise ValueError("Source URL must be public HTTPS")
    return raw


def _text(raw: Any, name: str) -> str:
    if not isinstance(raw, str) or not 2 <= len(raw.strip()) <= 300:
        raise ValueError(name + " requires bounded string")
    return raw.strip()


def _amount(raw: Any) -> str:
    if isinstance(raw, bool) or raw is None:
        raise ValueError("Amount must be a finite nonnegative decimal")
    try:
        x = Decimal(str(raw))
    except (TypeError, InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid price") from exc
    if not x.is_finite() or x < 0 or x > Decimal("1000000000000"):
        raise ValueError("Price out of bounds")
    if x != x.quantize(Decimal(".01")):
        raise ValueError("Prices use at most 2 decimal places")
    return format(x.quantize(Decimal(".01")), "f")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _tags(raw: Any, name: str) -> list[str]:
    if not isinstance(raw, list) or len(raw) > 18:
        raise ValueError(name + " needs a bounded list")
    if any(not isinstance(s, str) or not TAG.fullmatch(s) for s in raw) or len(set(raw)) != len(raw):
        raise ValueError(name + " must contain unique machine-readable tags")
    return sorted(raw)


def _observations(data: Any, *, today: date, cases: set[str]) -> list[dict[str, Any]]:
    if not isinstance(data, dict) or data.get("schema") != OBS_SCHEMA:
        raise ValueError("Unrecognized observations schema")
    raw = data.get("observations")
    if not isinstance(raw, list) or len(raw) > 10000:
        raise ValueError("Observations must be bounded list")
    ids: set[str] = set()
    out = []
    for o in raw:
        if not isinstance(o, dict):
            raise ValueError("Observation must be an object")
        allowed = {"observation_id", "case_id", "kind", "market", "seller",
                   "product", "observed_on", "source_url", "evidence_state",
                   "exact_variant_matched", "price", "stock_verified",
                   "buyer_verified", "supplier_qualified", "paid_sale_verified"}
        if set(o) - allowed:
            raise ValueError("Unexpected unsupported observation fields")
        oid = o.get("observation_id")
        if not isinstance(oid, str) or not IDENT.fullmatch(oid) or oid in ids:
            raise ValueError("Duplicate or invalid observation ID")
        ids.add(oid)
        if o.get("case_id") not in cases:
            raise ValueError("Observation refers to unknown case")
        kind, market = o.get("kind"), o.get("market")
        if kind not in KINDS or market not in MARKETS:
            raise ValueError("Invalid source kind or market")
        if kind == "local_offer" and market == "GLOBAL":
            raise ValueError("Local offer needs ID or TW market")
        if kind == "global_reference" and market != "GLOBAL":
            raise ValueError("Global reference must use GLOBAL market")
        if o.get("evidence_state") not in STATES:
            raise ValueError("Source quality status must be explicit")
        on = _day(o.get("observed_on"), "observed_on")
        if on > today:
            raise ValueError("Future-dated source observation")
        row = {
            "observation_id": oid,
            "case_id": o["case_id"],
            "kind": kind,
            "market": market,
            "seller": _text(o.get("seller"), "seller"),
            "product": _text(o.get("product"), "product"),
            "observed_on": on.isoformat(),
            "source_url": _url(o.get("source_url")),
            "evidence_state": o["evidence_state"],
            "exact_variant_matched": o.get("exact_variant_matched"),
            "stock_verified": False,
            "independent_transaction_verified": False,
        }
        if type(o.get("exact_variant_matched")) is not bool:
            raise ValueError("Exact variant comparability must be boolean")
        price = o.get("price")
        if price is None:
            row["price"] = None
        else:
            if (not isinstance(price, dict) or set(price) != {"amount", "currency"}
                    or price["currency"] not in {"IDR", "TWD", "USD"}):
                raise ValueError("Each price requires currency and amount")
            row["price"] = {"currency": price["currency"], "amount": _amount(price["amount"])}
        # This intake has no authenticated inventory, buyer receipts or procurement
        # mechanism: untrusted claims must never set these to true.
        if any(o.get(f) is True for f in ("stock_verified", "buyer_verified", "supplier_qualified", "paid_sale_verified")):
            raise ValueError("Public observation cannot self-certify downstream evidence")
        out.append(row)
    return sorted(out, key=lambda x: x["observation_id"])


def _capabilities(data: Any, cases: set[str]) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    if not isinstance(data, dict) or data.get("schema") != CAP_SCHEMA:
        raise ValueError("Unrecognized capability manifest")
    needs = data.get("case_needs")
    if not isinstance(needs, dict) or set(needs) != cases:
        raise ValueError("Manifest requires explicit needs for every case")
    normalized = {cid: _tags(t, "case_needs") for cid, t in needs.items()}
    raw = data.get("capabilities")
    if not isinstance(raw, list) or len(raw) > 1000:
        raise ValueError("Capabilities require bounded list")
    out, seen = [], set()
    for c in raw:
        if not isinstance(c, dict):
            raise ValueError("Capability must be object")
        cid = c.get("id")
        if not isinstance(cid, str) or not IDENT.fullmatch(cid) or cid in seen:
            raise ValueError("Invalid/duplicate capability ID")
        seen.add(cid)
        if c.get("maturity") not in MATURITY:
            raise ValueError("Capability maturity must be explicit")
        out.append({
            "id": cid, "name": _text(c.get("name"), "name"),
            "provides": _tags(c.get("provides"), "provides"),
            "maturity": c["maturity"],
            "source_url": _url(c.get("source_url")),
            "physically_verified": False,
            "procurement_qualified": False,
        })
    return normalized, sorted(out, key=lambda x: x["id"])



def _suppliers(data: Any) -> list[dict[str, Any]]:
    """Research-only sourcing DIRECTORY, with no product/quote/availability claims."""
    if data is None:
        return []
    if not isinstance(data, dict) or data.get("schema") != SUP_SCHEMA:
        raise ValueError("Unrecognized supplier candidate manifest")
    raw = data.get("suppliers")
    if not isinstance(raw, list) or len(raw) > 1000:
        raise ValueError("Suppliers need a bounded list")
    out, seen = [], set()
    for supplier in raw:
        if not isinstance(supplier, dict):
            raise ValueError("Supplier entry must be an object")
        sid = supplier.get("id")
        if not isinstance(sid, str) or not IDENT.fullmatch(sid) or sid in seen:
            raise ValueError("Invalid/duplicate supplier ID")
        seen.add(sid)
        if supplier.get("role") not in {
                "manufacturer_reference", "parts_distributor",
                "fabrication_service", "robotics_module_vendor"}:
            raise ValueError("Unsupported supplier role")
        if supplier.get("status") != "public_catalog_unqualified":
            raise ValueError("Supplier may not self-certify qualification")
        out.append({
            "id": sid,
            "name": _text(supplier.get("name"), "supplier.name"),
            "role": supplier["role"],
            "source_url": _url(supplier.get("source_url")),
            "advertised_capability_tags": _tags(supplier.get("advertised_capability_tags"), "supplier.tags"),
            "status": "public_catalog_unqualified",
            "verified_sku_availability": False,
            "verified_quote_or_moq": False,
            "verified_serves_target_market": False,
            "licensed_for_reuse": None,
            "procurement_qualified": False,
        })
    return sorted(out, key=lambda s: s["id"])

def evaluate(
    catalog: dict[str, Any], queue: dict[str, Any],
    observations: dict[str, Any], capability_manifest: dict[str, Any],
    *, as_of: str, previous: dict[str, Any] | None = None,
    supplier_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    today = _day(as_of, "as_of")
    concepts = catalog.get("concepts")
    if not isinstance(concepts, list) or not concepts or catalog.get("count") != len(concepts):
        raise ValueError("Catalog count or concepts invalid")
    by_atlas: dict[str, dict[str, Any]] = {}
    for c in concepts:
        if not isinstance(c, dict) or not isinstance(c.get("id"), str) or c["id"] in by_atlas:
            raise ValueError("Malformed or duplicated catalog identity")
        by_atlas[c["id"]] = c
    cases = queue.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Case queue missing")
    by_case: dict[str, dict[str, Any]] = {}
    for c in cases:
        if not isinstance(c, dict) or not isinstance(c.get("id"), str) or c["id"] in by_case:
            raise ValueError("Malformed or duplicated case identity")
        if c.get("atlas") not in by_atlas:
            raise ValueError("Case references unknown market concept")
        by_case[c["id"]] = c
    obs = _observations(observations, today=today, cases=set(by_case))
    needs, caps = _capabilities(capability_manifest, set(by_case))
    supplier_candidates = _suppliers(supplier_manifest)
    supplier_edges = [
        {"case_id": cid, "supplier_id": supplier["id"],
         "matched_needs": sorted(set(need).intersection(supplier["advertised_capability_tags"])),
         "relation": "CATALOG_TAG_OVERLAP_ONLY",
         "verified_product_compatibility": False,
         "qualified_supplier_quote": False}
        for cid, need in sorted(needs.items())
        for supplier in supplier_candidates
        if set(need).intersection(supplier["advertised_capability_tags"])
    ]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in obs:
        grouped[item["case_id"]].append(item)
    cap_map: dict[str, list[str]] = defaultdict(list)
    edges = []
    for cid in sorted(by_case):
        for cap in caps:
            overlap = sorted(set(needs[cid]).intersection(cap["provides"]))
            if overlap:
                cap_map[cap["id"]].append(cid)
                edges.append({
                    "case_id": cid, "capability_id": cap["id"],
                    "matched_needs": overlap,
                    "relation": "TAG_OVERLAP_CANDIDATE_ONLY",
                    "verified_design_compatibility": False,
                    "verified_cost_advantage": False,
                })
    board = []
    for cid, c in sorted(by_case.items()):
        rows = grouped[cid]
        local = [o for o in rows if o["kind"] == "local_offer" and o["market"] in {"ID", "TW"}
                 and o["evidence_state"] == "public_listing_unverified"]
        sellers = sorted({(o["market"], o["seller"].casefold()) for o in local})
        markets = sorted({o["market"] for o in local})
        stale = [o["observation_id"] for o in rows if (today - date.fromisoformat(o["observed_on"])).days > 30]
        board.append({
            "case_id": cid, "atlas_id": c["atlas"],
            "sector": c.get("sector"), "concept": c.get("concept"),
            "market_offer_state": "PUBLISHED_LOCAL_OFFER_EXISTS" if local else "UNKNOWN_NO_LOCAL_EVIDENCE",
            "named_local_sellers": len(sellers),
            "markets_with_local_offers": markets,
            "observation_count": len(rows),
            "observation_ids": [o["observation_id"] for o in rows],
            "stale_observation_ids": stale,
            "research_next": (
                "Verify paid demand, delivery/stock, exact SKU/features, all-in unit economics, "
                "compliance, and a physically tested build-or-buy alternative."
            ),
            "matched_capability_ids": sorted({e["capability_id"] for e in edges if e["case_id"] == cid}),
            "candidate_supplier_ids": sorted({e["supplier_id"] for e in supplier_edges if e["case_id"] == cid}),
            "qualified_commercial_opportunity": False,
            "local_shortage_proven": False,
            "customer_demand_verified": False,
            "landed_unit_cost": None,
            "net_margin": None,
            "delivery_authorized": False,
        })
    # An input feed dropping an observation is not evidence of delisting, shortage,
    # or a changed retail price. Emit only a provenance/input diff.
    current = {o["observation_id"]: hashlib.sha256(_canonical(o)).hexdigest() for o in obs}
    change = {"state": "BASELINE", "new": [], "revised": [], "missing_from_input_not_stockout": []}
    if previous is not None:
        if not isinstance(previous, dict) or previous.get("schema") != REPORT_SCHEMA:
            raise ValueError("Prior radar report schema mismatch")
        old = previous.get("observation_fingerprints")
        if not isinstance(old, dict):
            raise ValueError("Prior radar fingerprints missing")
        change = {
            "state": "COMPARED_WITH_PREVIOUS_SNAPSHOT",
            "new": sorted(current.keys() - old.keys()),
            "revised": sorted(k for k in current.keys() & old.keys() if current[k] != old[k]),
            "missing_from_input_not_stockout": sorted(old.keys() - current.keys()),
        }
    shared = [
        {"capability_id": k, "candidate_cases": sorted(v),
         "distinct_sectors": len({by_case[x].get("sector") for x in v}),
         "verified_reuse": False}
        for k, v in cap_map.items() if len({by_case[x].get("sector") for x in v}) > 1
    ]
    shared.sort(key=lambda x: (-x["distinct_sectors"], x["capability_id"]))
    return {
        "schema": REPORT_SCHEMA, "as_of": today.isoformat(),
        "source_snapshot_sha256": hashlib.sha256(_canonical([catalog, queue, observations, capability_manifest, supplier_manifest])).hexdigest(),
        "summary": {
            "catalog_concepts": len(concepts),
            "catalog_sectors": len({x.get("sector") for x in concepts}),
            "screened_cases": len(board),
            "source_observations": len(obs),
            "unqualified_supplier_directory_entries": len(supplier_candidates),
            "candidate_supplier_case_links": len(supplier_edges),
            "cases_with_local_listings": sum(x["named_local_sellers"] > 0 for x in board),
            "qualified_opportunities": 0, "verified_supplier_quotes": 0,
            "verified_customer_payments": 0, "physically_validated_builds": 0,
            "possible_cross_sector_reuse_groups": len(shared),
        },
        "cases": board,
        "observations": obs,
        "observation_fingerprints": current,
        "capabilities": caps,
        "candidate_capability_edges": edges,
        "supplier_candidates": supplier_candidates,
        "candidate_supplier_edges": supplier_edges,
        "cross_sector_reuse": shared,
        "change_detection": change,
        "safety_boundary": "Offline sources only; listings are not in-stock proof, tag matches not compatibility, no ranking of profit, no purchasing or outreach.",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Offline evidence-bounded global hardware opportunity radar")
    base = ROOT / "research_materials/opportunity_conversion"
    p.add_argument("--catalog", type=Path, default=base / "hardware_market_universe_64_unverified_20261028.json")
    p.add_argument("--cases", type=Path, default=base / "hardware_12_case_post_research_evidence_queue_20261028.json")
    p.add_argument("--observations", type=Path, default=base / "hardware_radar_observations_seed_20261028.json")
    p.add_argument("--capabilities", type=Path, default=base / "hardware_radar_capabilities_20261028.json")
    p.add_argument("--suppliers", type=Path, default=base / "hardware_radar_supplier_candidates_20261028.json")
    p.add_argument("--as-of", required=True, help="Explicit YYYY-MM-DD; never quietly use wall-clock time")
    p.add_argument("--previous", type=Path, default=None, help="Previous radar output; compare by observation ID and fingerprint")
    p.add_argument("--output", type=Path, default=None, help="Without this option, print JSON to stdout; no disk writes")
    a = p.parse_args(argv)
    def load(path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))
    report = evaluate(load(a.catalog), load(a.cases), load(a.observations), load(a.capabilities),
                      as_of=a.as_of, previous=load(a.previous) if a.previous else None,
                      supplier_manifest=load(a.suppliers))
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if a.output:
        a.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
