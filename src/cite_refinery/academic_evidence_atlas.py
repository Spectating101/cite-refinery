"""Independent Academic Atlas depth over frozen development material.

This is a source index plus source-text-bound *operator supplied* review receipts.
No LLM conclusion, scientific truth, study quality, or cross-layer edges.
The 66-record sealed holdout is never an input to this module.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "cite_refinery.academic_evidence_atlas.v1"
MANIFEST_SCHEMA = "cite_refinery.richer_development_manifest.v1"
SPLIT_SCHEMA = "cite_refinery.richer_corpus_public_manifest.v1"
REVIEW_SCHEMA = "cite_refinery.academic_evidence_reviews.v1"
GENRES = {
    "full_text_jats": "article_fulltext_author_report_not_validated",
    "report_extracted_text": "institutional_report_text_not_independent_outcome",
    "dataset_metadata": "catalog_metadata_not_underlying_data",
}
ROLES = {"method", "result", "limitation", "contrary_result", "research_question"}
STATUS = {"candidate", "analyst_source_span_checked"}


def _hash(text):
    return sha256(text.encode("utf-8")).hexdigest()


def _hex(value):
    if not isinstance(value, str) or len(value) != 64 or any(
        ch not in "0123456789abcdef" for ch in value
    ):
        raise ValueError("Academic original source digest missing or malformed")
    return value


def _https(value):
    p = urlsplit(value) if isinstance(value, str) else None
    if not p or p.scheme != "https" or not p.hostname or p.username:
        raise ValueError("Academic source must have an HTTPS original identity")
    return value


def _bound(value, *, limit, field):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Malformed academic " + field)
    return value.strip()


def _check_materials(manifest, receipt):
    if (manifest.get("schema") != MANIFEST_SCHEMA or
        receipt.get("schema") != SPLIT_SCHEMA or
        manifest.get("scientific_truth_validated") is not False or
        manifest.get("heldout_source_records_exposed") != 0 or
        manifest.get("model_given_collection_quota_labels") is not False or
        receipt.get("holdout_status") != "sealed_not_mapped_not_reviewed" or
        receipt.get("accuracy_scores_available") is not False):
        raise ValueError("Expected frozen development-only Academic material")
    docs = manifest.get("documents")
    if not isinstance(docs, list) or not 1 <= len(docs) <= 5000:
        raise ValueError("Invalid academic source universe")
    if (manifest.get("development_source_count") != len(docs) or
        receipt.get("development_count") != len(docs)):
        raise ValueError("Academic development source counts disagree")
    if (manifest.get("material_by_type") != receipt.get("development_type_counts") or
        receipt.get("holdout_count", 0) <= 0 or
        receipt.get("development_count", 0) + receipt.get("holdout_count", 0) !=
        receipt.get("eligible_new_materials", 0)):
        raise ValueError("Academic frozen split counts changed")
    seen_ids = set()
    seen_urls = set()
    out = {}
    for doc in docs:
        did = _bound(doc.get("id"), limit=140, field="source ID")
        url = _https(doc.get("canonical_url"))
        kind = doc.get("type")
        if kind not in GENRES or did in seen_ids or url in seen_urls:
            raise ValueError("Duplicate academic identity or unsupported material kind")
        if ("collection_quota" in doc or "text" in doc or "holdout" in doc or
            "source_body" in doc):
            raise ValueError("Academic public development manifest contains restricted fields")
        title = _bound(doc.get("title"), limit=2500, field="title")
        checksum = _hex(doc.get("text_sha256"))
        if not isinstance(doc.get("word_count"), int) or doc["word_count"] < 0:
            raise ValueError("Invalid original extracted-text word count")
        seen_ids.add(did)
        seen_urls.add(url)
        out[did] = {
            "id": did, "url": url, "title": title,
            "text_sha256": checksum, "reported_extracted_words": doc["word_count"],
            "date": doc.get("document_date"),
            "origin_genre": kind, "genre_authority": GENRES[kind],
            "source_scope": str(doc.get("source_scope") or ""),
            "substantive_study_claims_reviewed": 0,
            "source_excerpt_available_in_this_map": False,
            "scientific_accuracy_independently_established": False,
            "study_design_unclassified_until_source_review": True,
        }
    actual = dict(Counter(x["origin_genre"] for x in out.values()))
    if actual != manifest["material_by_type"]:
        raise ValueError("Academic source-type inventory mismatch")
    if (receipt.get("holdout_seal_sha256") is None or
        receipt.get("source_fingerprint_sha256") is None):
        raise ValueError("Frozen holdout provenance missing")
    _hex(receipt["holdout_seal_sha256"])
    _hex(receipt["source_fingerprint_sha256"])
    if not (0 <= manifest.get("map_ready_source_count", -1) <= len(out)):
        raise ValueError("Academic mapper-ready source count malformed")
    return out


def build_academic_atlas(manifest, split_receipt, *, reviews=None, source_texts=None):
    """Assemble a standalone navigable map; accepted anchors require exact text."""
    entries = _check_materials(manifest, split_receipt)
    reviews = reviews if reviews is not None else {
        "schema": REVIEW_SCHEMA, "claims": [], "tensions": [],
    }
    if reviews.get("schema") != REVIEW_SCHEMA:
        raise ValueError("Academic review schema is invalid")
    raw_claims = reviews.get("claims")
    raw_tensions = reviews.get("tensions")
    if (not isinstance(raw_claims, list) or not isinstance(raw_tensions, list)
        or len(raw_claims) > 10000 or len(raw_tensions) > 2500):
        raise ValueError("Academic review batch exceeds safe bounds")
    source_texts = source_texts or {}
    if not isinstance(source_texts, dict) or any(k not in entries for k in source_texts):
        raise ValueError("Review source text outside frozen development inventory")
    verified_text = {}
    for sid, raw in source_texts.items():
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > 2_000_000:
            raise ValueError("Review text must be bounded original Unicode text")
        if _hash(raw) != entries[sid]["text_sha256"]:
            raise ValueError("Review text differs from source's frozen extracted-text SHA-256")
        verified_text[sid] = raw
    claims = {}
    by_source = defaultdict(list)
    quote_fingerprints = set()
    for item in raw_claims:
        if not isinstance(item, dict):
            raise ValueError("Malformed academic review claim")
        cid = _bound(item.get("id"), limit=140, field="claim ID")
        sid = item.get("source_id")
        if cid in claims or sid not in entries:
            raise ValueError("Duplicate claim or unknown Academic source")
        if sid not in verified_text:
            raise ValueError("Claim lacks frozen source text to authenticate exact span")
        if entries[sid]["origin_genre"] == "dataset_metadata":
            raise ValueError("Dataset metadata cannot be promoted into academic findings")
        role = item.get("role")
        state = item.get("review_state")
        if role not in ROLES or state not in STATUS:
            raise ValueError("Unrecognized Academic evidence role or review state")
        start, end = item.get("start"), item.get("end")
        text = verified_text[sid]
        quote = item.get("quote")
        if (type(start) is not int or type(end) is not int or
            not 0 <= start < end <= len(text) or
            not isinstance(quote, str) or not 20 <= len(quote) <= 1400 or
            text[start:end] != quote):
            raise ValueError("Academic claim quote is not an exact bounded source span")
        fp = (sid, start, end, role)
        if fp in quote_fingerprints:
            raise ValueError("Repeated source span is not independent claim evidence")
        quote_fingerprints.add(fp)
        statement = _bound(item.get("statement"), limit=2000, field="analyst interpretation")
        scope = item.get("scope")
        if not isinstance(scope, dict) or set(scope) != {
            "population", "setting", "outcome", "study_design"
        }:
            raise ValueError("Explicit population, setting, outcome and study design required")
        scope_clean = {k: _bound(v, limit=400, field=k) for k, v in scope.items()}
        reviewer = item.get("reviewer")
        if state == "analyst_source_span_checked":
            _bound(reviewer, limit=160, field="reviewer designation")
            _bound(item.get("reviewed_at"), limit=50, field="review date")
        claims[cid] = {
            "id": cid, "source_id": sid,
            "statement_operator_supplied": statement, "role_operator_supplied": role,
            "scope_operator_supplied": scope_clean,
            "quote_sha256": _hash(quote), "start": start, "end": end,
            "review_state": state, "reviewer": reviewer if state != "candidate" else None,
            "reviewed_at": item.get("reviewed_at") if state != "candidate" else None,
            "exact_span_matches_frozen_extracted_text": True,
            "publisher_claim_verified_or_replicated": False,
            "external_semantic_adjudication": False,
        }
        by_source[sid].append(cid)
    tensions = {}
    for row in raw_tensions:
        if not isinstance(row, dict):
            raise ValueError("Malformed academic tension")
        tid = _bound(row.get("id"), limit=140, field="tension ID")
        ids = row.get("claim_ids")
        if (tid in tensions or not isinstance(ids, list) or len(ids) != 2 or
            ids[0] == ids[1] or not all(cid in claims for cid in ids)):
            raise ValueError("Academic tension must link two distinct reviewed anchors")
        if claims[ids[0]]["source_id"] == claims[ids[1]]["source_id"]:
            raise ValueError("Independent-source comparison requires separate publications")
        reason = _bound(row.get("comparison_question"), limit=1500, field="comparison question")
        tensions[tid] = {
            "id": tid, "claim_ids": ids,
            "comparison_question": reason,
            "state": "candidate_scope_comparison_not_proven_contradiction",
            "scope_and_design_comparability_independently_verified": False,
        }
    for sid, ids in by_source.items():
        entries[sid]["substantive_study_claims_reviewed"] = len(ids)
        entries[sid]["study_design_unclassified_until_source_review"] = False
    groups = {
        kind: [sid for sid in sorted(entries) if entries[sid]["origin_genre"] == kind]
        for kind in GENRES
    }
    role_counts = Counter(c["role_operator_supplied"] for c in claims.values())
    return {
        "schema": SCHEMA,
        "provenance": {
            "split_receipt_schema": SPLIT_SCHEMA,
            "holdout_seal_sha256": split_receipt["holdout_seal_sha256"],
            "source_fingerprint_sha256": split_receipt["source_fingerprint_sha256"],
            "development_partition_only": True, "heldout_source_id_or_text_imported": False,
        },
        "coverage": {
            "development_documents": len(entries),
            "mapper_ready_development_documents": manifest["map_ready_source_count"],
            "indexed_article_fulltexts": len(groups["full_text_jats"]),
            "indexed_institutional_reports": len(groups["report_extracted_text"]),
            "dataset_metadata_records_not_observations": len(groups["dataset_metadata"]),
            "sealed_holdout_documents_not_imported": split_receipt["holdout_count"],
            "source_anchored_claims": len(claims),
            "sources_with_anchored_claims": len(by_source),
            "source_anchored_claim_roles": dict(role_counts),
            "candidate_scope_tensions": len(tensions),
            "independently_validated_scientific_findings": 0,
            "confirmed_scientific_contradictions": 0,
            "world_field_coverage_proven": False,
            "sampling_frame": "prior fixed topic search quotas, development partition only",
        },
        "groups": groups, "sources": entries, "claims": claims, "tensions": tensions,
        "interpretation": {
            "original_extracted_fulltext_digest_is_not_publisher_xml_digest": True,
            "source_quote_match_is_not_scientific_truth": True,
            "author_report_is_not_replicated_effect": True,
            "dataset_metadata_is_not_dataset": True,
            "cross_layer_edges_created": 0,
        }
    }


def browse_academic(atlas, *, terms=None, genre=None, limit=25):
    if atlas.get("schema") != SCHEMA or not 1 <= limit <= 100:
        raise ValueError("Invalid Academic Atlas or browse limit")
    if genre is not None and genre not in GENRES:
        raise ValueError("Unknown material genre")
    if terms is not None and (not isinstance(terms, str) or len(terms) > 160):
        raise ValueError("Malformed Academic search")
    needles = (terms or "").casefold().split()
    claims_by_source = defaultdict(list)
    for claim in atlas["claims"].values():
        claims_by_source[claim["source_id"]].append(claim)
    results = []
    for sid, row in sorted(atlas["sources"].items()):
        if genre and row["origin_genre"] != genre:
            continue
        haystack = " ".join([
            sid, row["title"], row["url"], row["origin_genre"],
            *[cl["statement_operator_supplied"] for cl in claims_by_source[sid]],
        ]).casefold()
        if all(n in haystack for n in needles):
            results.append(row)
    return {
        "schema": "cite_refinery.academic_evidence_browse.v1",
        "genre": genre, "terms": terms, "matching_count": len(results),
        "results": results[:limit], "lexical_only": True,
        "not_quality_ranked": True, "heldout_sealed": True,
        "cross_layer_join_performed": False,
    }


def balanced_review_queue(atlas, *, per_genre=10):
    if atlas.get("schema") != SCHEMA or not 1 <= per_genre <= 40:
        raise ValueError("Malformed Academic review backlog request")
    selected = []
    for kind, ids in sorted(atlas["groups"].items()):
        candidates = [sid for sid in ids
                      if atlas["sources"][sid]["substantive_study_claims_reviewed"] == 0]
        ordered = sorted(candidates, key=lambda sid: _hash(kind+"|"+sid))
        for sid in ordered[:per_genre]:
            selected.append({
                "source_id": sid, "genre": kind,
                "source_url": atlas["sources"][sid]["url"],
                "text_sha256": atlas["sources"][sid]["text_sha256"],
                "source_text_available_in_this_map": False,
                "source_span_review_completed": False,
                "task": ("validate underlying dataset availability and metadata"
                         if kind == "dataset_metadata" else
                         "recover source text; anchor methods/results/limitations with explicit scope"),
            })
    return {
        "schema": "cite_refinery.academic_balanced_review_queue.v1",
        "selection": "stable_sha256_within_original_source_genre_not_quality_ranking",
        "total_items": len(selected), "entries": selected,
    }


def load_review_source_texts(directory, source_ids):
    """Read only explicitly referenced frozen text files; never store body in atlas."""
    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Academic reviewer text directory is unavailable")
    texts = {}
    for source_id in sorted(set(source_ids)):
        if (not isinstance(source_id, str) or "/" in source_id or
            "\\" in source_id or source_id in {".", ".."}):
            raise ValueError("Unsafe original academic source ID")
        file = root / (source_id + ".txt")
        if file.is_symlink() or not file.is_file() or file.stat().st_size > 2_000_000:
            raise ValueError("Missing, symlinked or oversized local frozen Academic text")
        texts[source_id] = file.read_text(encoding="utf-8")
    return texts
