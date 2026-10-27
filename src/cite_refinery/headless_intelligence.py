"""Local-first, headless polling of reviewed cross-domain evidence snapshots.

This is an inbox and change detector, NOT a graph-writer or investigation
authority. Third-party sources are only imported as leads unless a separate
source-reviewed semantic packet already contains explicit relationships.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .cross_layer_stack import stack_packet

CONFIG_SCHEMA = "cite_refinery.headless_feeds.v1"
RECORD_SCHEMA = "cite_refinery.headless_records.v1"
ALLOWED_KINDS = {"semantic_packet", "record_list"}
MAX_FEED_BYTES = 2 * 1024 * 1024
MAX_ITEMS = 2000
DDL = """
CREATE TABLE IF NOT EXISTS records (
    feed TEXT NOT NULL, record_id TEXT NOT NULL, digest TEXT NOT NULL,
    observed_at TEXT NOT NULL, PRIMARY KEY(feed, record_id)
);
CREATE TABLE IF NOT EXISTS events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    feed TEXT NOT NULL, system TEXT NOT NULL,
    record_id TEXT NOT NULL, change TEXT NOT NULL,
    digest TEXT NOT NULL, observed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_feed_seq ON events(feed, sequence);
CREATE TABLE IF NOT EXISTS feed_runs (
    feed TEXT PRIMARY KEY, system TEXT NOT NULL, snapshot_digest TEXT NOT NULL,
    observed_at TEXT NOT NULL, record_count INTEGER NOT NULL,
    interpretation_json TEXT NOT NULL
);
"""


def _digest(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_config(path: Path) -> list[dict[str, Any]]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("schema") != CONFIG_SCHEMA:
        raise ValueError("invalid headless feed configuration schema")
    feeds = config.get("feeds")
    if not isinstance(feeds, list) or not feeds or len(feeds) > 32:
        raise ValueError("configuration requires 1..32 feeds")
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for feed in feeds:
        if not isinstance(feed, dict):
            raise ValueError("feed must be an object")
        fid, system, kind = feed.get("id"), feed.get("system"), feed.get("kind")
        if not isinstance(fid, str) or not fid or len(fid) > 64 or not all(
            char.isalnum() or char in "_-" for char in fid
        ) or fid in seen:
            raise ValueError("feed IDs must be distinct, short, alphanumeric IDs")
        if not isinstance(system, str) or not system.strip() or len(system) > 80:
            raise ValueError("feed system must be a named provenance source")
        if kind not in ALLOWED_KINDS:
            raise ValueError("unsupported feed kind")
        if not isinstance(feed.get("path"), str) or not feed["path"].strip():
            raise ValueError("feed requires an explicit local snapshot path")
        seen.add(fid)
        result.append({
            "id": fid, "system": system, "kind": kind,
            "path": (path.parent / feed["path"]).resolve(),
        })
    return result


def _load_snapshot(feed: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    path: Path = feed["path"]
    if not path.is_file():
        raise ValueError(f"missing snapshot for feed {feed['id']}")
    size = path.stat().st_size
    if size > MAX_FEED_BYTES:
        raise ValueError(f"snapshot exceeds 2 MiB for feed {feed['id']}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("snapshot must be an object")
    items: dict[str, Any] = {}
    interpretation: dict[str, Any] = {
        "authority": "lead_only", "findings": 0, "problems": 0,
        "boundary": "Polling never authorizes graph writes, assertions, or publication.",
    }
    if feed["kind"] == "semantic_packet":
        if document.get("schema") != "cite_refinery.semantic_graph.v1":
            raise ValueError("expected semantic graph packet")
        if not isinstance(document.get("project_id"), str) or not document["project_id"]:
            raise ValueError("semantic packet must be scoped to a project")
        # This rejects malformed topology and preserves existing review gates.
        synthesis = stack_packet(document)
        interpretation.update({
            "authority": synthesis["authority"],
            "problems": len(synthesis["problems"]),
            "findings": sum(len(p["findings"]) for p in synthesis["problems"]),
        })
        nodes, edges = document["nodes"], document["edges"]
        if len(nodes) + len(edges) > MAX_ITEMS:
            raise ValueError("too many records")
        for node in nodes:
            key = "node:" + document["project_id"] + ":" + node["key"]
            if key in items:
                raise ValueError("duplicate node")
            items[key] = node
        for edge in edges:
            key = "edge:" + document["project_id"] + ":" + _digest({
                "source": edge["source"], "relation": edge.get("relation"),
                "target": edge["target"],
            })
            if key in items:
                raise ValueError("duplicate semantic edge")
            items[key] = edge
    else:
        if document.get("schema") != RECORD_SCHEMA:
            raise ValueError("expected headless_records.v1")
        rows = document.get("records")
        if not isinstance(rows, list) or len(rows) > MAX_ITEMS:
            raise ValueError("invalid record_list items")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("record must be an object")
            rid = row.get("id")
            if not isinstance(rid, str) or not rid.strip() or len(rid) > 300:
                raise ValueError("record requires stable ID")
            if rid in items:
                raise ValueError("duplicate record ID")
            items[rid] = row
    return items, interpretation, _digest(document)


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(path, timeout=15)
    db.executescript(DDL)
    if os.name == "posix":
        os.chmod(path, 0o600)
    return db


def poll(config_path: Path, db_path: Path) -> dict[str, Any]:
    """Poll configured local exports, committing each complete feed atomically.

    Missing/broken snapshots fail without generating removals or changing the
    previously accepted checkpoint. Records that disappear are *not* deleted;
    truncation and incomplete vendor exports must not erase evidence.
    """
    feeds = load_config(config_path)
    result: list[dict[str, Any]] = []
    with _connect(db_path) as db:
        for feed in feeds:
            try:
                items, interpretation, snapshot = _load_snapshot(feed)
                old = {
                    row[0]: row[1]
                    for row in db.execute("SELECT record_id,digest FROM records WHERE feed=?", (feed["id"],))
                }
                timestamp = _now()
                created = changed = 0
                with db:
                    for rid, payload in sorted(items.items()):
                        sha = _digest(payload)
                        if old.get(rid) == sha:
                            continue
                        change = "created" if rid not in old else "changed"
                        created += change == "created"
                        changed += change == "changed"
                        db.execute(
                            "INSERT INTO records(feed,record_id,digest,observed_at) VALUES (?,?,?,?) "
                            "ON CONFLICT(feed,record_id) DO UPDATE SET digest=excluded.digest,"
                            " observed_at=excluded.observed_at",
                            (feed["id"], rid, sha, timestamp),
                        )
                        db.execute(
                            "INSERT INTO events(feed,system,record_id,change,digest,observed_at) "
                            "VALUES (?,?,?,?,?,?)",
                            (feed["id"], feed["system"], rid, change, sha, timestamp),
                        )
                    db.execute(
                        "INSERT INTO feed_runs(feed,system,snapshot_digest,observed_at,record_count,interpretation_json) "
                        "VALUES (?,?,?,?,?,?) ON CONFLICT(feed) DO UPDATE SET "
                        "system=excluded.system,snapshot_digest=excluded.snapshot_digest,"
                        "observed_at=excluded.observed_at,record_count=excluded.record_count,"
                        "interpretation_json=excluded.interpretation_json",
                        (feed["id"], feed["system"], snapshot, timestamp, len(items),
                         json.dumps(interpretation, sort_keys=True)),
                    )
                result.append({
                    "feed": feed["id"], "system": feed["system"], "status": "polled",
                    "created": created, "changed": changed, "items": len(items),
                    "insight": interpretation,
                })
            except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
                # Do not echo private snapshot contents or paths to log consumers.
                result.append({
                    "feed": feed["id"], "system": feed["system"], "status": "error",
                    "error_type": type(exc).__name__,
                })
    return {
        "schema": "cite_refinery.headless_poll_result.v1",
        "feeds": result, "ok": all(f["status"] == "polled" for f in result),
        "boundary": "Local change inbox only; no graph mutation or autonomous publication.",
    }


def status(db_path: Path, event_limit: int = 25) -> dict[str, Any]:
    if not db_path.is_file():
        return {"feeds": [], "events": [], "status": "not_initialized"}
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as db:
        feeds = [
            {
                "feed": feed, "system": system, "snapshot_digest": sha,
                "last_poll": observed_at, "record_count": count,
                "insight": json.loads(interpretation),
            }
            for feed, system, sha, observed_at, count, interpretation in db.execute(
                "SELECT feed,system,snapshot_digest,observed_at,record_count,interpretation_json "
                "FROM feed_runs ORDER BY feed"
            )
        ]
        events = [
            {
                "sequence": seq, "feed": feed, "system": system, "record_id": rid,
                "change": change, "digest": digest, "observed_at": observed_at,
            }
            for seq, feed, system, rid, change, digest, observed_at in db.execute(
                "SELECT sequence,feed,system,record_id,change,digest,observed_at "
                "FROM events ORDER BY sequence DESC LIMIT ?", (max(1, min(event_limit, 200)),)
            )
        ]
    return {"schema": "cite_refinery.headless_status.v1", "feeds": feeds, "events": events}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cite-refinery-headless")
    p.add_argument("--db", required=True, type=Path, help="Local private event inbox database")
    sub = p.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run", help="One bounded polling pass (schedule with systemd/cron/Prefect)")
    run.add_argument("--config", required=True, type=Path)
    recent = sub.add_parser("status", help="Read-only feed health and changes")
    recent.add_argument("--limit", type=int, default=25)
    args = p.parse_args(argv)
    try:
        response = poll(args.config, args.db) if args.action == "run" else status(args.db, args.limit)
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0 if response.get("ok", True) else 2
    except (OSError, ValueError, json.JSONDecodeError, sqlite3.Error) as exc:
        print(json.dumps({"status": "error", "error_type": type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
