"""Read-only, evidence-bounded discovery from external topic graphs.

External search hits are *candidate navigation records*, never Practical/
Academic/Program evidence or qualified semantic edges.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

WIKIDATA = "https://www.wikidata.org/w/api.php"
OPENALEX = "https://api.openalex.org/topics"
USER_AGENT = "CiteRefineryExternalDiscovery/0.1 (https://github.com/Spectating101/cite-refinery)"
QID = re.compile(r"Q[1-9][0-9]*\Z")
TOPIC_ID = re.compile(r"T[1-9][0-9]*\Z")

def _read_json(url: str) -> Any:
    # Both URLs are hardcoded; inputs only enter URL-encoded query parameters.
    req = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    # Refuse redirects before any second destination can be fetched.
    class RejectRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ValueError("external API redirect refused")
    with build_opener(RejectRedirect()).open(req, timeout=8) as response:
        if "json" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("external endpoint returned non-JSON")
        raw = response.read(262145)
        if len(raw) > 262144:
            raise ValueError("oversize external response")
    return json.loads(raw)

def discover(
    query: str,
    *,
    sources: tuple[str, ...] = ("wikidata",),
    limit: int = 5,
    fetch_json: Callable[[str], Any] = _read_json,
) -> dict[str, Any]:
    if not isinstance(query, str) or not (2 <= len(query.strip()) <= 120):
        raise ValueError("query must be 2-120 characters")
    if not 1 <= limit <= 10:
        raise ValueError("limit must be 1-10")
    if not sources or any(s not in {"wikidata", "openalex"} for s in sources):
        raise ValueError("unsupported source")
    query = query.strip()
    hits: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    for source in dict.fromkeys(sources):
        try:
            if source == "wikidata":
                url = WIKIDATA + "?" + urlencode({"action": "wbsearchentities", "search": query, "language": "en", "format": "json", "limit": limit})
                payload = fetch_json(url)
                rows = payload.get("search", [])
                if not isinstance(rows, list):
                    raise ValueError("invalid Wikidata result")
                for row in rows[:limit]:
                    if not isinstance(row, dict) or not QID.fullmatch(str(row.get("id", ""))):
                        continue
                    qid = row["id"]
                    hits.append({"provider": source, "external_id": qid,
                                 "label": str(row.get("label") or "")[:200],
                                 "description": str(row.get("description") or "")[:500],
                                 "source_url": "https://www.wikidata.org/wiki/" + qid,
                                 "authority": "navigation_candidate_only", "evidence_layer": None})
            else:
                url = OPENALEX + "?" + urlencode({"search": query, "per-page": limit})
                payload = fetch_json(url)
                rows = payload.get("results", [])
                if not isinstance(rows, list):
                    raise ValueError("invalid OpenAlex result")
                for row in rows[:limit]:
                    if not isinstance(row, dict):
                        continue
                    raw_id = str(row.get("id") or "").split("/")[-1]
                    if not TOPIC_ID.fullmatch(raw_id):
                        continue
                    hits.append({"provider": source, "external_id": raw_id,
                                 "label": str(row.get("display_name") or "")[:200],
                                 "description": str(row.get("description") or "")[:500],
                                 "source_url": "https://openalex.org/" + raw_id,
                                 "authority": "navigation_candidate_only", "evidence_layer": None})
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            # A rate-limited provider cannot silently turn a partial result into a complete map.
            errors[source] = type(exc).__name__
    return {"query": query, "status": "partial" if errors else "complete_fetch",
            "records": hits, "provider_errors": errors, "promotion_authorized": False,
            "boundary": "Topic labels are discovery leads, not verified claims, evidence edges, or solved problems."}
