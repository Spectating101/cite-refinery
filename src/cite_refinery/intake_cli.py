from __future__ import annotations

import argparse
import json
from pathlib import Path

from .problem_intake import OwnerIntake


def _print(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="problem-intake",
        description="Validate external problem-owner intake and generate a fail-closed Problem Commons draft.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate one problem-owner intake JSON file")
    validate.add_argument("path")

    draft = sub.add_parser("draft", help="Generate a non-public candidate Problem Packet from an intake")
    draft.add_argument("path")
    draft.add_argument("--steward", required=True)
    draft.add_argument("--out", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        intake = OwnerIntake.load(args.path)
        report = intake.validation()
        if args.command == "validate":
            _print({"valid": report.valid, "errors": report.errors, "warnings": report.warnings})
            return 0 if report.valid else 2
        if args.command == "draft":
            if not report.valid:
                _print({"valid": False, "errors": report.errors, "warnings": report.warnings})
                return 2
            packet = intake.to_problem_packet(steward=args.steward)
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(packet.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            _print({
                "written": str(target),
                "problem_id": packet.id,
                "status": packet.status.value,
                "visibility": packet.visibility.value,
                "owner_confirmed": intake.owner_is_confirmed,
                "candidate_work_paths": len(packet.subproblems),
                "publishability": packet.publishability(require_decomposition=False).__dict__ if hasattr(packet.publishability(require_decomposition=False), "__dict__") else {
                    "publishable": packet.publishability(require_decomposition=False).publishable,
                    "missing": packet.publishability(require_decomposition=False).missing,
                    "warnings": packet.publishability(require_decomposition=False).warnings,
                },
            })
            return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        _print({"error": str(exc)})
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
