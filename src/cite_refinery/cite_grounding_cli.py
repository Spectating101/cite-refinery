"""Review and queue a Cite-Agent claim-grounding JSON receipt in a private project.

The operator runs cite-agent-research ground separately, reviews the receipt,
and supplies it as a file. No model is required to use this import interface.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

from .cite_grounding_bridge import convert_grounding
from .hosted_store import WorkspaceDB, PermissionDenied, StateConflict, NotFound


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cite-refinery-ground")
    parser.add_argument("--db", required=True, help="private local SQLite DB")
    parser.add_argument("--project", required=True)
    parser.add_argument("--candidate", required=True, help="Nocturnal case ID")
    parser.add_argument("--ground-json", required=True, help="reviewed Cite-Agent ground command JSON")
    parser.add_argument("--token-env", default="CITE_REFINERY_TOKEN")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("preview")
    enqueue = sub.add_parser("enqueue")
    enqueue.add_argument("--expected-revision", type=int, required=True)
    enqueue.add_argument("--expected-packet-digest", required=True)
    args = parser.parse_args(argv)
    try:
        raw = os.environ.get(args.token_env)
        if not raw:
            raise PermissionDenied("missing private bearer credential")
        path = Path(args.ground_json)
        if path.stat().st_size > 1_048_576:
            raise ValueError("grounding JSON exceeds 1 MiB")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        db = WorkspaceDB(args.db)
        user = db.authenticate(raw)
        state = db.project_state(user, args.project)
        packet = convert_grounding(receipt, state, args.project, args.candidate)
        if args.action == "preview":
            data = {
                "action": "preview_only",
                "grounding_scope": packet["conversion_metadata"],
                "review": db.preview(user, args.project, packet),
            }
        else:
            if args.expected_revision < 0:
                raise ValueError("negative revision not allowed")
            job = db.enqueue(
                user, args.project, packet,
                args.expected_revision, args.expected_packet_digest,
            )
            data = {"action": "enqueued", "job_id": job, "status": "queued"}
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError,
            PermissionDenied, StateConflict, NotFound) as exc:
        print("error: " + str(exc)[:200], file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
