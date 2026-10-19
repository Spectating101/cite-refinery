"""Authenticated local operator review of pinned Refinery assessment history.

Import requires a previously imported narrow execution source episode. The
historical campaign and its narrower successor retain separate authority.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .hosted_store import WorkspaceDB, PermissionDenied, NotFound, StateConflict
from .refinery_execution_bridge import load_case
from .refinery_history_bridge import load_broad, history_comparison


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cite-refinery-history")
    parser.add_argument("--db", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--refinery-repo", required=True)
    parser.add_argument("--ref", required=True, help="exact pinned Refinery Git commit")
    parser.add_argument("--token-env", default="CITE_REFINERY_TOKEN")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("preview")
    enqueue = sub.add_parser("enqueue")
    enqueue.add_argument("--expected-revision", type=int, required=True)
    enqueue.add_argument("--expected-packet-digest", required=True)
    args = parser.parse_args(argv)
    try:
        token = os.environ.get(args.token_env)
        if not token:
            raise PermissionDenied("missing private operator credential")
        db = WorkspaceDB(args.db)
        user = db.authenticate(token)
        state = db.project_state(user, args.project)
        if not db.preview(user, args.project, {
            "schema": "cite_refinery.semantic_graph.v1",
            "source_system": "refinery_history",
            "clusters": [], "nodes": [], "edges": [],
        }):
            raise ValueError("private project permission check failed")
        earlier, meta = load_broad(args.refinery_repo, args.ref)
        later, later_meta = load_case(args.refinery_repo, args.ref)
        packet = history_comparison(
            earlier, meta, later, later_meta, state, args.project,
        )
        if args.action == "preview":
            response = {
                "action": "preview_only",
                "epistemic_scope": packet["conversion_metadata"],
                "review": db.preview(user, args.project, packet),
            }
        else:
            if args.expected_revision < 0:
                raise ValueError("expected revision must be nonnegative")
            job_id = db.enqueue(
                user, args.project, packet,
                args.expected_revision, args.expected_packet_digest,
            )
            response = {"action": "enqueued", "job_id": job_id, "status": "queued"}
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError,
            PermissionDenied, NotFound, StateConflict) as exc:
        print("error: " + str(exc)[:200], file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
