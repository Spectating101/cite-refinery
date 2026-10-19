"""One-shot external topic lookup; explicitly read-only and non-promoting."""
from __future__ import annotations
import argparse
import json
from .external_knowledge import discover

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cite-refinery-topics")
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--with-openalex", action="store_true", help="Optional provider; may rate limit")
    args = parser.parse_args(argv)
    sources = ("wikidata", "openalex") if args.with_openalex else ("wikidata",)
    result = discover(args.query, sources=sources, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["provider_errors"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
