"""Candidate-only development steering, built on the headless change inbox.

Opt-in project registry + explicit subject tags + source receipts -> persisted
project-specific next checks. This never edits a repository, creates issues,
sends prompts to an LLM, or promotes source leads into accepted evidence.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

from .headless_intelligence import _connect, _digest, _load_snapshot, load_config

REGISTRY_SCHEMA = "cite_refinery.development_registry.v1"
REPORT_SCHEMA = "cite_refinery.development_steering.v1"
VALID_STATES = {"active", "paused", "archived"}
VALID_SIGNALS = {
    "new_capability", "competitor_release", "research_finding",
    "deprecation", "security_advisory", "regulatory_change",
    "market_demand", "funding_opportunity", "project_change",
}
ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")
REPO_RE = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")
MAX_EVENTS_PER_PROJECT = 500

STEERING_DDL = """
CREATE TABLE IF NOT EXISTS steering_cursor (
 project_id TEXT PRIMARY KEY, last_sequence INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS steering_candidates (
 project_id TEXT NOT NULL, feed TEXT NOT NULL, record_id TEXT NOT NULL,
 revision_digest TEXT NOT NULL, event_sequence INTEGER NOT NULL,
 repository TEXT NOT NULL, signal TEXT NOT NULL,
 source_url TEXT NOT NULL, title TEXT NOT NULL,
 reason TEXT NOT NULL, next_check TEXT NOT NULL,
 matched_tags_json TEXT NOT NULL, match_basis TEXT NOT NULL,
 urgency TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'candidate_review',
 first_seen TEXT NOT NULL,
 PRIMARY KEY(project_id,feed,record_id,revision_digest)
);
CREATE INDEX IF NOT EXISTS steering_project_order
 ON steering_candidates(project_id,event_sequence DESC);
"""


def _tags(value: Any, *, context: str) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > 32:
        raise ValueError(f"{context} must be a bounded list")
    if any(not isinstance(x, str) or not TAG_RE.fullmatch(x) for x in value):
        raise ValueError(f"{context} contains an invalid tag")
    return tuple(sorted(set(value)))


def _strings(value: Any, *, context: str, max_count: int, max_length: int) -> list[str]:
    if not isinstance(value, list) or len(value) > max_count:
        raise ValueError(f"{context} must be a bounded string list")
    if any(not isinstance(x, str) or not x.strip() or len(x) > max_length for x in value):
        raise ValueError(f"{context} contains an invalid string")
    return list(dict.fromkeys(value))


def load_registry(path: Path, *, feed_ids: set[str] | None = None) -> list[dict[str, Any]]:
    if not path.is_file() or path.stat().st_size > 256 * 1024:
        raise ValueError("project registry is missing or oversized")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != REGISTRY_SCHEMA:
        raise ValueError("invalid project registry schema")
    raw = data.get("projects")
    if not isinstance(raw, list) or not 1 <= len(raw) <= 64:
        raise ValueError("registry must have 1..64 projects")
    seen: set[str] = set()
    result = []
    for p in raw:
        if not isinstance(p, dict):
            raise ValueError("invalid project")
        pid, repository, state = p.get("id"), p.get("repository"), p.get("state")
        if not isinstance(pid, str) or not ID_RE.fullmatch(pid) or pid in seen:
            raise ValueError("invalid or repeated project id")
        if not isinstance(repository, str) or not REPO_RE.fullmatch(repository):
            raise ValueError("repository must be owner/name")
        if state not in VALID_STATES:
            raise ValueError("project state must be active, paused, or archived")
        tags = _tags(p.get("watch_tags"), context="watch_tags")
        feeds = _strings(p.get("feeds"), context="feeds", max_count=32, max_length=64)
        if not tags or not feeds or any(not ID_RE.fullmatch(f) for f in feeds):
            raise ValueError("project must select feeds and at least one specific tag")
        if feed_ids is not None and any(f not in feed_ids for f in feeds):
            raise ValueError("project references unconfigured feed")
        goals = _strings(p.get("goals", []), context="goals", max_count=8, max_length=250)
        priorities = _strings(p.get("current_priorities", []),
                              context="current_priorities", max_count=8, max_length=250)
        benchmark = p.get("benchmark", "")
        if not isinstance(benchmark, str) or len(benchmark) > 400:
            raise ValueError("benchmark must be a short string")
        seen.add(pid)
        result.append({
            "id": pid, "repository": repository, "state": state,
            "watch_tags": tags, "feeds": feeds, "goals": goals,
            "current_priorities": priorities, "benchmark": benchmark,
        })
    return result


ACTION = {
    "new_capability": "Reproduce the capability and benchmark it against the current implementation, integration cost, licensing and failure cases.",
    "competitor_release": "Compare the release against the project's pinned baseline; identify a measurable gap before proposing a replacement.",
    "research_finding": "Read the original source, check experimental methods and limitations, and design a project-specific replication.",
    "deprecation": "Identify whether any project dependency is affected and test a bounded migration path.",
    "security_advisory": "Verify affected versions, exposure and remediation using authoritative security advisories; do not assume compromise.",
    "regulatory_change": "Check the official text, applicability, jurisdiction and effective date before updating requirements.",
    "market_demand": "Validate a specific counterparty problem, delivery feasibility and buying evidence before changing priorities.",
    "funding_opportunity": "Verify application eligibility, terms, dates, funding scope and resource commitments.",
    "project_change": "Compare the new project state against roadmap assumptions, benchmarks and watched external alternatives.",
}


def _candidate(project: dict[str, Any], feed: str, rid: str, row: dict[str, Any],
               event: tuple[int, str, str]) -> dict[str, Any] | None:
    seq, revision, observed_at = event
    signal = row.get("signal")
    if signal not in VALID_SIGNALS:
        return None
    targets = row.get("project_targets", [])
    if not isinstance(targets, list) or len(targets) > 64 or any(
        not isinstance(t, str) or not ID_RE.fullmatch(t) for t in targets
    ):
        return None
    try:
        tags = _tags(row.get("tags", []), context="feed tags")
    except ValueError:
        return None
    explicit = project["id"] in targets
    matched = sorted(set(tags).intersection(project["watch_tags"]))
    if not explicit and not matched:
        return None
    url = row.get("source_url") or row.get("url")
    title = row.get("title")
    if (not isinstance(url, str) or not url.startswith("https://")
            or len(url) > 1200 or not isinstance(title, str) or not title.strip()
            or len(title) > 250):
        return None
    basis = "explicit_project_target" if explicit else "structured_tag_intersection"
    return {
        "project_id": project["id"], "repository": project["repository"],
        "feed": feed, "record_id": rid, "revision_digest": revision,
        "event_sequence": seq, "source_url": url, "title": title.strip(),
        "signal": signal, "reason": (
            f"New source revision routed via {basis}; matched tags: "
            f"{', '.join(matched) if matched else '(none)'}. "
            "Source claims and relevance are unverified."
        ),
        "next_check": ACTION[signal],
        "matched_tags": matched, "match_basis": basis,
        "urgency": "inspect_soon" if signal in {"security_advisory", "deprecation"} else "routine_review",
        "status": "candidate_review", "first_seen": observed_at,
    }


def steer(config_path: Path, registry_path: Path, db_path: Path, *,
          project_id: str | None = None) -> dict[str, Any]:
    """Use committed source events and latest snapshots; never rewrite the source ledger.

    Stale events from intermediate versions are not assigned to newer source
    content. Project cursor advances only after all subscribed snapshots load
    cleanly and its candidate rows are committed.
    """
    feeds = {f["id"]: f for f in load_config(config_path)}
    projects = load_registry(registry_path, feed_ids=set(feeds))
    if project_id is not None:
        if project_id not in {p["id"] for p in projects}:
            raise ValueError("unknown project")
        projects = [p for p in projects if p["id"] == project_id]
    output = []
    with _connect(db_path) as db:
        db.executescript(STEERING_DDL)
        for p in projects:
            if p["state"] != "active":
                output.append({"project_id": p["id"], "status": "skipped_" + p["state"]})
                continue
            # All source inputs must be valid before advancing any cursor.
            try:
                snapshots = {feed: _load_snapshot(feeds[feed])[0] for feed in p["feeds"]}
            except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
                output.append({
                    "project_id": p["id"], "status": "source_unavailable",
                    "error_type": type(exc).__name__, "candidates": 0,
                })
                continue
            cursor_row = db.execute(
                "SELECT last_sequence FROM steering_cursor WHERE project_id=?", (p["id"],)
            ).fetchone()
            cursor = cursor_row[0] if cursor_row else 0
            placeholders = ",".join("?" for _ in p["feeds"])
            rows = db.execute(
                "SELECT sequence,feed,record_id,digest,observed_at "
                f"FROM events WHERE sequence>? AND feed IN ({placeholders}) "
                "ORDER BY sequence LIMIT ?",
                (cursor, *p["feeds"], MAX_EVENTS_PER_PROJECT),
            ).fetchall()
            created = superseded = discarded = 0
            with db:
                for seq, feed, rid, digest, observed_at in rows:
                    current = snapshots[feed].get(rid)
                    if current is None or _digest(current) != digest:
                        superseded += 1
                        continue
                    # Native graph packets remain the responsibility of graph-review.
                    if feeds[feed]["kind"] != "record_list":
                        discarded += 1
                        continue
                    candidate = _candidate(p, feed, rid, current, (seq, digest, observed_at))
                    if candidate is None:
                        discarded += 1
                        continue
                    result = db.execute(
                        "INSERT OR IGNORE INTO steering_candidates "
                        "(project_id,feed,record_id,revision_digest,event_sequence,"
                        "repository,signal,source_url,title,reason,next_check,"
                        "matched_tags_json,match_basis,urgency,status,first_seen) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            p["id"], feed, rid, digest, seq, p["repository"],
                            candidate["signal"], candidate["source_url"],
                            candidate["title"], candidate["reason"],
                            candidate["next_check"],
                            json.dumps(candidate["matched_tags"]),
                            candidate["match_basis"], candidate["urgency"],
                            "candidate_review", observed_at,
                        ),
                    )
                    created += result.rowcount
                if rows:
                    db.execute(
                        "INSERT INTO steering_cursor(project_id,last_sequence) VALUES (?,?) "
                        "ON CONFLICT(project_id) DO UPDATE SET last_sequence=excluded.last_sequence",
                        (p["id"], rows[-1][0]),
                    )
            output.append({
                "project_id": p["id"], "repository": p["repository"], "status": "evaluated",
                "candidates": created, "superseded": superseded,
                "ignored": discarded, "cursor": rows[-1][0] if rows else cursor,
                "has_more": len(rows) == MAX_EVENTS_PER_PROJECT,
            })
    return {
        "schema": REPORT_SCHEMA, "projects": output,
        "authority": "candidate_development_triage_only",
        "no_repository_changes": True, "no_graph_mutation": True,
    }


def project_brief(db_path: Path, project_id: str, *, limit: int = 20) -> dict[str, Any]:
    """Inspect persisted project recommendations, no source fetch or mutation."""
    if not ID_RE.fullmatch(project_id):
        raise ValueError("invalid project ID")
    if not db_path.is_file():
        return {"project_id": project_id, "candidates": [], "status": "not_initialized"}
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as db:
        rows = db.execute(
            "SELECT feed,record_id,revision_digest,repository,signal,source_url,"
            "title,reason,next_check,matched_tags_json,match_basis,urgency,status,"
            "first_seen,event_sequence FROM steering_candidates WHERE project_id=? "
            "ORDER BY event_sequence DESC LIMIT ?",
            (project_id, max(1, min(limit, 100))),
        ).fetchall()
    return {
        "schema": "cite_refinery.development_brief.v1",
        "project_id": project_id,
        "candidates": [
            {
                "feed": feed, "record_id": rid, "revision_digest": digest,
                "repository": repo, "signal": signal, "source_url": url,
                "title": title, "reason": reason, "next_check": check,
                "matched_tags": json.loads(tags), "match_basis": basis,
                "urgency": urgency, "status": state, "first_seen": time,
                "event_sequence": seq,
            }
            for (feed, rid, digest, repo, signal, url, title, reason, check, tags,
                 basis, urgency, state, time, seq) in rows
        ],
        "authority": "lead_only_not_an_implementation_instruction",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cite-refinery-steer")
    parser.add_argument("--db", required=True, type=Path)
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run")
    run.add_argument("--config", required=True, type=Path)
    run.add_argument("--registry", required=True, type=Path)
    run.add_argument("--project", help="Optional registered project ID")
    brief = sub.add_parser("brief")
    brief.add_argument("--project", required=True)
    brief.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    try:
        response = (steer(args.config, args.registry, args.db, project_id=args.project)
                    if args.action == "run" else project_brief(args.db, args.project, limit=args.limit))
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0 if all(p.get("status") != "source_unavailable"
                        for p in response.get("projects", [])) else 2
    except (OSError, ValueError, KeyError, json.JSONDecodeError, sqlite3.Error) as exc:
        print(json.dumps({"status": "error", "error_type": type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
