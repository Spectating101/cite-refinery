"""Bounded, independent STEP exchange check; no existing project data is used."""
from __future__ import annotations

import argparse

import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sys
from datetime import datetime, timezone

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepCheck import BRepCheck_Analyzer
from smlibpy import Box, Cylinder, GridLocations, Rectangle, Z

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output-dir", required=True, type=Path)
parser.add_argument("--installation-receipt", required=True, type=Path)
args = parser.parse_args()
OUT = args.output_dir.resolve()
OUT.mkdir(parents=True, exist_ok=True)
INSTALL_REPORT = args.installation_receipt.resolve()
if not INSTALL_REPORT.is_file():
    parser.error("--installation-receipt must be the pip --report JSON for the executed environment")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_independently(path):
    model = cq.importers.importStep(str(path))
    shape = model.val()
    box = shape.BoundingBox()
    cylinders = []
    for face in shape.Faces():
        if face.geomType() == "CYLINDER":
            cylinder = BRepAdaptor_Surface(face.wrapped).Cylinder()
            point = cylinder.Location()
            cylinders.append({"radius": cylinder.Radius(), "axis_location": [point.X(), point.Y(), point.Z()]})
    return {
        "volume": shape.Volume(), "dimensions": [box.xlen, box.ylen, box.zlen],
        "valid_brep": BRepCheck_Analyzer(shape.wrapped).IsValid(),
        "solids": len(shape.Solids()), "faces": len(shape.Faces()), "edges": len(shape.Edges()),
        "cylindrical_faces": cylinders,
    }


cases = []
for name in ("central_bore", "filleted_plate_four_holes_and_recess"):
    part = Box(80, 60, 10)
    if name == "central_bore":
        part -= Cylinder(4, 10)
        expected_volume = 80 * 60 * 10 - math.pi * 4**2 * 10
        expected_holes = [(0.0, 0.0)]
    else:
        part = part.fillet(part.edges().parallel_to(Z), 8)
        part -= GridLocations(60, 40, 2, 2) * Cylinder(4, 10)
        part -= Rectangle(30, 20).on(part.faces().top()).extrude(-4)
        # Corner removal 4*(8^2 - pi*8^2/4)*10, four bores pi*4^2*10 each,
        # and a disjoint 30*20*4 pocket; the pi terms cancel, leaving 43040.
        expected_volume = 43040.0
        expected_holes = [(-30.0, -20.0), (-30.0, 20.0), (30.0, -20.0), (30.0, 20.0)]
    path = OUT / (name + ".step")
    part.export(str(path))
    independent = read_independently(path)
    holes = sorted((round(c["axis_location"][0], 6), round(c["axis_location"][1], 6))
                   for c in independent["cylindrical_faces"] if abs(c["radius"] - 4) < 1e-7)
    checks = {
        "smlibpy_valid": bool(part.is_valid()),
        "smlibpy_no_check_findings": part.check() == [],
        "independent_valid_brep": independent["valid_brep"],
        "one_solid": independent["solids"] == 1,
        "dimensions_preserved": all(abs(a - b) < 2e-6 for a, b in zip(independent["dimensions"], [80, 60, 10])),
        "analytic_volume": abs(independent["volume"] - expected_volume) < 1e-5,
        "source_volume_matches_independent": abs(float(part.volume) - independent["volume"]) < 1e-5,
        "hole_axes_and_radii": holes == expected_holes,
    }
    cases.append({"case": name, "result": "pass" if all(checks.values()) else "fail",
                  "input_dimensions_mm": [80, 60, 10], "expected_volume_mm3": expected_volume,
                  "smlibpy_volume_mm3": float(part.volume), "independent": independent,
                  "checks": checks, "step": {"path": str(path), "bytes": path.stat().st_size, "sha256": sha(path)}})

receipt = {
    "schema": "cite_refinery.bounded_execution.v1", "repository_id": "github:awv-informatik/smlibpy",
    "observed_at": datetime.now(timezone.utc).isoformat(), "result": "pass" if all(c["result"] == "pass" for c in cases) else "fail",
    "scope": "Two local exact-body STEP exchanges, read independently through CadQuery/OpenCascade; no HS integration or manufacturing proof.",
    "versions": {name: importlib.metadata.version(name) for name in ("smlibpy", "cadquery", "cadquery-ocp", "numpy")},
    "environment": {"python": sys.version, "platform": platform.platform()}, "cases": cases,
    "limitations": ["Two deterministic fixtures only; assemblies, tolerances on imported industrial parts, unit conversion, meshing, MCP, browser/WASM, and physical manufacture were not tested.",
                    "No claim of compatibility with an entire HS workflow; only the exact exported STEP files were independently validated."],
    "script": {"path": str(Path(__file__).resolve()), "sha256": sha(__file__)},
    "installation_receipt": {"path": str(INSTALL_REPORT), "sha256": sha(INSTALL_REPORT)},
}
(OUT / "execution.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"result": receipt["result"], "cases": [{"case": c["case"], "result": c["result"], "checks": c["checks"], "volume": c["independent"]["volume"]} for c in cases]}))
sys.exit(0 if receipt["result"] == "pass" else 1)
