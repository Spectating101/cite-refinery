"""Authenticated local Cite-Agent literature discovery -> private graph queue."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from .cite_literature_bridge import convert_search, resolve_target
from .hosted_store import WorkspaceDB, NotFound, PermissionDenied, StateConflict


def get_search(args) -> dict:
    if args.search_json:
        source = Path(args.search_json)
        if source.stat().st_size > 1024 * 1024:
            raise ValueError("search JSON exceeds 1 MiB")
        return json.loads(source.read_text(encoding="utf-8"))
    query = args.query.strip()
    if not query:
        raise ValueError("search query required when --search-json absent")
    proc = subprocess.run(
        ["cite-agent-research", "search", query, "--limit", str(args.limit)],
        capture_output=True, timeout=90, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("Cite-Agent search unavailable or returned an error")
    if len(proc.stdout) > 1024 * 1024:
        raise ValueError("Cite-Agent search exceeds 1 MiB")
    return json.loads(proc.stdout)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cite-refinery-cite")
    p.add_argument("--db", required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--token-env", default="CITE_REFINERY_TOKEN")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--query")
    group.add_argument("--search-json", help="Operator-reviewed Cite-Agent JSON snapshot")
    p.add_argument("--limit", type=int, default=8)
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("preview")
    commit = sub.add_parser("enqueue")
    commit.add_argument("--expected-revision", type=int, required=True)
    commit.add_argument("--expected-packet-digest", required=True)
    args = p.parse_args(argv)
    try:
        token = os.environ.get(args.token_env)
        if not token:
            raise ValueError("private bearer token environment variable missing")
        if not 1 <= args.limit <= 20:
            raise ValueError("search limit must be 1..20")
        db = WorkspaceDB(args.db)
        user = db.authenticate(token)
        state = db.project_state(user, args.project)
        target = resolve_target(state, args.project, args.candidate)
        result = get_search(args)
        packet = convert_search(result, target)
        if args.action == "preview":
            payload = {"action": "preview_only",
                       "metadata": packet["conversion_metadata"],
                       "review": db.preview(user, args.project, packet)}
        else:
            job_id = db.enqueue(
                user, args.project, packet,
                args.expected_revision, args.expected_packet_digest)
            payload = {"action": "enqueued", "status": "queued", "job_id": job_id}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError,
            PermissionDenied, StateConflict, NotFound) as exc:
        print("error: " + str(exc)[:240], file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
