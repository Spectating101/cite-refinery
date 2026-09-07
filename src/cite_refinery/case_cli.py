from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .problem_case import ProblemCaseWorkspace
from .review_pack import build_review_pack


DEFAULT_COMMONS = Path(".cite-refinery/problem-commons.json")
DEFAULT_STAGES = Path(".cite-refinery/problem-stages.json")
DEFAULT_GOVERNANCE = Path(".cite-refinery/problem-governance.json")
DEFAULT_PILOT = Path(".cite-refinery/problem-pilot.json")
DEFAULT_RUBRICS = Path("pilot/rubrics.v0.1.json")


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="problem-case",
        description="Join Problem Commons, stage, governance and pilot state into one inspectable case view.",
    )
    parser.add_argument("--commons", default=str(DEFAULT_COMMONS))
    parser.add_argument("--stages", default=str(DEFAULT_STAGES))
    parser.add_argument("--governance", default=str(DEFAULT_GOVERNANCE))
    parser.add_argument("--pilot", default=str(DEFAULT_PILOT))
    sub = parser.add_subparsers(dest="command", required=True)

    snapshot = sub.add_parser("snapshot", help="Summarize one problem across all V0.1 planes")
    snapshot.add_argument("problem_id")

    validate = sub.add_parser("validate", help="Check cross-plane referential and readiness invariants")
    validate.add_argument("problem_id")

    next_cmd = sub.add_parser("next", help="Show the next bounded actions and current blockers")
    next_cmd.add_argument("problem_id")

    export = sub.add_parser("export", help="Write a complete operator/reviewer case bundle")
    export.add_argument("problem_id")
    export.add_argument("--out", required=True)

    review = sub.add_parser("review-pack", help="Write a minimum-necessary external pilot review pack")
    review.add_argument("problem_id")
    review.add_argument("--audience", choices=["owner", "reviewer", "solver"], required=True)
    review.add_argument("--rubrics", default=str(DEFAULT_RUBRICS))
    review.add_argument("--out", required=True)

    list_cmd = sub.add_parser("list", help="List all known Problem Packets with case-level milestone counts")
    list_cmd.add_argument("--public", action="store_true")
    return parser


def _workspace(args: argparse.Namespace) -> ProblemCaseWorkspace:
    return ProblemCaseWorkspace.load(
        commons_path=args.commons,
        stages_path=args.stages,
        governance_path=args.governance,
        pilot_path=args.pilot,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        workspace = _workspace(args)
        if args.command == "snapshot":
            _print(workspace.snapshot(args.problem_id).to_dict())
        elif args.command == "validate":
            report = workspace.validate(args.problem_id)
            _print({"valid": report.valid, "errors": report.errors, "warnings": report.warnings})
            return 0 if report.valid else 2
        elif args.command == "next":
            snapshot = workspace.snapshot(args.problem_id)
            _print({
                "problem_id": args.problem_id,
                "status": snapshot.status,
                "next_actions": snapshot.next_actions,
                "blockers": snapshot.blockers,
                "warnings": snapshot.warnings,
            })
        elif args.command == "export":
            path = workspace.save_bundle(args.problem_id, args.out)
            _print({"written": str(path), "problem_id": args.problem_id})
        elif args.command == "review-pack":
            rubrics = json.loads(Path(args.rubrics).read_text(encoding="utf-8"))
            pack = build_review_pack(workspace, args.problem_id, audience=args.audience, rubrics=rubrics)
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            _print({"written": str(target), "problem_id": args.problem_id, "audience": args.audience})
        elif args.command == "list":
            rows = workspace.commons.list_public() if args.public else list(workspace.commons.problems.values())
            payload = []
            for problem in rows:
                snapshot = workspace.snapshot(problem.id)
                payload.append({
                    "problem_id": problem.id,
                    "title": problem.title,
                    "status": snapshot.status,
                    "public": snapshot.public,
                    "milestones_complete": sum(snapshot.milestones.values()),
                    "milestones_total": len(snapshot.milestones),
                    "blockers": len(snapshot.blockers),
                    "next_action": snapshot.next_actions[0] if snapshot.next_actions else None,
                })
            _print(payload)
        else:
            parser.error("unknown command")
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
