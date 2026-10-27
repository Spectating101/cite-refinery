"""Opt-in public GitHub release discovery -> normalized lead snapshots.

No arbitrary HTTP targets: only constructed api.github.com repository releases
endpoints are queried. Metadata only, never source code or release body.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .development_steering import ID_RE, REPO_RE, VALID_SIGNALS, _tags, load_registry
from .git_head_export import write_atomic
from .headless_intelligence import RECORD_SCHEMA

SCHEMA = "cite_refinery.github_release_watch.v1"
MAX_SOURCES = 30


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_sources(path: Path, *, project_ids: set[str]) -> list[dict[str, Any]]:
    if not path.is_file() or path.stat().st_size > 128 * 1024:
        raise ValueError("source manifest absent or too large")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ValueError("invalid GitHub release source manifest")
    raw = doc.get("repositories")
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_SOURCES:
        raise ValueError("expected 1..30 release sources")
    seen = set()
    sources = []
    for row in raw:
        if not isinstance(row, dict):
            raise ValueError("invalid source entry")
        repo = row.get("repository")
        if not isinstance(repo, str) or not REPO_RE.fullmatch(repo) or repo.casefold() in seen:
            raise ValueError("invalid or duplicate public repository")
        signal = row.get("signal", "new_capability")
        if signal not in VALID_SIGNALS:
            raise ValueError("invalid release signal")
        tags = _tags(row.get("tags", []), context="release watch tags")
        targets = row.get("project_targets", [])
        if (not isinstance(targets, list) or len(targets) > 64
                or any(not isinstance(t, str) or not ID_RE.fullmatch(t)
                       or t not in project_ids for t in targets)):
            raise ValueError("invalid project target")
        if not tags and not targets:
            raise ValueError("source needs specific tags or registered project targets")
        since = row.get("published_since")
        if since is not None and (not isinstance(since, str)
                                  or len(since) != 20
                                  or since[10:] == ""
                                  or since[10] != "T" or not since.endswith("Z")):
            raise ValueError("published_since must be fixed YYYY-MM-DDTHH:MM:SSZ")
        prerelease = row.get("include_prereleases", False)
        if not isinstance(prerelease, bool):
            raise ValueError("include_prereleases must be boolean")
        seen.add(repo.casefold())
        sources.append({
            "repository": repo, "signal": signal, "tags": tags,
            "project_targets": sorted(set(targets)),
            "published_since": since, "include_prereleases": prerelease,
        })
    return sources


def _fetch_json(url: str, token: str | None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "CiteRefineryHeadlessReleaseWatch/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers, method="GET")
    # Repository renames are reviewed before a manifest is changed;
    # no redirects carrying credentials to another host.
    with build_opener(NoRedirects).open(request, timeout=15) as response:
        body = response.read(512 * 1024 + 1)
        if len(body) > 512 * 1024:
            raise ValueError("GitHub release API result exceeds 512 KiB")
        return json.loads(body)


def collect_releases(
    sources_path: Path, registry_path: Path,
    *, fetcher: Callable[[str, str | None], Any] | None = None,
) -> dict:
    projects = load_registry(registry_path)
    known = {p["id"] for p in projects}
    sources = load_sources(sources_path, project_ids=known)
    token = os.environ.get("GITHUB_TOKEN") or None
    request = fetcher or _fetch_json
    records = []
    for source in sources:
        repo = source["repository"]
        url = f"https://api.github.com/repos/{repo}/releases?per_page=10"
        rows = request(url, token)
        if not isinstance(rows, list) or len(rows) > 10:
            raise ValueError("upstream GitHub release response was not a bounded list")
        for release in rows:
            if not isinstance(release, dict) or release.get("draft") is not False:
                continue
            if release.get("prerelease") and not source["include_prereleases"]:
                continue
            rid, tag, published = (release.get("id"),
                                   release.get("tag_name"), release.get("published_at"))
            if (not isinstance(rid, int) or isinstance(rid, bool) or rid <= 0
                    or not isinstance(tag, str) or not tag or len(tag) > 120
                    or not isinstance(published, str) or len(published) != 20
                    or not published.endswith("Z")):
                continue
            if source["published_since"] and published < source["published_since"]:
                continue
            name = release.get("name")
            if not isinstance(name, str):
                name = ""
            records.append({
                "id": f"github-release:{repo}:{rid}",
                "title": f"{repo} {tag}: {name}"[:250],
                "source_url": f"https://github.com/{repo}/releases/tag/{quote(tag, safe='')}",
                "signal": source["signal"],
                "tags": list(source["tags"]),
                "project_targets": source["project_targets"],
                "release_id": rid, "tag": tag, "published_at": published,
                "prerelease": bool(release.get("prerelease", False)),
            })
    records.sort(key=lambda r: r["id"])
    return {"schema": RECORD_SCHEMA, "records": records}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cite-refinery-github-releases")
    p.add_argument("--sources", required=True, type=Path)
    p.add_argument("--registry", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        result = collect_releases(args.sources, args.registry)
        write_atomic(args.out, result)
        print(json.dumps({"status": "exported", "releases": len(result["records"])}))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError,
            HTTPError, URLError, TimeoutError) as exc:
        print(json.dumps({"status": "error", "error_type": type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
