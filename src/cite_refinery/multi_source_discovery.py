"""Atlas multi-source discovery: bounded, provenance-retaining candidate collection.

This is a research-lead collector, NOT a factual verification, endorsement,
legal authority or autonomous development operator. Network reads are opt-in,
restricted to hardcoded provider endpoints and constrained by size/time limits.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCHEMA = "cite_refinery.multisource_discovery.v1"
HEADLESS_SCHEMA = "cite_refinery.headless_records.v1"
CATALOG_SCHEMA = "cite_refinery.discovery_source_catalog.v1"
SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{2,60}$")
REPO_RE = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")
SAFE_TAG_RE = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
MAX_RESULT = 12
MAX_SOURCES = 12
MAX_BYTES = 750_000
MAX_RECORDS = MAX_SOURCES * MAX_RESULT
# All actual HTTP endpoints are constructed internally, never taken from
# upstream text, a JSON catalog, or a caller-supplied URL.
PROVIDERS = {
    "github_signals": ("githubsignals.io", "software"),
    "github_search": ("api.github.com", "software"),
    "openalex": ("api.openalex.org", "research"),
    "crossref": ("api.crossref.org", "research"),
    "npm": ("registry.npmjs.org", "software"),
    "huggingface_models": ("huggingface.co", "models"),
    "huggingface_datasets": ("huggingface.co", "datasets"),
    "pypi_updates": ("pypi.org", "software"),
    "arxiv_ai": ("rss.arxiv.org", "research"),
    "datacite": ("api.datacite.org", "datasets"),
    "zenodo": ("zenodo.org", "datasets"),
    "hackernews": ("hn.algolia.com", "community"),
    "federal_register": ("www.federalregister.gov", "regulation"),
}
SUPPORTED = frozenset(PROVIDERS)
READONLY_NOTE = "candidate_only; external metadata is neither independent validation nor evidence of adoption"
Fetch = Callable[[str], bytes]


class SourceFailure(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_http(url: str) -> bytes:
    p = urllib.parse.urlsplit(url)
    allowed = {host for host, _ in PROVIDERS.values()}
    if p.scheme != "https" or p.hostname not in allowed or p.port is not None or p.username:
        raise SourceFailure("disallowed provider endpoint")
    headers = {"User-Agent": "CiteRefineryAtlasDiscovery/0.1 (research metadata; bounded fetch)",
               "Accept": "application/json, text/csv, application/atom+xml, application/rss+xml"}
    try:
        r = urllib.request.build_opener(NoRedirect).open(
            urllib.request.Request(url, headers=headers, method="GET"), timeout=14
        )
        with r:
            if r.status != 200:
                raise SourceFailure("provider HTTP response not successful")
            data = r.read(MAX_BYTES + 1)
    except (OSError, ValueError) as e:
        raise SourceFailure("provider_fetch_error:" + type(e).__name__) from e
    if len(data) > MAX_BYTES:
        raise SourceFailure("provider content exceeds fetch budget")
    return data


def github_json(endpoint: str) -> dict[str, Any]:
    if not endpoint.startswith("search/repositories?"):
        raise SourceFailure("unsupported GitHub API endpoint")
    try:
        p = subprocess.run(["gh", "api", "--method", "GET", endpoint],
                           capture_output=True, timeout=16, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise SourceFailure("github_cli_unavailable") from e
    if p.returncode or len(p.stdout) > MAX_BYTES:
        raise SourceFailure("github_api_failed_or_oversize")
    try:
        body = json.loads(p.stdout)
    except (ValueError, UnicodeDecodeError) as e:
        raise SourceFailure("invalid_github_json") from e
    if not isinstance(body, dict):
        raise SourceFailure("invalid_github_result")
    return body


def validate_sources(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("invalid discovery manifest")
    rows = data.get("sources")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_SOURCES:
        raise ValueError("select between 1 and 12 bounded sources")
    out = []
    ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid source entry")
        sid = row.get("id")
        provider = row.get("provider")
        query = row.get("query", "")
        tags = row.get("tags")
        targets = row.get("project_targets", [])
        limit = row.get("limit", 8)
        if (not isinstance(sid, str) or not SLUG_RE.fullmatch(sid)
                or sid in ids or provider not in SUPPORTED):
            raise ValueError("source id/provider invalid or duplicated")
        if not isinstance(query, str) or len(query) > 120 or "\n" in query or "\r" in query:
            raise ValueError("query invalid")
        if provider in {"github_search", "openalex", "crossref", "npm", "huggingface_models",
                        "huggingface_datasets", "datacite", "zenodo",
                        "hackernews", "federal_register"} and len(query.strip()) < 3:
            raise ValueError("search sources need a substantive query")
        if type(limit) is not int or not 1 <= limit <= MAX_RESULT:
            raise ValueError("source limit must be 1..12")
        ranking = row.get("ranking", "relevance")
        if provider == "github_search" and ranking not in {"relevance", "recent"}:
            raise ValueError("GitHub search ranking must be relevance or recent")
        if provider != "github_search" and "ranking" in row:
            raise ValueError("ranking only applies to GitHub repository search")
        if (not isinstance(tags, list) or not tags or len(tags) > 8
                or any(not isinstance(t, str) or not SAFE_TAG_RE.fullmatch(t) for t in tags)):
            raise ValueError("source must have specific, safe tags")
        if (not isinstance(targets, list) or len(targets) > 12
                or any(not isinstance(t, str) or not SLUG_RE.fullmatch(t) for t in targets)):
            raise ValueError("invalid project target")
        ids.add(sid)
        out.append({"id": sid, "provider": provider, "query": query.strip(),
                    "limit": limit, "tags": sorted(set(tags)),
                    "project_targets": sorted(set(targets)),
                    "ranking": ranking if provider == "github_search" else None})
    return out


def _json(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise SourceFailure("invalid JSON provider body") from e


def _text(v: Any, maximum: int) -> str:
    return " ".join(str(v or "").split())[:maximum]


def _url(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) > 850:
        return None
    p = urllib.parse.urlsplit(value)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        return None
    return value


def _doi(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    v = value.lower().strip().removeprefix("https://doi.org/")
    return "doi:" + v if re.fullmatch(r"10\.\d{4,9}/\S{2,250}", v) else None


def _record(source: dict[str, Any], identity: str, title: Any, url: Any,
            entity_key: str, *, summary: Any = "", dated: Any = None) -> dict[str, Any] | None:
    where = _url(url)
    allowed_hosts = {
        "github_signals": {"github.com"},
        "github_search": {"github.com"},
        "openalex": {"openalex.org", "doi.org"},
        "crossref": {"doi.org"},
        "datacite": {"doi.org"},
        "zenodo": {"zenodo.org"},
        "hackernews": {"news.ycombinator.com"},
        "federal_register": {"www.federalregister.gov"},
        "npm": {"www.npmjs.com"},
        "huggingface_models": {"huggingface.co"},
        "huggingface_datasets": {"huggingface.co"},
        "pypi_updates": {"pypi.org"},
        "arxiv_ai": {"arxiv.org"},
    }
    if where and urllib.parse.urlsplit(where).hostname not in allowed_hosts[source["provider"]]:
        where = None
    name = _text(title, 250)
    if not where or not name or len(identity) > 200:
        return None
    row = {
        "id": f'{source["id"]}:{identity}',
        "title": name, "source_url": where,
        "tags": source["tags"],
        "project_targets": source["project_targets"],
        "signal": "new_capability" if PROVIDERS[source["provider"]][1] in {"software","models"} else "research_finding",
        "discovery_provider": source["provider"],
        "entity_key": entity_key[:260],
        "evidence_status": "unverified_external_metadata",
        "observation_type": PROVIDERS[source["provider"]][1],
    }
    if summary:
        row["description"] = _text(summary, 450)
    if isinstance(dated, str) and len(dated) <= 40:
        row["provider_date"] = dated
    return row


def collect_provider(source: dict[str, Any], fetch: Fetch = fetch_http,
                     gh: Callable[[str], dict[str, Any]] = github_json) -> list[dict[str, Any]]:
    provider, q, n = source["provider"], source["query"], source["limit"]
    quote = urllib.parse.quote
    rows = []
    if provider == "github_signals":
        raw = fetch("https://githubsignals.io/export.csv")
        for v in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
            slug = v.get("repo_slug", "")
            url = v.get("repo_url", "")
            if not REPO_RE.fullmatch(slug) or url != f"https://github.com/{slug}":
                continue
            searchable = (slug + " " + (v.get("repo_keywords") or "") + " " + (v.get("caption") or "")).lower()
            if q and q.lower() not in searchable:
                continue
            rows.append(_record(source, slug.lower(), slug, url,
                                "github:" + slug.casefold(),
                                summary=v.get("repo_keywords"), dated=v.get("published_at")))
            if len(rows) >= n:
                break
    elif provider == "github_search":
        params = {"q": q, "per_page": n}
        # Explicit opt-in to recent activity; retrieval relevance is the
        # default because updated-time sorting buries foundational tools.
        if source.get("ranking") == "recent":
            params.update(sort="updated", order="desc")
        endpoint = "search/repositories?" + urllib.parse.urlencode(params)
        raw = gh(endpoint)
        for v in raw.get("items", [])[:n]:
            slug = v.get("full_name", "")
            if not isinstance(slug, str) or not REPO_RE.fullmatch(slug):
                continue
            rows.append(_record(source, slug.lower(), slug, v.get("html_url"),
                                "github:" + slug.casefold(),
                                summary=v.get("description"), dated=v.get("pushed_at")))
    elif provider == "openalex":
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode({"search":q, "per_page": n})
        raw = _json(fetch(url))
        for v in raw.get("results", [])[:n]:
            ident = str(v.get("id") or "").rsplit("/", 1)[-1]
            key = _doi(v.get("doi")) or ("openalex:" + ident)
            rows.append(_record(source, ident, v.get("display_name") or v.get("title"),
                                v.get("doi") or v.get("id"), key, dated=v.get("publication_date")))
    elif provider == "crossref":
        url = "https://api.crossref.org/works?" + urllib.parse.urlencode({"query.title":q, "rows": n})
        raw = _json(fetch(url))
        for v in raw.get("message", {}).get("items", [])[:n]:
            doi = v.get("DOI")
            key = _doi(doi)
            if not key:
                continue
            title = v.get("title") or []
            rows.append(_record(source, str(doi).lower(), title[0] if title else "",
                                "https://doi.org/" + doi, key,
                                dated=v.get("published", {}).get("date-parts", [[None]])[0][0]))
    elif provider == "datacite":
        url = "https://api.datacite.org/dois?" + urllib.parse.urlencode({"query":q, "page[size]":n})
        raw = _json(fetch(url))
        for v in raw.get("data", [])[:n]:
            attr = v.get("attributes") or {}
            doi = attr.get("doi") or v.get("id")
            key = _doi(doi)
            titles = attr.get("titles") or []
            title = titles[0].get("title") if titles and isinstance(titles[0], dict) else ""
            if key:
                rows.append(_record(source, key[4:], title, "https://doi.org/" + str(doi),
                                    key, summary=attr.get("publisher"), dated=str(attr.get("publicationYear") or "")))
    elif provider == "zenodo":
        url = "https://zenodo.org/api/records?" + urllib.parse.urlencode({"q":q, "size":n})
        raw = _json(fetch(url))
        for v in (raw.get("hits") or {}).get("hits", [])[:n]:
            ident = str(v.get("id") or "")
            meta = v.get("metadata") or {}
            if not ident.isdigit():
                continue
            doi = meta.get("doi") or v.get("doi")
            key = _doi(doi) or "zenodo:" + ident
            rows.append(_record(source, ident, meta.get("title"),
                                "https://zenodo.org/records/" + ident, key,
                                summary=meta.get("description"), dated=meta.get("publication_date")))
    elif provider == "hackernews":
        url = "https://hn.algolia.com/api/v1/search_by_date?" + urllib.parse.urlencode(
            {"query":q, "tags":"story", "hitsPerPage":n})
        raw = _json(fetch(url))
        for v in raw.get("hits", [])[:n]:
            ident = str(v.get("objectID") or "")
            if ident.isdigit():
                rows.append(_record(source, ident, v.get("title"),
                                    "https://news.ycombinator.com/item?id=" + ident,
                                    "hn:" + ident, dated=v.get("created_at")))
    elif provider == "federal_register":
        url = "https://www.federalregister.gov/api/v1/documents.json?" + urllib.parse.urlencode(
            {"conditions[term]":q, "per_page":n, "order":"newest"})
        raw = _json(fetch(url))
        for v in raw.get("results", [])[:n]:
            ident = v.get("document_number")
            if isinstance(ident, str) and len(ident) < 90:
                rows.append(_record(source, ident, v.get("title"), v.get("html_url"),
                                    "federal_register:" + ident,
                                    summary=v.get("abstract"), dated=v.get("publication_date")))
    elif provider == "npm":
        url = "https://registry.npmjs.org/-/v1/search?" + urllib.parse.urlencode({"text":q, "size":n})
        raw = _json(fetch(url))
        for v in raw.get("objects", [])[:n]:
            p = v.get("package") or {}
            ident = p.get("name", "")
            if not ident or len(ident) > 160:
                continue
            rows.append(_record(source, ident, p.get("name"),
                                "https://www.npmjs.com/package/" + quote(ident, safe="@/"),
                                "npm:" + ident.casefold(), summary=p.get("description"),
                                dated=p.get("date")))
    elif provider in {"huggingface_models", "huggingface_datasets"}:
        kind = "models" if provider == "huggingface_models" else "datasets"
        url = f"https://huggingface.co/api/{kind}?" + urllib.parse.urlencode({"search":q, "limit":n})
        raw = _json(fetch(url))
        for v in raw[:n]:
            ident = v.get("id", "")
            if not ident or len(ident) > 180:
                continue
            rows.append(_record(source, ident, ident,
                                "https://huggingface.co/" + ("datasets/" if kind == "datasets" else "") + quote(ident, safe="/"),
                                "huggingface:" + kind + ":" + ident.casefold(), dated=v.get("lastModified")))
    elif provider in {"pypi_updates", "arxiv_ai"}:
        url = ("https://pypi.org/rss/updates.xml" if provider == "pypi_updates"
               else "https://rss.arxiv.org/atom/cs.AI")
        root = ET.fromstring(fetch(url))
        if provider == "pypi_updates":
            for item in root.findall(".//item")[:n]:
                link = item.findtext("link")
                title = item.findtext("title")
                path = urllib.parse.urlsplit(link or "").path
                package = path.split("/")[2] if path.startswith("/project/") and len(path.split("/")) > 2 else ""
                key = "pypi:" + package.lower() if package else "rss:" + hashlib.sha256((link or "").encode()).hexdigest()[:24]
                rows.append(_record(source, key, title, link, key, dated=item.findtext("pubDate")))
        else:
            atom = "{http://www.w3.org/2005/Atom}"
            for entry in root.findall(f"{atom}entry")[:n]:
                link = next((x.get("href") for x in entry.findall(f"{atom}link") if x.get("rel") in ("alternate",None)), None)
                ident = entry.findtext(f"{atom}id") or ""
                key = "arxiv:" + ident.rsplit("/",1)[-1].lower()
                rows.append(_record(source, key, entry.findtext(f"{atom}title"), link or ident,
                                    key, dated=entry.findtext(f"{atom}updated")))
    # Preserve the first source observation for a stable ID; the same
    # GitHub Signals repository may have been featured more than once.
    unique: dict[str, dict[str, Any]] = {}
    for entry in rows:
        if entry is not None:
            unique.setdefault(entry["id"], entry)
    return list(unique.values())[:n]


def collect(manifest: dict[str, Any], fetch: Fetch = fetch_http,
            gh: Callable[[str], dict[str, Any]] = github_json) -> dict[str, Any]:
    sources = validate_sources(manifest)
    records: list[dict[str, Any]] = []
    outcomes = []
    for source in sources:
        try:
            incoming = collect_provider(source, fetch=fetch, gh=gh)
            existing = {x["id"] for x in records}
            new = [x for x in incoming if x["id"] not in existing]
            records.extend(new)
            outcomes.append({"source": source["id"], "provider": source["provider"],
                             "state": "ok" if new else "empty", "count": len(new)})
        except (ValueError, KeyError, TypeError, UnicodeError, ET.ParseError) as exc:
            outcomes.append({"source": source["id"], "provider": source["provider"],
                             "state": "unavailable", "error_type": type(exc).__name__})
        if len(records) > MAX_RECORDS:
            raise ValueError("result exceeds bounded record limit")
    clusters: dict[str, list[str]] = {}
    for item in records:
        clusters.setdefault(item["entity_key"], []).append(item["id"])
    return {
        "schema": SCHEMA,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "authority": "candidate_only_no_graph_mutation_no_automatic_evidence_promotion",
        "source_results": outcomes, "records": records,
        "same_identity_candidates": [
            {"entity_key": key, "record_ids": ids} for key, ids in sorted(clusters.items()) if len(ids) > 1
        ],
        "caveat": READONLY_NOTE,
    }


def headless_packet(collected: dict[str, Any]) -> dict[str, Any]:
    if collected.get("schema") != SCHEMA:
        raise ValueError("not a discovery collection")
    return {"schema": HEADLESS_SCHEMA, "records": collected["records"]}


def _save(path: Path, value: Any) -> None:
    root = path.resolve().parent
    if any((p / ".git").exists() for p in (root, *root.parents)):
        raise ValueError("discovery output must remain outside any Git working tree")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.exists():
        raise ValueError("output already exists; snapshots are append-only")
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Atlas bounded multi-source discovery collector")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True, help="private directory outside any Git repo")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    collection = collect(manifest)
    output = Path(args.out).expanduser().resolve()
    _save(output / "collection.json", collection)
    _save(output / "headless_records.json", headless_packet(collection))
    print(json.dumps({"sources": collection["source_results"],
                      "record_count": len(collection["records"]),
                      "cross_source_identity_matches": len(collection["same_identity_candidates"]),
                      "output": str(output), "status": "REVIEW_ONLY"}, indent=2))


if __name__ == "__main__":
    main()
