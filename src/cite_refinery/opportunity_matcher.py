"""AI-assisted problem → existing repository capability matching.

Inherits the same evidence-status discipline as Cite-Refinery's cross-layer
candidate reasoner. The model can propose relevance and technical next tests,
not license rights, funding, buyer interest or performance conclusions.
"""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlsplit

SCHEMA = "cite_refinery.opportunity_match_input.v1"
FITS = {"direct_documented", "adaptation_hypothesis", "not_fit"}
_NEGATIVE_CAPABILITY = re.compile(
    r"\b(?:lacks?\s+|zero native\s+|total absence\b|no native\s+|does not provide\s+)", re.I)
_FORBIDDEN = re.compile(
    r"\b(?:proves?|guarantees?|definitively(?: solves?| achieves?)|"
    r"commercially validated|confirmed buyer|paid contract confirmed|"
    r"directly implements? the research)\b", re.I)


def _ref(value: str) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("invalid candidate source URL")
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
        raise ValueError("source reference must be HTTPS")
    return value


def _statement(value: Any) -> str:
    if not isinstance(value, str) or not 15 <= len(value.strip()) <= 1200:
        raise ValueError("candidate statement must be 15-1200 chars")
    if _FORBIDDEN.search(value):
        raise ValueError("unearned commercial or scientific certainty")
    return " ".join(value.split())


def validate_input(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("invalid matching input schema")
    probs = data.get("problems")
    repos = data.get("repositories")
    if not isinstance(probs, list) or not 1 <= len(probs) <= 12:
        raise ValueError("1-12 problem inputs required")
    if not isinstance(repos, list) or not 1 <= len(repos) <= 20:
        raise ValueError("1-20 repository candidates required")
    seen = set()
    for item in probs + repos:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not re.fullmatch("[a-z][a-z0-9_-]{2,70}", item["id"]):
            raise ValueError("stable candidate IDs required")
        if item["id"] in seen:
            raise ValueError("duplicate candidate ID")
        seen.add(item["id"])
        key = "need" if item in probs else "capability"
        _statement(item.get(key))
        _ref(item.get("source_url"))
        if item in repos and item.get("license") not in {"copyleft", "permissive", "unknown"}:
            raise ValueError("repository licensing signal required")
        if item in probs and item.get("evidence_status") not in {"reviewed", "model_candidate", "reported"}:
            raise ValueError("problem claim status required")
    return data


def matching_prompt(data: dict[str, Any]) -> str:
    validate_input(data)
    return (
        "You are Cite-Refinery's OPPORTUNITY MATCHING reasoner. Given bounded and attributed "
        "real-world problems and technical repository capability descriptions, identify "
        "*potential* solution fits. Evaluate mechanisms and actual workflow functions, "
        "not topical co-occurrence. Avoid forcing three-layer completeness. Distinguish "
        "direct documented capability from substantial adaptation and from a wrong fit. "
        "Report what the source materials fail to establish, including operational "
        "deployment, economics, license rights and paid customer demand. Treat all "
        "repository descriptions as developer-authored claims, not deployment proof. "
        "Choose up to 6 useful pairs; include a NOT_FIT pair if that prevents a "
        "misleading conversion effort. Do not assume the maintainer is interested "
        "in commercial partnership. Return ONLY JSON: "
        '{"matches":[{"problem_id":"exact ID","repository_id":"exact ID",'
        '"fit":"direct_documented|adaptation_hypothesis|not_fit",'
        '"mechanism":"technical workflow or mismatch reasoning",'
        '"limitation":"what this connection does not establish",'
        '"next_test":"single low-cost falsifying test"}],'
        '"boundary":"source bounded, unverified buyers and rights"}'
        " INPUT:\n" + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    )


def inspect_matches(data: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    validate_input(data)
    if not isinstance(answer, dict) or not isinstance(answer.get("matches"), list) or len(answer["matches"]) > 6:
        raise ValueError("model must provide at most six matches")
    problems = {p["id"]: p for p in data["problems"]}
    repos = {r["id"]: r for r in data["repositories"]}
    results, rejects, seen = [], [], set()
    for idx, m in enumerate(answer["matches"]):
        try:
            if not isinstance(m, dict) or m.get("problem_id") not in problems or m.get("repository_id") not in repos:
                raise ValueError("unknown problem/repository identity")
            if m.get("fit") not in FITS:
                raise ValueError("unknown match class")
            key = (m["problem_id"], m["repository_id"])
            if key in seen:
                raise ValueError("duplicate problem/repository pair")
            seen.add(key)
            explanation = {k: _statement(m.get(k)) for k in ("mechanism", "limitation", "next_test")}
            negative_claims = any(_NEGATIVE_CAPABILITY.search(t) for t in explanation.values())
            results.append({
                "unverified_capability_absence_flag": bool(negative_claims),
                "absence_review_note": ("Claims that code lacks a feature need repo code/docs inspection; "
                                        "no negative capability claim is accepted yet."
                                        if negative_claims else None),
                "problem_id": key[0], "repository_id": key[1], "fit": m["fit"],
                **explanation, "problem_ref": problems[key[0]]["source_url"],
                "repository_ref": repos[key[1]]["source_url"],
                "review_status": "unverified_semantic_match_requires_execution_and_market_validation",
                "rights_clearance": False, "buyer_validated": False,
            })
        except ValueError as exc:
            rejects.append({"candidate": idx + 1, "reason": str(exc)})
    return {
        "schema": "cite_refinery.opportunity_matches.v1",
        "matches": results, "rejected_candidates": rejects,
        "authority": "hypothesis_only_not_commercial_proof",
        "boundary": "Semantic fit hypothesis from supplied problem/repository descriptions only; no purchased service, licensing, maintainer agreement, actual operational tests or economic value established.",
    }
