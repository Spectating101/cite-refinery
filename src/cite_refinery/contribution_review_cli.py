from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contribution_handoff import ContributorWorkspace
from .contribution_revision import ContributionRevisionWorkspace, validate_revision_submission
from .contribution_review import (
    ContributionReview,
    ContributionVerdict,
    project_review_into_commons,
    project_revision_review_into_commons,
    validate_submission_snapshot,
)
from .problem_commons import ProblemCommons


def _print(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _add_review_fields(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--reviewer-ref", required=True)
    parser.add_argument("--verdict", choices=[item.value for item in ContributionVerdict], required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--strength", action="append", default=[])
    parser.add_argument("--limitation", action="append", default=[])
    parser.add_argument("--revision-requirement", action="append", default=[])
    parser.add_argument("--evidence-ref", action="append", default=[])
    parser.add_argument("--out", required=True)


def _create_review(args, submission: dict) -> ContributionReview:
    return ContributionReview.from_submission(
        submission,
        reviewer_ref=args.reviewer_ref,
        verdict=args.verdict,
        summary=args.summary,
        strengths=args.strength,
        limitations=args.limitation,
        revision_requirements=args.revision_requirement,
        evidence_refs=args.evidence_ref,
    )


def _write_review(review: ContributionReview, out: str) -> int:
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(review.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = review.validation(reviewable_submission := _load_json_from_review_binding(review, target)) if False else None
    del report, reviewable_submission
    return 0


def _load_json_from_review_binding(review: ContributionReview, target: Path) -> dict:
    # Unreachable helper retained only to keep review-file writing free of hidden state.
    raise RuntimeError(f"no implicit submission lookup for {review.id} at {target}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="problem-contribution-review",
        description="Review submitted Problem Commons contributions and project reviewed attempts into canonical Commons state.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create an independent review bound to an exact initial submission")
    create.add_argument("submission")
    create.add_argument("--workspace", required=True)
    _add_review_fields(create)

    validate = sub.add_parser("validate", help="Validate an initial review against the retained workspace and submission")
    validate.add_argument("review")
    validate.add_argument("--submission", required=True)
    validate.add_argument("--workspace", required=True)

    project = sub.add_parser("project", help="Project one reviewed initial submission into canonical Problem Commons Attempt state")
    project.add_argument("review")
    project.add_argument("--submission", required=True)
    project.add_argument("--workspace", required=True)
    project.add_argument("--state", required=True)
    project.add_argument("--receipt-out")

    create_revision = sub.add_parser("create-revision", help="Create an independent review bound to an exact revision submission")
    create_revision.add_argument("submission")
    create_revision.add_argument("--workspace", required=True)
    create_revision.add_argument("--parent-submission", required=True)
    create_revision.add_argument("--trigger-review", required=True)
    _add_review_fields(create_revision)

    validate_revision = sub.add_parser("validate-revision", help="Validate a revision review and its exact lineage")
    validate_revision.add_argument("review")
    validate_revision.add_argument("--submission", required=True)
    validate_revision.add_argument("--workspace", required=True)
    validate_revision.add_argument("--parent-submission", required=True)
    validate_revision.add_argument("--trigger-review", required=True)

    project_revision = sub.add_parser("project-revision", help="Append one reviewed revision round to the existing canonical Attempt")
    project_revision.add_argument("review")
    project_revision.add_argument("--submission", required=True)
    project_revision.add_argument("--workspace", required=True)
    project_revision.add_argument("--parent-submission", required=True)
    project_revision.add_argument("--trigger-review", required=True)
    project_revision.add_argument("--state", required=True)
    project_revision.add_argument("--receipt-out")

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
            review = _create_review(args, submission)
            report = review.validation(submission)
            if not report.valid:
                _print({"valid": False, "errors": report.errors, "warnings": report.warnings})
                return 2
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(review.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            _print({"written": str(target), "review_id": review.id, "verdict": review.verdict.value, "warnings": report.warnings})
            return 0

        if args.command == "create-revision":
            submission = _load_json(args.submission)
            workspace = ContributionRevisionWorkspace.load(args.workspace)
            parent_submission = _load_json(args.parent_submission)
            trigger_review = _load_json(args.trigger_review)
            errors = validate_revision_submission(
                submission,
                workspace=workspace,
                parent_submission=parent_submission,
                trigger_review=trigger_review,
            )
            if errors:
                _print({"valid": False, "errors": errors})
                return 2
            review = _create_review(args, submission)
            report = review.validation(submission)
            if not report.valid:
                _print({"valid": False, "errors": report.errors, "warnings": report.warnings})
                return 2
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(review.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            _print({
                "written": str(target),
                "review_id": review.id,
                "workspace_id": workspace.id,
                "revision_number": workspace.revision_number,
                "verdict": review.verdict.value,
                "warnings": report.warnings,
            })
            return 0

        if args.command in {"validate", "project"}:
            submission = _load_json(args.submission)
            workspace = ContributorWorkspace.load(args.workspace)
            review = ContributionReview.from_dict(_load_json(args.review))

            if args.command == "validate":
                errors = validate_submission_snapshot(submission, workspace=workspace)
                report = review.validation(submission)
                errors.extend(report.errors)
                _print({"valid": not errors, "errors": errors, "warnings": report.warnings})
                return 0 if not errors else 2

            receipt_target = Path(args.receipt_out) if args.receipt_out else None
            if receipt_target is not None:
                receipt_target.parent.mkdir(parents=True, exist_ok=True)
                if receipt_target.exists():
                    raise ValueError("receipt output already exists; refusing to mutate canonical state or overwrite projection evidence")
            commons = ProblemCommons.load(args.state)
            receipt = project_review_into_commons(commons, workspace, submission, review)
            commons.save(args.state)
            if receipt_target is not None:
                receipt_target.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            _print(receipt)
            return 0

        if args.command in {"validate-revision", "project-revision"}:
            submission = _load_json(args.submission)
            workspace = ContributionRevisionWorkspace.load(args.workspace)
            parent_submission = _load_json(args.parent_submission)
            trigger_review = _load_json(args.trigger_review)
            review = ContributionReview.from_dict(_load_json(args.review))

            if args.command == "validate-revision":
                errors = validate_revision_submission(
                    submission,
                    workspace=workspace,
                    parent_submission=parent_submission,
                    trigger_review=trigger_review,
                )
                report = review.validation(submission)
                errors.extend(report.errors)
                _print({"valid": not errors, "errors": errors, "warnings": report.warnings})
                return 0 if not errors else 2

            receipt_target = Path(args.receipt_out) if args.receipt_out else None
            if receipt_target is not None:
                receipt_target.parent.mkdir(parents=True, exist_ok=True)
                if receipt_target.exists():
                    raise ValueError("receipt output already exists; refusing to mutate canonical state or overwrite projection evidence")
            commons = ProblemCommons.load(args.state)
            receipt = project_revision_review_into_commons(
                commons,
                workspace,
                submission,
                review,
                parent_submission=parent_submission,
                trigger_review=trigger_review,
            )
            commons.save(args.state)
            if receipt_target is not None:
                receipt_target.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            _print(receipt)
            return 0

    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        _print({"error": str(exc)})
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
