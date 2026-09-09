from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from .intake_batch import load_owner_intake_csv
from .intake_review import build_intake_owner_review_pack, validate_owner_review_response
from .problem_intake import OwnerIntake
from .owner_review_contract import build_owner_review_receipt
from .owner_review_page import render_owner_review_page


def _print(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def _file_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return token.strip("-") or "intake"


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
    review.add_argument("--html-out", help="Also create an offline single-file review page")
    review.add_argument("--assets-dir", help="Override the repository prototype asset directory")

    batch = sub.add_parser(
        "batch-csv",
        help="Convert a plain CSV of institutional/field needs into restricted candidate + owner-review artifacts",
    )
    batch.add_argument("path")
    batch.add_argument("--steward", required=True)
    batch.add_argument("--rubrics", default="pilot/rubrics.v0.1.json")
    batch.add_argument("--out-dir", required=True)

    validate_review = sub.add_parser("validate-owner-review", help="Validate a completed owner-review response pack")
    validate_review.add_argument("path")
    validate_review.add_argument("--require-complete", action="store_true")
    validate_review.add_argument("--original", help="Curator-retained issued pack to bind the response to")

    record = sub.add_parser("record-owner-review", help="Validate a returned review against the issued pack; write a private receipt, without changing case state")
    record.add_argument("path", help="Returned review file")
    record.add_argument("--original", required=True, help="Curator-retained original review pack")
    record.add_argument("--actor", required=True, help="Curator recording the return, not asserted reviewer identity")
    record.add_argument("--receipt-ref", required=True)
    record.add_argument("--out", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate-owner-review":
            pack = json.loads(Path(args.path).read_text(encoding="utf-8"))
            original = json.loads(Path(args.original).read_text(encoding="utf-8")) if args.original else None
            errors = validate_owner_review_response(pack, require_complete=args.require_complete, expected_pack=original)
            _print({"valid": not errors, "errors": errors})
            return 0 if not errors else 2

        if args.command == "record-owner-review":
            original = json.loads(Path(args.original).read_text(encoding="utf-8"))
            returned = json.loads(Path(args.path).read_text(encoding="utf-8"))
            receipt = build_owner_review_receipt(original, returned, actor=args.actor, receipt_ref=args.receipt_ref)
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            # Refuse overwrite and make local receipts private by default.
            import os
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(receipt, handle, indent=2, ensure_ascii=False, allow_nan=False)
                handle.write("\n")
            _print({"written": str(target), "receipt_id": receipt["id"], "status": receipt["status"],
                    "next_action": receipt["next_action"], "case_state_changed": False})
            return 0

        if args.command == "batch-csv":
            records = load_owner_intake_csv(args.path)
            rubrics = json.loads(Path(args.rubrics).read_text(encoding="utf-8"))
            out_dir = Path(args.out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            rows = []
            for record in records:
                if not record.valid or record.intake is None:
                    rows.append({
                        "row_number": record.row_number,
                        "valid": False,
                        "errors": record.errors,
                        "warnings": record.warnings,
                    })
                    continue

                intake = record.intake
                packet = intake.to_problem_packet(steward=args.steward)
                token = _file_token(intake.id.split(":", 1)[1])
                candidate_path = out_dir / f"{token}.candidate.json"
                review_path = out_dir / f"{token}.owner-review.json"
                candidate_path.write_text(json.dumps(packet.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                review_pack = build_intake_owner_review_pack(intake, packet, rubrics=rubrics)
                review_path.write_text(json.dumps(review_pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                rows.append({
                    "row_number": record.row_number,
                    "valid": True,
                    "intake_id": intake.id,
                    "problem_id": packet.id,
                    "potential_owner": intake.owner_org,
                    "owner_confirmed": intake.owner_is_confirmed,
                    "candidate_work_paths": len(packet.subproblems),
                    "candidate_path": str(candidate_path),
                    "owner_review_path": str(review_path),
                    "warnings": record.warnings,
                })

            manifest = {
                "schema": "problem-owner-intake-batch-result/v0.1",
                "source": str(Path(args.path)),
                "rows": rows,
                "valid_rows": sum(1 for row in rows if row["valid"]),
                "invalid_rows": sum(1 for row in rows if not row["valid"]),
            }
            manifest_path = out_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            _print({**manifest, "manifest_path": str(manifest_path)})
            return 0 if manifest["invalid_rows"] == 0 else 2

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
            page = render_owner_review_page(pack, assets_dir=args.assets_dir) if args.html_out else None
            output_paths = [target] + ([Path(args.html_out)] if args.html_out else [])
            if len({path.resolve() for path in output_paths}) != len(output_paths):
                raise ValueError("JSON and HTML outputs must use different paths")
            if Path(args.path).resolve() in {path.resolve() for path in output_paths}:
                raise ValueError("review output cannot overwrite its source intake")
            target.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            if page is not None:
                html_target = Path(args.html_out)
                html_target.parent.mkdir(parents=True, exist_ok=True)
                html_target.write_text(page, encoding="utf-8")
            _print({
                "html_written": args.html_out,
                "written": str(target),
                "schema": pack["schema"],
                "problem_id": packet.id,
                "potential_owner": intake.owner_org,
                "candidate_work_paths": len(packet.subproblems),
            })
            return 0
    except (ValueError, TypeError, KeyError, AttributeError, OSError, json.JSONDecodeError) as exc:
        _print({"error": str(exc)})
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
