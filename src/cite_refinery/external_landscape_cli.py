"""Explicit opt-in discovery leads. This command never changes Cite-Refinery records."""
from __future__ import annotations

import argparse
import json

from .external_knowledge import discover as discover_topics
from .external_solution_sources import lookup_repository, scan, stage_landscape_packet
from .external_reuse_bridge import consolidate_discovery, ftm_preview


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cite-refinery-landscape")
    sub = parser.add_subparsers(dest="command", required=True)
    topic = sub.add_parser("scan", help="Read-only source leads from external registries")
    topic.add_argument("query")
    topic.add_argument("--sources", default="wikidata,openaire",
                       help="Comma-separated: wikidata,openalex,openaire,dpg")
    topic.add_argument("--limit", type=int, default=5)
    topic.add_argument("--module-id", help="Optional isolated candidate packet, not automatic graph import")
    topic.add_argument("--module-title", help="Required together with --module-id")
    repo = sub.add_parser("repo", help="Inspect an exact GitHub repository with ecosyste.ms")
    repo.add_argument("github_repository", help="owner/repo or canonical https://github.com/owner/repo")
    reuse = sub.add_parser("reuse", help="Read-only Science/ORKG leads consolidated as neutral review-only records")
    reuse.add_argument("query", help="Discovery query; Science matches literal software names")
    reuse.add_argument("--sources", default="science,orkg", help="Comma-separated: science,orkg")
    reuse.add_argument("--limit", type=int, default=6)
    reuse.add_argument("--module-id", help="Optional neutral graph packet, never auto-import")
    reuse.add_argument("--module-title", help="Used with --module-id")

    ftm = sub.add_parser("ftm-preview", help="Local FollowTheMoney-compatible JSON counts, never entity names")
    ftm.add_argument("path", help="Local JSON file with bounded entity array")
    ftm.add_argument("--dataset-id", required=True)

    opts = parser.parse_args(argv)
    if opts.command == "repo":
        result = lookup_repository(opts.github_repository)
    elif opts.command == "ftm-preview":
        result = ftm_preview(opts.path, dataset_id=opts.dataset_id)
    elif opts.command == "reuse":
        selected = tuple(x.strip() for x in opts.sources.split(","))
        try:
            result = consolidate_discovery(
                opts.query, sources=selected, limit=opts.limit,
                module_id=opts.module_id, module_title=opts.module_title)
        except ValueError as exc:
            parser.error(str(exc))
    else:
        requested = [x.strip() for x in opts.sources.split(",")]
        if not requested or len(requested) != len(set(requested)) or any(
                x not in {"wikidata", "openalex", "openaire", "dpg"} for x in requested):
            parser.error("invalid provider selection")
        if opts.limit > 10 and any(x in {"wikidata", "openalex"} for x in requested):
            parser.error("Wikidata/OpenAlex topic sources accept --limit <= 10")
        records = []
        errors = {}
        topics = tuple(x for x in requested if x in {"wikidata", "openalex"})
        registries = tuple(x for x in requested if x in {"openaire", "dpg"})
        if topics:
            packet = discover_topics(opts.query, sources=topics, limit=opts.limit)
            records.extend(packet["records"])
            errors.update(packet["provider_errors"])
        if registries:
            packet = scan(opts.query, sources=registries, limit=opts.limit)
            records.extend(packet["records"])
            errors.update(packet["provider_errors"])
        result = {
            "query": opts.query, "sources": requested, "status": "partial" if errors else "complete_fetch",
            "records": records, "provider_errors": errors, "promotion_authorized": False,
            "boundary": "Discovery only. No automatic evidence, solution or relationship promotion.",
        }
    if opts.command == "scan" and (opts.module_id or opts.module_title):
        if not (opts.module_id and opts.module_title):
            parser.error("--module-id and --module-title are required together")
        result["candidate_packet"] = stage_landscape_packet(opts.module_id, opts.module_title, result["records"])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result.get("provider_errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
