"""Pinned Git portfolio -> Program nodes and bounded historical change observations.

Repo content is read from committed Git objects, never mutable working files.
A module key is explicitly curated by the operator. Shared-topic relationships
are candidates, not proof of capability equivalence or real-world effectiveness.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import quote

SHA = re.compile(r"^[0-9a-f]{40}$")
SLUG = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{2,100}$")
KEY = re.compile(r"^[a-z][a-z0-9_-]{2,80}$")
PATH = re.compile(r"^[A-Za-z0-9_./-]{1,180}$")
ALLOWED = {".md", ".py", ".ts", ".tsx", ".js", ".json", ".yml", ".yaml", ".toml", ".rs", ".sol"}
MAX_BLOB = 262144


def _run(repo: Path, args: list[str], *, limit: int = 500000) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, timeout=18, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Git source read failed or timed out") from exc
    if result.returncode:
        raise ValueError("Pinned Git object, ancestry, or file not accessible")
    if len(result.stdout) > limit:
        raise ValueError("Git source output exceeds safety cap")
    return result.stdout


def _sha(repo: Path, value: str) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError("explicit 40-character commit SHA required")
    if _run(repo, ["cat-file", "-t", value], limit=100).strip() != b"commit":
        raise ValueError("Git pin does not resolve to a commit")
    return value


def _file(repo: Path, sha: str, path: str) -> tuple[str, int]:
    if (not isinstance(path, str) or not PATH.fullmatch(path)
            or path.startswith("/") or ".." in path.split("/")
            or Path(path).suffix.lower() not in ALLOWED
            or any(part.startswith(".") or any(w in part.lower() for w in ("secret", "credential", "token", "password", "private_key"))
                   for part in path.split("/"))):
        raise ValueError("file path outside approved source types")
    raw = _run(repo, ["show", f"{sha}:{path}"], limit=MAX_BLOB)
    try:
        value = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("pinned source file must be UTF-8") from exc
    return value, len(raw)


def _digest(data: Any) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def manifest_to_packet(
    config: dict[str, Any], repo_root: str | Path, *,
    project_state: dict[str, Any] | None = None, project_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(config, dict) or config.get("schema") != "cite_refinery.repository_portfolio.v1":
        raise ValueError("unsupported repository portfolio manifest")
    topics = config.get("topics")
    repos = config.get("repositories")
    if not isinstance(topics, list) or not 1 <= len(topics) <= 30:
        raise ValueError("1..30 explicitly curated topics required")
    if not isinstance(repos, list) or not 1 <= len(repos) <= 15:
        raise ValueError("1..15 repository snapshots required")
    root = Path(repo_root).resolve(strict=True)
    cluster_names: dict[str, str] = {}
    clusters = []
    for item in topics:
        if not isinstance(item, dict):
            raise ValueError("topic must be an object")
        key = item.get("key")
        title = " ".join(str(item.get("title") or "").split())
        if not isinstance(key, str) or not KEY.fullmatch(key) or key in cluster_names:
            raise ValueError("topic keys must be unique and safe")
        if not 5 <= len(title) <= 140:
            raise ValueError("topic title invalid")
        cluster_names[key] = title
        clusters.append({
            "key": key, "title": title, "tags": ["operator_curated_topic"],
            "provenance": {
                "classification": "human_supplied_topic_not_automatically_inferred",
                "boundary": "Shared topic does not prove solutions or shared functionality",
            },
        })
    umbrella = "repository_portfolio"
    if umbrella in cluster_names:
        raise ValueError("repository_portfolio is a reserved module key")
    clusters.insert(0, {
        "key": umbrella, "title": "Repository portfolio and pinned development history",
        "tags": ["portfolio", "history_not_adoption"],
    })
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_repos: set[str] = set()
    per_topic: dict[str, list[tuple[str, str]]] = {k: [] for k in cluster_names}
    source_fact_keys: dict[tuple[str, str], str] = {}
    summary = []
    for rec in repos:
        if not isinstance(rec, dict):
            raise ValueError("repository spec must be object")
        slug, dirname = rec.get("repository"), rec.get("directory")
        if not isinstance(slug, str) or not SLUG.fullmatch(slug) or slug in seen_repos:
            raise ValueError("repository identity invalid or duplicated")
        seen_repos.add(slug)
        if (not isinstance(dirname, str) or not KEY.fullmatch(dirname.lower().replace(".", "-"))):
            raise ValueError("repository directory must be safe relative basename")
        repo = (root / dirname).resolve(strict=True)
        if not repo.is_relative_to(root) or not repo.is_dir():
            raise ValueError("local repository escapes trusted portfolio root")
        permitted_origins = {
            f"https://github.com/{slug}.git", f"https://github.com/{slug}",
            f"git@github.com:{slug}.git",
        }
        origin = _run(repo, ["remote", "get-url", "origin"], limit=4096).decode().strip()
        if origin not in permitted_origins:
            raise ValueError("local repository origin does not match declared owner/repo")
        head = _sha(repo, rec.get("head"))
        base = _sha(repo, rec.get("base"))
        _run(repo, ["merge-base", "--is-ancestor", base, head], limit=10)
        history_count = int(_run(repo, ["rev-list", "--count", f"{base}..{head}"], limit=40).strip())
        if history_count > 300:
            raise ValueError("revision window is too broad")
        changed = [x for x in _run(repo, ["diff", "--name-only", base, head]).decode("utf-8", errors="replace").splitlines() if x]
        if len(changed) > 400:
            raise ValueError("changed-file list too large")
        history = []
        for row in _run(repo, ["log", "--format=%H%x09%cI%x09%s", "--max-count=50", f"{base}..{head}"], limit=50000).decode(errors="replace").splitlines():
            parts = row.split("\t", 2)
            if len(parts) == 3 and SHA.fullmatch(parts[0]):
                history.append({
                    "sha": parts[0], "committed_at": parts[1][:48],
                    "subject": parts[2][:180],
                    "url": f"https://github.com/{slug}/commit/{parts[0]}",
                })
        # Stable and collision-resistant across GitHub owners sharing a repo name.
        shortname = re.sub(r"[^a-z0-9_-]+", "-", slug.lower().replace("/", "-"))[:52]
        root_key = f"repo-{shortname}-{hashlib.sha256(slug.encode()).hexdigest()[:10]}"
        if not KEY.fullmatch(root_key):
            raise ValueError("repo-derived node key invalid")
        repo_url = f"https://github.com/{slug}/tree/{head}"
        nodes.append({
            "key": root_key, "statement": f"Source repository: {slug}",
            "kind": "repository", "layer": "program",
            "clusters": [umbrella], "source_refs": [repo_url],
            "tags": ["pinned_repository_identity", "not_verified_deployment"],
            "provenance": {
                "repository": slug, "snapshot_commit": head, "base_commit": base,
                "origin_verified": True, "verification_scope": "Git repository identity and commit object",
                "boundary": "The presence of a source repository does not prove deployment, use or effectiveness",
            },
        })
        event_key = root_key + "-delta-" + base[:10] + "-" + head[:10]
        nodes.append({
            "key": event_key,
            "statement": f"Git history for {slug}: {history_count} commits and {len(changed)} changed paths between {base[:9]} and {head[:9]}",
            "kind": "event", "layer": "program", "clusters": [umbrella],
            "tags": ["bounded_commit_history", "not_market_adoption", "not_product_readiness"],
            "source_refs": [f"https://github.com/{slug}/compare/{base}...{head}"],
            "provenance": {
                "repository": slug, "base_commit": base, "head_commit": head,
                "commit_count": history_count, "changed_path_count": len(changed),
                "changed_paths_sample": changed[:80], "commit_sample": history,
                "full_history_sample_truncated": history_count > len(history) or len(changed) > 80,
                "boundary": "Historical Git activity only; not growth, adoption, roadmap progress, readiness or effectiveness",
            },
        })
        edges.append({
            "source": event_key, "target": root_key,
            "relation": "DERIVED_FROM", "status": "qualified",
            "evidence_refs": [f"https://github.com/{slug}/compare/{base}...{head}"],
            "provenance": {"basis": "pinned_git_history", "boundary": "This relationship asserts only Git history provenance"},
        })
        facts = rec.get("evidence")
        if not isinstance(facts, list) or not 1 <= len(facts) <= 20:
            raise ValueError("each repo requires 1..20 explicit source-backed facts")
        used: set[str] = set()
        for fact in facts:
            if not isinstance(fact, dict):
                raise ValueError("source fact must be an object")
            label = fact.get("key")
            topic = fact.get("topic")
            if not isinstance(label, str) or not KEY.fullmatch(label) or label in used:
                raise ValueError("fact keys must be unique per repository")
            used.add(label)
            if topic not in cluster_names:
                raise ValueError("fact references unknown semantic topic")
            path = fact.get("path")
            marker = fact.get("needle")
            if not isinstance(marker, str) or not 10 <= len(marker) <= 230:
                raise ValueError("a bounded exact source excerpt is required")
            content, byte_count = _file(repo, head, path)
            if marker not in content:
                raise ValueError(f"pinned evidence excerpt absent: {slug}:{path}:{label}")
            start_line = content[:content.index(marker)].count("\n") + 1
            end_line = start_line + marker.count("\n")
            summary_text = " ".join(str(fact.get("summary") or "").split())
            if not 12 <= len(summary_text) <= 220:
                raise ValueError("source fact summary must be bounded and informative")
            key = root_key + "-" + label + "-" + head[:10]
            source_url = (f"https://github.com/{slug}/blob/{head}/"
                          f"{quote(path, safe='/._-')}#L{start_line}-L{end_line}")
            nodes.append({
                "key": key, "statement": summary_text,
                "kind": "capability", "layer": "program", "clusters": [topic],
                "source_refs": [source_url],
                "tags": ["pinned_repo_source_excerpt", "capability_not_runtime_proven"],
                "provenance": {
                    "repository": slug, "commit": head, "file": path,
                    "line_start": start_line, "line_end": end_line,
                    "exact_excerpt": marker,
                    "source_sha256": hashlib.sha256(content.encode()).hexdigest(),
                    "file_size": byte_count,
                    "verification_scope": "verbatim excerpt in pinned committed file",
                    "boundary": "Text/code presence alone does not prove capability quality, acceptance or live deployment",
                },
            })
            edges.append({
                "source": key, "target": root_key,
                "relation": "DERIVED_FROM", "status": "qualified",
                "evidence_refs": [source_url],
                "provenance": {"boundary": "Evidence anchored to a committed repository file, not proof of operation"},
            })
            per_topic[topic].append((slug, key))
            source_fact_keys[(slug, label)] = key
        summary.append({
            "repository": slug, "head": head, "base": base,
            "commit_count": history_count, "changed_path_count": len(changed),
            "source_fact_count": len(facts),
        })
    candidates = 0
    for topic, pairs in per_topic.items():
        # One bounded link to the first *other repository* in the curated topic.
        for i, (slug, key) in enumerate(pairs):
            previous = next((old_key for old_slug, old_key in pairs[:i] if old_slug != slug), None)
            if previous:
                edges.append({
                    "source": key, "target": previous,
                    "relation": "RELATED_TO", "status": "candidate",
                    "provenance": {
                        "topic": topic, "origin": "operator_curated_shared_topic",
                        "review_state": "not_semantically_verified",
                        "boundary": "Topic grouping alone does not assert equivalence, interoperability, support or adoption",
                    },
                })
                candidates += 1
    # Explicit operator-bounded cross-layer suggestions. Never infer addresses,
    # support, causality, or readiness from repository text or topic membership.
    curated_links = config.get("problem_links", [])
    if not isinstance(curated_links, list) or len(curated_links) > 30:
        raise ValueError("problem_links must be a list of <=30 reviewed proposals")
    if curated_links and (project_state is None or not project_id):
        raise ValueError("explicit existing project state required for cross-layer links")
    used_links: set[tuple[str, str, str]] = set()
    for proposal in curated_links:
        if not isinstance(proposal, dict):
            raise ValueError("cross-layer proposal must be an object")
        identity = (proposal.get("repository"), proposal.get("evidence_key"))
        src_key = source_fact_keys.get(identity)
        if src_key is None:
            raise ValueError("cross-layer proposal source is not a verified pinned repo fact")
        dst = proposal.get("target_node_id")
        relation = proposal.get("relation", "RELATED_TO")
        if relation not in {"RELATED_TO", "ADAPTABLE_TO", "ADDRESSES", "PARTIALLY_ADDRESSES"}:
            raise ValueError("cross-layer proposed relation not allowed")
        rationale = " ".join(str(proposal.get("rationale") or "").split())
        if not 20 <= len(rationale) <= 300:
            raise ValueError("cross-layer proposal must have a bounded rationale")
        target = (project_state or {}).get("semantic_nodes", {}).get(dst)
        if (not isinstance(target, dict) or target.get("project_id") != project_id
                or target.get("layer") not in {"practical", "academic", "neutral"}):
            raise ValueError("cross-layer target does not belong to this project or allowed layers")
        proposal_key = (src_key, str(dst), relation)
        if proposal_key in used_links:
            raise ValueError("duplicate cross-layer proposal")
        used_links.add(proposal_key)
        edges.append({
            "source": src_key, "target": dst,
            "relation": relation, "status": "candidate",
            "provenance": {
                "curator_rationale": rationale,
                "review_state": "proposal_only_not_approved",
                "target_layer": target["layer"],
                "boundary": "Exact target manually nominated; repository docs alone do not establish applicability or effectiveness",
            },
        })
    return {
        "schema": "cite_refinery.semantic_graph.v1",
        "source_system": "repository_portfolio",
        "clusters": clusters, "nodes": nodes, "edges": edges,
        "conversion_metadata": {
            "schema": "cite_refinery.repository_portfolio_snapshot.v1",
            "manifest_digest": _digest(config),
            "repositories": summary, "operator_topics": list(cluster_names),
            "shared_topic_candidate_links": candidates,
            "proposed_cross_layer_links": len(used_links),
            "boundary": "Source-file statements and bounded commit ranges, not software execution, product readiness or market adoption",
        },
    }
