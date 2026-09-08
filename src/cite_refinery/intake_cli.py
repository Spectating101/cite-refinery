from __future__ import annotations

import argparse
import json
from pathlib import Path

from .intake_review import build_intake_owner_review_pack, validate_owner_review_response
from .problem_intake import OwnerIntake


def _print(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="problem-intake",
        description="Validate external problem-owner intake and generate fail-closed Problem Commons pilot artifacts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate one problem-owner intake JSON file")
    validate.add_argument("path")

    draft = sub.add_parser("draft", help="Generate a non-public candidate Problem Packet from an intake")
    draft.add_argument("path")
    draft.add_argument("--steward", required=True)
    draft.add_argument("--out", required=True)

    review = sub.add_parser("owner-review", help="Generate a minimum-necessary review pack for the potential problem owner")
    review.add_argument("path")
    review.add_argument("--steward", required=True)
    review.add_argument("--rubrics", default="pilot/rubrics.v0.1.json")
    review.add_argument("--out", required=True)

    validate_review = sub.add_parser("validate-owner-review", help="Validate a completed owner-review response pack")
    validate_review.add_argument("path")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate-owner-review":
            pack = json.loads(Path(args.path).read_text(encoding="utf-8"))
            errors = validate_owner_review_response(pack)
            _print({"valid": not errors, "errors": errors})
            return 0 if not errors else 2

        intake = OwnerIntake.load(args.path)
        report = intake.validation()
        if args.command == "validate":
            _print({"valid": report.valid, "errors": report.errors, "warnings": report.warnings})
            return 0 if report.valid else 2
        if not report.valid:
            _print({"valid": False, "errors": report.errors, "warnings": report.warnings})
            return 2

        packet = intake.to_problem_packet(steward=args.steward)
        if args.command == "draft":
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(packet.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            publishability = packet.publishability(require_decomposition=False)
            _print({
                "written": str(target),
                "problem_id": packet.id,
                "status": packet.status.value,
                "visibility": packet.visibility.value,
                "owner_confirmed": intake.owner_is_confirmed,
                "candidate_work_paths": len(packet.subproblems),
                "publishability": {
                    "publishable": publishability.publishable,
                    "missing": publishability.missing,
                    "warnings": publishability.warnings,
                },
            })
            return 0

        if args.command == "owner-review":
            rubrics = json.loads(Path(args.rubrics).read_text(encoding="utf-8"))
            pack = build_intake_owner_review_pack(intake, packet, rubrics=rubrics)
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            _print({
                "written": str(target),
                "schema": pack["schema"],
                "problem_id": packet.id,
                "potential_owner": intake.owner_org,
                "candidate_work_paths": len(packet.subproblems),
            })
            return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        _print({"error": str(exc)})
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
