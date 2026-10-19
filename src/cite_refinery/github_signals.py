"""Bounded, operator-reviewed GitHub PUBLIC signals + immutable Git dependency diffs.

Public GitHub API observations are point-in-time self-reported metadata, not
verified adoption. Local package-manifest deltas are exact pinned Git content,
not successful builds or vulnerability analysis. No model is required.
"""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .repository_trend_bridge import _run, _sha, SLUG

SCHEMA = "cite_refinery.github_public_signals.v1"
SHA = re.compile(r"^[0-9a-f]{40}$")
RFC3339 = re.compile(r"^20\d{2}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$")
SAFE = re.compile(r"^[A-Za-z0-9_./-]{1,140}$")
BUNDLES = ("pyproject.toml", "package.json", "requirements.txt")
LIMIT_REPOS = 12


def _json(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(v: Any) -> str:
    return hashlib.sha256(_json(v).encode()).hexdigest()


def _datetime(raw: Any) -> str:
    if not isinstance(raw, str) or not RFC3339.fullmatch(raw):
        raise ValueError("timestamp must have exact RFC3339 UTC offset")
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid source timestamp") from exc
    return raw


def _github(repo: str, endpoint: str) -> Any:
    """Invoke configured GitHub CLI only for hardcoded allowlisted public endpoints."""
    if not SLUG.fullmatch(repo):
        raise ValueError("invalid GitHub repository name")
    if endpoint not in {"", "/releases?per_page=8", "/tags?per_page=12", "/commits?per_page=8"}:
        raise ValueError("disallowed GitHub endpoint")
    try:
        p = subprocess.run(["gh", "api", f"repos/{repo}{endpoint}"],
                           capture_output=True, check=False, timeout=25)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("GitHub API collection failed") from exc
    if p.returncode or len(p.stdout) > 1_800_000:
        raise ValueError("GitHub API unavailable, inaccessible or over size limit")
    try:
        return json.loads(p.stdout)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("invalid GitHub API response") from exc


def collect_public(repos: list[str]) -> dict[str, Any]:
    """Collect allowlisted public repository metadata, without storing gh secrets."""
    if not isinstance(repos, list) or not 1 <= len(repos) <= LIMIT_REPOS:
        raise ValueError("collect between 1 and 12 public repositories")
    if len(set(repos)) != len(repos):
        raise ValueError("duplicate requested repositories")
    items = []
    for slug in repos:
        if not isinstance(slug, str) or not SLUG.fullmatch(slug):
            raise ValueError("invalid repository slug")
        metadata = _github(slug, "")
        if (metadata.get("full_name") != slug or metadata.get("private") is not False
                or metadata.get("archived") not in {True, False}):
            raise ValueError("repository metadata not confirmed public and matching identity")
        releases = _github(slug, "/releases?per_page=8")
        tags = _github(slug, "/tags?per_page=12")
        commits = _github(slug, "/commits?per_page=8")
        if not all(isinstance(rows, list) for rows in (releases, tags, commits)):
            raise ValueError("malformed GitHub listing")
        # Only publish verified Github fields from fixed endpoint paths; no
        # raw payloads, descriptions, bodies, actor profiles or private data.
        item = {
            "repository": slug,
            "visibility": "public", "archived": metadata["archived"],
            "default_branch": metadata["default_branch"],
            "stars": metadata["stargazers_count"], "forks": metadata["forks_count"],
            "open_issues": metadata["open_issues_count"],
            "pushed_at": metadata.get("pushed_at"),
            "releases": [
                {
                    "tag_name": row["tag_name"], "name": (row.get("name") or "")[:130],
                    "draft": row.get("draft"), "prerelease": row.get("prerelease"),
                    "published_at": row.get("published_at"), "url": row.get("html_url"),
                }
                for row in releases if row.get("draft") is False
            ],
            "tags": [
                {"name": row["name"], "sha": row["commit"]["sha"]}
                for row in tags[:12]
            ],
            "recent_commits": [
                {"sha": row["sha"], "committed_at": row["commit"]["committer"]["date"]}
                for row in commits[:8]
            ],
        }
        items.append(item)
    return {
        "schema": SCHEMA,
        "observed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "observations": items,
        "source": "GitHub REST API via gh CLI (repository/release/tag/commit public endpoints)",
        "boundary": "Public provider counters and latest sampled records, not adoption, capabilities or a complete release/commit census",
    }


def _git_meta(repo: Path, slug: str) -> None:
    expected = {f"https://github.com/{slug}", f"https://github.com/{slug}.git",
                f"git@github.com:{slug}.git"}
    origin = _run(repo, ["remote", "get-url", "origin"], limit=4096).decode().strip()
    if origin not in expected:
        raise ValueError("Git repository origin disagrees with evidence slug")


def _dependencies(data: bytes, path: str) -> dict[str, str]:
    """Conservative top-level dependency names/specifiers, never code execution."""
    if len(data) > 190_000:
        raise ValueError("dependency manifest too large")
    try:
        txt = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("dependency manifest not UTF-8") from exc
    dep: dict[str, str] = {}
    if path.endswith("package.json"):
        content = json.loads(txt)
        for section in ("dependencies", "devDependencies"):
            values = content.get(section) or {}
            if not isinstance(values, dict):
                raise ValueError("package dependency block must be a map")
            for key, value in values.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise ValueError("dependency identifiers must be strings")
                dep[f"{section}:{key}"] = value
    elif path.endswith("pyproject.toml"):
        content = tomllib.loads(txt)
        for raw in (content.get("project") or {}).get("dependencies", []) or []:
            if not isinstance(raw, str):
                raise ValueError("dependency requirement must be text")
            match = re.match(r"^\s*([A-Za-z0-9_.-]+)", raw)
            if match:
                dep[f"dependencies:{match.group(1).lower().replace('_','-')}"] = raw.strip()
        optional = (content.get("project") or {}).get("optional-dependencies", {}) or {}
        if isinstance(optional, dict):
            for group, requirements in optional.items():
                for raw in requirements if isinstance(requirements, list) else []:
                    if not isinstance(raw, str):
                        continue
                    match = re.match(r"^\s*([A-Za-z0-9_.-]+)", raw)
                    if match:
                        dep[f"optional:{group}:{match.group(1).lower().replace('_','-')}"] = raw.strip()
        # Do not assume Poetry, PDM, uv tool sections are covered.
    elif path.endswith("requirements.txt"):
        for line in txt.splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or raw.startswith(("-","git+","http")):
                continue
            match = re.match(r"^([A-Za-z0-9_.-]+)(?:\[.*?\])?(?=[!~=<>;\s]|$)", raw)
            if match:
                dep[f"requirements:{match.group(1).lower().replace('_','-')}"] = raw
    else:
        raise ValueError("unsupported dependency manifest type")
    if len(dep) > 400 or any(len(k) > 160 or len(v) > 600 for k,v in dep.items()):
        raise ValueError("dependency manifest exceeds bounded parse coverage")
    return dep


def _show_optional(repo: Path, rev: str, path: str) -> bytes | None:
    # A missing path is valid. Existing oversized/binary blobs must fail;
    # do not silently convert source-validation errors into absence.
    exists = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{rev}:{path}"],
                            capture_output=True, check=False, timeout=15)
    if exists.returncode:
        return None
    return _run(repo, ["show", f"{rev}:{path}"], limit=190_000)


def dependency_diff(root: str | Path, repo_spec: dict[str, Any]) -> list[dict[str, Any]]:
    slug = repo_spec.get("repository")
    local_dir = repo_spec.get("directory")
    if not isinstance(slug, str) or not SLUG.fullmatch(slug):
        raise ValueError("invalid dependency Git source")
    if not isinstance(local_dir, str) or not SAFE.fullmatch(local_dir) or "/" in local_dir or local_dir.startswith("."):
        raise ValueError("dependency checkout must be relative basename")
    root_path = Path(root).resolve(strict=True)
    repo = (root_path / local_dir).resolve(strict=True)
    if not repo.is_relative_to(root_path):
        raise ValueError("local repository outside root")
    _git_meta(repo, slug)
    base = _sha(repo, repo_spec.get("base"))
    head = _sha(repo, repo_spec.get("head"))
    _run(repo, ["merge-base", "--is-ancestor", base, head], limit=20)
    files = repo_spec.get("dependency_files", ["pyproject.toml", "package.json"])
    if not isinstance(files, list) or len(files) > 6 or len(set(files)) != len(files):
        raise ValueError("at most six manifest files per repository")
    results = []
    for path in files:
        if (not isinstance(path, str) or not SAFE.fullmatch(path)
                or path.startswith(("/", ".")) or ".." in path.split("/")
                or any(w in path.lower() for w in ("secret","credential","token","password"))
                or not path.endswith(BUNDLES)):
            raise ValueError("manifest file is unsafe or unsupported")
        old_raw = _show_optional(repo, base, path)
        new_raw = _show_optional(repo, head, path)
        if old_raw is None and new_raw is None:
            continue
        before = _dependencies(old_raw, path) if old_raw is not None else {}
        after = _dependencies(new_raw, path) if new_raw is not None else {}
        names = sorted(set(before) | set(after))
        added = [{"name":k, "spec":after[k]} for k in names if k not in before]
        removed = [{"name":k, "spec":before[k]} for k in names if k not in after]
        modified = [{"name":k, "before":before[k], "after":after[k]}
                    for k in names if k in before and k in after and before[k]!=after[k]]
        results.append({
            "path": path, "base": base, "head": head,
            "before_sha256": hashlib.sha256(old_raw).hexdigest() if old_raw is not None else None,
            "after_sha256": hashlib.sha256(new_raw).hexdigest() if new_raw is not None else None,
            "added": added, "removed": removed, "changed": modified,
            "source_url": f"https://github.com/{slug}/compare/{base}...{head}",
            "boundary": "Declared manifest source strings only; no resolved lockfile, build, vulnerability or transitive dependency validation",
        })
    return results


def _count(v: Any, label: str) -> int:
    if type(v) is not int or v < 0 or v > 5_000_000_000:
        raise ValueError(f"invalid public {label} count")
    return v


def _release_url(slug: str, url: Any) -> str:
    base = f"https://github.com/{slug}/releases/tag/"
    if not isinstance(url, str) or not url.startswith(base) or len(url) > 600:
        raise ValueError("release URL outside exact repository")
    return url


def _validate_snapshot(snap: dict[str, Any]) -> None:
    if not isinstance(snap, dict) or snap.get("schema") != SCHEMA:
        raise ValueError("unsupported public signals schema")
    _datetime(snap.get("observed_at"))
    items = snap.get("observations")
    if not isinstance(items, list) or not 1 <= len(items) <= LIMIT_REPOS:
        raise ValueError("observations count invalid")
    seen: set[str] = set()
    for row in items:
        if not isinstance(row, dict):
            raise ValueError("observation must be object")
        slug = row.get("repository")
        if not isinstance(slug, str) or not SLUG.fullmatch(slug) or slug in seen:
            raise ValueError("invalid or duplicate observed repository")
        seen.add(slug)
        if row.get("visibility") != "public" or type(row.get("archived")) is not bool:
            raise ValueError("GitHub visibility not explicitly public")
        if not isinstance(row.get("default_branch"), str) or len(row["default_branch"]) > 180:
            raise ValueError("invalid default branch")
        for k in ("stars", "forks", "open_issues"):
            _count(row.get(k), k)
        if row.get("pushed_at") is not None:
            _datetime(row["pushed_at"])
        for k, maximum in (("releases",8),("tags",12),("recent_commits",8)):
            if not isinstance(row.get(k), list) or len(row[k]) > maximum:
                raise ValueError("GitHub listing missing or exceeded cap")
        for rel in row["releases"]:
            if (not isinstance(rel, dict) or not isinstance(rel.get("tag_name"), str)
                or len(rel["tag_name"]) > 180
                or type(rel.get("draft")) is not bool or type(rel.get("prerelease")) is not bool
                or rel.get("draft") is True):
                raise ValueError("release metadata malformed or draft not allowed")
            _release_url(slug, rel.get("url"))
            _datetime(rel.get("published_at"))
        for tag in row["tags"]:
            if (not isinstance(tag, dict) or not isinstance(tag.get("name"), str)
                    or len(tag["name"]) > 180 or not SHA.fullmatch(str(tag.get("sha","")))):
                raise ValueError("Git tag name/sha invalid")
        for commit in row["recent_commits"]:
            if (not isinstance(commit, dict) or not SHA.fullmatch(str(commit.get("sha","")))):
                raise ValueError("GitHub recent commit SHA invalid")
            _datetime(commit.get("committed_at"))


def signals_to_packet(
    snap: dict[str, Any], *, project_state: dict[str, Any],
    project_id: str, manifest: dict[str, Any], repo_root: str | Path,
) -> dict[str, Any]:
    """Produce source-limited Program modules with reviewed repo identity.

    Converting arbitrary JSON does *not* cryptographically prove live GitHub
    authorship. The operator must review output and the collector provenance.
    """
    _validate_snapshot(snap)
    if not isinstance(project_state, dict) or project_id not in project_state.get("projects", {}):
        raise ValueError("authorized existing project state required")
    if manifest.get("schema") != "cite_refinery.repository_portfolio.v1":
        raise ValueError("source-pinned portfolio manifest required")
    specs = {x["repository"]: x for x in manifest.get("repositories", [])}
    if len(specs) != len(manifest.get("repositories", [])):
        raise ValueError("duplicate source manifest repositories")
    repo_nodes = {}
    prior = {}
    for n in project_state.get("semantic_nodes", {}).values():
        if n.get("project_id") != project_id or n.get("layer") != "program":
            continue
        for receipt in n.get("provenance_receipts") or []:
            if not isinstance(receipt, dict):
                continue
            if (n.get("kind") == "repository"
                    and receipt.get("source_system") == "repository_portfolio"
                    and receipt.get("origin_verified") is True):
                repo_nodes.setdefault(receipt.get("repository"), []).append(n)
            if (n.get("kind") == "event"
                    and receipt.get("source_system") == "github_public_signals"
                    and receipt.get("observation_role") == "github_repo_counter_snapshot"):
                prior.setdefault(receipt.get("repository"), []).append((receipt, n))
    nodes, edges, clusters, summary = [], [], [], []
    capture = snap["observed_at"]
    ident = capture.replace(":","").replace("-","").replace("+","").replace(".","")
    snap_digest = _hash(snap)
    for item in snap["observations"]:
        slug = item["repository"]
        if slug not in specs:
            raise ValueError("GitHub observed repository not in declared source-pinned portfolio")
        candidate = repo_nodes.get(slug, [])
        if len(candidate)!=1:
            raise ValueError("exactly one verified repository identity node required for GitHub signals")
        rid = candidate[0]["id"]
        key = "github-" + hashlib.sha256(slug.encode()).hexdigest()[:14]
        cluster = "github-signals-" + hashlib.sha256(slug.encode()).hexdigest()[:14]
        clusters.append({
            "key": cluster, "title": f"GitHub signals and dependency changes: {slug}",
            "tags": ["public_github_provider_observation", "not_software_validation"],
            "provenance": {"repository": slug, "observation": capture,
               "boundary": "GitHub public metadata and pinned manifest diffs, not adoption or capability quality"},
        })
        receipt = {
            "repository":slug,"observed_at":capture,
            "snapshot_sha256":snap_digest,
            "provider":"GitHub public REST API (operator-provided collector output)",
            "public_metadata_verified_by_adapter":False,
            "boundary":"Unsigned point-in-time collector JSON; provider statistics are not independent market adoption verification",
        }
        snap_key=f"{key}-observed-{ident}-{snap_digest[:12]}"
        node_data={"stars":item["stars"],"forks":item["forks"],"open_issues":item["open_issues"],
                   "archived":item["archived"],"pushed_at":item["pushed_at"]}
        nodes.append({
            "key": snap_key, "kind":"event","layer":"program",
            "statement": (f"GitHub public observation for {slug} at {capture}: "
                          f"{item['stars']} stars, {item['forks']} forks, "
                          f"{item['open_issues']} open issues/PRs; "
                          f"{len(item['releases'])} most-recent published releases returned; "
                          f"{len(item['tags'])} tag refs sampled"),
            "clusters":[cluster],"source_refs":[f"https://github.com/{slug}"],
            "tags":["github_public_counter_snapshot","not_adoption"],
            "provenance": {**receipt, "observation_role":"github_repo_counter_snapshot",
                "counters":node_data, "default_branch":item["default_branch"],
                "sample_limits":{"releases":8,"tags":12,"commits":8},
                "boundary":"Single provider reported point-in-time snapshot, no directional trend without prior comparable observation"},
        })
        edges.append({
            "source":snap_key,"target":rid,"relation":"DERIVED_FROM","status":"qualified",
            "evidence_refs":[f"https://github.com/{slug}"],
            "provenance":{**receipt,"scope":"Same verified repository slug only, not exact checked-out revision"},
        })
        for rel in item["releases"]:
            # Release records are factual about what GitHub public API listed;
            # they are not proof a downloadable artifact was built or installed.
            rel_key=f"{key}-release-{hashlib.sha256(rel['tag_name'].encode()).hexdigest()[:12]}"
            nodes.append({
                "key":rel_key,"kind":"event","layer":"program",
                "statement":f"GitHub published release {slug} {rel['tag_name']} at {rel['published_at']}",
                "clusters":[cluster],"source_refs":[rel["url"]],
                "tags":["published_release","not_deployment"],
                "provenance":{**receipt,"release_tag":rel["tag_name"],
                    "release_published_at":rel["published_at"],"prerelease":rel["prerelease"],
                    "boundary":"Provider published release metadata; not verified binaries, adoption or production rollout"},
            })
            edges.append({"source":rel_key,"target":snap_key,
              "relation":"DERIVED_FROM","status":"qualified","evidence_refs":[rel["url"]],
              "provenance":{**receipt,"scope":"Release listed in observed provider snapshot"}})
        for tag in item["tags"]:
            tag_key=f"{key}-tag-{hashlib.sha256((tag['name']+tag['sha']).encode()).hexdigest()[:12]}"
            ref=f"https://github.com/{slug}/tags"
            nodes.append({
                "key":tag_key,"kind":"event","layer":"program",
                "statement":f"GitHub tag ref {tag['name']} points to {tag['sha'][:12]} in a sampled provider listing",
                "clusters":[cluster],"source_refs":[ref],
                "tags":["git_ref_not_release","mutable_ref_possible"],
                "provenance":{**receipt,"tag_name":tag["name"],"tag_object_sha":tag["sha"],
                    "boundary":"Tag is not automatically a published release, immutable annotated build, or deployed software"},
            })
            edges.append({"source":tag_key,"target":snap_key,"relation":"DERIVED_FROM",
                          "status":"qualified","evidence_refs":[ref],
                          "provenance":{**receipt,"scope":"Git tag ref listed at collection"}})
        if item["recent_commits"]:
            activity_key=f"{key}-recent-commits-{ident}-{snap_digest[:12]}"
            nodes.append({
                "key":activity_key,"kind":"event","layer":"program",
                "statement":f"GitHub listed {len(item['recent_commits'])} latest default-branch commits for {slug} at {capture}",
                "clusters":[cluster],"source_refs":[f"https://github.com/{slug}/commits/{item['default_branch']}"],
                "tags":["bounded_recent_commit_sample","not_all_activity"],
                "provenance":{**receipt,"recent_commit_samples":item["recent_commits"],
                    "boundary":"At most eight commits listed by provider; not all activity, engineering velocity or completed releases"},
            })
            edges.append({
                "source":activity_key,"target":snap_key,"relation":"DERIVED_FROM","status":"qualified",
                "evidence_refs":[f"https://github.com/{slug}/commits/{item['default_branch']}"],
                "provenance":{**receipt,"scope":"Most recent sampled default branch commits"},
            })
        changes=dependency_diff(repo_root,specs[slug])
        for delta in changes:
            if not (delta["added"] or delta["removed"] or delta["changed"]):
                continue
            delta_key=f"{key}-dependency-{hashlib.sha256((delta['path']+delta['base']+delta['head']).encode()).hexdigest()[:14]}"
            nodes.append({
                "key":delta_key,"kind":"event","layer":"program",
                "statement":(f"Pinned dependency declarations changed in {slug}:{delta['path']}: "
                             f"{len(delta['added'])} added, {len(delta['removed'])} removed, "
                             f"{len(delta['changed'])} specifier changed"),
                "clusters":[cluster],"source_refs":[delta["source_url"]],
                "tags":["pinned_git_dependency_declarations","not_installed_dependency_audit"],
                "provenance":{**receipt,"dependency_diff":delta,
                  "source_verification":"Verified immutable local Git objects at exact base/head revisions",
                  "boundary":delta["boundary"]},
            })
            edges.append({"source":delta_key,"target":rid,"relation":"DERIVED_FROM",
                          "status":"qualified","evidence_refs":[delta["source_url"]],
                          "provenance":{**receipt,"scope":"Actual immutable committed manifest diff, not deployed dependency"}})
        earlier=[(rec,n) for rec,n in prior.get(slug,[])
                 if isinstance(rec.get("observed_at"),str)
                 and rec["observed_at"]<capture and isinstance(rec.get("counters"),dict)]
        if earlier:
            older, oldnode = max(earlier,key=lambda pair:pair[0]["observed_at"])
            a=older["counters"]
            if all(type(a.get(k)) is int for k in ("stars","forks","open_issues")):
                diffs={k:item[k]-a[k] for k in ("stars","forks","open_issues")}
                hist_key=f"{key}-counter-delta-{_hash([older['observed_at'],capture,diffs])[:14]}"
                nodes.append({
                    "key":hist_key,"kind":"comparison","layer":"program",
                    "statement": (f"Two observed GitHub public counter snapshots for {slug}: "
                                  f"stars {diffs['stars']:+d}, forks {diffs['forks']:+d}, "
                                  f"open issues/PRs {diffs['open_issues']:+d}; "
                                  f"not interpretable as adoption or source-engineering quality"),
                    "clusters":[cluster],"source_refs":[f"https://github.com/{slug}"],
                    "tags":["two_observation_counter_difference","not_market_adoption"],
                    "provenance":{**receipt,"previous_observed_at":older["observed_at"],
                        "delta":diffs,"previous_node_id":oldnode["id"],
                        "boundary":"Net provider counter difference over two observations; stars/forks/issues do not measure use, effectiveness or popularity ranking"},
                })
                edges.extend([
                    {"source":hist_key,"target":snap_key,"relation":"COMPARES_WITH",
                     "status":"qualified","provenance":{**receipt,"scope":"Newer provider counter snapshot"}},
                    {"source":hist_key,"target":oldnode["id"],"relation":"COMPARES_WITH",
                     "status":"qualified","provenance":{**receipt,"scope":"Older provider counter snapshot"}},
                ])
        summary.append({
            "repository":slug,"captured_at":capture,"stars":item["stars"],
            "forks":item["forks"],"open_issues":item["open_issues"],
            "latest_releases_returned":len(item["releases"]),
            "latest_tags_returned":len(item["tags"]),
            "recent_commits_returned":len(item["recent_commits"]),
            "declared_dependency_manifest_files_checked":len(changes),
            "manifest_changes_found":sum(bool(d["added"] or d["removed"] or d["changed"]) for d in changes),
        })
    return {
        "schema":"cite_refinery.semantic_graph.v1",
        "source_system":"github_public_signals",
        "clusters":clusters,"nodes":nodes,"edges":edges,
        "conversion_metadata":{
            "schema":"cite_refinery.github_public_signals_import.v1",
            "observed_at":capture,"source_snapshot_digest":snap_digest,
            "sources":summary,"boundary":(
                "Public GitHub provider observations plus locally verified pinned dependency manifests. "
                "No automatic market adoption, causality, security, deployability or successful code execution."
            ),
        },
    }
