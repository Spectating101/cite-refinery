from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contribution_handoff import (
    ContributorWorkspace,
    ParticipationBasis,
    hash_file,
    validate_project_brief,
)


def _print(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="problem-contribution",
        description="Create and validate bounded contributor workspaces from Problem Commons Project Briefs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate_brief = sub.add_parser("validate-brief")
    validate_brief.add_argument("brief")

    init = sub.add_parser("init")
    init.add_argument("brief")
    init.add_argument("--contributor-ref", required=True)
    init.add_argument("--out", required=True)

    activate = sub.add_parser("activate")
    activate.add_argument("workspace")
    activate.add_argument("--basis", choices=[item.value for item in ParticipationBasis if item != ParticipationBasis.NOT_ESTABLISHED], required=True)
    activate.add_argument("--participation-note", default="")

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

    validate = sub.add_parser("validate")
    validate.add_argument("workspace")
    validate.add_argument("--submittable", action="store_true")

    submit = sub.add_parser("submit")
    submit.add_argument("workspace")
    submit.add_argument("--submission-out", required=True)

    withdraw = sub.add_parser("withdraw")
    withdraw.add_argument("workspace")
    withdraw.add_argument("--reason", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate-brief":
            brief = _load_json(args.brief)
            errors = validate_project_brief(brief)
            _print({"valid": not errors, "errors": errors})
            return 0 if not errors else 2

        if args.command == "init":
            brief = _load_json(args.brief)
            workspace = ContributorWorkspace.from_project_brief(brief, contributor_ref=args.contributor_ref)
            workspace.dump(args.out)
            _print({"written": args.out, "workspace_id": workspace.id, "state": workspace.state.value, "project_brief_hash": workspace.project_brief_hash})
            return 0

        workspace = ContributorWorkspace.load(args.workspace)

        if args.command == "activate":
            workspace.activate(basis=args.basis, participation_note=args.participation_note)
            workspace.dump(args.workspace)
            _print({"workspace_id": workspace.id, "state": workspace.state.value, "participation_basis": workspace.participation_basis.value})
            return 0

        if args.command == "set-work":
            workspace.set_work(
                method_scope=args.method_scope,
                produced_outputs=args.produced_output,
                blockers=args.blocker,
                notes=args.notes,
            )
            workspace.dump(args.workspace)
            _print({"workspace_id": workspace.id, "state": workspace.state.value, "method_scope": workspace.method_scope, "produced_outputs": workspace.produced_outputs, "blockers": workspace.blockers})
            return 0

        if args.command == "artifact-add":
            locator = args.locator or args.file
            digest = args.sha256
            if args.file:
                digest = hash_file(args.file)
            item = workspace.add_artifact(title=args.title, kind=args.kind, locator=locator, sha256_value=digest, notes=args.notes)
            workspace.dump(args.workspace)
            _print(item.__dict__ if hasattr(item, "__dict__") else {"id": item.id, "title": item.title, "kind": item.kind, "locator": item.locator, "sha256": item.sha256, "notes": item.notes})
            return 0

        if args.command == "validate":
            report = workspace.validation(require_submittable=args.submittable)
            _print({"valid": report.valid, "errors": report.errors, "warnings": report.warnings})
            return 0 if report.valid else 2

        if args.command == "submit":
            submission = workspace.submit()
            workspace.dump(args.workspace)
            target = Path(args.submission_out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(submission, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            _print({"workspace_id": workspace.id, "state": workspace.state.value, "submission": str(target), "workspace_hash": submission["workspace_hash"]})
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
