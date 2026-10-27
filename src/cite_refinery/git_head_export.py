"""Read-only local Git HEAD exporter for active portfolio projects.

Produces normalized record_list snapshots from explicitly authorized local
checkouts. No git fetch, no remote write, no code extraction, no shell.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from .development_steering import ID_RE, load_registry
from .headless_intelligence import RECORD_SCHEMA

CHECKOUT_SCHEMA = "cite_refinery.local_checkouts.v1"
SHA_RE = re.compile(r"^[a-f0-9]{40,64}$")


def _git(checkout: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(checkout), *args],
        text=True, encoding="utf-8", errors="replace",
        capture_output=True, check=False, timeout=8,
    )
    if completed.returncode:
        raise ValueError("local git command failed")
    return completed.stdout.strip()


def _origin_repo(remote: str) -> str | None:
    if remote.startswith("git@github.com:"):
        path = remote[len("git@github.com:"):]
    elif remote.startswith("ssh://git@github.com/"):
        path = remote[len("ssh://git@github.com/"):]
    else:
        url = urlparse(remote)
        if url.scheme != "https" or url.netloc != "github.com":
            return None
        path = url.path.lstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if len(path.split("/")) != 2:
        return None
    return path


def load_checkouts(path: Path, project_ids: set[str]) -> dict[str, Path]:
    if not path.is_file() or path.stat().st_size > 64 * 1024:
        raise ValueError("missing or oversized local checkout manifest")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != CHECKOUT_SCHEMA:
        raise ValueError("invalid local checkout manifest")
    checkouts = payload.get("checkouts")
    if not isinstance(checkouts, list) or not checkouts or len(checkouts) > 64:
        raise ValueError("expected 1..64 local checkouts")
    result = {}
    for item in checkouts:
        if not isinstance(item, dict):
            raise ValueError("checkout must be object")
        pid, raw_path = item.get("project_id"), item.get("path")
        if not isinstance(pid, str) or not ID_RE.fullmatch(pid) or pid not in project_ids or pid in result:
            raise ValueError("checkout project must be a unique registered project")
        if not isinstance(raw_path, str) or not Path(raw_path).is_absolute():
            raise ValueError("local checkout path must be absolute")
        checkout = Path(raw_path).resolve(strict=True)
        if not checkout.is_dir():
            raise ValueError("local checkout is not a directory")
        result[pid] = checkout
    return result


def export_heads(registry_path: Path, checkouts_path: Path) -> dict:
    projects = load_registry(registry_path)
    registered = {p["id"]: p for p in projects}
    checkouts = load_checkouts(checkouts_path, set(registered))
    records = []
    for pid, checkout in sorted(checkouts.items()):
        project = registered[pid]
        if project["state"] != "active":
            continue
        git_root = Path(_git(checkout, "rev-parse", "--show-toplevel")).resolve(strict=True)
        if git_root != checkout:
            raise ValueError("checkout path must point to the Git worktree root")
        origin = _origin_repo(_git(checkout, "remote", "get-url", "origin"))
        if not origin or origin.casefold() != project["repository"].casefold():
            raise ValueError("git origin does not match registered repository")
        sha = _git(checkout, "rev-parse", "--verify", "HEAD")
        if not SHA_RE.fullmatch(sha):
            raise ValueError("git HEAD did not return a commit identifier")
        subject = _git(checkout, "log", "-1", "--format=%s").replace("\n", " ")[:120]
        recorded = _git(checkout, "log", "-1", "--format=%cI")
        branch = _git(checkout, "rev-parse", "--abbrev-ref", "HEAD")[:80]
        records.append({
            "id": f"git-head:{pid}",
            "title": f"{project['repository']} {sha[:12]}: {subject}"[:250],
            "source_url": f"https://github.com/{project['repository']}/commit/{sha}",
            "signal": "project_change",
            "tags": [],
            "project_targets": [pid],
            "commit": sha,
            "commit_date": recorded,
            "branch": branch,
        })
    return {"schema": RECORD_SCHEMA, "records": records}


def write_atomic(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    payload = json.dumps(content, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=".head-export-", suffix=".tmp", dir=str(path.parent))
    try:
        if os.name == "posix":
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cite-refinery-git-heads")
    p.add_argument("--registry", required=True, type=Path)
    p.add_argument("--checkouts", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        records = export_heads(args.registry, args.checkouts)
        write_atomic(args.out, records)
        print(json.dumps({"status": "exported", "records": len(records["records"])}))
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error_type": type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
