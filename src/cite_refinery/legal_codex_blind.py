"""Blinded, corpus-bounded legal mechanism retrieval baseline.

The runner sees only incident questions and candidate text/date/source; it is
not given any relevance labels, pre-labelled failure-mode tags or answer keys.
This is a test of retrieval from a supplied candidate library, NOT autonomous
web discovery, legal correctness or a causal effect estimator.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

STOP = frozenset((
    "the a an and or of in on for to from by with that this as is are was were be"
    " have has had will shall under about into may can over a case cases affected"
    " system systems law laws rule rules legal policy policies government"
).split())
ALLOWED_CASE = {"case_id", "problem_statement", "anchor_date"}
ALLOWED_CANDIDATE = {"id", "description", "jurisdiction", "available_from", "source_url"}


def tokens(text: str) -> list[str]:
    result = []
    for term in re.findall(r"[a-z][a-z0-9]{2,}", text.lower()):
        if term in STOP:
            continue
        if term.endswith("ies") and len(term) > 5:
            term = term[:-3] + "y"
        elif term.endswith("ing") and len(term) > 6:
            term = term[:-3]
        elif term.endswith("ed") and len(term) > 5:
            term = term[:-2]
        elif term.endswith("s") and len(term) > 4:
            term = term[:-1]
        if term not in STOP:
            result.append(term)
    return result


def prepare_questions(bundle: dict) -> list[dict]:
    """Strict projection explicitly removes both labels and expected matches."""
    return [{
        "case_id": c["id"],
        "problem_statement": c["problem_statement"],
        "anchor_date": c["anchor_date"],
    } for c in bundle["cases"]]


def retrieve(questions: list[dict], library: list[dict], *, top_k: int = 3) -> dict:
    if not 1 <= top_k <= 10:
        raise ValueError("top_k outside allowed range")
    if not isinstance(library, list) or len(library) < 5:
        raise ValueError("at least five candidate mechanisms required")
    if not isinstance(questions, list) or not questions:
        raise ValueError("questions required")
    seen = set()
    docs = []
    for doc in library:
        if set(doc) != ALLOWED_CANDIDATE or doc["id"] in seen:
            raise ValueError("candidate leakage, duplicate, or missing field")
        seen.add(doc["id"])
        date.fromisoformat(doc["available_from"])
        u = urlsplit(doc["source_url"])
        if u.scheme != "https" or not u.hostname or u.username or u.password:
            raise ValueError("candidate lacks a valid source locator")
        terms = tokens(doc["description"])
        if len(terms) < 4:
            raise ValueError("candidate description too weak")
        docs.append((doc, Counter(terms)))
    freq = Counter(word for _, bag in docs for word in bag)
    n = len(docs)
    results = []
    case_ids = set()
    for q in questions:
        if set(q) != ALLOWED_CASE or q["case_id"] in case_ids:
            raise ValueError("question leaked hidden labels or repeated an ID")
        case_ids.add(q["case_id"])
        anchor = date.fromisoformat(q["anchor_date"])
        query = set(tokens(q["problem_statement"]))
        if len(query) < 3:
            raise ValueError("case description too short")
        eligible, excluded = [], []
        for doc, bag in docs:
            shared = query & set(bag)
            score = sum(math.log(1 + (n + 1) / (freq[w] + .5)) for w in shared)
            candidate = {
                "candidate_id": doc["id"], "jurisdiction": doc["jurisdiction"],
                "source_url": doc["source_url"], "overlap_tokens": sorted(shared),
                "lexical_score": round(score, 6),
                "status": "unreviewed_retrieval_candidate",
            }
            if date.fromisoformat(doc["available_from"]) > anchor:
                excluded.append({**candidate, "reason": "postdates_incident"})
            elif len(shared) >= 2:
                eligible.append(candidate)
        eligible.sort(key=lambda x: (-x["lexical_score"], x["candidate_id"]))
        results.append({
            "case_id": q["case_id"], "ranked_candidates": eligible[:top_k],
            "excluded_after_incident": sorted(excluded, key=lambda x: x["candidate_id"]),
            "correctness": "not_adjudicated", "causal_effect": None,
            "publication_authorized": False,
        })
    return {"schema": "legal_codex.blind_retrieval.v1", "method": "idf_lexical_overlap",
            "candidate_count": len(library), "results": results,
            "answer_keys_seen_by_retriever": False,
            "external_web_discovery_performed": False,
            "publication_authorized": False}


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("benchmark")
    p.add_argument("library")
    p.add_argument("--output", default="legal_codex_blind_results.json")
    args = p.parse_args(argv)
    seed = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
    library = json.loads(Path(args.library).read_text(encoding="utf-8"))
    result = retrieve(prepare_questions(seed), library)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "cases": len(result["results"]),
        "candidates": result["candidate_count"],
        "web_discovery": False, "publication_authorized": False,
    }))


if __name__ == "__main__":
    main()
