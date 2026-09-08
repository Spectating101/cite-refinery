from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .problem_commons import ProblemCommons
from .problem_funding import CompensationMode, FundingNeed, FundingRegistry, FundingStatus, build_project_brief
from .problem_stages import ProblemStage, StageRegistry


DEFAULT_FUNDING_STATE = Path(".cite-refinery/problem-funding.json")
DEFAULT_PROBLEM_STATE = Path(".cite-refinery/problem-commons.json")
DEFAULT_STAGE_STATE = Path(".cite-refinery/problem-stages.json")


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="problem-funding", description="Minimal Problem Commons funding extension V0.1")
    parser.add_argument("--state", dest="state_path", default=str(DEFAULT_FUNDING_STATE), help="funding registry JSON path")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="Add or replace a funding need for one contribution")
    add.add_argument("problem_id")
    add.add_argument("subproblem_id")
    add.add_argument("--stage", required=True, choices=[item.value for item in ProblemStage])
    add.add_argument("--status", default=FundingStatus.UNKNOWN.value, choices=[item.value for item in FundingStatus])
    add.add_argument("--compensation", default=CompensationMode.UNSPECIFIED.value, choices=[item.value for item in CompensationMode])
    add.add_argument("--volunteer-compatible", action="store_true")
    add.add_argument("--currency", default="TWD")
    add.add_argument("--minimum", type=float)
    add.add_argument("--target", type=float)
    add.add_argument("--committed", type=float, default=0.0)
    add.add_argument("--instrument", action="append", default=[])
    add.add_argument("--in-kind", action="append", default=[])
    add.add_argument("--expense", action="append", default=[])
    add.add_argument("--restriction", action="append", default=[])
    add.add_argument("--source-ref", action="append", default=[])
    add.add_argument("--implementation-budget-owner", default="")
    add.add_argument("--maintenance-budget-owner", default="")
    add.add_argument("--note", default="")

    show = sub.add_parser("show", help="Show one funding need")
    show.add_argument("problem_id")
    show.add_argument("subproblem_id")

    listing = sub.add_parser("list", help="List funding needs")
    listing.add_argument("--problem-id")

    coverage = sub.add_parser("coverage", help="Summarize funding readiness for a problem")
    coverage.add_argument("problem_id")

    validate = sub.add_parser("validate", help="Validate all funding needs")

    brief = sub.add_parser("brief", help="Build one solver-facing project brief from existing state")
    brief.add_argument("problem_id")
    brief.add_argument("subproblem_id")
    brief.add_argument("--problem-state", default=str(DEFAULT_PROBLEM_STATE))
    brief.add_argument("--stage-state", default=str(DEFAULT_STAGE_STATE))

    import_cmd = sub.add_parser("import", help="Import a problem-funding/v0.1 JSON registry")
    import_cmd.add_argument("path")
    import_cmd.add_argument("--replace", action="store_true")

    export = sub.add_parser("export", help="Export the funding registry")
    export.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    registry = FundingRegistry.load(args.state_path)
    changed = False

    try:
        if args.command == "add":
            need = FundingNeed(
                problem_id=args.problem_id,
                subproblem_id=args.subproblem_id,
                stage=ProblemStage(args.stage),
                status=FundingStatus(args.status),
                compensation_mode=CompensationMode(args.compensation),
                volunteer_compatible=args.volunteer_compatible,
                currency=args.currency,
                minimum_amount=args.minimum,
                target_amount=args.target,
                committed_amount=args.committed,
                eligible_instruments=args.instrument,
                in_kind_needs=args.in_kind,
                expense_categories=args.expense,
                restrictions=args.restriction,
                funding_source_refs=args.source_ref,
                implementation_budget_owner=args.implementation_budget_owner,
                maintenance_budget_owner=args.maintenance_budget_owner,
                notes=args.note,
            )
            registry.upsert(need)
            _print(need.to_dict())
            changed = True
        elif args.command == "show":
            _print(registry.get(args.problem_id, args.subproblem_id).to_dict())
        elif args.command == "list":
            _print([row.to_dict() for row in registry.list(problem_id=args.problem_id)])
        elif args.command == "coverage":
            _print(registry.coverage(args.problem_id))
        elif args.command == "validate":
            rows = []
            valid = True
            for need in registry.list():
                report = need.validation()
                rows.append({"id": need.id, "valid": report.valid, "errors": report.errors, "warnings": report.warnings})
                valid = valid and report.valid
            _print({"schema": registry.schema, "valid": valid, "needs": rows})
            if not valid:
                return 2
        elif args.command == "brief":
            commons = ProblemCommons.load(args.problem_state)
            packet = commons.get(args.problem_id)
            stages = StageRegistry.load(args.stage_state)
            stage_profile = stages.profiles.get((args.problem_id, args.subproblem_id))
            funding_need = registry.needs.get((args.problem_id, args.subproblem_id))
            _print(build_project_brief(packet, args.subproblem_id, stage_profile=stage_profile, funding_need=funding_need).to_dict())
        elif args.command == "import":
            incoming = FundingRegistry.load(args.path)
            if args.replace:
                registry = incoming
            else:
                for need in incoming.list():
                    registry.upsert(need)
            _print({"imported": len(incoming.needs), "total": len(registry.needs)})
            changed = True
        elif args.command == "export":
            target = Path(args.out)
            registry.dump(target)
            _print({"written": str(target), "needs": len(registry.needs)})
        else:
            parser.error("unknown command")
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    if changed:
        registry.dump(args.state_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
