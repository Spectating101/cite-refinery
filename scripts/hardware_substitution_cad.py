#!/usr/bin/env python3
"""Build and re-import fixture enclosures using real CadQuery/STEP geometry.

This bounded experiment validates digital envelope clearance only. The Z envelope,
print process, retention, solder clearance and connector qualification are fixtures
or unverified; its output never authorizes physical manufacture.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import shlex
import sys
from typing import Any

import cadquery as cq


TOLERANCE_MM = 1e-6
VOLUME_TOLERANCE_MM3 = 1e-6


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value: Any, label: str, *, positive: bool = False) -> float:
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError(f"Invalid {label}: {value!r}")
    return result


def bounds_dict(shape: cq.Shape) -> dict[str, float]:
    bounds = shape.BoundingBox()
    return {name: round(float(getattr(bounds, name)), 9)
            for name in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")}


def box(xmin: float, xmax: float, ymin: float, ymax: float,
        zmin: float, zmax: float) -> cq.Shape:
    if xmax <= xmin or ymax <= ymin or zmax <= zmin:
        raise ValueError("Non-positive geometric interval")
    return cq.Workplane("XY").box(
        xmax - xmin, ymax - ymin, zmax - zmin,
        centered=(False, False, False),
    ).translate((xmin, ymin, zmin)).val()


def load_inputs(job_path: Path, engineering_path: Path) -> tuple[dict, dict]:
    job = json.loads(job_path.read_text())
    engineering = json.loads(engineering_path.read_text())
    if job.get("schema") != "cite_refinery.hardware_substitution_job.v1":
        raise ValueError("Unsupported job schema")
    if engineering.get("schema") != "cite_refinery.hardware_board.v1":
        raise ValueError("Unsupported engineering schema")
    if engineering.get("job_id") != job["job_id"]:
        raise ValueError("Engineering input belongs to a different job")
    if not engineering.get("board_sha256") or not engineering.get("revision"):
        raise ValueError("Engineering input requires a saved board hash and revision")
    if not engineering.get("connectors"):
        raise ValueError("Engineering input has no extracted connectors")
    board = engineering["board"]
    for axis in ("width_mm", "height_mm", "thickness_mm"):
        if abs(number(board[axis], axis, positive=True) -
               number(job["board"][axis], axis, positive=True)) > TOLERANCE_MM:
            raise ValueError(f"Saved board and job disagree on {axis}")
    for c in engineering["connectors"]:
        b = c["body_bounds_mm"]
        for k in ("xmin", "xmax", "ymin", "ymax"):
            number(b[k], f"{c['reference']}.{k}")
        if b["xmax"] <= b["xmin"] or b["ymax"] <= b["ymin"]:
            raise ValueError(f"Invalid footprint body bounds: {c['reference']}")
    configuration_ids = [c["id"] for c in job["configurations"]]
    if not configuration_ids or len(set(configuration_ids)) != len(configuration_ids):
        raise ValueError("Configuration identities must be nonempty and unique")
    if any(not re.fullmatch(r"[A-Za-z0-9_-]+", cid) for cid in configuration_ids):
        raise ValueError("Configuration identities must be safe single directory names")
    for configuration in job["configurations"]:
        quantity = configuration["quantity"]
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            raise ValueError("Configuration quantities must be positive integers")
        number(configuration["wall_mm"], "wall thickness", positive=True)
    if sum(c["quantity"] for c in job["configurations"]) != job["quantity"]:
        raise ValueError("Variant quantities do not sum to the job quantity")
    return job, engineering


def connector_shape(job: dict, engineering: dict, connector: dict) -> cq.Shape:
    bounds = connector["body_bounds_mm"]
    bottom = number(engineering["board"]["thickness_mm"], "board thickness", positive=True)
    height = number(job["mechanical_fixture"]["connector_height_mm"],
                    "fixture connector height", positive=True)
    return box(bounds["xmin"], bounds["xmax"], bounds["ymin"], bounds["ymax"],
               bottom, bottom + height)


def build_shapes(job: dict, engineering: dict, configuration: dict) -> tuple[cq.Shape, cq.Shape]:
    board = engineering["board"]
    mechanical = job["mechanical_fixture"]
    width, height = board["width_mm"], board["height_mm"]
    wall = number(configuration["wall_mm"], "wall", positive=True)
    margin = number(mechanical["board_margin_mm"], "board margin", positive=True)
    lid_bottom = number(mechanical["lid_bottom_z_mm"], "lid height", positive=True)
    clearance = number(mechanical["opening_clearance_mm"], "opening clearance", positive=True)
    inside_floor_z = -4.0
    xmin, xmax = -margin - wall, width + margin + wall
    ymin, ymax = -margin - wall, height + margin + wall
    outside = box(xmin, xmax, ymin, ymax, inside_floor_z - wall, lid_bottom)
    cavity = box(-margin, width + margin, -margin, height + margin,
                 inside_floor_z, lid_bottom + 1)
    base = outside.cut(cavity)
    # Four digital support posts touch the PCB at z=0. No retention or fastener
    # qualification is inferred from them.
    for x, y in ((3, 3), (width - 3, 3), (3, height - 3), (width - 3, height - 3)):
        post = cq.Workplane("XY").circle(1.5).extrude(-inside_floor_z).translate(
            (x, y, inside_floor_z)).val()
        base = base.fuse(post)
    lid = box(xmin, xmax, ymin, ymax, lid_bottom, lid_bottom + wall)
    for connector in engineering["connectors"]:
        b = connector["body_bounds_mm"]
        opening = box(b["xmin"] - clearance, b["xmax"] + clearance,
                      b["ymin"] - clearance, b["ymax"] + clearance,
                      lid_bottom - 1, lid_bottom + wall + 1)
        lid = lid.cut(opening)
    return base.clean(), lid.clean()


def file_record(path: Path, output: Path) -> dict:
    return {"path": path.relative_to(output).as_posix(), "sha256": sha256(path),
            "bytes": path.stat().st_size}


def read_step(path: Path) -> cq.Shape:
    # This reads the exported exchange artifact back from disk. Checks never use
    # the pre-export object or a recorded pass/fail flag as evidence of clearance.
    imported = cq.importers.importStep(str(path))
    shapes = [s for s in imported.vals() if isinstance(s, cq.Shape)]
    if not shapes:
        raise ValueError(f"STEP has no geometric shapes: {path}")
    return cq.Compound.makeCompound(shapes)


def measure_existing(job: dict, engineering: dict, base_path: Path, lid_path: Path) -> dict:
    base, lid = read_step(base_path), read_step(lid_path)
    case = cq.Compound.makeCompound([base, lid])
    required = number(job["mechanical_fixture"]["opening_clearance_mm"],
                      "opening clearance", positive=True)
    checks = []
    for connector in engineering["connectors"]:
        envelope = connector_shape(job, engineering, connector)
        intersection = case.intersect(envelope)
        collision_volume = max(0.0, intersection.Volume())
        actual_clearance = max(0.0, case.distance(envelope))
        checks.append({
            "reference": connector["reference"],
            "envelope_bounds_mm": bounds_dict(envelope),
            "collision_volume_mm3": round(collision_volume, 9),
            "minimum_clearance_mm": round(actual_clearance, 9),
            "required_clearance_mm": required,
            "passed": collision_volume <= VOLUME_TOLERANCE_MM3 and
                      actual_clearance + TOLERANCE_MM >= required,
        })
    board = engineering["board"]
    board_shape = box(0, board["width_mm"], 0, board["height_mm"],
                      0, board["thickness_mm"])
    board_collision = max(0.0, case.intersect(board_shape).Volume())
    base_valid = base.isValid() and len(base.Solids()) == 1 and base.Volume() > 0
    lid_valid = lid.isValid() and len(lid.Solids()) == 1 and lid.Volume() > 0
    return {
        "verification_method": "STEP re-import, BRep solid validity, exact solid intersection and distance",
        "base_valid_single_solid": base_valid,
        "lid_valid_single_solid": lid_valid,
        "base_bounds_mm": bounds_dict(base),
        "lid_bounds_mm": bounds_dict(lid),
        "base_volume_mm3": round(base.Volume(), 6),
        "lid_volume_mm3": round(lid.Volume(), 6),
        "material_volume_mm3": round(base.Volume() + lid.Volume(), 6),
        "board_collision_volume_mm3": round(board_collision, 9),
        "board_support_contact_is_intentional": True,
        "connector_clearances": checks,
        "passed": bool(base_valid and lid_valid and
                       board_collision <= VOLUME_TOLERANCE_MM3 and
                       all(check["passed"] for check in checks)),
    }


def build(job_path: Path, engineering_path: Path, output: Path) -> dict:
    job, engineering = load_inputs(job_path, engineering_path)
    output.mkdir(parents=True, exist_ok=True)
    result = common_metadata(job_path, engineering_path, job, engineering)
    result["variants"] = []
    for configuration in job["configurations"]:
        directory = output / configuration["id"]
        directory.mkdir(parents=True, exist_ok=True)
        base, lid = build_shapes(job, engineering, configuration)
        paths = {}
        for name, shape in (("base", base), ("lid", lid)):
            for extension in ("step", "stl"):
                path = directory / f"{name}.{extension}"
                cq.exporters.export(shape, str(path), tolerance=0.05, angularTolerance=0.1)
                paths[f"{name}_{extension}"] = path
        assembly_path = directory / "enclosure.step"
        cq.exporters.export(cq.Compound.makeCompound([base, lid]), str(assembly_path))
        paths["enclosure_step"] = assembly_path
        view_path = directory / "enclosure.svg"
        cq.exporters.export(cq.Compound.makeCompound([base, lid]), str(view_path),
                            opt={"width": 900, "height": 600, "marginLeft": 30,
                                 "marginTop": 30, "showAxes": False,
                                 "projectionDir": (1, -1, 1), "strokeWidth": 0.7,
                                 "strokeColor": (20, 55, 75), "hiddenColor": (180, 195, 205)})
        paths["enclosure_svg"] = view_path
        measurement = measure_existing(job, engineering, paths["base_step"], paths["lid_step"])
        result["variants"].append({
            "configuration_id": configuration["id"],
            "quantity": configuration["quantity"],
            "wall_mm": configuration["wall_mm"],
            "files": {name: file_record(path, output) for name, path in paths.items()},
            "measurements": measurement,
        })
    result["all_checks_pass"] = all(v["measurements"]["passed"] for v in result["variants"])
    result["total_material_volume_mm3"] = round(sum(
        v["quantity"] * v["measurements"]["material_volume_mm3"] for v in result["variants"]), 6)
    (output / "geometry.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def common_metadata(job_path: Path, engineering_path: Path, job: dict, engineering: dict) -> dict:
    return {
        "schema": "cite_refinery.hardware_geometry.v1",
        "job_id": job["job_id"],
        "revision": engineering["revision"],
        "job_sha256": sha256(job_path),
        "source_engineering_sha256": sha256(engineering_path),
        "source_board_sha256": engineering["board_sha256"],
        "tool_versions": {"cadquery": cq.__version__, "python": platform.python_version()},
        "command": sys.argv,
        "measurement_tolerance_mm": TOLERANCE_MM,
        "volume_tolerance_mm3": VOLUME_TOLERANCE_MM3,
        "physical_release_authorized": False,
        "limits": [
            "Connector XY envelopes are KiCad footprint F.Fab bounds, not metrology of delivered components.",
            "The 12 mm connector-height envelope is a declared fixture assumption, not a verified datasheet dimension.",
            "Geometry generation and re-import checking use the same CadQuery/OpenCascade kernel; this is artifact-level verification, not cross-engine qualification.",
            "This proves digital body/window clearance only; cable access, fasteners, strain relief, solder clearance, retention and print tolerances remain unqualified.",
            "Positive electrical or mechanical software checks do not authorize manufacture or establish physical function.",
        ],
    }


def contained_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Artifact path escapes the supplied geometry directory")
    return path


def check_existing(job_path: Path, engineering_path: Path, existing: Path, output: Path) -> dict:
    job, engineering = load_inputs(job_path, engineering_path)
    manifest = json.loads((existing / "geometry.json").read_text())
    result = common_metadata(job_path, engineering_path, job, engineering)
    result["mode"] = "independent_existing_STEP_check"
    result["existing_geometry_revision"] = manifest["revision"]
    result["existing_geometry_source_board_sha256"] = manifest["source_board_sha256"]
    result["variants"] = []
    expected_configurations = {c["id"] for c in job["configurations"]}
    actual_configurations = {v["configuration_id"] for v in manifest["variants"]}
    if expected_configurations != actual_configurations or len(manifest["variants"]) != len(expected_configurations):
        raise ValueError("Existing geometry has a different or duplicate configuration set")
    for variant in manifest["variants"]:
        paths = {}
        for part in ("base_step", "lid_step"):
            record = variant["files"][part]
            path = contained_path(existing, record["path"])
            if sha256(path) != record["sha256"]:
                raise ValueError(f"Existing artifact hash mismatch: {part}")
            paths[part] = path
        measurement = measure_existing(job, engineering, paths["base_step"], paths["lid_step"])
        result["variants"].append({"configuration_id": variant["configuration_id"],
                                    "measurements": measurement})
    result["all_checks_pass"] = all(v["measurements"]["passed"] for v in result["variants"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "geometry_check.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, type=Path)
    parser.add_argument("--engineering", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--check-existing", type=Path,
                        help="Re-import and verify this existing geometry directory against the given engineering revision")
    args = parser.parse_args()
    if args.check_existing:
        result = check_existing(args.job, args.engineering, args.check_existing, args.output)
    else:
        result = build(args.job, args.engineering, args.output)
    summary = {"revision": result["revision"], "all_checks_pass": result["all_checks_pass"],
               "variants": [{"id": v["configuration_id"],
                             "passed": v["measurements"]["passed"],
                             "connector_clearances": v["measurements"]["connector_clearances"]}
                            for v in result["variants"]]}
    exit_code = 0 if result["all_checks_pass"] else 2
    rendered = json.dumps(summary, indent=2)
    (args.output / "execution.log").write_text(
        "$ " + shlex.join([sys.executable, *sys.argv]) + "\n" +
        f"CadQuery {cq.__version__}; Python {platform.python_version()}\n" +
        "STEP exchange files re-imported before measurements.\n" +
        rendered + f"\nexit_code={exit_code}\n")
    print(rendered)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
