from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .problem_stages import (
    AuthorityLevel,
    MethodMaturity,
    ProblemStage,
    StageProfile,
    StageRegistry,
    UncertaintyLevel,
)


DEFAULT_STAGE_STATE = Path(".cite-refinery/problem-stages.json")


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="problem-stages", description="Problem Commons problem-solving stage extension V0.1")
    parser.add_argument("--state", dest="state_path", default=str(DEFAULT_STAGE_STATE), help="stage registry JSON path")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="Add or replace a contribution-stage profile")
    add.add_argument("problem_id")
    add.add_argument("subproblem_id")
    add.add_argument("--stage", required=True, choices=[stage.value for stage in ProblemStage])
    add.add_argument("--question", required=True)
    add.add_argument("--epistemic-type", required=True)
    add.add_argument("--uncertainty", required=True, choices=[item.value for item in UncertaintyLevel])
    add.add_argument("--method-maturity", required=True, choices=[item.value for item in MethodMaturity])
    add.add_argument("--output", action="append", required=True)
    add.add_argument("--evaluation", required=True)
    add.add_argument("--authority-level", choices=[item.value for item in AuthorityLevel], default=AuthorityLevel.NONE.value)
    add.add_argument("--authority-requirement", default="")
    add.add_argument("--credential", action="append", default=[])
    add.add_argument("--route", action="append", default=[])
    add.add_argument("--reuse-target", default="")
    add.add_argument("--note", default="")

    show = sub.add_parser("show", help="Show one contribution-stage profile")
    show.add_argument("problem_id")
    show.add_argument("subproblem_id")

    listing = sub.add_parser("list", help="List stage profiles")
    listing.add_argument("--problem-id")
    listing.add_argument("--stage", choices=[stage.value for stage in ProblemStage])

    route = sub.add_parser("route", help="Show routing and work-mode interpretation")
    route.add_argument("problem_id")
    route.add_argument("subproblem_id")

    coverage = sub.add_parser("coverage", help="Summarize stage/system/work-mode coverage for a problem")
    coverage.add_argument("problem_id")

    validate = sub.add_parser("validate", help="Validate all profiles")

    import_cmd = sub.add_parser("import", help="Import a problem-stages/v0.1 JSON registry")
    import_cmd.add_argument("path")
    import_cmd.add_argument("--replace", action="store_true", help="replace current registry instead of merging")

    export = sub.add_parser("export", help="Export the stage registry")
    export.add_argument("--out", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    registry = StageRegistry.load(args.state_path)
    changed = False

    try:
        if args.command == "add":
            profile = StageProfile(
                problem_id=args.problem_id,
                subproblem_id=args.subproblem_id,
                stage=ProblemStage(args.stage),
                question=args.question,
                epistemic_type=args.epistemic_type,
                uncertainty=UncertaintyLevel(args.uncertainty),
                method_maturity=MethodMaturity(args.method_maturity),
                expected_outputs=args.output,
                evaluation_method=args.evaluation,
                authority_level=AuthorityLevel(args.authority_level),
                authority_requirement=args.authority_requirement,
                required_credentials=args.credential,
                system_routes=args.route,
                reuse_target=args.reuse_target,
                notes=args.note,
            )
            registry.upsert(profile)
            _print(profile.to_dict())
            changed = True
        elif args.command == "show":
            _print(registry.get(args.problem_id, args.subproblem_id).to_dict())
        elif args.command == "list":
            rows = registry.list(problem_id=args.problem_id, stage=ProblemStage(args.stage) if args.stage else None)
            _print([row.to_dict() for row in rows])
        elif args.command == "route":
            profile = registry.get(args.problem_id, args.subproblem_id)
            _print({
                "problem_id": profile.problem_id,
                "subproblem_id": profile.subproblem_id,
                "stage": profile.stage.value,
                "work_mode": profile.work_mode.value,
                "requires_professional_authority": profile.requires_professional_authority,
                "route_plan": profile.route_plan(),
            })
        elif args.command == "coverage":
            _print(registry.coverage(args.problem_id))
        elif args.command == "validate":
            report = registry.validate_all()
            _print(report)
            if not report["valid"]:
                return 2
        elif args.command == "import":
            incoming = StageRegistry.load(args.path)
            if args.replace:
                registry = incoming
            else:
                for profile in incoming.list():
                    registry.upsert(profile)
            _print({"imported": len(incoming.profiles), "total": len(registry.profiles)})
            changed = True
        elif args.command == "export":
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            registry.save(target)
            _print({"written": str(target), "profiles": len(registry.profiles)})
        else:
            parser.error("unknown command")
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    if changed:
        registry.save(args.state_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
