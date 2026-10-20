"""Bounded, opt-in semantic matching of documented needs and OSS assets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .opportunity_matcher import matching_prompt, inspect_matches


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cite-refinery-opportunity-match")
    p.add_argument("source_manifest", type=Path, help="Development-only needs and attributed repository briefs")
    p.add_argument("--provider", choices=["antigravity", "copilot", "codex", "gemini", "claude", "ollama"])
    p.add_argument("--model")
    p.add_argument("--model-output", type=Path, help="Replay saved model output")
    p.add_argument("--timeout", type=int, default=150)
    p.add_argument("--output", type=Path)
    opts = p.parse_args(argv)
    material = json.loads(opts.source_manifest.read_text(encoding="utf-8"))
    prompt = matching_prompt(material)
    if opts.model_output:
        raw = json.loads(opts.model_output.read_text(encoding="utf-8"))
    else:
        if not opts.provider:
            p.error("--provider or --model-output required")
        from .external_llm_runtime import invoke_semantic_llm
        raw = invoke_semantic_llm(prompt, provider=opts.provider,
                                  model=opts.model, timeout_seconds=opts.timeout)["raw"]
    result = inspect_matches(material, raw)
    body = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if opts.output:
        opts.output.parent.mkdir(parents=True, exist_ok=True)
        opts.output.write_text(body, encoding="utf-8")
        print(opts.output)
    else:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
