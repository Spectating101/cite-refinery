from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contribution_handoff import ContributorWorkspace
from .contribution_review import (
    ContributionReview,
    ContributionVerdict,
    project_review_into_commons,
    validate_submission_snapshot,
)
from .problem_commons import ProblemCommons


def _print(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="problem-contribution-review",
        description="Review submitted Problem Commons contributions and project reviewed attempts into canonical Commons state.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create an independent review bound to an exact submission")
    create.add_argument("submission")
    create.add_argument("--workspace", required=True)
    create.add_argument("--reviewer-ref", required=True)
    create.add_argument("--verdict", choices=[item.value for item in ContributionVerdict], required=True)
    create.add_argument("--summary", required=True)
    create.add_argument("--strength", action="append", default=[])
    create.add_argument("--limitation", action="append", default=[])
    create.add_argument("--revision-requirement", action="append", default=[])
    create.add_argument("--evidence-ref", action="append", default=[])
    create.add_argument("--out", required=True)

    validate = sub.add_parser("validate", help="Validate a review against the retained workspace and submission")
    validate.add_argument("review")
    validate.add_argument("--submission", required=True)
    validate.add_argument("--workspace", required=True)

    project = sub.add_parser("project", help="Project one reviewed submission into canonical Problem Commons Attempt state")
    project.add_argument("review")
    project.add_argument("--submission", required=True)
    project.add_argument("--workspace", required=True)
    project.add_argument("--state", required=True)
    project.add_argument("--receipt-out")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "create":
            submission = _load_json(args.submission)
            workspace = ContributorWorkspace.load(args.workspace)
            errors = validate_submission_snapshot(submission, workspace=workspace)
            if errors:
                _print({"valid": False, "errors": errors})
                return 2
            review = ContributionReview.from_submission(
                submission,
                reviewer_ref=args.reviewer_ref,
                verdict=args.verdict,
                summary=args.summary,
                strengths=args.strength,
                limitations=args.limitation,
                revision_requirements=args.revision_requirement,
                evidence_refs=args.evidence_ref,
            )
            report = review.validation(submission)
            if not report.valid:
                _print({"valid": False, "errors": report.errors, "warnings": report.warnings})
                return 2
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(review.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            _print({"written": str(target), "review_id": review.id, "verdict": review.verdict.value, "warnings": report.warnings})
            return 0

        submission = _load_json(args.submission)
        workspace = ContributorWorkspace.load(args.workspace)
        review = ContributionReview.from_dict(_load_json(args.review))

        if args.command == "validate":
            errors = validate_submission_snapshot(submission, workspace=workspace)
            report = review.validation(submission)
            errors.extend(report.errors)
            _print({"valid": not errors, "errors": errors, "warnings": report.warnings})
            return 0 if not errors else 2

        if args.command == "project":
            commons = ProblemCommons.load(args.state)
            receipt = project_review_into_commons(commons, workspace, submission, review)
            commons.dump(args.state)
            if args.receipt_out:
                target = Path(args.receipt_out)
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    raise ValueError("receipt output already exists; refusing to overwrite projection evidence")
                target.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            _print(receipt)
            return 0

    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        _print({"error": str(exc)})
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
