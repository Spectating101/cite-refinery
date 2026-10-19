"""Literal source-span integrity checks for untrusted external model assertions.

This deliberately DOES NOT infer semantic entailment, causality, or intervention
effectiveness. It tests only whether the supplied span is actually present in
the cited retrieved text and whether a model negative conflicts with an explicit
controlled institutional relationship assertion.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any


def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(text)).split()).casefold()


def verify_source_span(source: dict[str, Any], claimed_quote: str,
                       *, max_quote_chars: int = 1000) -> dict[str, Any]:
    """Source-backed literal quote check, never an entailment adjudication."""
    source_id = str(source.get("id") or "")
    source_url = str(source.get("url") or "")
    passage = str(source.get("text") or "")
    quote = str(claimed_quote or "").strip()
    if not source_id or not source_url.startswith("https://") or not passage:
        raise ValueError("source requires id, https URL and non-empty text")
    if not 12 <= len(quote) <= max_quote_chars:
        raise ValueError("quote must be 12..1000 characters")
    found = _normalize(quote) in _normalize(passage)
    return {
        "source_id": source_id, "source_url": source_url,
        "quote": quote, "literal_quote_found": found,
        "source_passage_sha256": hashlib.sha256(passage.encode("utf-8")).hexdigest(),
        "status": "verbatim_span_present_not_entailment" if found else "quote_not_in_source",
        "review_state": "human_or_strong_source_validation_required",
        "boundary": "Literal source-text presence is not semantic entailment, cross-document replication or proof of an effect.",
    }


def detect_explicit_link_misread(source: dict[str, Any], *,
                                 model_decision: str,
                                 exact_span: str,
                                 subject: str,
                                 object_name: str) -> dict[str, Any]:
    """Flag a negative answer that conflicts with literally co-stated entities.

    Conservative signal, not a general natural-language contradiction classifier.
    """
    quote = verify_source_span(source, exact_span)
    span = _normalize(exact_span)
    entity_match = _normalize(subject) in span and _normalize(object_name) in span
    predicate_match = bool(re.search(r"\b(supports?|supporting|backbone|enables?|feeds?)\b", span))
    explicit_source_signal = bool(quote["literal_quote_found"] and entity_match and predicate_match)
    decision = _normalize(model_decision)
    return {
        "source_id": quote["source_id"], "quote_check": quote,
        "literal_relationship_signal": explicit_source_signal,
        "model_decision": decision,
        "potential_source_contradiction": bool(explicit_source_signal and decision == "no"),
        "status": "manual_review_required",
        "boundary": "Regex only identifies source wording vs a binary model answer. It does not verify causation, efficacy, or an implied relationship.",
    }
