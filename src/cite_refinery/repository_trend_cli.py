"""Trusted local Git portfolio -> transactional Program semantic import.

A human-authored manifest selects source repositories and topics. No network
fetches, live GitHub credential access, automatic trend interpretations, or
external commands beyond bounded read-only Git inspection.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .hosted_store import NotFound, PermissionDenied, StateConflict, WorkspaceDB
from .repository_trend_bridge import manifest_to_packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cite-refinery-repos")
    parser.add_argument("--db", required=True, help="local private SQLite database")
    parser.add_argument("--project", required=True, help="authorized portfolio project")
    parser.add_argument("--repo-root", required=True, help="trusted local portfolio checkout directory")
    parser.add_argument("--manifest", required=True, help="operator-curated pinned repository manifest JSON")
    parser.add_argument("--token-env", default="CITE_REFINERY_TOKEN")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("preview")
    apply = sub.add_parser("enqueue")
    apply.add_argument("--expected-revision", type=int, required=True)
    apply.add_argument("--expected-packet-digest", required=True)
    args = parser.parse_args(argv)
    try:
        secret = os.environ.get(args.token_env)
        if not secret:
            raise PermissionDenied("missing authorized private operator credential")
        path = Path(args.manifest)
        if path.stat().st_size > 131072:
            raise ValueError("portfolio manifest exceeds 128 KiB")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        db = WorkspaceDB(args.db)
        user = db.authenticate(secret)
        # RBAC check before accessing local Git objects.
        db.preview(user, args.project, {
            "schema": "cite_refinery.semantic_graph.v1", "source_system": "repository_portfolio",
            "clusters": [], "nodes": [], "edges": [],
        })
        packet = manifest_to_packet(
            manifest, args.repo_root,
            project_state=db.project_state(user, args.project), project_id=args.project,
        )
        if args.action == "preview":
            result = {
                "action": "preview_only",
                "portfolio_metadata": packet["conversion_metadata"],
                "review": db.preview(user, args.project, packet),
            }
        else:
            if args.expected_revision < 0:
                raise ValueError("revision must not be negative")
            job = db.enqueue(
                user, args.project, packet,
                args.expected_revision, args.expected_packet_digest,
            )
            result = {"action": "enqueued", "status": "queued", "job_id": job}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError,
            PermissionDenied, StateConflict, NotFound) as exc:
        # Print no Git blobs, tenant state, tokens or packet contents.
        print("error: " + str(exc)[:200], file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
