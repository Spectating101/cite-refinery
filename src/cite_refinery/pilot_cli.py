from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pilot import PilotLedger


DEFAULT_STATE = Path(".cite-refinery/problem-pilot.json")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="problem-pilot", description="Record evidence from a Problem Commons pilot")
    root.add_argument("--state", default=str(DEFAULT_STATE), help="pilot ledger JSON path")
    sub = root.add_subparsers(dest="command", required=True)

    production = sub.add_parser("production-add", help="record Problem Packet production cost/quality")
    production.add_argument("problem_id")
    production.add_argument("--minutes", type=float, required=True)
    production.add_argument("--sources", type=int, default=0)
    production.add_argument("--corrections", type=int, default=0)
    production.add_argument("--reframings", type=int, default=0)
    production.add_argument("--owner-agreement", type=float)
    production.add_argument("--reviewer-score", type=float)
    production.add_argument("--publishable", action="store_true")
    production.add_argument("--blocker", action="append", default=[])
    production.add_argument("--notes", default="")

    solver = sub.add_parser("solver-add", help="record an independent solver session")
    solver.add_argument("problem_id")
    solver.add_argument("participant_id")
    solver.add_argument("--arm", default="problem_packet")
    solver.add_argument("--comprehension", type=float)
    solver.add_argument("--minutes-to-edge", type=float)
    solver.add_argument("--coaching-minutes", type=float, default=0)
    solver.add_argument("--subproblem-id")
    solver.add_argument("--serious-attempt", action="store_true")
    solver.add_argument("--abandoned", action="store_true")
    solver.add_argument("--abandonment-reason", default="")
    solver.add_argument("--usefulness", type=float)
    solver.add_argument("--notes", default="")

    adoption = sub.add_parser("adoption-add", help="record attempt-to-world conversion state")
    adoption.add_argument("problem_id")
    adoption.add_argument("attempt_id")
    adoption.add_argument("--accepted-review", action="store_true")
    adoption.add_argument("--accepted-pilot", action="store_true")
    adoption.add_argument("--authorized", action="store_true")
    adoption.add_argument("--deployed", action="store_true")
    adoption.add_argument("--maintenance-owner", action="store_true")
    adoption.add_argument("--outcome-observed", action="store_true")
    adoption.add_argument("--guardrail-violation", action="store_true")
    adoption.add_argument("--stop-reason", default="")
    adoption.add_argument("--notes", default="")

    reuse = sub.add_parser("reuse-add", help="measure cross-problem reuse net of search/adaptation cost")
    reuse.add_argument("source_problem_id")
    reuse.add_argument("target_problem_id")
    reuse.add_argument("asset_type")
    reuse.add_argument("asset_ref")
    reuse.add_argument("--search-minutes", type=float, required=True)
    reuse.add_argument("--adaptation-minutes", type=float, required=True)
    reuse.add_argument("--rebuild-minutes", type=float, required=True)
    reuse.add_argument("--failed", action="store_true")
    reuse.add_argument("--notes", default="")

    sub.add_parser("report", help="print aggregate pilot measurements")
    sub.add_parser("dump", help="print raw pilot ledger")
    return root


def emit(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    path = Path(args.state)
    ledger = PilotLedger.load(path)

    if args.command == "production-add":
        item = ledger.record_production(
            problem_id=args.problem_id,
            curator_minutes=args.minutes,
            source_count=args.sources,
            correction_count=args.corrections,
            reframing_count=args.reframings,
            owner_agreement=args.owner_agreement,
            reviewer_score=args.reviewer_score,
            publishable=args.publishable,
            blocker_codes=args.blocker,
            notes=args.notes,
        )
    elif args.command == "solver-add":
        item = ledger.record_solver(
            problem_id=args.problem_id,
            participant_id=args.participant_id,
            arm=args.arm,
            comprehension_score=args.comprehension,
            minutes_to_useful_edge=args.minutes_to_edge,
            coaching_minutes=args.coaching_minutes,
            selected_subproblem_id=args.subproblem_id,
            serious_attempt=args.serious_attempt,
            abandoned=args.abandoned,
            abandonment_reason=args.abandonment_reason,
            usefulness_rating=args.usefulness,
            notes=args.notes,
        )
    elif args.command == "adoption-add":
        item = ledger.record_adoption(
            problem_id=args.problem_id,
            attempt_id=args.attempt_id,
            accepted_for_review=args.accepted_review,
            accepted_for_pilot=args.accepted_pilot,
            pilot_authorized=args.authorized,
            deployed=args.deployed,
            maintenance_owner_identified=args.maintenance_owner,
            outcome_observed=args.outcome_observed,
            guardrail_violation=args.guardrail_violation,
            stop_reason=args.stop_reason,
            notes=args.notes,
        )
    elif args.command == "reuse-add":
        item = ledger.record_reuse(
            source_problem_id=args.source_problem_id,
            target_problem_id=args.target_problem_id,
            asset_type=args.asset_type,
            asset_ref=args.asset_ref,
            search_minutes=args.search_minutes,
            adaptation_minutes=args.adaptation_minutes,
            estimated_rebuild_minutes=args.rebuild_minutes,
            successful=not args.failed,
            notes=args.notes,
        )
    elif args.command == "report":
        emit(ledger.report().to_dict())
        return 0
    elif args.command == "dump":
        emit(ledger.to_dict())
        return 0
    else:
        raise AssertionError(args.command)

    ledger.save(path)
    emit({"recorded": item.__class__.__name__, "id": item.id, "state": str(path)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
