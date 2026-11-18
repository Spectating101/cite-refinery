"""Byte-bound engineering handoff for the illustrative hardware job.

The core uses the existing Refinery subprocess runner. Engineering engines live
in optional scripts, so importing this module adds no CAD dependency. Receipts
are local execution evidence, not authenticated third-party attestations or
permission to manufacture. Physical release is never granted here.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

SCHEMA = "cite_refinery.hardware_substitution_package.v1"
REQUIRED_MANUFACTURING_FORMATS = {"gtl", "gbl", "gts", "gbs", "gto", "gm1", "gbrjob", "drl"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path.name}")
    return value


def _within(root: Path, path: Path) -> Path:
    path = path.resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"missing artifact or path outside package: {path.name}")
    return path


def _descriptor(root: Path, path: Path) -> dict[str, str]:
    path = _within(root, path)
    return {"path": path.relative_to(root.resolve()).as_posix(), "sha256": sha256_file(path)}


def _checked(root: Path, descriptor: dict[str, Any]) -> Path:
    if not isinstance(descriptor, dict) or not isinstance(descriptor.get("path"), str):
        raise ValueError("missing artifact descriptor")
    relative = Path(descriptor["path"])
    if relative.is_absolute():
        raise ValueError("package paths must be relative")
    path = _within(root, root / relative)
    if descriptor.get("sha256") != sha256_file(path):
        raise ValueError(f"artifact hash mismatch: {relative}")
    return path


def _receipt_path(root: Path, receipt_path: Path, value: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("missing receipt artifact path")
    return _within(root, receipt_path.parent / value)


def _number(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"finite number required: {label}")
    if value < 0 or (positive and value == 0):
        raise ValueError(f"invalid nonnegative quantity: {label}")
    return float(value)


def validate_job(job: dict[str, Any]) -> None:
    if job.get("schema") != "cite_refinery.hardware_substitution_job.v1":
        raise ValueError("unknown job schema")
    quantity = job.get("quantity")
    if type(quantity) is not int or quantity <= 0:
        raise ValueError("positive integer job quantity required")
    configs = job.get("configurations", [])
    if not configs or len({c["id"] for c in configs}) != len(configs):
        raise ValueError("unique nonempty configurations required")
    if any(type(c.get("quantity")) is not int or c["quantity"] <= 0 for c in configs):
        raise ValueError("positive integer configuration quantities required")
    if sum(c["quantity"] for c in configs) != quantity:
        raise ValueError("configuration quantities must equal job quantity")
    for c in configs:
        _number(c["wall_mm"], "wall thickness", positive=True)
    for key in ("width_mm", "height_mm", "thickness_mm"):
        _number(job["board"][key], "board " + key, positive=True)
    for key in ("connector_height_mm", "opening_clearance_mm", "lid_bottom_z_mm", "board_margin_mm"):
        _number(job["mechanical_fixture"][key], key, positive=True)
    for key in ("minimum_clearance_mm", "minimum_track_width_mm", "track_width_mm"):
        _number(job["routing_rules"][key], key, positive=True)
    if job["routing_rules"]["track_width_mm"] < job["routing_rules"]["minimum_track_width_mm"]:
        raise ValueError("routing width is below the native minimum")
    if job.get("release_policy") != {"digital_review_only": True, "physical_release_authorized": False}:
        raise ValueError("this fixture cannot authorize physical release")


def validate_board_contract(job: dict[str, Any], engineering: dict[str, Any]) -> None:
    revision = engineering.get("revision")
    if revision not in {"A", "B"}:
        raise ValueError("unknown board revision")
    recipe = job["revision_" + revision.lower()]
    expected = {ref: value for ref, value in recipe.items() if ref != "id"}
    bom = engineering.get("bom", [])
    actual = {row["reference"]: row["part_id"] for row in bom}
    if len(actual) != len(bom) or actual != expected or any(type(row.get("quantity_per_board")) is not int or row["quantity_per_board"] != 1 for row in bom):
        raise ValueError("BOM does not match the specified connector revision")
    connectors = engineering.get("connectors", [])
    if len(connectors) != len(expected) or {c["reference"] for c in connectors} != set(expected):
        raise ValueError("missing or duplicate connector observation")
    for connector in connectors:
        if connector.get("footprint") != expected[connector["reference"]]:
            raise ValueError("observed footprint differs from BOM")
        pins = connector.get("pins", [])
        observed = {str(pin["number"]): pin["net"] for pin in pins}
        if len(observed) != len(pins) or observed != job["interface"]:
            raise ValueError("connector pin semantics changed")
    if engineering.get("checks", {}).get("digital_electrical_pass") is not True:
        raise ValueError("electrical check missing or failed")
    if engineering.get("checks", {}).get("pin_semantics_match") is not True:
        raise ValueError("pin semantics check missing or failed")


def derive_material_plan(job: dict[str, Any], engineering: dict[str, Any], geometry: dict[str, Any]) -> dict[str, Any]:
    """Use the saved-board BOM and reimported solid volumes, not a parallel BOM."""
    validate_job(job)
    validate_board_contract(job, engineering)
    demand: Counter[str] = Counter()
    for row in engineering["bom"]:
        demand[row["part_id"]] += row["quantity_per_board"] * job["quantity"]
    supply = job["supply_fixture"]
    old_part = job["revision_a"]["J1"]
    new_part = job["revision_b"]["J1"]
    free_old = _number(supply["free_old_connector_stock"], "free old stock")
    free_new = _number(supply["free_new_connector_stock"], "free new stock")
    reserved = _number(supply["reserved_new_connector_stock"], "reserved stock")
    incoming = _number(supply["incoming_new_connector_stock"], "incoming stock")
    pack = supply["candidate_supplier_pack_size"]
    if type(pack) is not int or pack <= 0:
        raise ValueError("positive integer supplier pack size required")
    old_shortage = max(0, demand[old_part] - free_old)
    new_shortage = max(0, demand[new_part] - free_new - incoming)
    purchase_units = math.ceil(new_shortage / pack) * pack
    price = _number(supply["candidate_supplier_unit_price"], "unit price")
    configs = {c["id"]: c for c in job["configurations"]}
    variants = geometry.get("variants", [])
    if len(variants) != len(configs) or {v["configuration_id"] for v in variants} != set(configs):
        raise ValueError("geometry configuration set differs from job")
    volume = 0.0
    for variant in variants:
        config = configs[variant["configuration_id"]]
        if variant["quantity"] != config["quantity"]:
            raise ValueError("geometry quantity differs from job")
        volume += _number(variant["measurements"]["material_volume_mm3"], "measured material volume", positive=True) * config["quantity"]
    rate = _number(supply["deposition_mm3_per_second_fixture"], "deposition rate", positive=True)
    overhead = _number(supply["print_overhead_factor_fixture"], "print overhead", positive=True)
    hours = volume / rate / 3600 * overhead
    available = _number(supply["printing_available_hours"], "printer hours")
    return {
        "evidence_status": "synthetic inventory, price, lead-time and print-throughput inputs; generated BOM and measured solid volume",
        "demand_by_footprint": dict(demand),
        "free_new_stock_used": min(free_new, demand[new_part]),
        "reserved_new_stock_used": 0,
        "reserved_new_stock_preserved": reserved,
        "old_connector_shortage": old_shortage,
        "new_connector_shortage": new_shortage,
        "purchase_new_units": purchase_units,
        "purchase_packs": purchase_units // pack,
        "purchase_cost_fixture": purchase_units * price,
        "currency": supply["currency"],
        "total_solid_volume_mm3": round(volume, 6),
        "estimated_print_hours_fixture": round(hours, 6),
        "print_capacity_available_hours_fixture": available,
        "additional_print_capacity_hours_fixture": round(max(0, hours - available), 6),
        "materials_feasible_in_fixture": old_shortage == 0,
        "print_capacity_feasible_in_fixture": hours <= available,
        "fixture_feasible": old_shortage == 0 and hours <= available,
        "commercial_commitment_made": False,
        "note": "Free stock is already net of reservations. Volume-based hours are a planning proxy, not a sliced machine job.",
    }


def build_manifest(root: Path, job_path: Path, engineering_path: Path, geometry_path: Path) -> dict[str, Any]:
    root = root.resolve()
    engineering = _read(engineering_path)
    geometry = _read(geometry_path)
    drc = engineering["checks"]["drc"]
    files = {"job": _descriptor(root, job_path), "engineering": _descriptor(root, engineering_path),
             "geometry": _descriptor(root, geometry_path),
             "board": _descriptor(root, _receipt_path(root, engineering_path, engineering["board_path"])),
             "drc": _descriptor(root, _receipt_path(root, engineering_path, drc["report_path"])),
             "project": _descriptor(root, _receipt_path(root, engineering_path, drc["checked_project_path"])),
             "rules": _descriptor(root, _receipt_path(root, engineering_path, drc["checked_rules_path"]))}
    board_path = _receipt_path(root, engineering_path, engineering["board_path"])
    for kind in ("dsn", "ses"):
        files[kind] = _descriptor(root, board_path.with_suffix("." + kind))
    manufacturing = engineering.get("manufacturing_artifacts", [])
    if not REQUIRED_MANUFACTURING_FORMATS.issubset({item.get("format") for item in manufacturing}):
        raise ValueError("missing required fabrication plot or drill output")
    if len({item["path"] for item in manufacturing}) != len(manufacturing):
        raise ValueError("duplicate manufacturing artifact path")
    for item in manufacturing:
        files["manufacturing:" + item["path"]] = _descriptor(root, _receipt_path(root, engineering_path, item["path"]))
    for variant in geometry["variants"]:
        for kind, item in variant["files"].items():
            key = f"{variant['configuration_id']}:{kind}"
            files[key] = _descriptor(root, _receipt_path(root, geometry_path, item["path"]))
    return {"schema": SCHEMA, "revision": engineering["revision"], "files": files,
            "physical_release_authorized": False,
            "claim_scope": "local digital artifact interoperability under an illustrative fixture"}


def review_fingerprint(manifest: dict[str, Any]) -> str:
    """Content identity only. A matching fingerprint is not user authorization."""
    return hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def review_matches(manifest: dict[str, Any], previous_fingerprint: str) -> bool:
    return review_fingerprint(manifest) == previous_fingerprint


def verify_package(root: Path, manifest: dict[str, Any], *, current_job_path: Path | None = None,
                   previous_review_fingerprint: str | None = None) -> dict[str, Any]:
    if manifest.get("schema") != SCHEMA or manifest.get("physical_release_authorized") is not False:
        raise ValueError("invalid package schema or physical-release assertion")
    files = manifest.get("files", {})
    if not {"job", "engineering", "geometry", "board", "drc", "project", "rules", "dsn", "ses"}.issubset(files):
        raise ValueError("missing required package artifacts")
    paths = {key: _checked(root, value) for key, value in files.items()}
    if current_job_path is not None and sha256_file(current_job_path) != files["job"]["sha256"]:
        raise ValueError("job changed after engineering checks")
    job = _read(paths["job"])
    engineering = _read(paths["engineering"])
    geometry = _read(paths["geometry"])
    validate_job(job)
    validate_board_contract(job, engineering)
    if engineering.get("schema") != "cite_refinery.hardware_board.v1" or geometry.get("schema") != "cite_refinery.hardware_geometry.v1":
        raise ValueError("unknown engineering receipt schema")
    if engineering.get("job_id") != job["job_id"] or geometry.get("job_id") != job["job_id"]:
        raise ValueError("mixed job identities")
    if not (manifest["revision"] == engineering["revision"] == geometry.get("revision")):
        raise ValueError("mixed revisions")
    board_sha = files["board"]["sha256"]
    if engineering.get("board_sha256") != board_sha or engineering.get("source_hashes", {}).get("job") != files["job"]["sha256"]:
        raise ValueError("engineering receipt belongs to different board or job")
    if _receipt_path(root, paths["engineering"], engineering["board_path"]) != paths["board"]:
        raise ValueError("board receipt path mismatch")
    drc_receipt = engineering["checks"]["drc"]
    if drc_receipt.get("checked_board_sha256") != board_sha or drc_receipt.get("report_sha256") != files["drc"]["sha256"]:
        raise ValueError("DRC not bound to current board and report")
    if _receipt_path(root, paths["engineering"], drc_receipt["report_path"]) != paths["drc"]:
        raise ValueError("DRC report path mismatch")
    for kind, source_key, receipt_key in (("project", "project", "checked_project"), ("rules", "native_rules", "checked_rules")):
        if engineering["source_hashes"].get(source_key) != files[kind]["sha256"] or drc_receipt.get(receipt_key + "_sha256") != files[kind]["sha256"]:
            raise ValueError("native project or rules changed after DRC")
        if _receipt_path(root, paths["engineering"], drc_receipt[receipt_key + "_path"]) != paths[kind]:
            raise ValueError("native project or rules path mismatch")
    for kind in ("dsn", "ses"):
        if engineering["source_hashes"].get(kind) != files[kind]["sha256"]:
            raise ValueError("routing interchange hash mismatch")
    manufacturing = engineering.get("manufacturing_artifacts", [])
    if not REQUIRED_MANUFACTURING_FORMATS.issubset({item.get("format") for item in manufacturing}):
        raise ValueError("missing required fabrication plot or drill output")
    if len({item["path"] for item in manufacturing}) != len(manufacturing):
        raise ValueError("duplicate manufacturing artifact path")
    for item in manufacturing:
        key = "manufacturing:" + item["path"]
        if key not in files or item.get("sha256") != files[key]["sha256"] or item.get("source_board_sha256") != board_sha:
            raise ValueError("manufacturing artifact is stale or missing")
        if _receipt_path(root, paths["engineering"], item["path"]) != paths[key]:
            raise ValueError("manufacturing artifact path mismatch")
    native_drc = _read(paths["drc"])
    if not isinstance(native_drc.get("violations"), list) or not isinstance(native_drc.get("unconnected_items"), list):
        raise ValueError("missing native DRC result arrays")
    errors = [item for item in native_drc["violations"] if item.get("severity") != "warning"]
    parity = native_drc.get("schematic_parity", [])
    if not isinstance(parity, list) or any(item.get("severity") != "warning" for item in parity):
        raise ValueError("native schematic parity errors or malformed result")
    if errors or native_drc["unconnected_items"] or drc_receipt.get("exit_code") not in (0, 5):
        raise ValueError("native DRC errors or unconnected items")
    if geometry.get("source_board_sha256") != board_sha or geometry.get("source_engineering_sha256") != files["engineering"]["sha256"] or geometry.get("job_sha256") != files["job"]["sha256"]:
        raise ValueError("geometry receipt belongs to different board, engineering or job")
    if geometry.get("all_checks_pass") is not True or geometry.get("physical_release_authorized") is not False:
        raise ValueError("mechanical check missing, failed or overclaimed")
    for variant in geometry.get("variants", []):
        measurements = variant["measurements"]
        configs = {config["id"]: config for config in job["configurations"]}
        if variant.get("configuration_id") not in configs or variant.get("wall_mm") != configs[variant["configuration_id"]]["wall_mm"]:
            raise ValueError("geometry wall configuration differs from job")
        base_volume = _number(measurements["base_volume_mm3"], "base volume", positive=True)
        lid_volume = _number(measurements["lid_volume_mm3"], "lid volume", positive=True)
        total_volume = _number(measurements["material_volume_mm3"], "material volume", positive=True)
        if abs(base_volume + lid_volume - total_volume) > 1e-4:
            raise ValueError("geometry material volume does not match its parts")
        if measurements.get("base_valid_single_solid") is not True or measurements.get("lid_valid_single_solid") is not True:
            raise ValueError("invalid enclosure solids")
        if _number(measurements["board_collision_volume_mm3"], "board collision") > 1e-6:
            raise ValueError("board collides with enclosure")
        clearances = measurements.get("connector_clearances", [])
        if len(clearances) != 2 or {c["reference"] for c in clearances} != {"J1", "J2"}:
            raise ValueError("missing connector clearance checks")
        for item in clearances:
            if _number(item["collision_volume_mm3"], "connector collision") > 1e-6 or _number(item["minimum_clearance_mm"], "clearance") + 1e-5 < job["mechanical_fixture"]["opening_clearance_mm"]:
                raise ValueError("connector collision or insufficient clearance")
        for kind, item in variant["files"].items():
            key = f"{variant['configuration_id']}:{kind}"
            if key not in files or item["sha256"] != files[key]["sha256"] or _receipt_path(root, paths["geometry"], item["path"]) != paths[key]:
                raise ValueError("geometry artifact is stale or missing")
        if not {"base_step", "lid_step", "base_stl", "lid_stl"}.issubset(variant["files"]):
            raise ValueError("missing enclosure manufacturing artifacts")
    plan = derive_material_plan(job, engineering, geometry)
    return {"schema": "cite_refinery.hardware_substitution_verification.v1", "revision": manifest["revision"],
            "digital_package_valid": True, "physical_release_authorized": False,
            "fingerprint": review_fingerprint(manifest),
            "previous_review_still_matches": review_matches(manifest, previous_review_fingerprint) if previous_review_fingerprint is not None else None,
            "native_drc_warning_count": len(native_drc["violations"]), "material_plan": plan,
            "limits": ["component electrical equivalence unqualified", "connector Z envelope assumed", "no physical assembly or fit test", "no slicing, machine execution, live supplier or customer commitment"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--worker-stdin", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.worker_stdin:
            payload = json.load(sys.stdin)
            root, manifest_path = Path(payload["root"]), Path(payload["manifest"])
        else:
            root, manifest_path = args.root, args.manifest
        if root is None or manifest_path is None:
            raise ValueError("root and manifest required")
        result = verify_package(root, _read(manifest_path))
        print(json.dumps(result, allow_nan=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"digital_package_valid": False, "physical_release_authorized": False, "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
