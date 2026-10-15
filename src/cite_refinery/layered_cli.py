from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from . import cli as core_cli
from .app import CiteRefinery
from .scorecard import build_end_to_end_scorecard


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


def main(argv: list[str] | None = None) -> int:
    raw = list(argv) if argv is not None else list(sys.argv[1:])
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

    # Reuse the stable core CLI parser/dispatch for all established commands.
    core_cli.CiteRefinery = CiteRefinery
    return core_cli.main(raw)


if __name__ == "__main__":
    raise SystemExit(main())
