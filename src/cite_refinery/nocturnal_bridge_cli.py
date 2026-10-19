"""Manual trusted bridge: pinned Nocturnal case -> authenticated private ingest queue.

Never copies the Nocturnal case into GitHub or the public Vercel preview.
Requires a locally accessible Nocturnal git repository and a pre-existing
authorized Cite-Refinery private project.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .hosted_store import PermissionDenied, StateConflict, NotFound, WorkspaceDB
from .nocturnal_bridge import case_to_semantic_packet, load_frozen_china_case


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cite-refinery-nocturnal")
    parser.add_argument("--db", required=True, help="Private local workspace DB path")
    parser.add_argument("--nocturnal-repo", required=True, help="Local Nocturnal Git repository")
    parser.add_argument("--candidate-id", required=True, help="Frozen China development candidate ID")
    parser.add_argument("--project", required=True, help="Existing private Cite-Refinery project")
    parser.add_argument("--token-env", default="CITE_REFINERY_TOKEN",
                        help="Environment variable holding an authorized bearer token")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("preview")
    queue = sub.add_parser("enqueue")
    queue.add_argument("--expected-revision", type=int, required=True)
    queue.add_argument("--expected-packet-digest", required=True)
    args = parser.parse_args(argv)
    try:
        token = os.environ.get(args.token_env)
        if not token:
            raise ValueError(f"missing bearer credential in env var {args.token_env}")
        db = WorkspaceDB(args.db)
        user = db.authenticate(token)
        case, freeze, provenance = load_frozen_china_case(args.nocturnal_repo, args.candidate_id)
        packet = case_to_semantic_packet(case, freeze, provenance)
        if args.action == "preview":
            result = {
                "action": "preview_only",
                "source": packet["conversion_metadata"],
                "review": db.preview(user, args.project, packet),
            }
        else:
            if args.expected_revision < 0:
                raise ValueError("expected revision must be non-negative")
            job = db.enqueue(
                user, args.project, packet, args.expected_revision, args.expected_packet_digest)
            result = {"action": "enqueued", "job_id": job, "status": "queued",
                      "frozen_case": args.candidate_id}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, PermissionError, PermissionDenied, StateConflict, NotFound) as exc:
        # Do not echo tokens or private packet payloads.
        print(f"error: {str(exc)[:300]}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
