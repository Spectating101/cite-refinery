"""Run an actual CPU semantic retriever on the frozen three Atlas maps.

Real pretrained ONNX text embeddings versus the browser's exact existing
lexical search. This measures source-retrieval navigation only, NOT scientific
entailment, causal reasoning, cross-layer validity, or end-to-end answers.
No private Nocturnal material or sealed Academic holdout source IDs are read.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Callable
import argparse
import json
import math

from .three_map_capability_packet import _check_pilot, _hash, LAYERS, PILOT
from .semantic_integration_reality_audit import PAIRS, frontend_match

SCHEMA = "cite_refinery.actual_semantic_retrieval_replay.v1"
MODEL = "BAAI/bge-small-en-v1.5"
COMPARATOR_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VALID_REAL_MODELS = {MODEL, COMPARATOR_MODEL}
# Development references only, known to the team before this evaluation.
PROBE_ORIGIN = "historical_investigator_chosen_pairs_not_blind_independent_gold"

# Coverage/safety questions are explicitly unsupported by this frozen
# source-only workspace. These are diagnostics of the always-return behavior;
# they are NOT labeled negative examples for relevance calibration.
ABSTENTION_CHALLENGES = (
    ("practical", "Which Nocturnal case received an independently authorized, "
                  "publicly verified field-outcome certification in this Atlas?"),
    ("academic", "Which source in this Atlas has a newly independently verified "
                 "causal scientific finding, including replication evidence?"),
    ("implementation", "Which listed implementation was independently certified "
                       "for safe real-time flood alerts at a public operational site?"),
)


def _require(ok, reason):
    if not ok:
        raise ValueError(reason)


def _document(card):
    """No source IDs, URLs, benchmark questions or target labels in embeddings."""
    return " ".join([
        card["title"],
        card.get("summary", ""),
        " ".join(card.get("subjects", [])[:5]),
        " ".join(card.get("tags", [])[:6]),
        " ".join(d.get("text", "")[:320] for d in card.get("details", [])[:2]),
    ])[:1400]


def _vectors(texts, embed: Callable[[list[str]], object]):
    import numpy as np
    _require(texts and len(texts) <= 1600 and all(
        isinstance(x, str) and x.strip() for x in texts), "Invalid source or query texts")
    array = np.asarray(embed(texts), dtype=np.float32)
    _require(array.ndim == 2 and array.shape[0] == len(texts)
             and 128 <= array.shape[1] <= 2048
             and np.all(np.isfinite(array)), "Invalid dimensions/NaN in neural embeddings")
    norms = np.linalg.norm(array, axis=1)
    _require(np.all(np.isfinite(norms)) and np.all(norms > 1e-10),
             "Degenerate or nonfinite embedding norm")
    return array / norms[:, None]


def actual_fastembed(texts, *, model_name=MODEL):
    """No fake/keyword embedding fallback; missing model is an honest failure."""
    from fastembed import TextEmbedding
    from pathlib import Path
    import os
    model = TextEmbedding(model_name=model_name,
                          cache_dir=os.environ.get("FASTEMBED_CACHE_PATH", None),
                          threads=2)
    return list(model.embed(texts, batch_size=32, parallel=None))


def run(pilot: dict, *, embed: Callable = actual_fastembed,
        model_id=MODEL):
    """Single embedding/model pass across all 1,497 existing source cards."""
    known = _check_pilot(pilot)
    _require(model_id and isinstance(model_id, str) and len(model_id) <= 140,
             "Model identifier required")
    if embed is actual_fastembed:
        _require(model_id in VALID_REAL_MODELS,
                 "Only explicit predeclared real embedding models are supported")
    ordered = [*sorted(pilot["cards"], key=lambda x: x["id"])]
    source_texts = [_document(c) for c in ordered]
    _require(all(source_texts), "Blank original source card")
    queries = []
    for target, literal, paraphrase in PAIRS:
        _require(target in known, "Development probe target not in frozen corpus")
        for variant, text in (("literal", literal), ("paraphrase", paraphrase)):
            queries.append({
                "layer": known[target]["layer"], "target": target,
                "variant": variant, "text": text,
            })
    for layer, text in ABSTENTION_CHALLENGES:
        queries.append({"layer": layer, "variant": "unanswerable_safety_prompt",
                        "target": None, "text": text})
    # NOTE: all queries are chosen *before* running the model and not part of
    # any vectorized source documents. No query title is inserted into source.
    import numpy as np
    vector_embed = (lambda texts: actual_fastembed(texts, model_name=model_id)) if (
        embed is actual_fastembed) else embed
    all_vectors = _vectors(source_texts + [q["text"] for q in queries], vector_embed)
    source_vecs = all_vectors[:len(ordered)]
    query_vecs = all_vectors[len(ordered):]
    _require(source_vecs.shape[0] == 1497 and len(queries) == 23,
             "Expected 1,497 records and 23 predefined retrieval probes")
    by_layer = {
        layer: [i for i, card in enumerate(ordered) if card["layer"] == layer]
        for layer in LAYERS
    }
    _require({layer: len(indices) for layer, indices in by_layer.items()} == LAYERS,
             "Frozen independent source map sizes changed")
    results, stats = [], defaultdict(lambda: defaultdict(int))
    for q, vector in zip(queries, query_vecs):
        indices = by_layer[q["layer"]]
        similarity = source_vecs[indices] @ vector
        _require(np.all(np.isfinite(similarity)), "Nonfinite cosine similarity")
        ranked_local = sorted(range(len(indices)),
                              key=lambda i: (-float(similarity[i]),
                                             ordered[indices[i]]["id"]))
        top = [ordered[indices[i]]["id"] for i in ranked_local[:10]]
        top_sims = [round(float(similarity[i]), 6) for i in ranked_local[:10]]
        base = {
            "layer": q["layer"], "variant": q["variant"],
            "model_top1_card_id": top[0], "model_top10_card_ids": top,
            "model_top10_cosine": top_sims,
            "reference_status": PROBE_ORIGIN if q["target"] else
                                "authority_unanswerable_but_no_gold_relevance_set",
        }
        if q["target"] is not None:
            # Do not claim this chosen target is the only relevant document.
            ranking = next(i + 1 for i, pos in enumerate(ranked_local)
                           if ordered[indices[pos]]["id"] == q["target"])
            strict_ids = frontend_match(ordered, q["layer"], q["text"])
            rec = {
                **base, "query": q["text"], "developer_selected_target_id": q["target"],
                "rank_of_developer_target": ranking,
                "top1_target_hit": ranking == 1,
                "top5_target_hit": ranking <= 5,
                "top10_target_hit": ranking <= 10,
                "frontend_literal_filter_target_hit": q["target"] in strict_ids,
                "frontend_literal_filter_result_count": len(strict_ids),
            }
            stats[q["variant"]]["total"] += 1
            stats[q["variant"]]["top1"] += int(ranking == 1)
            stats[q["variant"]]["top5"] += int(ranking <= 5)
            stats[q["variant"]]["top10"] += int(ranking <= 10)
            stats[q["variant"]]["browser_hit"] += int(q["target"] in strict_ids)
            stats[q["variant"]][q["layer"] + "_total"] += 1
            stats[q["variant"]][q["layer"] + "_top5"] += int(ranking <= 5)
        else:
            # A nearest-neighbor index unconditionally returns an ID; its
            # similarity cannot authorize an answer or prove abstention.
            rec = {
                **base, "query": q["text"],
                "expected_safe_answer_status": "insufficient_validated_sources",
                "ranked_document_is_not_evidence_of_answerability": True,
                "retriever_automatically_abstained": False,
                "field_validation_available_in_frozen_workspace": False,
            }
        results.append(rec)
    by_variant = {}
    for k in ("literal", "paraphrase"):
        d = stats[k]
        by_variant[k] = {
            "selected_development_probes": d["total"],
            "browser_selected_target_retrieved": d["browser_hit"],
            "embedding_target_recall_at_1": d["top1"],
            "embedding_target_recall_at_5": d["top5"],
            "embedding_target_recall_at_10": d["top10"],
            "by_layer_selected_target_recall_at_5": {
                layer: {"hits": d[layer + "_top5"],
                        "trials": d[layer + "_total"]} for layer in LAYERS
            },
        }
    import importlib.metadata
    version = ("injected_test_embedder" if embed is not actual_fastembed
               else importlib.metadata.version("fastembed"))
    doc_fingerprint = sha256(json.dumps(source_texts, ensure_ascii=False,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "schema": SCHEMA, "corpus_schema": PILOT,
        "records_by_layer": LAYERS, "total_records": 1497,
        "source_cards_sha256": _hash(pilot["cards"]),
        "embedded_document_texts_sha256": doc_fingerprint,
        "embedding_model": model_id,
        "embedding_package_version": version,
        "embedding_dimension": int(source_vecs.shape[1]),
        "retrieval_type": "pretrained_neural_cosine_CPU_metadata_only",
        "historical_reference_probes": PROBE_ORIGIN,
        "development_probe_stats": by_variant,
        "safety_abstention_probes": len(ABSTENTION_CHALLENGES),
        "actual_semantic_answers_generated": 0,
        "automatic_safe_abstentions": 0,
        "validated_original_paper_claims": 0,
        "validated_original_practical_outcomes": 0,
        "validated_original_code_functionality_by_retriever": 0,
        "validated_cross_layer_semantic_claims": 0,
        "independent_blind_gold_or_fair_competitor_test": False,
        "model_weight_file_digest_or_revision_pinned": False,
        "browser_frontend_semantic_search_deployed": False,
        "passage_level_entailment_measured": False,
        "can_claim_intelligence_product_ready": False,
        "all_probes": results,
        "limitations": [
            "Chosen developer targets are not independent or exhaustive relevance judgments",
            "Only title/summary/tags/metadata indexed; no original paper bodies or code execution",
            "The original source cards contain claims that are often unverified",
            "Nearest-neighbor returns a candidate even for answer-unanswerable safety queries",
            "No model weights SHA/revision pin; exact scores can vary across installs",
            "Source URLs across layers may duplicate and do not independently corroborate",
        ],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--model", default=MODEL, choices=sorted(VALID_REAL_MODELS))
    args = p.parse_args(argv)
    _require(not args.out.exists(), "Never overwrite an earlier model trial")
    _require(args.pilot.is_file() and args.pilot.stat().st_size < 16_000_000
             and not args.pilot.is_symlink(), "Missing or invalid original pilot")
    pilot = json.loads(args.pilot.read_text(encoding="utf-8"))
    result = run(pilot, model_id=args.model)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print("ACTUAL_ATLAS_SEMANTIC_RETRIEVAL", json.dumps({
        "by_variant": result["development_probe_stats"],
        "model": result["embedding_model"],
        "source_cards_sha256": result["source_cards_sha256"],
        "actual_semantic_answers_generated": 0,
        "all_safety_probes_still_require_abstention": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
