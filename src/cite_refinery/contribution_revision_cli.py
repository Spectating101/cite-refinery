from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contribution_handoff import hash_file
from .contribution_revision import ContributionRevisionWorkspace


def _print(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="problem-contribution-revision",
        description="Create and operate immutable-lineage revision workspaces after a contribution receives REVISE.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a revision workspace from an exact submission and its REVISE review")
    init.add_argument("parent_submission")
    init.add_argument("--trigger-review", required=True)
    init.add_argument("--out", required=True)

    set_work = sub.add_parser("set-work")
    set_work.add_argument("workspace")
    set_work.add_argument("--method-scope")
    set_work.add_argument("--produced-output", action="append")
    set_work.add_argument("--blocker", action="append")
    set_work.add_argument("--notes")

    artifact = sub.add_parser("artifact-add")
    artifact.add_argument("workspace")
    artifact.add_argument("--title", required=True)
    artifact.add_argument("--kind", required=True)
    source = artifact.add_mutually_exclusive_group(required=True)
    source.add_argument("--locator")
    source.add_argument("--file")
    artifact.add_argument("--sha256", default="")
    artifact.add_argument("--notes", default="")

    artifact_remove = sub.add_parser("artifact-remove")
    artifact_remove.add_argument("workspace")
    artifact_remove.add_argument("--artifact-id", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("workspace")
    validate.add_argument("--parent-submission", required=True)
    validate.add_argument("--trigger-review", required=True)
    validate.add_argument("--submittable", action="store_true")

    submit = sub.add_parser("submit")
    submit.add_argument("workspace")
    submit.add_argument("--parent-submission", required=True)
    submit.add_argument("--trigger-review", required=True)
    submit.add_argument("--submission-out", required=True)

    withdraw = sub.add_parser("withdraw")
    withdraw.add_argument("workspace")
    withdraw.add_argument("--reason", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            parent_submission = _load_json(args.parent_submission)
            trigger_review = _load_json(args.trigger_review)
            workspace = ContributionRevisionWorkspace.from_revise(parent_submission, trigger_review)
            workspace.dump(args.out)
            _print({
                "written": args.out,
                "workspace_id": workspace.id,
                "root_workspace_id": workspace.root_workspace_id,
                "revision_number": workspace.revision_number,
                "state": workspace.state.value,
                "parent_submission_hash": workspace.parent_submission_hash,
                "trigger_review_hash": workspace.trigger_review_hash,
                "revision_requirements": workspace.revision_requirements,
            })
            return 0

        workspace = ContributionRevisionWorkspace.load(args.workspace)

        if args.command == "set-work":
            workspace.set_work(
                method_scope=args.method_scope,
                produced_outputs=args.produced_output,
                blockers=args.blocker,
                notes=args.notes,
            )
            workspace.dump(args.workspace)
            _print({
                "workspace_id": workspace.id,
                "revision_number": workspace.revision_number,
                "state": workspace.state.value,
                "work_hash": workspace.current_work_hash(),
            })
            return 0

        if args.command == "artifact-add":
            locator = args.locator or args.file
            digest = args.sha256
            if args.file:
                digest = hash_file(args.file)
            item = workspace.add_artifact(
                title=args.title,
                kind=args.kind,
                locator=locator,
                sha256_value=digest,
                notes=args.notes,
            )
            workspace.dump(args.workspace)
            _print({
                "id": item.id,
                "title": item.title,
                "kind": item.kind,
                "locator": item.locator,
                "sha256": item.sha256,
                "notes": item.notes,
            })
            return 0

        if args.command == "artifact-remove":
            item = workspace.remove_artifact(args.artifact_id)
            workspace.dump(args.workspace)
            _print({"removed": item.id, "workspace_id": workspace.id, "work_hash": workspace.current_work_hash()})
            return 0

        if args.command == "validate":
            parent_submission = _load_json(args.parent_submission)
            trigger_review = _load_json(args.trigger_review)
            report = workspace.validation(
                parent_submission=parent_submission,
                trigger_review=trigger_review,
                require_submittable=args.submittable,
            )
            _print({"valid": report.valid, "errors": report.errors, "warnings": report.warnings})
            return 0 if report.valid else 2

        if args.command == "submit":
            parent_submission = _load_json(args.parent_submission)
            trigger_review = _load_json(args.trigger_review)
            submission = workspace.submit(parent_submission=parent_submission, trigger_review=trigger_review)
            workspace.dump(args.workspace)
            target = Path(args.submission_out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(submission, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            _print({
                "workspace_id": workspace.id,
                "root_workspace_id": workspace.root_workspace_id,
                "revision_number": workspace.revision_number,
                "state": workspace.state.value,
                "submission": str(target),
                "workspace_hash": submission["workspace_hash"],
                "work_hash": submission["work_hash"],
            })
            return 0

        if args.command == "withdraw":
            workspace.withdraw(reason=args.reason)
            workspace.dump(args.workspace)
            _print({"workspace_id": workspace.id, "state": workspace.state.value})
            return 0

    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        _print({"error": str(exc)})
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
