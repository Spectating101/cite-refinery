#!/usr/bin/env python3
"""Bounded private Atlas GitHub-release monitoring; no tool execution or auto-upgrades.

The source checkout is commit-pinned and must have no local source changes.
All mutable state lives inside --workdir. Network access is restricted by the
existing Cite-Refinery github_release_export allowlist and size limits.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

MIN_FREE_BYTES = 2 * 1024**3
EXPECTED_FILES = ("sources.json", "projects.json", "feeds.json")
EXPECTED_FEED = "releases"
MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".atlas-status-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            os.fchmod(out.fileno(), 0o600)
            json.dump(data, out, sort_keys=True, indent=2)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".atlas-brief-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            os.fchmod(out.fileno(), 0o600)
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def json_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("expected JSON object: " + path.name)
    return data


def checkout_guard(repo: Path, expected_sha: str) -> None:
    if not re.fullmatch(r"[a-f0-9]{40}", expected_sha):
        raise ValueError("expected commit must be a complete 40-character SHA")
    repo = repo.resolve(strict=True)
    if not (repo / "src/cite_refinery/github_release_export.py").is_file():
        raise ValueError("Atlas collector missing from pinned checkout")
    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(repo), *args], text=True, timeout=12,
            stderr=subprocess.DEVNULL).strip()
    if git("rev-parse", "HEAD") != expected_sha:
        raise ValueError("Atlas source checkout is not at its approved exact commit")
    if git("status", "--porcelain=v1", "--untracked-files=normal", "--",
           "src/cite_refinery", "scripts/atlas_release_monitor.py",
           "tests/test_atlas_release_monitor.py"):
        raise ValueError("Atlas source files have unreviewed local modifications")


def validate_inputs(work: Path) -> None:
    if not work.is_dir() or work.is_symlink():
        raise ValueError("private Atlas workdir missing or linked")
    if work.stat().st_mode & 0o077:
        raise ValueError("private Atlas workdir must deny group/other access")
    for name in EXPECTED_FILES:
        f = work / name
        if f.is_symlink() or not f.is_file() or f.stat().st_size > 256 * 1024:
            raise ValueError("missing, linked or oversized Atlas configuration: " + name)
        json_file(f)
    feeds = json_file(work / "feeds.json")
    if feeds.get("schema") != "cite_refinery.headless_feeds.v1":
        raise ValueError("unexpected feed configuration schema")
    if feeds.get("feeds") != [{
        "id": "releases", "system": "github_public_release",
        "kind": "record_list", "path": "github_releases.json",
    }]:
        raise ValueError("only the reviewed public release feed is allowed")
    if shutil.disk_usage(work).free < MIN_FREE_BYTES:
        raise ValueError("less than 2 GiB free: withholding nonessential monitoring")


@contextmanager
def exclusive_lock(work: Path):
    lock_path = work / ".atlas-release-monitor.lock"
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def release_gaps(previous: list[dict], current: list[dict]) -> list[str]:
    """Flag fully disjoint latest-ten windows; absence of a flag is not proof of completeness."""
    old = {}
    new = {}
    for row in previous:
        old.setdefault(row["id"].split(":")[1], set()).add(row["id"])
    for row in current:
        new.setdefault(row["id"].split(":")[1], set()).add(row["id"])
    return sorted(repo for repo, ids in new.items()
                  if len(ids) >= 10 and repo in old and old[repo] and
                  not ids.intersection(old[repo]))


def render_brief(now: str, records: list[dict], fresh: list[dict],
                 matches: dict[str, int], gaps: list[str]) -> str:
    def safe_tag(value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9._+-]", "_", value)[:110]
    lines = [
        "# Atlas technology release watch",
        "",
        f"**Last successful scan (UTC):** {now}",
        f"**Current release records:** {len(records)}",
        f"**New source records versus previous snapshot:** {len(fresh)}",
        "",
        "This is GitHub *release metadata*, not proof of a useful feature, vulnerability, or upgrade.",
    ]
    if gaps:
        lines += ["", "**Coverage warning:** No overlap across saturated latest-ten windows: " +
                  ", ".join(gaps) + ". Inspect full upstream history manually."]
    lines += ["", "## Recent observed releases"]
    if not fresh:
        lines.append("No new release IDs in this scan.")
    else:
        for item in sorted(fresh, key=lambda x: x["published_at"], reverse=True)[:25]:
            repo = item["id"].split(":")[1]
            tag = safe_tag(item["tag"])
            lines.append(f"- {item['published_at'][:10]} — [{repo} {tag}]({item['source_url']})")
        if len(fresh) > 25:
            lines.append(f"- {len(fresh) - 25} additional new records in the private feed")
    lines += [
        "", "## Project candidate routing",
        "", "| Project | New candidate links |", "|---|---:|",
    ]
    for name, count in sorted(matches.items()):
        lines.append(f"| {name} | {count} |")
    lines += ["", "Only distinct source changes require manual inspection. "
              "No release activates an installation, repository mutation, model execution or publication."]
    return "\n".join(lines) + "\n"


def perform_once(work: Path, repo: Path, expected_sha: str) -> dict[str, Any]:
    checkout_guard(repo, expected_sha)
    validate_inputs(work)
    # Do not accidentally pass a privileged user token to the public read-only watcher.
    os.environ.pop("GITHUB_TOKEN", None)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.path.insert(0, str(repo / "src"))
    from cite_refinery.github_release_export import collect_releases, write_atomic
    from cite_refinery.headless_intelligence import poll
    from cite_refinery.development_steering import steer

    original_path = work / "github_releases.json"
    previous = json_file(original_path).get("records", []) if original_path.exists() else []
    if not isinstance(previous, list):
        raise ValueError("existing release snapshot invalid")
    snapshot = collect_releases(work / "sources.json", work / "projects.json")
    records = snapshot["records"]
    if len(json.dumps(snapshot).encode("utf-8")) > MAX_SNAPSHOT_BYTES:
        raise ValueError("release snapshot exceeds the 2 MiB inbox contract")
    old_ids = {row["id"] for row in previous}
    fresh = [row for row in records if row["id"] not in old_ids]
    gaps = release_gaps(previous, records)
    write_atomic(original_path, snapshot)
    polled = poll(work / "feeds.json", work / "radar.sqlite")
    if not polled.get("ok") or len(polled.get("feeds", [])) != 1:
        raise RuntimeError("Atlas headless inbox did not complete one successful feed")
    routed = steer(work / "feeds.json", work / "projects.json", work / "radar.sqlite")
    projects = routed.get("projects", [])
    if not projects or any(p.get("status") != "evaluated" or p.get("has_more") for p in projects):
        raise RuntimeError("Atlas steering did not fully evaluate registered projects")
    matches = {p["project_id"]: p["candidates"] for p in projects}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    outcome = {
        "status": "success_with_coverage_warning" if gaps else "success",
        "timestamp_utc": now, "pinned_commit": expected_sha,
        "total_release_records": len(records),
        "new_release_records": len(fresh),
        "new_project_candidate_links": sum(matches.values()),
        "project_candidates": matches,
        "possible_latest_ten_gaps": gaps,
        "authority": "release_metadata_leads_only",
    }
    atomic_text(work / "LATEST_TECH_RADAR.md", render_brief(now, records, fresh, matches, gaps))
    atomic_json(work / "last_success.json", outcome)
    return outcome


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "check", "status"])
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--expected-head")
    args = parser.parse_args(argv)
    os.umask(0o077)
    work = args.workdir.expanduser().resolve()
    if args.action == "status":
        for name in ("last_attempt.json", "last_success.json"):
            path = work / name
            print(name, path.read_text(encoding="utf-8").strip() if path.exists()
                  else "(not yet recorded)")
        return 0
    if args.repo is None or args.expected_head is None:
        parser.error("--repo and --expected-head are mandatory for check/run")
    repo = args.repo.expanduser().resolve()
    if args.action == "check":
        checkout_guard(repo, args.expected_head)
        validate_inputs(work)
        print(json.dumps({"status": "ready", "repo": str(repo),
                          "available_bytes": shutil.disk_usage(work).free}))
        return 0
    try:
        with exclusive_lock(work):
            try:
                result = perform_once(work, repo, args.expected_head)
                atomic_json(work / "last_attempt.json", result)
                print(json.dumps(result, sort_keys=True))
                return 0
            except Exception as exc:
                record = {
                    "status": "failed", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:180],
                    "authority": "no_success_asserted",
                }
                atomic_json(work / "last_attempt.json", record)
                print(json.dumps(record, sort_keys=True), file=sys.stderr)
                return 2
    except BlockingIOError:
        print(json.dumps({"status": "failed", "error": "another Atlas scan is running"}),
              file=sys.stderr)
        return 75


if __name__ == "__main__":
    raise SystemExit(main())
