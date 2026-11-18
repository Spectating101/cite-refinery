#!/usr/bin/python3
"""Build and inspect a real KiCad/Freerouting connector-substitution fixture.

Run with the Python shipped for KiCad's pcbnew bindings. Freerouting is supplied
explicitly; this program never downloads or executes a tool chosen by job data.
The fixture is a digital experiment, not a qualified electrical design.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

import pcbnew


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def mm(value):
    return pcbnew.FromMM(float(value))


def point(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def execute(command, log, timeout=180):
    start = time.monotonic()
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        if isinstance(stdout, bytes): stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes): stderr = stderr.decode(errors="replace")
        Path(log).write_text(stdout + stderr + "\nBOUNDED EXECUTION TIMEOUT\n")
        raise
    Path(log).write_text(result.stdout + result.stderr)
    receipt = {"argv": command, "exit_code": result.returncode,
               "elapsed_seconds": round(time.monotonic() - start, 3),
               "log": str(log), "log_sha256": sha256(log)}
    return result, receipt


def setup_project(directory, name, job, footprint_root):
    rules = job["routing_rules"]
    project = {
        "meta": {"filename": name + ".kicad_pro", "version": 1},
        "board": {"design_settings": {"rules": {
            "min_clearance": rules["minimum_clearance_mm"],
            "min_track_width": rules["minimum_track_width_mm"],
            "min_connection": rules["minimum_track_width_mm"],
            "min_copper_edge_clearance": 0.5,
            "min_hole_clearance": 0.25,
            "min_through_hole_diameter": 0.3,
            "min_via_diameter": 0.6,
            "min_via_annular_width": 0.15
        }}},
        "net_settings": {"meta": {"version": 4}, "classes": [{
            "name": "Default", "clearance": rules["minimum_clearance_mm"],
            "track_width": rules["track_width_mm"], "via_diameter": 0.8,
            "via_drill": 0.4, "diff_pair_width": 0.4, "diff_pair_gap": 0.2,
            "diff_pair_via_gap": 0.25, "microvia_diameter": 0.3,
            "microvia_drill": 0.1, "bus_width": 12, "wire_width": 6,
            "schematic_color": "rgba(0, 0, 0, 0.000)", "pcb_color": "rgba(0, 0, 0, 0.000)"
        }]}
    }
    write_json(directory / (name + ".kicad_pro"), project)
    (directory / (name + ".kicad_dru")).write_text(
        '(version 1)\n'
        '(rule "Declared minimum copper clearance" (constraint clearance (min '
        + str(rules["minimum_clearance_mm"]) + 'mm)))\n'
        '(rule "Declared minimum track width" (constraint track_width (min '
        + str(rules["minimum_track_width_mm"]) + 'mm)))\n')
    libraries = {}
    for key in ("revision_a", "revision_b"):
        for reference in ("J1", "J2"):
            lib, fp = job[key][reference].split(":", 1)
            source = footprint_root / (lib + ".pretty") / (fp + ".kicad_mod")
            dest = directory / "footprints" / (lib + ".pretty") / source.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            libraries[lib] = str(dest.parent)
    rows = ['(fp_lib_table\n  (version 7)']
    for lib in sorted(libraries):
        rows.append(f'  (lib (name "{lib}")(type "KiCad")(uri "${{KIPRJMOD}}/footprints/{lib}.pretty")(options "")(descr "Pinned local footprint copy"))')
    (directory / "fp-lib-table").write_text("\n".join(rows) + "\n)\n")


def generate_board(job, revision, directory, footprint_root):
    directory.mkdir(parents=True, exist_ok=True)
    name = "adapter_" + revision
    setup_project(directory, name, job, footprint_root)
    board = pcbnew.BOARD()
    board.SetFileName(str(directory / (name + ".kicad_pcb")))
    board.SetCopperLayerCount(2)
    board.GetDesignSettings().SetBoardThickness(mm(job["board"]["thickness_mm"]))
    settings = board.GetDesignSettings()
    settings.m_MinClearance = mm(job["routing_rules"]["minimum_clearance_mm"])
    settings.m_TrackMinWidth = mm(job["routing_rules"]["minimum_track_width_mm"])
    settings.m_CopperEdgeClearance = mm(0.5)
    default = board.GetAllNetClasses()["Default"]
    default.SetClearance(mm(job["routing_rules"]["minimum_clearance_mm"]))
    default.SetTrackWidth(mm(job["routing_rules"]["track_width_mm"]))
    default.SetViaDiameter(mm(0.8))
    default.SetViaDrill(mm(0.4))
    nets = {}
    for netname in job["interface"].values():
        net = pcbnew.NETINFO_ITEM(board, netname)
        board.Add(net)
        nets[netname] = net
    revision_data = job["revision_" + revision.lower()]
    for reference in ("J1", "J2"):
        lib, footprint_name = revision_data[reference].split(":", 1)
        footprint = pcbnew.FootprintLoad(str(directory / "footprints" / (lib + ".pretty")), footprint_name)
        if footprint is None:
            raise RuntimeError("Cannot load footprint " + revision_data[reference])
        footprint.SetReference(reference)
        footprint.SetValue(footprint_name)
        footprint.SetFPID(pcbnew.LIB_ID(lib, footprint_name))
        footprint.SetPosition(point(*job["positions_mm"][reference]))
        board.Add(footprint)
        for pad in footprint.Pads():
            pad.SetNet(nets[job["interface"][pad.GetNumber()]])
    width, height = job["board"]["width_mm"], job["board"]["height_mm"]
    corners = [(0, 0), (width, 0), (width, height), (0, height)]
    for start, end in zip(corners, corners[1:] + corners[:1]):
        segment = pcbnew.PCB_SHAPE(board)
        segment.SetShape(pcbnew.SHAPE_T_SEGMENT)
        segment.SetLayer(pcbnew.Edge_Cuts)
        segment.SetStart(point(*start))
        segment.SetEnd(point(*end))
        segment.SetWidth(mm(0.05))
        board.Add(segment)
    board.BuildListOfNets()
    board.BuildConnectivity()
    path = directory / (name + ".kicad_pcb")
    pcbnew.SaveBoard(str(path), board)
    if not pcbnew.ExportSpecctraDSN(board, str(directory / (name + ".dsn"))):
        raise RuntimeError("KiCad DSN export failed")
    return path


def inspect_board(path, job, revision):
    """Extract the semantic inputs from the SAVED board, not from expected JSON."""
    board = pcbnew.LoadBoard(str(path))
    connectors = []
    errors = []
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        xs, ys = [], []
        for shape in fp.GraphicalItems():
            if shape.GetLayer() != pcbnew.F_Fab or not hasattr(shape, "GetShape"):
                continue
            if shape.GetShape() == pcbnew.SHAPE_T_SEGMENT:
                for p in (shape.GetStart(), shape.GetEnd()):
                    xs.append(pcbnew.ToMM(p.x)); ys.append(pcbnew.ToMM(p.y))
        if not xs:
            raise RuntimeError("No F.Fab body outline in " + fp.GetReference())
        pins = [{"number": p.GetNumber(), "x_mm": pcbnew.ToMM(p.GetPosition().x),
                 "y_mm": pcbnew.ToMM(p.GetPosition().y), "net": p.GetNetname()}
                for p in fp.Pads()]
        pins.sort(key=lambda p: int(p["number"]))
        actual_map = {p["number"]: p["net"] for p in pins}
        if actual_map != job["interface"]:
            errors.append({"reference": fp.GetReference(), "expected": job["interface"], "actual": actual_map})
        connectors.append({"reference": fp.GetReference(),
            "footprint": str(fp.GetFPID().GetLibNickname()) + ":" + str(fp.GetFPID().GetLibItemName()),
            "pins": pins, "body_bounds_mm": {"xmin": min(xs), "xmax": max(xs), "ymin": min(ys), "ymax": max(ys)}})
    expected_refs = {"J1", "J2"}
    if {c["reference"] for c in connectors} != expected_refs:
        errors.append({"error": "unexpected component/reference set"})
    outlines = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    pts = [p for d in outlines for p in [d.GetStart(), d.GetEnd()]]
    board_shape = {"width_mm": pcbnew.ToMM(max(p.x for p in pts)-min(p.x for p in pts)),
                   "height_mm": pcbnew.ToMM(max(p.y for p in pts)-min(p.y for p in pts)),
                   "thickness_mm": pcbnew.ToMM(board.GetDesignSettings().GetBoardThickness())}
    return {"schema": "cite_refinery.hardware_board.v1", "revision": revision,
            "job_id": job["job_id"], "board_path": path.name, "board_sha256": sha256(path),
            "board": board_shape, "connectors": connectors,
            "bom": [{"reference": c["reference"], "part_id": c["footprint"], "quantity_per_board": 1} for c in connectors],
            "checks": {"pin_semantics_match": not errors, "semantic_errors": errors},
            "track_count": len(list(board.GetTracks())),
            "tool_versions": {"kicad": pcbnew.Version()},
            "limits": ["No schematic/ERC, supplier qualification, physical electrical test, or connector-height measurement.",
                       "Pin function equivalence is an explicit fixture assumption; native DRC does not establish it."]}


def run_drc(path, output, commands):
    report = output / (path.stem + "_drc.json")
    command = ["kicad-cli", "pcb", "drc", "--format", "json", "--all-track-errors", "--severity-all", "--exit-code-violations", "-o", str(report), str(path)]
    result, receipt = execute(command, output / (path.stem + "_drc.log"))
    commands.append(receipt)
    if result.returncode not in (0, 5) or not report.is_file():
        raise RuntimeError("KiCad DRC execution failed: " + result.stderr)
    data = json.loads(report.read_text())
    if not isinstance(data, dict) or any(not isinstance(data.get(k), list) for k in ("violations", "unconnected_items")):
        raise RuntimeError("Malformed native DRC report: required finding arrays are missing")
    if "schematic_parity" in data and not isinstance(data["schematic_parity"], list):
        raise RuntimeError("Malformed native schematic-parity result")
    findings = data["violations"] + data["unconnected_items"] + data.get("schematic_parity", [])
    if any(not isinstance(v, dict) or v.get("severity") not in {"error", "warning"} for v in findings):
        raise RuntimeError("Unrecognized native DRC finding or severity")
    errors = [v for v in findings if v.get("severity") == "error"]
    warnings = [v for v in findings if v.get("severity") == "warning"]
    return {"report_path": report.name, "report_sha256": sha256(report),
            "checked_board_sha256": sha256(path), "command": command,
            "tool_version": pcbnew.Version(),
            "checked_project_path": path.with_suffix(".kicad_pro").name,
            "checked_project_sha256": sha256(path.with_suffix(".kicad_pro")),
            "checked_rules_path": path.with_suffix(".kicad_dru").name,
            "checked_rules_sha256": sha256(path.with_suffix(".kicad_dru")),
            "exit_code": result.returncode, "errors": len(errors), "warnings": len(warnings),
            "unconnected": len(data["unconnected_items"]),
            "error_types": sorted({v.get("type", "unknown") for v in errors}),
            "warning_types": sorted({v.get("type", "unknown") for v in warnings})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--freerouting", required=True, type=Path)
    parser.add_argument("--footprint-root", type=Path, default=Path("/usr/share/kicad/footprints"))
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    freerouting = args.freerouting.resolve()
    if not freerouting.is_file():
        raise SystemExit("Freerouting executable missing")
    commands = []
    summaries = []
    for revision in ("A", "B"):
        directory = output / revision
        path = generate_board(job, revision, directory, args.footprint_root)
        # Source-level evidence can be consumed by the CAD branch before routing;
        # final engineering receipt replaces this only after native DRC executes.
        engineering = inspect_board(path, job, revision)
        engineering["checks"]["routing_pending"] = True
        write_json(directory / "engineering.json", engineering)
        dsn, ses = path.with_suffix(".dsn"), path.with_suffix(".ses")
        command = [str(freerouting), "-de", str(dsn), "-do", str(ses), "-da",
                   "--gui.enabled=false", "--api_server.enabled=false",
                   "--router.max_threads=2", "--router.autorouter.max_passes=20",
                   "--router.optimizer.enabled=false", "--logging.console.level=INFO",
                   "--user_data_path=" + str(directory / "freerouting_config")]
        result, receipt = execute(command, directory / "freerouting.log", timeout=150)
        commands.append(receipt)
        if result.returncode or not ses.is_file():
            raise RuntimeError("Freerouting failed; inspect " + str(directory / "freerouting.log"))
        board = pcbnew.LoadBoard(str(path))
        if not pcbnew.ImportSpecctraSES(board, str(ses)):
            raise RuntimeError("KiCad SES import failed")
        pcbnew.SaveBoard(str(path), board)
        engineering = inspect_board(path, job, revision)
        version = re.search(r"Freerouting(?: CLI)? v([0-9.]+)", result.stdout + result.stderr)
        if not version:
            raise RuntimeError("Freerouting did not provide a recognizable version receipt")
        engineering["tool_versions"]["freerouting"] = version.group(1)
        engineering["checks"]["drc"] = run_drc(path, directory, commands)
        engineering["checks"]["digital_electrical_pass"] = (
            engineering["checks"]["pin_semantics_match"] and
            engineering["checks"]["drc"]["errors"] == 0 and
            engineering["checks"]["drc"]["unconnected"] == 0)
        engineering["source_hashes"] = {"job": sha256(args.job), "freerouting_binary": sha256(freerouting),
            "dsn": sha256(dsn), "ses": sha256(ses), "project": sha256(path.with_suffix(".kicad_pro")),
            "native_rules": sha256(path.with_suffix(".kicad_dru"))}
        packaged_jar = freerouting.parent.parent / "lib" / "app" / "freerouting-executable.jar"
        if packaged_jar.is_file():
            engineering["source_hashes"]["freerouting_packaged_jar"] = sha256(packaged_jar)
        engineering["artifacts"] = {
            "board": path.name, "dsn": dsn.name, "ses": ses.name,
            "project": path.with_suffix(".kicad_pro").name,
            "native_rules": path.with_suffix(".kicad_dru").name,
            "drc_report": engineering["checks"]["drc"]["report_path"],
            "freerouting_log": "freerouting.log"
        }
        engineering["routing_rule_handoff"] = {
            "dsn_netclass_rules_exported": True,
            "custom_rules_verified_by": "native KiCad DRC on final imported PCB",
            "note": "Freerouting receives DSN netclass rules; full KiCad custom-rule equivalence is not presumed."}
        write_json(directory / "engineering.json", engineering)
        if not engineering["checks"]["digital_electrical_pass"]:
            write_json(output / "commands.json", commands)
            raise RuntimeError("Generated PCB failed native/semantic electrical checks")
        # Real manufacturing plot is useful evidence, but remains digital-review-only.
        gerber_dir = directory / "gerbers"
        gerber_dir.mkdir(exist_ok=True)
        gerber_command = ["kicad-cli", "pcb", "export", "gerbers", "-o", str(gerber_dir) + "/",
                          "-l", "F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,Edge.Cuts", str(path)]
        result, receipt = execute(gerber_command, directory / "gerbers.log")
        commands.append(receipt)
        if result.returncode:
            raise RuntimeError("Gerber generation failed")
        drill_command = ["kicad-cli", "pcb", "export", "drill", "-o", str(gerber_dir) + "/", str(path)]
        result, receipt = execute(drill_command, directory / "drill.log")
        commands.append(receipt)
        if result.returncode:
            raise RuntimeError("Drill generation failed")
        if sha256(path) != engineering["board_sha256"]:
            raise RuntimeError("Board changed during manufacturing export")
        engineering["manufacturing_artifacts"] = [
            {"path": str(p.relative_to(directory)), "sha256": sha256(p),
             "source_board_sha256": engineering["board_sha256"],
             "format": p.suffix.removeprefix(".")}
            for p in sorted(gerber_dir.iterdir()) if p.is_file()
        ]
        if not engineering["manufacturing_artifacts"] or not any(p["format"] == "drl" for p in engineering["manufacturing_artifacts"]):
            raise RuntimeError("Required manufacturing outputs missing")
        engineering["manufacturing_commands"] = [gerber_command, drill_command]
        write_json(directory / "engineering.json", engineering)
        summaries.append({"revision": revision, "engineering": str(directory / "engineering.json"), "checks": engineering["checks"]})

    # Delete every segment of ONE net. This is a physical connectivity fault in
    # the PCB, not a fabricated failed-check flag.
    directory = output / "negative_disconnected"; directory.mkdir(exist_ok=True)
    source = output / "B" / "adapter_B.kicad_pcb"
    path = directory / "adapter_B_disconnected.kicad_pcb"
    board = pcbnew.LoadBoard(str(source))
    removed = 0
    for track in list(board.GetTracks()):
        if track.GetNetname() == "SENSE":
            board.Remove(track); removed += 1
    if not removed:
        raise RuntimeError("Negative control removed no real copper")
    pcbnew.SaveBoard(str(path), board)
    for ext in (".kicad_pro", ".kicad_dru"):
        shutil.copyfile(source.with_suffix(ext), path.with_suffix(ext))
    shutil.copytree(output / "B" / "footprints", directory / "footprints", dirs_exist_ok=True)
    shutil.copyfile(output / "B" / "fp-lib-table", directory / "fp-lib-table")
    negative = {"mutation": "remove all SENSE copper tracks", "removed_tracks": removed,
                "board_sha256": sha256(path), "drc": run_drc(path, directory, commands)}
    negative["correctly_rejected"] = negative["drc"]["unconnected"] > 0
    write_json(directory / "result.json", negative)
    write_json(output / "commands.json", commands)
    print(json.dumps({"revisions": summaries, "negative_control": negative}), flush=True)
    if not negative["correctly_rejected"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
