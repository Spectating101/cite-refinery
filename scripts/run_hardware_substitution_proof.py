#!/usr/bin/env python3
"""Run the digital substitution proof through Cite-Refinery's real registry.

Requires KiCad Python bindings, a reviewed Freerouting distribution and a
CadQuery interpreter. Never sends orders or commands a physical machine.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from cite_refinery.app import CiteRefinery
from cite_refinery.hardware_substitution import (
    build_manifest, review_fingerprint, review_matches, verify_package,
)


def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def read(path):
    return json.loads(path.read_text())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--job", type=Path, default=REPO / "examples/hardware_substitution/job.json")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--freerouting", type=Path, required=True)
    p.add_argument("--pcb-python", default="/usr/bin/python3")
    p.add_argument("--cad-python", default=sys.executable)
    args = p.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit("Use a new or empty output directory; prior evidence is retained.")
    output.mkdir(parents=True, exist_ok=True)
    job = output / "job.json"
    shutil.copyfile(args.job, job)
    app = CiteRefinery(output / "refinery_state")
    project = app.init_project(
        "Hardware substitution: digital artifact proof",
        "A supply fixture changes connector pitch; propagate and verify the PCB, enclosure and material plan.",
    )
    runs = []

    def invoke(name, argv, *, input_data=None, expected_exit=0, timeout=300):
        capability = app.refinery.register_capability(
            project_id=project.id, name=name,
            description="Bounded digital engineering fixture, with local execution receipts.",
            tags=["hardware_substitution", "digital_trial"],
            provenance={"scope": "project-local proof", "physical_release_authorized": False},
        )
        implementation = app.refinery.register_implementation(
            project_id=project.id, capability_id=capability.id, provider="subprocess",
            invocation={"argv": [str(a) for a in argv], "input_mode": "json_stdin" if input_data is not None else "none", "timeout_seconds": timeout},
        )
        run = app.invoke(project.id, implementation.id, input_data=input_data)
        runs.append({"name": name, "run_id": run.id, "status": run.status,
                     "exit_code": run.exit_code, "expected_exit_code": expected_exit,
                     "duration_ms": run.duration_ms, "capability_id": capability.id,
                     "implementation_id": implementation.id})
        write(output / "run_progress.json", {"project_id": project.id, "runs": runs})
        if run.exit_code != expected_exit:
            raise RuntimeError(f"{name} failed with exit {run.exit_code}: {run.stderr[-1800:]} {str(run.output)[-1200:]}")
        return run

    invoke("KiCad and Freerouting: generate and verify both PCB revisions", [
        args.pcb_python, REPO / "scripts/hardware_substitution_pcb.py", "--job", job,
        "--output", output / "pcb", "--freerouting", args.freerouting.resolve(),
    ], timeout=400)
    for revision in ("A", "B"):
        invoke(f"CadQuery: rebuild and reimport revision {revision} enclosures", [
            args.cad_python, REPO / "scripts/hardware_substitution_cad.py", "--job", job,
            "--engineering", output / f"pcb/{revision}/engineering.json",
            "--output", output / f"cad/{revision}",
        ])
    invoke("Negative control: old enclosure with replacement connector", [
        args.cad_python, REPO / "scripts/hardware_substitution_cad.py", "--job", job,
        "--engineering", output / "pcb/B/engineering.json", "--check-existing", output / "cad/A",
        "--output", output / "cad/negative_old_case",
    ], expected_exit=2)

    manifests, verified = {}, {}
    for revision in ("A", "B"):
        manifests[revision] = build_manifest(output, job, output / f"pcb/{revision}/engineering.json", output / f"cad/{revision}/geometry.json")
        write(output / f"manifest_{revision}.json", manifests[revision])
        verified[revision] = verify_package(output, manifests[revision])
    verifier_argv = [sys.executable, "-c",
        f"import sys;sys.path.insert(0,{str(REPO / 'src')!r});from cite_refinery.hardware_substitution import main;raise SystemExit(main(['--worker-stdin']))"]
    invoke("Verify bound artifacts and derive the production inputs", verifier_argv,
           input_data={"root": str(output), "manifest": str(output / "manifest_B.json")})

    # Same-name corruption of an actual copied generated PCB. The original run
    # stays unchanged and the old manifest must detect the altered bytes.
    tampered = output / "negative_tamper"
    for descriptor in manifests["B"]["files"].values():
        target = tampered / descriptor["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(output / descriptor["path"], target)
    board = tampered / manifests["B"]["files"]["board"]["path"]
    with board.open("ab") as stream:
        stream.write(b"\n; negative control: changed after review\n")
    try:
        verify_package(tampered, manifests["B"])
        raise AssertionError("Altered PCB unexpectedly accepted")
    except ValueError as exc:
        tamper_result = {"correctly_rejected": True, "reason": str(exc)}
    stale_review = not review_matches(manifests["B"], review_fingerprint(manifests["A"]))
    if not stale_review:
        raise AssertionError("Old review unexpectedly matches changed design")
    electrical_negative = read(output / "pcb/negative_disconnected/result.json")
    mechanical_negative = read(output / "cad/negative_old_case/geometry_check.json")
    if electrical_negative.get("correctly_rejected") is not True or mechanical_negative.get("all_checks_pass") is not False:
        raise AssertionError("Engineering negative controls did not reject")
    negatives = {"disconnected_trace": electrical_negative, "old_enclosure": mechanical_negative,
                 "same_path_tamper": tamper_result,
                 "prior_review_identity": {"correctly_invalidated": stale_review, "scope": "simulated prior content review; no human approval represented"}}
    write(output / "negative_controls.json", negatives)
    experiment = app.add_experiment(
        project.id, name="Supply-driven PCB and enclosure substitution",
        method="Real DSN/SES routing, native DRC, STEP solid re-import, byte-bound handoff and adversarial controls",
        result="Digital A/B checks passed and deliberately broken handoffs were rejected. Physical release remains false.",
        verdict="passed", metrics={"digital_revisions": 2, "enclosure_variants": 4, "negative_controls": 4},
        run_ids=[r["run_id"] for r in runs],
    )
    for revision in ("A", "B"):
        app.add_artifact(project.id, name=f"Revision {revision} engineering package manifest", kind="engineering_manifest",
                         uri=str(output / f"manifest_{revision}.json"), description="Digital review only; no physical or commercial qualification.")
    result = {"schema": "cite_refinery.hardware_substitution_proof.v1", "project_id": project.id,
              "experiment_id": experiment.id, "runs": runs, "verified": verified,
              "negative_controls_passed": True, "physical_release_authorized": False,
              "existing_optiplex_graph_modified": False}
    write(output / "integration_result.json", result)
    print(json.dumps({"project_id": project.id, "runs": len(runs), "digital_revisions_passed": 2,
                      "negative_controls_passed": True, "B_material_plan": verified["B"]["material_plan"],
                      "result": str(output / "integration_result.json")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
