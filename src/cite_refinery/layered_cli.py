from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import cli as core_cli
from .app import CiteRefinery
from .preflight import build_preflight
from .scorecard import build_end_to_end_scorecard


def _preflight_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery preflight")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument(
        "--require-reviewed-market",
        action="store_true",
        help="Exit nonzero unless the optional broad reviewed-market supply layer is also ready.",
    )
    return parser


def _research_discover_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery research-discover")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    parser.add_argument("brief_id")
    parser.add_argument("--target-count", type=int, default=30)
    parser.add_argument("--snowball-depth", type=int, default=1)
    parser.add_argument("--max-questions", type=int, default=4)
    return parser


def _scorecard_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery scorecard")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    return parser


def _feedback_request_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery feedback-request")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    parser.add_argument("experiment_id")
    parser.add_argument("--observation-id", action="append", default=None)
    parser.add_argument("--signal", action="append", default=None)
    parser.add_argument("--window-start")
    parser.add_argument("--window-end")
    return parser


def _feedback_ingest_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery feedback-ingest")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    parser.add_argument("--input", required=True, help="Nocturnal feedback result JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    raw = list(argv) if argv is not None else list(sys.argv[1:])

    if "preflight" in raw:
        index = raw.index("preflight")
        command_args = [*raw[:index], *raw[index + 1 :]]
        args = _preflight_parser().parse_args(command_args)
        report = build_preflight(args.workspace)
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
        ready = report["full_broad_supply_ready"] if args.require_reviewed_market else report["core_ready"]
        return 0 if ready else 1

    if "research-discover" in raw:
        index = raw.index("research-discover")
        discover_args = [*raw[:index], *raw[index + 1 :]]
        args = _research_discover_parser().parse_args(discover_args)
        app = CiteRefinery(args.workspace)
        try:
            audit = app.discover_research_brief(
                args.project_id,
                args.brief_id,
                target_count=args.target_count,
                snowball_depth=args.snowball_depth,
                max_questions=args.max_questions,
            )
            print(json.dumps(asdict(audit), indent=2, ensure_ascii=False, default=str))
            return 0
        except (KeyError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    if "feedback-request" in raw:
        index = raw.index("feedback-request")
        command_args = [*raw[:index], *raw[index + 1 :]]
        args = _feedback_request_parser().parse_args(command_args)
        app = CiteRefinery(args.workspace)
        try:
            packet = app.create_nocturnal_feedback_request(
                args.project_id,
                args.experiment_id,
                observation_ids=args.observation_id,
                requested_signals=args.signal,
                window_start=args.window_start,
                window_end=args.window_end,
            )
            print(json.dumps(packet, indent=2, ensure_ascii=False, default=str))
            return 0
        except (KeyError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    if "feedback-ingest" in raw:
        index = raw.index("feedback-ingest")
        command_args = [*raw[:index], *raw[index + 1 :]]
        args = _feedback_ingest_parser().parse_args(command_args)
        app = CiteRefinery(args.workspace)
        try:
            packet = json.loads(Path(args.input).read_text(encoding="utf-8"))
            if not isinstance(packet, dict):
                raise ValueError("feedback input must be a JSON object")
            result = app.ingest_nocturnal_feedback_result(args.project_id, packet)
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return 0
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    if "scorecard" in raw:
        index = raw.index("scorecard")
        score_args = [*raw[:index], *raw[index + 1 :]]
        args = _scorecard_parser().parse_args(score_args)
        app = CiteRefinery(args.workspace)
        try:
            scorecard = build_end_to_end_scorecard(app.store.load(), args.project_id)
            print(json.dumps(scorecard, indent=2, ensure_ascii=False, default=str))
            return 0
        except KeyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    core_cli.CiteRefinery = CiteRefinery
    return core_cli.main(raw)


if __name__ == "__main__":
    raise SystemExit(main())
