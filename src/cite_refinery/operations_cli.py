from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .case_operations import CaseOperations
from .draft_admission import admit_draft_packet


DEFAULT_COMMONS = Path(".cite-refinery/problem-commons.json")
DEFAULT_STAGES = Path(".cite-refinery/problem-stages.json")
DEFAULT_GOVERNANCE = Path(".cite-refinery/problem-governance.json")
DEFAULT_PILOT = Path(".cite-refinery/problem-pilot.json")
DEFAULT_OPERATIONS = Path(".cite-refinery/problem-operations.json")
DEFAULT_POLICY = Path("pilot/operations-policy.v0.1.json")


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="problem-ops",
        description="Explicit reviewed operations for running Problem Commons V0.1 cases.",
    )
    parser.add_argument("--commons", default=str(DEFAULT_COMMONS))
    parser.add_argument("--stages", default=str(DEFAULT_STAGES))
    parser.add_argument("--governance", default=str(DEFAULT_GOVERNANCE))
    parser.add_argument("--pilot", default=str(DEFAULT_PILOT))
    parser.add_argument("--operations", default=str(DEFAULT_OPERATIONS))
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    sub = parser.add_subparsers(dest="command", required=True)

    draft = sub.add_parser("draft-import", help="Admit a standalone non-public Problem Packet draft for curation")
    draft.add_argument("path")
    draft.add_argument("--actor", required=True)
    draft.add_argument("--allow-duplicate", action="store_true")

    prod = sub.add_parser("production-start", help="Record curation cost/quality for a problem candidate")
    prod.add_argument("problem_id")
    prod.add_argument("--actor", required=True)
    prod.add_argument("--curator-minutes", type=float, required=True)
    prod.add_argument("--source-count", type=int, default=0)
    prod.add_argument("--correction-count", type=int, default=0)
    prod.add_argument("--reframing-count", type=int, default=0)
    prod.add_argument("--publishable", action="store_true")
    prod.add_argument("--blocker", action="append", default=[])
    prod.add_argument("--note", default="")

    ingest = sub.add_parser("review-ingest", help="Ingest a completed owner/reviewer/solver review pack")
    ingest.add_argument("path")
    ingest.add_argument("--participant", required=True)
    ingest.add_argument("--coaching-minutes", type=float, default=0.0)
    ingest.add_argument("--serious-attempt", action=argparse.BooleanOptionalAction, default=None)
    ingest.add_argument("--usefulness", type=float)
    ingest.add_argument("--subproblem")
    ingest.add_argument("--abandoned", action=argparse.BooleanOptionalAction, default=None)
    ingest.add_argument("--abandonment-reason")
    ingest.add_argument("--note", default="")

    assess = sub.add_parser("assess", help="Evaluate one case against the explicit pilot operations policy")
    assess.add_argument("problem_id")

    queue = sub.add_parser("queue", help="Show operational queue across known problems")
    queue.add_argument("--public", action="store_true")

    promote = sub.add_parser("promote", help="Explicit curator promotion after review gates")
    promote.add_argument("problem_id")
    promote.add_argument("target", choices=["verified", "open"])
    promote.add_argument("--actor", required=True)
    promote.add_argument("--reason", required=True)

    receipts = sub.add_parser("receipts", help="Show append-only case operation receipts")
    receipts.add_argument("problem_id")
    return parser


def _operations(args: argparse.Namespace) -> CaseOperations:
    return CaseOperations.load(
        commons_path=args.commons,
        stages_path=args.stages,
        governance_path=args.governance,
        pilot_path=args.pilot,
        operations_path=args.operations,
    )


def _save(ops: CaseOperations, args: argparse.Namespace) -> None:
    ops.save(commons_path=args.commons, pilot_path=args.pilot, operations_path=args.operations)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        ops = _operations(args)
        policy = _load_json(args.policy)
        changed = False

        if args.command == "draft-import":
            payload = _load_json(args.path)
            packet, receipt, duplicates = admit_draft_packet(
                ops, payload, actor=args.actor, allow_duplicate=args.allow_duplicate,
            )
            _print({
                "problem_id": packet.id,
                "status": packet.status.value,
                "visibility": packet.visibility.value,
                "duplicate_candidates": duplicates,
                "receipt_id": receipt.id,
            })
            changed = True
        elif args.command == "production-start":
            if min(args.curator_minutes, args.source_count, args.correction_count, args.reframing_count) < 0:
                raise ValueError("curation time/count values must be non-negative")
            item = ops.start_production(
                args.problem_id,
                actor=args.actor,
                curator_minutes=args.curator_minutes,
                source_count=args.source_count,
                correction_count=args.correction_count,
                reframing_count=args.reframing_count,
                publishable=args.publishable,
                blocker_codes=args.blocker,
                notes=args.note,
            )
            _print(item)
            changed = True
        elif args.command == "review-ingest":
            if args.coaching_minutes < 0:
                raise ValueError("coaching_minutes must be non-negative")
            pack = _load_json(args.path)
            result = ops.ingest_review_pack(
                pack,
                participant_id=args.participant,
                coaching_minutes=args.coaching_minutes,
                serious_attempt=args.serious_attempt,
                usefulness_rating=args.usefulness,
                selected_subproblem_id=args.subproblem,
                abandoned=args.abandoned,
                abandonment_reason=args.abandonment_reason,
                notes=args.note,
            )
            _print(result.to_dict())
            changed = True
        elif args.command == "assess":
            _print(ops.assess(args.problem_id, policy=policy).to_dict())
        elif args.command == "queue":
            _print(ops.queue(policy=policy, public_only=args.public))
        elif args.command == "promote":
            receipt = ops.promote(args.problem_id, target=args.target, actor=args.actor, reason=args.reason, policy=policy)
            _print(receipt)
            changed = True
        elif args.command == "receipts":
            _print([{
                "id": item.id, "problem_id": item.problem_id, "action": item.action, "actor": item.actor,
                "summary": item.summary, "inputs": item.inputs, "outputs": item.outputs,
                "problem_sha256": item.problem_sha256, "pilot_sha256": item.pilot_sha256, "created_at": item.created_at,
            } for item in ops.operations.for_problem(args.problem_id)])
        else:
            parser.error("unknown command")

        if changed:
            _save(ops, args)
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
