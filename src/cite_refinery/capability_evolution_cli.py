"""Operator-authenticated, revision-pinned project evidence evolution explorer."""
from __future__ import annotations

import argparse
import json
import os
import sys

from .hosted_store import NotFound, PermissionDenied, StateConflict, WorkspaceDB


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cite-refinery-evolution")
    p.add_argument("--db", required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--token-env", default="CITE_REFINERY_TOKEN")
    sub = p.add_subparsers(dest="action", required=True)
    add = sub.add_parser("capture")
    add.add_argument("--label", required=True)
    add.add_argument("--expected-revision", type=int, required=True)
    sub.add_parser("list")
    compare = sub.add_parser("compare")
    compare.add_argument("--from-snapshot", required=True)
    compare.add_argument("--to-snapshot", required=True)
    args = p.parse_args(argv)
    try:
        credential = os.environ.get(args.token_env)
        if not credential:
            raise PermissionDenied("missing private operator credential")
        db = WorkspaceDB(args.db)
        user = db.authenticate(credential)
        if args.action == "capture":
            data = db.capture_snapshot(
                user, args.project, args.label, args.expected_revision)
        elif args.action == "list":
            data = db.list_snapshots(user, args.project)
        else:
            data = db.compare_snapshots(
                user, args.project, args.from_snapshot, args.to_snapshot)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, TypeError,
            PermissionDenied, StateConflict, NotFound) as exc:
        print("error: " + str(exc)[:200], file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
