"""Explicit operator setup and worker commands for first private backend milestone."""
from __future__ import annotations

import argparse
import json
import sys
import time

from .hosted_store import WorkspaceDB


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cite-refinery-private")
    p.add_argument("--db", required=True, help="SQLite workspace database file")
    sub = p.add_subparsers(dest="command", required=True)
    create = sub.add_parser("bootstrap")
    create.add_argument("--tenant", required=True)
    create.add_argument("--owner", required=True)
    add = sub.add_parser("add-user")
    add.add_argument("username")
    grant = sub.add_parser("grant")
    grant.add_argument("owner_id")
    grant.add_argument("tenant_id")
    grant.add_argument("target_user_id")
    grant.add_argument("role", choices=["owner", "editor", "viewer"])
    token = sub.add_parser("issue-token")
    token.add_argument("user_id")
    token.add_argument("--ttl-hours", type=int, default=24)
    sub.add_parser("worker-once")
    work = sub.add_parser("worker-loop")
    work.add_argument("--interval", type=float, default=2.0)
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1", help="loopback only")
    serve.add_argument("--port", type=int, default=8780)
    args = p.parse_args(argv)
    db = WorkspaceDB(args.db)
    try:
        if args.command == "bootstrap":
            result = db.create_tenant(args.tenant, args.owner)
        elif args.command == "add-user":
            result = {"user_id": db.add_user(args.username)}
        elif args.command == "grant":
            db.grant_membership(args.owner_id, args.tenant_id, args.target_user_id, args.role)
            result = {"granted": True}
        elif args.command == "issue-token":
            # Treat stdout as a secret. Never log the token elsewhere.
            result = {"bearer_token": db.issue_token(args.user_id, args.ttl_hours)}
        elif args.command == "worker-once":
            result = db.run_one_job() or {"status": "empty"}
        elif args.command == "worker-loop":
            if not 0.25 <= args.interval <= 300:
                raise ValueError("interval must be 0.25..300 seconds")
            print("Worker started (Ctrl-C to stop)", file=sys.stderr)
            while True:
                if db.run_one_job() is None:
                    time.sleep(args.interval)
        else:
            if args.host not in {"127.0.0.1", "localhost"}:
                raise ValueError("private API requires loopback; external TLS/reverse proxy needs review")
            try:
                import uvicorn
            except ImportError as exc:
                raise RuntimeError("Install cite-refinery[server]") from exc
            from .hosted_api import create_private_app
            uvicorn.run(create_private_app(args.db), host=args.host, port=args.port,
                        access_log=False, proxy_headers=False)
            return 0
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, RuntimeError, PermissionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
