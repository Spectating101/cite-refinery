from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .pilot import PilotLedger
from .problem_case import ProblemCaseWorkspace
from .solver_experiment import CONTROL_ARM, TREATMENT_ARM, assign_arm, build_experiment_pack, summarize_experiment


DEFAULT_COMMONS = Path(".cite-refinery/problem-commons.json")
DEFAULT_STAGES = Path(".cite-refinery/problem-stages.json")
DEFAULT_GOVERNANCE = Path(".cite-refinery/problem-governance.json")
DEFAULT_PILOT = Path(".cite-refinery/problem-pilot.json")
DEFAULT_RUBRICS = Path("pilot/rubrics.v0.1.json")


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="problem-experiment",
        description="Build and summarize the ordinary-brief vs Problem-Packet solver pilot.",
    )
    parser.add_argument("--commons", default=str(DEFAULT_COMMONS))
    parser.add_argument("--stages", default=str(DEFAULT_STAGES))
    parser.add_argument("--governance", default=str(DEFAULT_GOVERNANCE))
    parser.add_argument("--pilot", default=str(DEFAULT_PILOT))
    parser.add_argument("--rubrics", default=str(DEFAULT_RUBRICS))
    sub = parser.add_subparsers(dest="command", required=True)

    assign = sub.add_parser("assign", help="Deterministically counterbalance one participant")
    assign.add_argument("problem_id")
    assign.add_argument("--participant", required=True)
    assign.add_argument("--sequence-index", type=int, default=0)

    build = sub.add_parser("build", help="Build a solver review pack for the assigned experiment arm")
    build.add_argument("problem_id")
    build.add_argument("--participant", required=True)
    build.add_argument("--sequence-index", type=int, default=0)
    build.add_argument("--force-arm", choices=[CONTROL_ARM, TREATMENT_ARM])
    build.add_argument("--out", required=True)

    report = sub.add_parser("report", help="Summarize recorded solver sessions by experiment arm")
    report.add_argument("--problem-id")
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
        if args.command == "assign":
            _print(assign_arm(args.problem_id, args.participant, sequence_index=args.sequence_index).to_dict())
        elif args.command == "build":
            rubrics = json.loads(Path(args.rubrics).read_text(encoding="utf-8"))
            pack = build_experiment_pack(
                _workspace(args), args.problem_id,
                participant_id=args.participant,
                sequence_index=args.sequence_index,
                forced_arm=args.force_arm,
                rubrics=rubrics,
            )
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            _print({"written": str(target), "problem_id": args.problem_id, "participant_id": args.participant, "arm": pack["response"]["arm"]})
        elif args.command == "report":
            ledger = PilotLedger.load(args.pilot)
            _print(summarize_experiment(ledger.solvers, problem_id=args.problem_id))
        else:
            parser.error("unknown command")
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
