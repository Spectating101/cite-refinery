"""Read-only cross-layer problem interpretation and AI candidate synthesis."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cross_layer_stack import stack_packet
from .cross_layer_report import render
from .cross_layer_proposals import selected_readings, attach_original_excerpts, alignment_prompt, inspect_alignments


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cite-refinery-stack")
    sub = parser.add_subparsers(dest="command", required=True)
    pkt = sub.add_parser("packet", help="Stack explicitly reviewed semantic packet links")
    pkt.add_argument("packet", type=Path)
    atlas = sub.add_parser("atlas", help="Propose semantic alignment from unverified development readings")
    atlas.add_argument("provisional_map", type=Path)
    atlas.add_argument("global_atlas", type=Path)
    atlas.add_argument("--domain", required=True, help="Exact domain label")
    atlas.add_argument("--source-corpus", type=Path, help="Optional LOCAL development-only originals; verifies source fingerprints")
    atlas.add_argument("--provider", choices=["antigravity", "copilot", "codex", "gemini", "claude", "ollama"])
    atlas.add_argument("--model")
    atlas.add_argument("--model-output", type=Path, help="Replay a previously saved JSON response, no model call")
    atlas.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", type=Path, help="Optional report output path")
    parser.add_argument("--format", choices=["json","markdown"], default="json")
    opts = parser.parse_args(argv)
    if opts.command == "packet":
        result = stack_packet(json.loads(opts.packet.read_text(encoding="utf-8")))
    else:
        selected = selected_readings(
            json.loads(opts.provisional_map.read_text(encoding="utf-8")),
            json.loads(opts.global_atlas.read_text(encoding="utf-8")),
            domain=opts.domain,
        )
        if opts.source_corpus:
            selected = attach_original_excerpts(
                selected, json.loads(opts.source_corpus.read_text(encoding="utf-8")))
        if opts.model_output:
            raw = json.loads(opts.model_output.read_text(encoding="utf-8"))
        else:
            if not opts.provider:
                parser.error("atlas needs --provider or --model-output")
            from .external_llm_runtime import invoke_semantic_llm
            reply = invoke_semantic_llm(alignment_prompt(selected), provider=opts.provider,
                                        model=opts.model, timeout_seconds=opts.timeout)
            raw = reply["raw"]
        result = inspect_alignments(selected, raw)
    body = (render(result) if opts.format == "markdown"
            else json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    if opts.output:
        opts.output.parent.mkdir(parents=True, exist_ok=True)
        opts.output.write_text(body, encoding="utf-8")
        print(str(opts.output))
    else:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
