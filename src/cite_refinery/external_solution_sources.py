"""Read-only cross-layer discovery of outside research and implementation leads.

External registry records are NEVER scientific evidence, program outcomes,
approved graph edges, or authorization to modify the frozen corpus.
"""
from __future__ import annotations

import json
import hashlib
import re
from typing import Any, Callable
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

OPENAIRE = "https://api.openaire.eu/graph/v4/research-products"
DPG = "https://api.digitalpublicgoods.net/dpgs/"
ECOSYSTEMS = "https://repos.ecosyste.ms/api/v1/repositories/lookup"
USER_AGENT = "CiteRefineryDiscovery/0.1 (https://github.com/Spectating101/cite-refinery)"
REPO = re.compile(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}\Z")
DPG_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def _fetch_json(url: str) -> Any:
    """Only the fixed provider endpoints below are called; never accept a URL from API output."""
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ValueError("external redirect rejected")
    request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with build_opener(NoRedirect()).open(request, timeout=8) as response:
        if "json" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("unexpected non-JSON response")
        raw = response.read(1_048_577)
        if len(raw) > 1_048_576:
            raise ValueError("external response too large")
    return json.loads(raw)


def _candidate(provider: str, identifier: str, label: str, description: str,
               url: str, kind: str, **metadata: Any) -> dict[str, Any]:
    return {
        "provider": provider, "external_id": identifier, "label": label[:250],
        "description": description[:500], "source_url": url,
        "candidate_kind": kind, "metadata": metadata,
        "authority": "navigation_candidate_only", "evidence_layer": None,
        "outcomes_verified": False, "promotion_authorized": False,
    }


def scan(query: str, *, sources: tuple[str, ...] = ("openaire",),
         limit: int = 5, fetch_json: Callable[[str], Any] = _fetch_json) -> dict[str, Any]:
    """Bounded discovery; returning an empty result never means the topic is solved or uncovered."""
    if not isinstance(query, str) or not (2 <= len(query.strip()) <= 120):
        raise ValueError("query must be 2-120 characters")
    if not 1 <= limit <= 20:
        raise ValueError("limit must be 1-20")
    if not sources or any(source not in {"openaire", "dpg"} for source in sources):
        raise ValueError("unsupported discovery provider")
    query = query.strip()
    results: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    for source in dict.fromkeys(sources):
        try:
            if source == "openaire":
                url = OPENAIRE + "?" + urlencode({"search": query, "page_size": limit})
                payload = fetch_json(url)
                rows = payload.get("results") if isinstance(payload, dict) else None
                if not isinstance(rows, list):
                    raise ValueError("invalid OpenAIRE response")
                for row in rows[:limit]:
                    if not isinstance(row, dict):
                        continue
                    rid, label = row.get("id"), row.get("mainTitle")
                    if not isinstance(rid, str) or not rid or len(rid) > 200 or not isinstance(label, str) or not label:
                        continue
                    kind = str(row.get("type") or "research_product")[:70]
                    link = OPENAIRE + "?" + urlencode({"filter": "id:" + rid, "page_size": 1})
                    results.append(_candidate("openaire", rid, label, "", link,
                                              "research_product_metadata", reported_type=kind))
            else:
                payload = fetch_json(DPG)
                if not isinstance(payload, list):
                    raise ValueError("invalid digital public goods response")
                # The DPG API lists the registry. Matching is purely local lexical filtering,
                # not semantic relevance and not a DPG search service.
                words = query.casefold().split()
                for row in payload:
                    if not isinstance(row, dict):
                        continue
                    ident, label = row.get("id"), row.get("name")
                    if not isinstance(ident, str) or not DPG_ID.fullmatch(ident):
                        continue
                    if not isinstance(label, str):
                        continue
                    description = str(row.get("description") or "")
                    haystack = (label + " " + description).casefold()
                    if not all(word in haystack for word in words):
                        continue
                    results.append(_candidate("dpg", ident, label, description,
                                              "https://api.digitalpublicgoods.net/dpg/" + ident + "/",
                                              "reviewed_public_good_listing",
                                              listed_stage=str(row.get("stage") or "")[:64]))
                    if len([x for x in results if x["provider"] == "dpg"]) >= limit:
                        break
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            errors[source] = type(exc).__name__
    return {
        "query": query, "status": "partial" if errors else "complete_fetch",
        "records": results, "provider_errors": errors, "promotion_authorized": False,
        "boundary": "Listings are discovery leads, not independent validation of scientific claims, deployed solutions or program outcomes.",
    }


def lookup_repository(repo: str, *, fetch_json: Callable[[str], Any] = _fetch_json) -> dict[str, Any]:
    """Exact GitHub repository look-up via ecosyste.ms, never free-text or arbitrary URL fetching."""
    if not isinstance(repo, str):
        raise ValueError("repository must be a GitHub owner/repo or canonical URL")
    if repo.startswith("https://"):
        parsed = urlsplit(repo)
        if parsed.netloc.lower() != "github.com" or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError("only canonical GitHub repository URLs are accepted")
        repo = parsed.path.strip("/")
    if not REPO.fullmatch(repo) or ".." in repo or any(part.startswith(".") for part in repo.split("/")):
        raise ValueError("invalid GitHub owner/repository")
    canonical = "https://github.com/" + repo
    url = ECOSYSTEMS + "?" + urlencode({"url": canonical})
    try:
        payload = fetch_json(url)
        if not isinstance(payload, dict) or str(payload.get("full_name") or "").casefold() != repo.casefold():
            raise ValueError("repository metadata mismatch")
        record = _candidate("ecosyste.ms", repo, str(payload.get("full_name")),
                            str(payload.get("description") or ""), canonical,
                            "repository_metadata",
                            stars=payload.get("stargazers_count"),
                            forks=payload.get("forks_count"),
                            archived=payload.get("archived"), license=payload.get("license"),
                            pushed_at=payload.get("pushed_at"), last_synced_at=payload.get("last_synced_at"))
        return {"status": "complete_fetch", "records": [record], "provider_errors": {},
                "promotion_authorized": False}
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return {"status": "partial", "records": [], "provider_errors": {"ecosyste.ms": type(exc).__name__},
                "promotion_authorized": False}


def stage_landscape_packet(module_id: str, module_title: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    """Create neutral review nodes and candidate DISCOVERED_FOR links; no graph mutation."""
    if not module_id or not module_title or not isinstance(records, list) or len(records) > 100:
        raise ValueError("module identity and <=100 candidate records required")
    def key(prefix: str, raw: str) -> str:
        return prefix + "_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:18]
    parent = key("module", module_id)
    nodes = [{"key": parent, "statement": "Investigate " + module_title[:250],
              "layer": "neutral", "kind": "research_question", "clusters": [parent],
              "tags": ["module", "unreviewed"]}]
    edges = []
    seen = set()
    for r in records:
        if not isinstance(r, dict) or r.get("authority") != "navigation_candidate_only" or r.get("evidence_layer") is not None or r.get("promotion_authorized") is not False:
            raise ValueError("refuse to stage source with evidence authority")
        url = r.get("source_url")
        if not isinstance(url, str) or not url.startswith("https://") or len(url) > 2048:
            raise ValueError("only bounded HTTPS source references allowed")
        if url in seen:
            continue
        seen.add(url)
        node = key("external", url)
        nodes.append({"key": node, "statement": "Unverified external lead: " + str(r.get("label") or "")[:250],
                      "layer": "neutral", "kind": "external_discovery_lead", "clusters": [parent],
                      "source_refs": [url],
                      "tags": ["discovery_only", "not_an_evidence_claim", "not_a_validated_solution"],
                      "provenance": {"source_system": str(r.get("provider") or "external")[:80],
                                     "discovered_id": str(r.get("external_id") or "")[:200],
                                     "review_status": "discovery_metadata_only"}})
        edges.append({"source": node, "target": parent, "relation": "DISCOVERED_FOR",
                      "status": "candidate", "evidence_refs": [url],
                      "provenance": {"boundary": "Search relevance only; does not establish a problem or effective implementation."}})
    return {"schema": "cite_refinery.semantic_graph.v1", "source_system": "external-landscape-discovery",
            "clusters": [{"key": parent, "title": module_title[:250], "tags": ["unreviewed"]}],
            "nodes": nodes, "edges": edges, "conversion_metadata": {
                "status": "DISCOVERY_ONLY_NOT_ACCEPTED", "source_leads": len(seen),
                "limitation": "External listing metadata only; no claim entailment, intervention outcome or local deployment verified."}}
