"""Manual trusted Refinery execution source → private project preview/ingest."""
from __future__ import annotations
import argparse
import json
import os
import sys

from .hosted_store import WorkspaceDB, PermissionDenied, NotFound, StateConflict
from .refinery_execution_bridge import case_to_packet, load_case


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cite-refinery-refinery")
    p.add_argument("--db", required=True, help="Local private SQLite database")
    p.add_argument("--project", required=True)
    p.add_argument("--refinery-repo", required=True, help="Authorized local Refinery Git checkout")
    p.add_argument("--ref", required=True, help="Exact 40-character immutable source commit")
    p.add_argument("--token-env", default="CITE_REFINERY_TOKEN")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("preview")
    apply = sub.add_parser("enqueue")
    apply.add_argument("--expected-revision", type=int, required=True)
    apply.add_argument("--expected-packet-digest", required=True)
    args = p.parse_args(argv)
    try:
        secret = os.environ.get(args.token_env)
        if not secret:
            raise PermissionDenied("missing private operator credential")
        db = WorkspaceDB(args.db)
        user = db.authenticate(secret)
        # Permission check before reading evidence from an authorized local repo.
        db.preview(user, args.project, {
            "schema": "cite_refinery.semantic_graph.v1",
            "source_system": "refinery", "clusters": [], "nodes": [], "edges": [],
        })
        bundle, identity = load_case(args.refinery_repo, args.ref)
        packet = case_to_packet(
            bundle, identity,
            project_state=db.project_state(user, args.project), project_id=args.project,
        )
        if args.action == "preview":
            data = {
                "action": "preview_only",
                "source_evidence_scope": packet["conversion_metadata"],
                "review": db.preview(user, args.project, packet),
            }
        else:
            if args.expected_revision < 0:
                raise ValueError("expected revision must be nonnegative")
            job_id = db.enqueue(
                user, args.project, packet,
                args.expected_revision, args.expected_packet_digest,
            )
            data = {"action": "enqueued", "job_id": job_id, "status": "queued"}
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    except (OSError, KeyError, TypeError, ValueError, RuntimeError,
            PermissionDenied, NotFound, StateConflict) as exc:
        print(f"error: {str(exc)[:200]}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
