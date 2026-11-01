"""Atlas capability-first review: explicit requirements, conservative match + history.

No model/scoring engine is asked to decide truth. Suggestions are explainable
candidates derived only from provider descriptions and need original-source review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

SCHEMA = "cite_refinery.discovery_capability_review.v1"
REQUIREMENTS_SCHEMA = "cite_refinery.discovery_requirements.v1"
DISCOVERY_SCHEMA = "cite_refinery.multisource_discovery.v1"
ID = re.compile(r"^[a-z][a-z0-9_-]{2,60}$")
MAX_REQS = 12
MAX_TERMS = 12


def _terms(obj: Any, ctx: str) -> list[str]:
    if not isinstance(obj, list) or not 1 <= len(obj) <= MAX_TERMS:
        raise ValueError(ctx + " must have 1..12 terms")
    out = []
    for s in obj:
        if not isinstance(s, str) or not 2 <= len(s) <= 55 or not re.fullmatch(r"[a-z0-9 _-]+", s):
            raise ValueError(ctx + " has invalid term")
        out.append(s)
    return list(dict.fromkeys(out))


def load_requirements(doc: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(doc, dict) or doc.get("schema") != REQUIREMENTS_SCHEMA:
        raise ValueError("invalid requirement schema")
    raw = doc.get("requirements")
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_REQS:
        raise ValueError("1..12 requirements needed")
    seen = set()
    out = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("invalid requirement")
        rid = item["id"]
        if not ID.fullmatch(rid) or rid in seen:
            raise ValueError("invalid/duplicate requirement id")
        seen.add(rid)
        groups = item.get("must_match")
        if not isinstance(groups, list) or not 2 <= len(groups) <= 4:
            raise ValueError("require 2..4 independent mandatory concept groups")
        mandatory = [_terms(g, "must_match") for g in groups]
        optional = _terms(item.get("bonus", ["review"]), "bonus")
        allowed = item.get("allow_source_types")
        if not isinstance(allowed, list) or not allowed or any(x not in (
            "software", "research", "datasets", "models", "community", "regulation"
        ) for x in allowed):
            raise ValueError("invalid accepted source type")
        if not isinstance(item.get("project"), str) or not ID.fullmatch(item["project"]):
            raise ValueError("invalid project id")
        out.append({"id": rid, "project": item["project"],
                    "question": str(item.get("question") or "")[:280],
                    "must_match": mandatory, "bonus": optional,
                    "allow_source_types": allowed})
    return out


def _hits(terms: list[str], text: str) -> list[str]:
    """Whitespace tolerant stem tokens, anchored to a word boundary."""
    found = []
    for term in terms:
        pattern = r"(?<![a-z0-9])" + re.escape(term).replace(r"\ ", r"\s+")
        if re.search(pattern, text):
            found.append(term)
    return found


def match_one(requirement: dict[str, Any], record: dict[str, Any]) -> dict[str, Any] | None:
    if record.get("observation_type") not in requirement["allow_source_types"]:
        return None
    title = str(record.get("title") or "").casefold()
    desc = str(record.get("description") or "").casefold()
    combined = title + " " + desc
    concepts = [_hits(g, combined) for g in requirement["must_match"]]
    if not all(concepts):
        return None
    title_groups = sum(bool(_hits(g, title)) for g in requirement["must_match"])
    bonuses = _hits(requirement["bonus"], combined)
    score = len(concepts) * 10 + title_groups * 5 + min(len(bonuses), 3)
    return {
        "requirement_id": requirement["id"],
        "project": requirement["project"],
        "record_id": record["id"],
        "provider": record["discovery_provider"],
        "entity_key": record["entity_key"],
        "title": record["title"],
        "source_url": record["source_url"],
        "score_for_review_order_only": score,
        "matched_mandatory_concepts": concepts,
        "matched_bonus_terms": bonuses,
        "decision": "SOURCE_REVIEW_NEEDED",
        "reason": "Lexical match to predeclared requirements; NOT demonstrated functionality, evidence reliability or suitability.",
    }


def review(collection: dict[str, Any], req_doc: dict[str, Any],
           *, limit: int = 8) -> dict[str, Any]:
    if collection.get("schema") != DISCOVERY_SCHEMA:
        raise ValueError("invalid collection schema")
    if not isinstance(collection.get("records"), list):
        raise ValueError("collection has no records")
    if not 1 <= limit <= 20:
        raise ValueError("limit must be 1..20")
    requirements = load_requirements(req_doc)
    groups = []
    matched_ids = set()
    for req in requirements:
        results = []
        for r in collection["records"]:
            hit = match_one(req, r)
            if hit:
                results.append(hit)
                matched_ids.add(r["id"])
        results.sort(key=lambda r: (-r["score_for_review_order_only"], r["record_id"]))
        groups.append({"id": req["id"], "project": req["project"], "question": req["question"],
                       "screened": len(collection["records"]),
                       "matched": len(results), "unreviewed": results[:limit]})
    return {
        "schema": SCHEMA, "authority": "READ_ONLY_LEXICAL_TRIAGE_NO_CAPABILITY_ASSERTIONS",
        "requirements": groups,
        "source_collection_outcomes": collection.get("source_results", []),
        "total_records": len(collection["records"]),
        "records_abstained": len(collection["records"]) - len(matched_ids),
        "screening_limits": [
            "Document title and brief provider description only; no original paper/code or actual code execution.",
            "High lexical relevance can still be unrelated to requirements or fundamentally unsound.",
            "Matching different descriptions across providers does not establish independent corroboration.",
            "No matched record is an acceptance decision; unmatched records may contain missed solutions.",
        ],
    }


def _digest(record: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(record, ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":")).encode("utf-8")).hexdigest()


def changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compare retained records; missing != deletion and unsuccessful != empty."""
    if before.get("schema") != DISCOVERY_SCHEMA or after.get("schema") != DISCOVERY_SCHEMA:
        raise ValueError("invalid discovery collection")
    old = {r["id"]: r for r in before.get("records", [])}
    new = {r["id"]: r for r in after.get("records", [])}
    observed = {s["source"]: s["state"] for s in after.get("source_results", [])}
    entries = []
    for ident in sorted(old.keys() | new.keys()):
        if ident not in old:
            status = "new_observation"
        elif ident not in new:
            source_id = ident.split(":", 1)[0]
            status = "not_observed_in_latest_sample" if observed.get(source_id) in {"ok","empty"} else "source_not_compared"
        elif _digest(old[ident]) != _digest(new[ident]):
            status = "revised_observation"
        else:
            continue
        entries.append({"record_id": ident, "status": status,
                        "source_url": (new.get(ident) or old.get(ident))["source_url"]})
    counts: dict[str,int] = defaultdict(int)
    for e in entries:
        counts[e["status"]] += 1
    return {
        "schema": "cite_refinery.discovery_observation_diff.v1",
        "authority": "COMPARATIVE_METADATA_ONLY",
        "counts": dict(counts),
        "changes": entries,
        "caveat": "Missing from latest search/limited sample never proves deletion or upstream removal.",
    }


def main() -> None:
    cli = argparse.ArgumentParser(description="Atlas conservative capability screening")
    cli.add_argument("--collection", required=True)
    cli.add_argument("--requirements", required=True)
    cli.add_argument("--previous", help="optional earlier collection for observation-only comparison")
    cli.add_argument("--out", required=True, help="private directory outside any Git checkout")
    args = cli.parse_args()
    collection = json.loads(Path(args.collection).read_text(encoding="utf-8"))
    req = json.loads(Path(args.requirements).read_text(encoding="utf-8"))
    result = review(collection, req)
    out = Path(args.out).expanduser().resolve()
    from .multi_source_discovery import _save
    _save(out / "capability_review.json", result)
    if args.previous:
        older = json.loads(Path(args.previous).read_text(encoding="utf-8"))
        _save(out / "observation_changes.json", changes(older, collection))
    print(json.dumps({"requirements":len(result["requirements"]),
                      "abstained":result["records_abstained"],"screened":result["total_records"],
                      "matched_per_requirement":{r["id"]:r["matched"] for r in result["requirements"]},
                      "output":str(out)},indent=2))


if __name__ == "__main__":
    main()
