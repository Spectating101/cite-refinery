"""Reuse established science/ORKG discovery rather than duplicating their graphs.

All results are NAVIGATION LEADS only. No new corpus insertion, authority
promotion, acceptance of scientific claims, code execution, or graph mutation.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import json
import re
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.error import HTTPError

from .external_solution_sources import _candidate, _fetch_json, stage_landscape_packet

SCIENCE = "https://science.ecosyste.ms/api/v1"
ORKG = "https://orkg.org/api"
DOI = re.compile(r"10\.\d{4,9}/[^\s<>\"']{1,160}", re.IGNORECASE)
RESOURCE = re.compile(r"R[1-9]\d{0,16}\Z")
SOURCE_LIMIT = 20
_FTM_MAX_BYTES = 2_000_000


def _query(value: str, *, min_length: int = 3) -> str:
    if not isinstance(value, str) or not (min_length <= len(value.strip()) <= 120):
        raise ValueError("Provider query must have 3-120 characters")
    return value.strip()


def _limit(value: int) -> int:
    if type(value) is not int or not (1 <= value <= SOURCE_LIMIT):
        raise ValueError("1-20 records per provider required")
    return value


def _short(v: Any, cap: int = 250) -> str:
    return " ".join(str(v or "").split())[:cap]


def _doi(value: Any) -> str | None:
    if isinstance(value, list):
        value = next((x for x in value if isinstance(x, str) and x), None)
    if not isinstance(value, str):
        return None
    # Never infer validity or existence from a metadata DOI.
    found = DOI.search(value)
    return found.group(0).lower().rstrip(".,;)") if found else None


def _repo_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    from urllib.parse import urlsplit
    p = urlsplit(value)
    if (p.scheme != "https" or p.netloc.lower() != "github.com"
            or p.query or p.fragment or p.username or p.password):
        return None
    parts = p.path.strip("/").split("/")
    if (len(parts) != 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", x)
                                  for x in parts) or
            any(x.startswith(".") or ".." in x for x in parts)):
        return None
    return "https://github.com/" + "/".join(parts)


def science_software(query: str, *, limit: int = 8, after_id: int = 0,
                     fetch_json: Callable[[str], Any] = _fetch_json,
                     exact_kind: str | None = None) -> dict:
    """Search source Science index (literal names), or look up exact identity.

    The Science public API may return HTTP 404 if routes are not deployed.
    Treat that as PROVIDER UNAVAILABLE, never 'there is no scientific software'.
    """
    q = _query(query, min_length=1 if exact_kind else 3)
    _limit(limit)
    if type(after_id) is not int or after_id < 0:
        raise ValueError("Bad after_id cursor")
    if exact_kind is not None and exact_kind not in (
            "name", "doi", "repository_url", "homepage_url", "purl"):
        raise ValueError("Unsupported exact identifier kind")
    action = "lookup" if exact_kind else "search"
    args = {"q": q, "limit": limit, "after_id": after_id}
    if exact_kind:
        args["kind"] = exact_kind
    url = SCIENCE + "/software/" + action + "?" + urlencode(args)
    payload = fetch_json(url)
    if not isinstance(payload, dict) or not isinstance(payload.get("projects"), list):
        raise ValueError("Unexpected Science software response")
    rows = payload["projects"]
    if len(rows) > limit or not all(isinstance(p, dict) and
                                   type(p.get("project_id")) is int and
                                   p["project_id"] > 0 for p in rows):
        raise ValueError("Invalid Science project identities or page size")
    cursor = payload.get("next_after_id")
    if cursor is not None and (type(cursor) is not int or cursor <= after_id):
        raise ValueError("Invalid Science pagination cursor")
    leads = []
    for row in rows:
        pid = row["project_id"]
        repo = _repo_url(row.get("repository_url"))
        description = _short(row.get("description") or row.get("summary"), 500)
        name = _short(row.get("name") or row.get("project_name") or repo or
                      "Scientific software project " + str(pid))
        # Source entry intentionally points to the provider's identity-bearing
        # API resource, not a possibly false GitHub identity.
        leads.append(_candidate(
            "ecosyste.ms Science", "science-project:" + str(pid), name, description,
            SCIENCE + "/projects/" + str(pid) + "/search_context",
            "scientific_software_metadata",
            candidate_repository_url=repo,
            science_project_id=pid,
            reported_match_evidence=row.get("matches"),
            reported_science_score=row.get("science_score"),
            reported_fields=row.get("fields"),
            provider_license="CC-BY-SA-4.0",
            search_type="literal_substring" if not exact_kind else "exact_identifier",
            no_independently_verified_original_code=True,
        ))
    return {
        "provider": "ecosyste.ms Science",
        "provider_url": url,
        "records": leads, "next_after_id": cursor,
        "is_semantic_search": False, "promotion_authorized": False,
        "license_review_required_before_republishing_data": True,
        "note": "Project metadata, name matches and scores are not working software or proof of scientific merit.",
    }


def _fetch_orkg_v2(url: str) -> Any:
    """ORKG papers V2 explicitly requires its media type, not generic JSON.

    Generic Accept: application/json selects the separate LegacyPaperController,
    where only linked_to/linkedTo GET parameters are accepted. The v2
    controller produces application/vnd.orkg.paper.v2+json.
    """
    from urllib.parse import urlsplit
    from urllib.request import Request, HTTPRedirectHandler, build_opener
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != "orkg.org"
            or parsed.port is not None or parsed.username or parsed.password
            or parsed.path != "/api/papers" or parsed.fragment):
        raise ValueError("Only original ORKG v2 paper-search URL is permitted")
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ValueError("ORKG source redirected")
    req = Request(url, headers={
        "Accept": "application/vnd.orkg.paper.v2+json",
        "User-Agent": "CiteRefineryDiscovery/0.1"})
    with build_opener(NoRedirect()).open(req, timeout=9) as response:
        if response.status != 200 or "json" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("ORKG v2 response is not JSON HTTP 200")
        data = response.read(1_048_577)
        if len(data) > 1_048_576:
            raise ValueError("ORKG response exceeds bound")
    return json.loads(data)


def orkg_papers(title: str, *, limit: int = 8, fetch_json: Callable[[str], Any] = _fetch_orkg_v2) -> dict:
    """Read-only scholarly paper metadata from ORKG; not verified findings."""
    q = _query(title)
    _limit(limit)
    url = ORKG + "/papers?" + urlencode({"title": q, "page": 0, "size": limit})
    payload = fetch_json(url)
    if isinstance(payload, dict):
        if isinstance(payload.get("content"), list):
            rows = payload["content"]
        elif isinstance(payload.get("items"), list):
            rows = payload["items"]
        else:
            raise ValueError("Unknown ORKG page response")
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError("Unknown ORKG response")
    if len(rows) > limit:
        raise ValueError("ORKG returned oversized result page")
    leads = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        rid, label = row.get("id"), row.get("title") or row.get("label")
        if not isinstance(rid, str) or not RESOURCE.fullmatch(rid):
            continue
        if not isinstance(label, str) or not label.strip():
            continue
        identifiers = row.get("identifiers") or {}
        doi = _doi(identifiers.get("doi")) if isinstance(identifiers, dict) else None
        info = row.get("publication_info") or {}
        if not isinstance(info, dict):
            info = {}
        leads.append(_candidate(
            "ORKG", "orkg-paper:" + rid, _short(label), "",
            "https://orkg.org/paper/" + rid, "structured_research_paper_metadata",
            doi=doi,
            publication_year=info.get("published_year"),
            orkg_resource_id=rid,
            orkg_verified_flag=row.get("verified"),
            orkg_extraction_method=row.get("extraction_method"),
            semantic_finding_independently_verified=False,
        ))
    return {
        "provider": "ORKG", "provider_url": url, "records": leads,
        "promotion_authorized": False,
        "note": "A structured ORKG record or ORKG verified flag is not independent article entailment.",
    }


def ftm_preview(path: str | Path, *, dataset_id: str, max_entities: int = 100) -> dict:
    """Safely *summarize* a user-supplied public FollowTheMoney JSON export.

    No names, person properties or document contents leave the local machine.
    No entities are imported or connected to the Practical map.
    """
    if not isinstance(dataset_id, str) or not re.fullmatch(
            r"[a-zA-Z][a-zA-Z0-9_-]{2,63}", dataset_id):
        raise ValueError("Dataset identifier required for manual investigative provenance")
    if type(max_entities) is not int or not 1 <= max_entities <= 100:
        raise ValueError("max_entities must be 1-100")
    p = Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size > _FTM_MAX_BYTES:
        raise ValueError("Missing or oversized FTM export")
    raw = p.read_bytes()
    # Accept JSON list or a {"entities": [...]} export. Reject extra arbitrary
    # formats rather than trying to interpret confidential arbitrary files.
    data = json.loads(raw)
    if isinstance(data, dict):
        data = data.get("entities")
    if not isinstance(data, list) or len(data) > max_entities:
        raise ValueError("Expected bounded FTM entity list")
    counts: dict[str, int] = defaultdict(int)
    for x in data:
        if not isinstance(x, dict) or not isinstance(x.get("schema"), str):
            raise ValueError("Malformed FTM entity")
        if (not isinstance(x.get("id"), str) or
                not (1 <= len(x["id"]) <= 200) or
                not isinstance(x.get("properties", {}), dict)):
            raise ValueError("Invalid FTM identity or properties")
        counts[x["schema"][:90]] += 1
    return {
        "schema": "cite_refinery.ftm_local_review_only.v1",
        "source_format": "FollowTheMoney-compatible entity JSON, not an authenticated source validation",
        "dataset_id": dataset_id, "bytes_sha256": sha256(raw).hexdigest(),
        "entity_count": len(data), "entity_schema_counts": dict(sorted(counts.items())),
        "private_entity_names_or_properties_exported": False,
        "requires_dedicated_nocturnal_authorization": True,
        "records_imported": 0, "promotion_authorized": False,
        "no_corpus_or_graph_mutation": True,
    }


def consolidate_discovery(query: str, sources: tuple[str, ...] = ("science", "orkg"),
                          *, limit: int = 6,
                          fetch_json: Callable[[str], Any] = _fetch_json,
                          module_id: str | None = None, module_title: str | None = None) -> dict:
    """One read-only review queue; retains every provider's independent claims."""
    q = _query(query)
    _limit(limit)
    if not sources or len(sources) != len(set(sources)) or any(
            x not in {"science", "orkg"} for x in sources):
        raise ValueError("Select one or both supported read-only sources")
    if bool(module_id) != bool(module_title):
        raise ValueError("Module ID and title must be supplied together")
    records, errors, receipts = [], {}, []
    for provider in sources:
        try:
            packet = (science_software(q, limit=limit, fetch_json=fetch_json)
                      if provider == "science" else
                      orkg_papers(q, limit=limit, fetch_json=fetch_json))
            records.extend(packet["records"])
            receipts.append({"provider": packet["provider"],
                             "query_url": packet["provider_url"],
                             "candidate_count": len(packet["records"])})
        except (OSError, TimeoutError, ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
            # API 404, outage, malformed payload: unknown, NOT an empty graph.
            errors[provider] = ("HTTP_" + str(e.code) if isinstance(e, HTTPError)
                                else type(e).__name__)
    review = {
        "schema": "cite_refinery.external_oss_consolidation.v1",
        "query": q, "providers_requested": list(sources),
        "status": "partial" if errors else "retrieval_complete_not_verified",
        "records": records, "provider_receipts": receipts,
        "provider_errors": errors,
        "review_class": "navigation_candidates_only",
        "independent_answer_quality_evaluation": False,
        "external_software_verified_operational": False,
        "accepted_claim_edges": 0, "promotion_authorized": False,
        "no_frozen_holdout_access_or_graph_mutation": True,
        "note": "Separate provider snapshots; not one corroborated cross-layer scientific relationship.",
    }
    if module_id is not None:
        review["candidate_packet"] = stage_landscape_packet(module_id, module_title, records)
    return review
