"""Restricted GitHub observations for authorized local private-project research.

Sanitized provider metadata only, source-linked in a tenant-scoped Program
module. No commit messages, issue bodies, actors or raw provider payloads.
"""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .github_signals import _github, _datetime, _count, _hash, _release_url, dependency_diff
from .repository_trend_bridge import SLUG

SCHEMA = "cite_refinery.github_private_signals.v1"
BOUNDARY = ("Restricted private GitHub metadata. Provider counters, sampled refs and "
            "declared dependencies do not establish adoption, effectiveness or readiness.")


def collect_private(repositories: list[str]) -> dict[str, Any]:
    if not isinstance(repositories,list) or not 1 <= len(repositories) <= 8 or len(set(repositories)) != len(repositories):
        raise ValueError("select 1..8 distinct private repositories")
    rows=[]
    for slug in repositories:
        if not isinstance(slug,str) or not SLUG.fullmatch(slug):
            raise ValueError("invalid selected repository")
        meta=_github(slug,"")
        if meta.get("full_name")!=slug or meta.get("private") is not True or type(meta.get("archived")) is not bool:
            raise ValueError("GitHub identity or verified private visibility mismatch")
        releases=_github(slug,"/releases?per_page=8")
        tags=_github(slug,"/tags?per_page=12")
        commits=_github(slug,"/commits?per_page=8")
        if not all(isinstance(x,list) for x in (releases,tags,commits)):
            raise ValueError("malformed private provider response")
        rows.append({
            "repository":slug, "visibility":"private", "archived":meta["archived"],
            "default_branch":meta["default_branch"],
            "stars":meta["stargazers_count"],"forks":meta["forks_count"],
            "open_issues":meta["open_issues_count"],"pushed_at":meta.get("pushed_at"),
            "releases":[{"tag_name":x["tag_name"],"published_at":x["published_at"],
                         "prerelease":x["prerelease"],"url":x["html_url"]}
                        for x in releases[:8] if x.get("draft") is False],
            "tags":[{"name":x["name"],"sha":x["commit"]["sha"]} for x in tags[:12]],
            "recent_commits":[{"sha":x["sha"],"committed_at":x["commit"]["committer"]["date"]}
                              for x in commits[:8]],
        })
    snapshot={
        "schema":SCHEMA, "observed_at":datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "access_scope":"restricted_local_private_workspace", "observations":rows,
        "boundary":BOUNDARY,
    }
    validate_private(snapshot)
    return snapshot


def validate_private(snapshot: dict[str, Any]) -> None:
    if not isinstance(snapshot,dict) or snapshot.get("schema")!=SCHEMA or snapshot.get("access_scope")!="restricted_local_private_workspace":
        raise ValueError("restricted private snapshot schema required")
    _datetime(snapshot.get("observed_at"))
    rows=snapshot.get("observations")
    if not isinstance(rows,list) or not 1 <= len(rows) <= 8:
        raise ValueError("restricted observations missing")
    seen=set()
    for row in rows:
        slug=row.get("repository")
        if not isinstance(slug,str) or not SLUG.fullmatch(slug) or slug in seen:
            raise ValueError("invalid or duplicate private repository")
        seen.add(slug)
        if row.get("visibility")!="private" or type(row.get("archived")) is not bool:
            raise ValueError("private visibility must be explicit")
        if not isinstance(row.get("default_branch"),str) or not 1 <= len(row["default_branch"]) <= 180:
            raise ValueError("invalid private default branch")
        for key in ("stars","forks","open_issues"):
            _count(row.get(key),key)
        if row.get("pushed_at") is not None:_datetime(row["pushed_at"])
        for k,limit in (("releases",8),("tags",12),("recent_commits",8)):
            if not isinstance(row.get(k),list) or len(row[k])>limit:
                raise ValueError("private source sample malformed")
        for rel in row["releases"]:
            if (not isinstance(rel.get("tag_name"),str) or len(rel["tag_name"])>180
                    or type(rel.get("prerelease")) is not bool):
                raise ValueError("invalid published release sample")
            _datetime(rel.get("published_at"));_release_url(slug,rel.get("url"))
        for tag in row["tags"]:
            if (not isinstance(tag.get("name"),str) or len(tag["name"])>180
                    or not isinstance(tag.get("sha"),str) or len(tag["sha"])!=40
                    or any(c not in "0123456789abcdef" for c in tag["sha"])):
                raise ValueError("invalid private Git tag sample")
        for commit in row["recent_commits"]:
            sha=commit.get("sha")
            if not isinstance(sha,str) or len(sha)!=40 or any(c not in "0123456789abcdef" for c in sha):
                raise ValueError("invalid private commit sample")
            _datetime(commit.get("committed_at"))


def private_to_packet(snapshot: dict[str, Any], *, project_state: dict[str,Any],
                      project_id: str, manifest: dict[str,Any],
                      repo_root: str | Path) -> dict[str,Any]:
    """One restricted module per verified repository; no public source downgrade."""
    validate_private(snapshot)
    if project_id not in project_state.get("projects",{}):
        raise ValueError("existing authorized private project required")
    if manifest.get("schema")!="cite_refinery.repository_portfolio.v1":
        raise ValueError("source-pinned portfolio manifest required")
    specs=manifest.get("repositories",[])
    declared={x["repository"]:x for x in specs}
    if len(declared)!=len(specs):
        raise ValueError("duplicate declared repositories")
    verified={};older={}
    for n in project_state.get("semantic_nodes",{}).values():
        if n.get("project_id")!=project_id or n.get("layer")!="program":continue
        for rec in n.get("provenance_receipts") or []:
            if not isinstance(rec,dict):continue
            if (n.get("kind")=="repository" and rec.get("source_system")=="repository_portfolio"
                and rec.get("origin_verified") is True):
                verified.setdefault(rec.get("repository"),[]).append(n)
            if (n.get("kind")=="event" and rec.get("source_system")=="github_private_signals"
                and rec.get("observation_role")=="private_counter_snapshot"):
                older.setdefault(rec.get("repository"),[]).append((rec,n))
    clusters=[];nodes=[];edges=[];summary=[]
    cap=snapshot["observed_at"]
    digest=_hash(snapshot)
    for row in snapshot["observations"]:
        slug=row["repository"]
        if slug not in declared or len(verified.get(slug,[]))!=1:
            raise ValueError("restricted repo must have one verified same-project Git identity")
        rid=verified[slug][0]["id"]
        key="private-gh-"+hashlib.sha256(slug.encode()).hexdigest()[:14]
        topic=key+"-module"
        rev=hashlib.sha256((cap+digest).encode()).hexdigest()[:16]
        link=f"https://github.com/{slug}"
        clusters.append({"key":topic,"title":f"Restricted GitHub repository observations: {slug}",
                         "tags":["private_observation","not_market_adoption"],
                         "provenance":{"repository":slug,"access_scope":"restricted_local_private_workspace",
                                       "public_redistribution_allowed":False,"boundary":BOUNDARY}})
        receipt={"repository":slug,"observed_at":cap,"snapshot_digest":digest,
                 "access_scope":"restricted_local_private_workspace",
                 "public_redistribution_allowed":False,"boundary":BOUNDARY}
        def node(suffix,kind,statement,provenance,refs=None,tags=None):
            ident=f"{key}-{suffix}"
            nodes.append({"key":ident,"kind":kind,"layer":"program",
                          "statement":statement,"clusters":[topic],
                          "tags":["restricted_source",*(tags or [])],
                          "source_refs":refs or [link],"provenance":{**receipt,**provenance}})
            return ident
        def edge(src,dst,relation="DERIVED_FROM",refs=None):
            edges.append({"source":src,"target":dst,"relation":relation,
                          "status":"qualified","evidence_refs":refs or [link],
                          "provenance":{**receipt,"scope":"Restricted provider/source identity only"}})
        snap_id=node("snapshot-"+rev,"event",
            f"Restricted GitHub observation of {slug} on {cap}; provider counters and sampled activity",
            {"observation_role":"private_counter_snapshot",
             "counters":{k:row[k] for k in ("stars","forks","open_issues")},
             "pushed_at":row["pushed_at"],"archived":row["archived"],
             "boundary":"Two snapshots needed for net counter comparison; not adoption"})
        edge(snap_id,rid)
        for field in ("releases","tags","recent_commits"):
            if not row[field]:continue
            event=node(field+"-"+rev,"event",
                f"Private {slug}: {len(row[field])} sampled {field.replace('_',' ')} at {cap}",
                {"observation_role":"private_sample_"+field,"sample":row[field],
                 "boundary":"Bounded sanitized GitHub sample; not a complete repository history"},
                tags=["not_deployed_artifact"])
            edge(event,snap_id)
        changes=dependency_diff(repo_root,declared[slug])
        for diff in changes:
            if not (diff["added"] or diff["removed"] or diff["changed"]):continue
            stable=hashlib.sha256((diff["path"]+diff["base"]+diff["head"]).encode()).hexdigest()[:14]
            event=node("dependency-"+stable,"event",
                f"Restricted pinned dependency declarations changed: {slug}/{diff['path']}",
                {"dependency_diff":diff,
                 "boundary":"Verified Git manifest strings; not lockfile, transitive or runtime validation"},
                refs=[diff["source_url"]])
            edge(event,rid,refs=[diff["source_url"]])
        prev=[(a,n) for a,n in older.get(slug,[])
              if isinstance(a.get("observed_at"),str) and a["observed_at"]<cap
              and isinstance(a.get("counters"),dict)]
        if prev:
            old,previous=max(prev,key=lambda p:p[0]["observed_at"])
            if all(type(old["counters"].get(k)) is int for k in ("stars","forks","open_issues")):
                delta={k:row[k]-old["counters"][k] for k in ("stars","forks","open_issues")}
                comparison=node("comparison-"+rev,"comparison",
                    f"Two restricted observations of {slug}: provider-counter differences only, not adoption",
                    {"observation_role":"private_counter_comparison","delta":delta,
                     "previous_observed_at":old["observed_at"],
                     "boundary":"Net provider counters over two readings are not user adoption or quality"})
                edge(comparison,snap_id,"COMPARES_WITH")
                edge(comparison,previous["id"],"COMPARES_WITH")
        summary.append({"repository":slug,"observed_at":cap,
                        "releases_sampled":len(row["releases"]),
                        "tags_sampled":len(row["tags"]),
                        "commits_sampled":len(row["recent_commits"]),
                        "manifest_paths_checked":len(changes),
                        "changed_paths":sum(bool(x["added"] or x["removed"] or x["changed"]) for x in changes)})
    return {"schema":"cite_refinery.semantic_graph.v1","source_system":"github_private_signals",
            "clusters":clusters,"nodes":nodes,"edges":edges,
            "conversion_metadata":{"source_schema":SCHEMA,"observed_at":cap,
                                   "access_scope":"restricted_local_private_workspace",
                                   "public_redistribution_allowed":False,
                                   "snapshot_digest":digest,"summary":summary,"boundary":BOUNDARY}}
