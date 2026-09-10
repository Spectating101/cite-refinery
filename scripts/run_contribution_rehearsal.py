from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import shutil
from pathlib import Path
from typing import Any, Callable

from cite_refinery.contribution_cli import main as contribution_main
from cite_refinery.contribution_revision_cli import main as revision_main
from cite_refinery.contribution_review_cli import main as review_main
from cite_refinery.problem_commons import ProblemCommons, ProblemPacket, ProblemStatus, Subproblem, Visibility


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "contribution_rehearsal_v0"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _run_cli(
    label: str,
    func: Callable[[list[str] | None], int],
    argv: list[str],
    transcript: list[dict[str, Any]],
    *,
    expected: int = 0,
) -> dict[str, Any]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = func(argv)
    raw = buffer.getvalue().strip()
    transcript.append({"label": label, "argv": argv, "exit_code": code, "stdout": raw})
    if code != expected:
        raise RuntimeError(f"{label} returned {code}, expected {expected}: {raw}")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} did not emit JSON: {raw}") from exc


def _seed_commons(path: Path) -> None:
    commons = ProblemCommons()
    packet = ProblemPacket(
        id="problem:rehearsal-food-coverage",
        title="Synthetic community food-redistribution coverage rehearsal",
        observed_condition=(
            "A frozen synthetic intake register contains pickup records, but raw listed-record coverage can differ from "
            "coverage over records that meet the program eligibility window."
        ),
        unresolved_core=(
            "Determine what pickup-coverage ratio the frozen fixture supports without silently changing the denominator "
            "or inferring operational effectiveness."
        ),
        steward="curator:rehearsal",
        status=ProblemStatus.OPEN,
        visibility=Visibility.PUBLIC,
        domain="community-logistics",
        geography="synthetic",
        summary="Synthetic operating rehearsal for the contribution review and revision loop.",
        affected_actors=["synthetic donor", "synthetic recipient"],
        constraints=["frozen fixture only", "no causal inference", "no deployment authority"],
        knowledge_frontier=["eligible denominator must be explicit before eligible-program coverage is reported"],
        capability_frontier=["bounded data audit", "independent review", "revision lineage"],
        authority_boundary="Analysis and review only; no operational, funding, or deployment decision is authorized.",
        subproblems=[
            Subproblem(
                id="sub:coverage-audit",
                title="Audit pickup coverage without overstating the denominator",
                description=(
                    "Calculate raw listed-record pickup coverage, define the eligible-program denominator, and preserve "
                    "the distinction between descriptive coverage and operational outcome."
                ),
                kind="analysis",
                skill_tags=["data-audit", "reproducibility"],
                expected_outputs=[
                    "reproducible coverage calculation",
                    "explicit denominator definition",
                    "limitations statement",
                ],
            )
        ],
    )
    commons.problems[packet.id] = packet
    commons.save(path)


def run_rehearsal(out: Path) -> dict[str, Any]:
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"rehearsal output directory is not empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    source = out / "source"
    source.mkdir(parents=True, exist_ok=True)

    for name in ("intake_records.csv", "initial_analysis.md", "revised_analysis.md", "project_brief.json"):
        shutil.copy2(FIXTURES / name, source / name)

    brief = source / "project_brief.json"
    data_artifact = source / "intake_records.csv"
    initial_report = source / "initial_analysis.md"
    revised_report = source / "revised_analysis.md"
    commons_path = out / "problem-commons.json"
    workspace_v0 = out / "workspace-v0.json"
    submission_v0 = out / "submission-v0.json"
    review_v0 = out / "review-v0.json"
    projection_v0 = out / "projection-v0.json"
    workspace_r1 = out / "workspace-r1.json"
    submission_r1 = out / "submission-r1.json"
    review_r1 = out / "review-r1.json"
    projection_r1 = out / "projection-r1.json"
    transcript: list[dict[str, Any]] = []

    _seed_commons(commons_path)

    _run_cli(
        "initial workspace",
        contribution_main,
        ["init", str(brief), "--contributor-ref", "contributor:rehearsal-analyst", "--out", str(workspace_v0)],
        transcript,
    )
    _run_cli(
        "activate initial workspace",
        contribution_main,
        ["activate", str(workspace_v0), "--basis", "volunteer"],
        transcript,
    )
    _run_cli(
        "set initial work",
        contribution_main,
        [
            "set-work",
            str(workspace_v0),
            "--method-scope",
            "Count completed pickups over all listed records in the frozen fixture; eligibility denominator is not yet defined.",
            "--produced-output",
            "raw listed-record pickup coverage",
            "--blocker",
            "eligibility denominator is not yet defined",
            "--notes",
            "Initial bounded pass; no eligible-program coverage claim is made.",
        ],
        transcript,
    )
    _run_cli(
        "attach frozen dataset",
        contribution_main,
        [
            "artifact-add",
            str(workspace_v0),
            "--title",
            "Frozen intake records",
            "--kind",
            "dataset",
            "--file",
            str(data_artifact),
            "--notes",
            "Synthetic rehearsal fixture.",
        ],
        transcript,
    )
    _run_cli(
        "attach initial analysis",
        contribution_main,
        [
            "artifact-add",
            str(workspace_v0),
            "--title",
            "Initial pickup coverage note",
            "--kind",
            "report",
            "--file",
            str(initial_report),
        ],
        transcript,
    )

    initial_workspace_raw = json.loads(workspace_v0.read_text(encoding="utf-8"))
    initial_report_id = next(
        item["id"] for item in initial_workspace_raw["artifacts"] if item["title"] == "Initial pickup coverage note"
    )

    _run_cli(
        "submit initial work",
        contribution_main,
        ["submit", str(workspace_v0), "--submission-out", str(submission_v0)],
        transcript,
    )
    _run_cli(
        "create revise review",
        review_main,
        [
            "create",
            str(submission_v0),
            "--workspace",
            str(workspace_v0),
            "--reviewer-ref",
            "reviewer:rehearsal-methods",
            "--verdict",
            "revise",
            "--summary",
            "The raw 6/8 calculation is reproducible, but the program-eligible denominator is not defined.",
            "--strength",
            "raw listed-record numerator and denominator are explicit",
            "--limitation",
            "listed-record coverage cannot be presented as eligible-program coverage",
            "--revision-requirement",
            "Define the eligibility rule and report raw listed-record coverage separately from eligible-program pickup coverage.",
            "--out",
            str(review_v0),
        ],
        transcript,
    )
    _run_cli(
        "validate revise review",
        review_main,
        ["validate", str(review_v0), "--submission", str(submission_v0), "--workspace", str(workspace_v0)],
        transcript,
    )
    _run_cli(
        "project revise review",
        review_main,
        [
            "project",
            str(review_v0),
            "--submission",
            str(submission_v0),
            "--workspace",
            str(workspace_v0),
            "--state",
            str(commons_path),
            "--receipt-out",
            str(projection_v0),
        ],
        transcript,
    )

    after_revise = ProblemCommons.load(commons_path).get("problem:rehearsal-food-coverage")
    if len(after_revise.attempts) != 1 or after_revise.attempts[0].status.value != "active":
        raise RuntimeError("REVISE rehearsal did not return exactly one canonical Attempt to active")
    if [item.verdict for item in after_revise.attempt_reviews] != ["revise"]:
        raise RuntimeError("REVISE rehearsal did not preserve the expected initial review")

    _run_cli(
        "create revision workspace",
        revision_main,
        ["init", str(submission_v0), "--trigger-review", str(review_v0), "--out", str(workspace_r1)],
        transcript,
    )
    no_op = _run_cli(
        "prove no-op revision rejection",
        revision_main,
        [
            "validate",
            str(workspace_r1),
            "--parent-submission",
            str(submission_v0),
            "--trigger-review",
            str(review_v0),
            "--submittable",
        ],
        transcript,
        expected=2,
    )
    if not any("must change contributor work" in item for item in no_op.get("errors", [])):
        raise RuntimeError("no-op revision was rejected for an unexpected reason")

    _run_cli(
        "set revised work",
        revision_main,
        [
            "set-work",
            str(workspace_r1),
            "--method-scope",
            "Retain raw listed-record coverage and separately define eligibility as eligible_window=true before calculating eligible-program coverage.",
            "--produced-output",
            "raw listed-record pickup coverage",
            "--produced-output",
            "eligible-program pickup coverage with explicit denominator",
            "--blocker",
            "",
            "--notes",
            "Revision explicitly preserves both denominators and does not infer operational effectiveness.",
        ],
        transcript,
    )
    _run_cli(
        "remove superseded initial report",
        revision_main,
        ["artifact-remove", str(workspace_r1), "--artifact-id", initial_report_id],
        transcript,
    )
    _run_cli(
        "attach revised analysis",
        revision_main,
        [
            "artifact-add",
            str(workspace_r1),
            "--title",
            "Revised pickup coverage note",
            "--kind",
            "report",
            "--file",
            str(revised_report),
        ],
        transcript,
    )
    _run_cli(
        "validate revised work",
        revision_main,
        [
            "validate",
            str(workspace_r1),
            "--parent-submission",
            str(submission_v0),
            "--trigger-review",
            str(review_v0),
            "--submittable",
        ],
        transcript,
    )
    _run_cli(
        "submit revision",
        revision_main,
        [
            "submit",
            str(workspace_r1),
            "--parent-submission",
            str(submission_v0),
            "--trigger-review",
            str(review_v0),
            "--submission-out",
            str(submission_r1),
        ],
        transcript,
    )
    _run_cli(
        "create revision acceptance review",
        review_main,
        [
            "create-revision",
            str(submission_r1),
            "--workspace",
            str(workspace_r1),
            "--parent-submission",
            str(submission_v0),
            "--trigger-review",
            str(review_v0),
            "--reviewer-ref",
            "reviewer:rehearsal-methods",
            "--verdict",
            "accept",
            "--summary",
            "The revision now states the eligibility rule and preserves 6/8 raw coverage separately from 5/6 eligible-program coverage.",
            "--strength",
            "denominator distinction is explicit and reproducible",
            "--limitation",
            "acceptance is limited to the synthetic descriptive analysis and establishes no external outcome",
            "--out",
            str(review_r1),
        ],
        transcript,
    )
    _run_cli(
        "validate revision acceptance",
        review_main,
        [
            "validate-revision",
            str(review_r1),
            "--submission",
            str(submission_r1),
            "--workspace",
            str(workspace_r1),
            "--parent-submission",
            str(submission_v0),
            "--trigger-review",
            str(review_v0),
        ],
        transcript,
    )
    _run_cli(
        "project accepted revision",
        review_main,
        [
            "project-revision",
            str(review_r1),
            "--submission",
            str(submission_r1),
            "--workspace",
            str(workspace_r1),
            "--parent-submission",
            str(submission_v0),
            "--trigger-review",
            str(review_v0),
            "--state",
            str(commons_path),
            "--receipt-out",
            str(projection_r1),
        ],
        transcript,
    )

    final_commons = ProblemCommons.load(commons_path)
    final_packet = final_commons.get("problem:rehearsal-food-coverage")
    if len(final_packet.attempts) != 1:
        raise RuntimeError("rehearsal created more than one canonical Attempt")
    attempt = final_packet.attempts[0]
    if attempt.status.value != "accepted":
        raise RuntimeError(f"final rehearsal Attempt is {attempt.status.value}, expected accepted")
    if [item.verdict for item in final_packet.attempt_reviews] != ["revise", "accept"]:
        raise RuntimeError("final rehearsal review history is not REVISE -> ACCEPT")
    if final_packet.status != ProblemStatus.OPEN:
        raise RuntimeError("rehearsal unexpectedly changed the Problem lifecycle")
    if final_packet.outcomes or final_packet.authority_decisions:
        raise RuntimeError("rehearsal unexpectedly created Outcome or authority state")

    revised_submission_raw = json.loads(submission_r1.read_text(encoding="utf-8"))
    expected_artifact_ids = [item["id"] for item in revised_submission_raw["artifacts"]]
    if attempt.artifact_refs != expected_artifact_ids:
        raise RuntimeError("canonical Attempt artifact refs do not match the revised opaque artifact IDs")

    public_payload = json.dumps(final_packet.public_snapshot(), ensure_ascii=False)
    for private_locator in (str(data_artifact), str(initial_report), str(revised_report)):
        if private_locator in public_payload:
            raise RuntimeError("private rehearsal artifact locator leaked into canonical public snapshot")

    receipt_v0 = json.loads(projection_v0.read_text(encoding="utf-8"))
    receipt_r1 = json.loads(projection_r1.read_text(encoding="utf-8"))
    if not receipt_v0.get("changed") or receipt_v0.get("attempt_status") != "active":
        raise RuntimeError("initial projection receipt does not record the expected REVISE transition")
    if not receipt_r1.get("changed") or receipt_r1.get("attempt_status") != "accepted":
        raise RuntimeError("revision projection receipt does not record the expected ACCEPT transition")

    friction = [
        {
            "id": "F1",
            "severity": "medium",
            "surface": "revision lineage CLI",
            "observation": "Revision create/validate/review/project commands repeatedly require both parent submission and triggering review paths.",
            "interpretation": "This is explicit and safe but verbose for a human operator across multiple rounds.",
            "disposition": "Do not change architecture; consider a thin session/pack wrapper only if external rehearsal confirms repeated operator burden.",
        },
        {
            "id": "F2",
            "severity": "low",
            "surface": "inherited list editing",
            "observation": "Clearing an inherited blocker through the current CLI uses an explicit empty --blocker value, which works but is not self-explanatory.",
            "interpretation": "Ergonomic debt rather than a lifecycle defect.",
            "disposition": "Candidate for an explicit clear/replace flag in a later CLI-only polish pass if humans encounter it.",
        },
        {
            "id": "F3",
            "severity": "medium",
            "surface": "evidence-file management",
            "observation": "A complete single revision round produces workspace, submission, review, projection receipt, Commons state, and source artifacts that must remain associated.",
            "interpretation": "The evidence model is coherent, but manual file organization can become the dominant operator task.",
            "disposition": "The rehearsal pack itself is the reference organization; do not infer a broad frontend requirement yet.",
        },
        {
            "id": "F4",
            "severity": "expected-boundary",
            "surface": "review identity",
            "observation": "The workflow proves reviewer_ref differs from contributor_ref but does not authenticate reviewer identity or competence.",
            "interpretation": "Correctly remains outside this software seam.",
            "disposition": "Preserve the boundary; external pilot governance must establish identity and role.",
        },
    ]

    transcript_path = out / "transcript.json"
    _write_json(transcript_path, transcript)
    _write_json(out / "friction.json", friction)

    evidence_files = sorted(
        path for path in out.rglob("*") if path.is_file() and path.name not in {"manifest.json"}
    )
    manifest = {
        "schema": "contribution-rehearsal-pack/v0.1",
        "case": "synthetic-community-food-redistribution-coverage",
        "result": "pass",
        "workflow": ["SUBMIT", "REVISE", "REVISION_R1", "RESUBMIT", "ACCEPT"],
        "problem_status": final_packet.status.value,
        "attempt_id": attempt.id,
        "attempt_status": attempt.status.value,
        "attempt_count": len(final_packet.attempts),
        "review_verdicts": [item.verdict for item in final_packet.attempt_reviews],
        "outcome_count": len(final_packet.outcomes),
        "authority_decision_count": len(final_packet.authority_decisions),
        "no_op_revision_rejected": True,
        "private_locator_leak_check": "pass",
        "claims_boundary": (
            "This rehearsal demonstrates software workflow behavior on synthetic fixtures only. Acceptance does not establish "
            "external correctness, Problem resolution, funding, authority, deployment, adoption, or real-world outcome."
        ),
        "friction_ids": [item["id"] for item in friction],
        "files": {str(path.relative_to(out)): _sha256_file(path) for path in evidence_files},
    }
    _write_json(out / "manifest.json", manifest)

    readme = out / "README.md"
    readme.write_text(
        "# Contribution rehearsal evidence pack\n\n"
        "Synthetic operating rehearsal: raw coverage submission -> REVISE -> explicit revision -> ACCEPT.\n\n"
        f"Final canonical Attempt: `{attempt.id}` / `{attempt.status.value}`.\n\n"
        "The Problem remains `open`; no Outcome or authority decision is created. See `manifest.json`, `transcript.json`, "
        "`friction.json`, both submissions/reviews, projection receipts, and the final Commons state for inspectable evidence.\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the synthetic contribution review/revision rehearsal and emit an evidence pack.")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        manifest = run_rehearsal(Path(args.out))
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"result": "fail", "error": str(exc)}, indent=2, ensure_ascii=False))
        return 2
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
