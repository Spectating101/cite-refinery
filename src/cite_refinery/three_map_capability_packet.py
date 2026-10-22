"""Frozen-corpus, evidence-safe three-map capability evaluation packet.

This is a sampling/evaluation contract, not semantic model inference or gold
annotation. Never access Academic holdout records or private Nocturnal data.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
import argparse
import json

from cite_refinery.semantic_integration_reality_audit import PAIRS, frontend_match

SCHEMA = "cite_refinery.three_map_capability_packet.v1"
PREDICTIONS = "cite_refinery.three_map_capability_predictions.v1"
RESULT = "cite_refinery.three_map_capability_results.v1"
PILOT = "cite_refinery.standalone_research_pilot.v1"
LAYERS = {"practical": 57, "academic": 150, "implementation": 1290}
SEED = "2026-10-22-predeclared-source-sampling-v1"
PROMPTS = {
    "practical": (
        "For the item titled '{title}', what do its original public sources actually document? Distinguish direct records, unverified reporting, and missing evidence.",
        "For '{title}', reconstruct any verifiable dates and corrections. Which claimed outcomes remain uncorroborated or unknowable?",
    ),
    "academic": (
        "For the study titled '{title}', identify the measured result and research design from the original passage. Abstain if only index metadata is available.",
        "For '{title}', what population, methods, limitations, or contradictory findings constrain a causal or general conclusion?",
    ),
    "implementation": (
        "For the repository titled '{title}', which claimed function can be reproduced on a pinned original revision? Name the test input and observed behavior.",
        "For '{title}', propose one falsifying execution test; identify unsupported assumptions about deployment, integration, and reuse rights.",
    ),
}


def _require(ok, reason):
    if not ok:
        raise ValueError(reason)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value):
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _load(path, *, max_bytes=16_000_000):
    p = Path(path)
    _require(p.is_file() and not p.is_symlink() and p.stat().st_size <= max_bytes,
             "Missing, symlinked, or oversized evaluation input")
    return json.loads(p.read_text(encoding="utf-8"))


def _check_pilot(pilot):
    _require(isinstance(pilot, dict) and pilot.get("schema") == PILOT,
             "Requires the original standalone Atlas pilot")
    cards = pilot.get("cards")
    _require(isinstance(cards, list) and pilot.get("record_count") == len(cards) == 1497
             and pilot.get("by_layer") == LAYERS,
             "The frozen 1,497-card baseline has changed")
    original = pilot.get("original_data", {})
    _require(original.get("academic_sealed_holdout_not_imported") == 66
             and original.get("practical_public_nocturnal_attached") is False
             and original.get("independently_validated_scientific_findings") == 0
             and original.get("implementation_live_field_outcomes") == 0,
             "Frozen safety or evidence authority changed")
    known = {}
    tally = Counter()
    for c in cards:
        _require(isinstance(c, dict) and isinstance(c.get("id"), str)
                 and c["id"] not in known and c.get("layer") in LAYERS
                 and isinstance(c.get("title"), str) and c["title"]
                 and isinstance(c.get("group"), str) and c["group"],
                 "Duplicate, unknown, or invalid source card")
        _require(not any(k in c for k in ("text", "raw_document", "source_body", "heldout")),
                 "Original source text or holdout leaked into evaluation cards")
        known[c["id"]] = c
        tally[c["layer"]] += 1
    _require(dict(tally) == LAYERS, "Layer record totals are inconsistent")
    return known


def _sampling_group(card):
    """Split Implementation leads by *evidence stage*, not topic metadata alone."""
    if card["layer"] != "implementation":
        return card["group"]
    for stage in ("bounded_original_function_test", "original_code_sample_checked",
                  "original_commit_checked", "survey_metadata_only"):
        if stage in card.get("tags", []):
            return card["group"] + "::" + stage
    return card["group"] + "::historical_or_unknown"


def _sample(pilot, *, per_layer, seed):
    _require(isinstance(per_layer, int) and 2 <= per_layer <= 40,
             "Per-layer source review count must be 2-40")
    _require(isinstance(seed, str) and 1 <= len(seed) <= 150,
             "Source-sampling seed must be a short explicit string")
    result = {}
    for layer in LAYERS:
        groups = defaultdict(list)
        for c in pilot["cards"]:
            if c["layer"] == layer:
                groups[_sampling_group(c)].append(c)
        for group, items in groups.items():
            items.sort(key=lambda c: (sha256(
                (seed + "|" + layer + "|" + group + "|" + c["id"]).encode()
            ).hexdigest(), c["id"]))
        _require(len(groups) <= per_layer, "Insufficient slots for every source genre")
        assigned = {g: 1 for g in groups}
        counts = {g: len(v) for g, v in groups.items()}
        total = sum(counts.values())
        while sum(assigned.values()) < per_layer:
            options = [g for g in groups if assigned[g] < counts[g]]
            _require(bool(options), "Not enough records to sample")
            group = max(sorted(options),
                        key=lambda g: (per_layer * counts[g] / total - assigned[g], counts[g]))
            assigned[group] += 1
        result[layer] = sorted(
            (card for group, n in assigned.items() for card in groups[group][:n]),
            key=lambda c: c["id"])
    return result


def build_packet(pilot, *, per_layer=20, seed=SEED):
    """Create predeclared balanced samples, query-only prompts and private anchors."""
    known = _check_pilot(pilot)
    sampled = _sample(pilot, per_layer=per_layer, seed=seed)
    baseline = {
        "schema": PILOT, "records": 1497, "by_layer": LAYERS,
        "source_identity_fingerprint": _hash(pilot["cards"]),
        "seed": seed, "sample_per_layer": per_layer,
    }
    fingerprint = _hash(baseline)
    questions, anchors = [], []
    for layer in LAYERS:
        for index, card in enumerate(sampled[layer], 1):
            title = card["title"][:180].replace("\n", " ").replace("\r", " ")
            for k, template in enumerate(PROMPTS[layer], 1):
                tid = layer[:3].upper() + "-" + str(index).zfill(2) + "-" + str(k)
                questions.append({
                    "task_id": tid, "layer": layer, "question": template.format(title=title),
                    "type": "source_or_capability_challenge",
                    "gold_status": "not_independently_adjudicated",
                })
                anchors.append({
                    "task_id": tid, "selected_source_card_id": card["id"],
                    "source_group": card["group"],
                    "reference_is_development_sampling_anchor_not_gold": True,
                })
    development = []
    for n, (target, literal, paraphrase) in enumerate(PAIRS, 1):
        _require(target in known, "Original development probe source disappeared")
        layer = known[target]["layer"]
        development.append({
            "id": "DEV-" + str(n).zfill(2), "layer": layer, "target_card_id": target,
            "literal_query": literal, "paraphrase_query": paraphrase,
            "literal_hit": target in frontend_match(pilot["cards"], layer, literal),
            "paraphrase_hit": target in frontend_match(pilot["cards"], layer, paraphrase),
            "label_origin": "historical_investigator_chosen_development_not_blind_gold",
        })
    question_set = {
        "schema": SCHEMA, "baseline_sha256": fingerprint,
        "evidence_class": "unscored_development_questions",
        "questions": questions,
    }
    private_reference = {
        "schema": SCHEMA, "baseline_sha256": fingerprint, "baseline": baseline,
        "anchors": anchors, "historical_development_pairs": development,
        "allowed_card_ids_by_layer": {
            layer: sorted(c["id"] for c in pilot["cards"] if c["layer"] == layer)
            for layer in LAYERS
        },
        "selection_by_layer_and_group": {
            layer: dict(sorted(Counter(c["group"] for c in sampled[layer]).items()))
            for layer in LAYERS
        },
        "implementation_selected_source_stages": dict(sorted(Counter(
            _sampling_group(c) for c in sampled["implementation"]
        ).items())),
        "independent_answer_quality_gold_available": False,
        "source_hit_does_not_establish_answer_entailment": True,
        "no_sealed_holdout_or_private_nocturnal_material_used": True,
        "cross_layer_match_or_commercial_validation_performed": False,
    }
    _require(len(questions) == per_layer * 2 * 3 and len(development) == 10,
             "Incomplete original map evaluation question packet")
    return question_set, private_reference


def score(question_set, private_reference, predictions):
    """Score coverage and one weak retrieval diagnostic; never infer correctness."""
    _require(question_set.get("schema") == private_reference.get("schema") == SCHEMA
             and question_set.get("baseline_sha256") == private_reference.get("baseline_sha256"),
             "Question and reference packet do not belong together")
    _require(predictions.get("schema") == PREDICTIONS
             and predictions.get("baseline_sha256") == question_set["baseline_sha256"],
             "Wrong or unpinned prediction submission")
    questions = question_set["questions"]
    refs = {r["task_id"]: r for r in private_reference["anchors"]}
    ids = {q["task_id"]: q for q in questions}
    _require(len(ids) == len(questions) == len(refs),
             "Repeated or incomplete benchmark tasks")
    answers = predictions.get("responses")
    _require(isinstance(answers, list) and len(answers) <= len(ids),
             "Invalid response size")
    seen, by_layer = set(), defaultdict(lambda: Counter())
    for response in answers:
        _require(isinstance(response, dict) and response.get("task_id") in ids
                 and response["task_id"] not in seen, "Unknown or duplicate response")
        seen.add(response["task_id"])
        retrieved = response.get("retrieved_card_ids")
        _require(isinstance(retrieved, list) and len(retrieved) <= 100
                 and all(isinstance(s, str) and 0 < len(s) <= 500 for s in retrieved)
                 and len(retrieved) == len(set(retrieved))
                 and isinstance(response.get("abstained"), bool),
                 "Malformed or duplicated source retrieval response")
        layer = ids[response["task_id"]]["layer"]
        _require(all(x in private_reference["allowed_card_ids_by_layer"][layer]
                     for x in retrieved),
                 "Unknown or wrong-layer source identity in standalone-map benchmark")
        result = by_layer[layer]
        result["submitted"] += 1
        result["abstained"] += int(response["abstained"])
        result["developer_selected_anchor_hit"] += int(
            refs[response["task_id"]]["selected_source_card_id"] in retrieved)
    rows = {}
    for layer in LAYERS:
        t = by_layer[layer]
        expected = sum(q["layer"] == layer for q in questions)
        rows[layer] = {
            "expected": expected, "submitted": t["submitted"],
            "missing": expected - t["submitted"], "abstained": t["abstained"],
            "developer_selected_anchor_hits": t["developer_selected_anchor_hit"],
            "anchor_hit_rate_of_submitted": (
                t["developer_selected_anchor_hit"] / t["submitted"] if t["submitted"] else None
            ),
        }
    return {
        "schema": RESULT, "baseline_sha256": question_set["baseline_sha256"],
        "scoring": "source_anchor_diagnostic_only_not_gold_precision_or_semantic_accuracy",
        "by_layer": rows, "total_submitted": len(seen),
        "total_expected": len(ids), "blind_relevance_labels_available": False,
        "answer_grounding_or_entailment_scored": False,
        "technical_feasibility_independently_verified": False,
        "cross_layer_opportunity_value_established": False,
        "competitive_superiority_claim_allowed": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--sample-per-layer", type=int, default=20)
    p.add_argument("--seed", default=SEED)
    p.add_argument("--responses", type=Path,
                   help="Optional schema-checked agent output for diagnostic scoring")
    args = p.parse_args(argv)
    _require(not args.out_dir.exists(), "Do not overwrite a prior benchmark packet")
    questions, reference = build_packet(_load(args.pilot),
                                         per_layer=args.sample_per_layer, seed=args.seed)
    files = {"questions.json": questions, "reviewer-reference.json": reference}
    if args.responses is not None:
        files["diagnostic-results.json"] = score(
            questions, reference, _load(args.responses))
    args.out_dir.mkdir(parents=True)
    for name, value in files.items():
        (args.out_dir / name).write_text(json.dumps(value, indent=2, ensure_ascii=False)
                                          + "\n", encoding="utf-8")
    print(json.dumps({
        "baseline_sha256": questions["baseline_sha256"],
        "questions": len(questions["questions"]),
        "sampled_source_records": len(reference["anchors"]) // 2,
        "historical_literal_hits": sum(x["literal_hit"] for x in
                                       reference["historical_development_pairs"]),
        "historical_paraphrase_hits": sum(x["paraphrase_hit"] for x in
                                          reference["historical_development_pairs"]),
        "quality_gold_scored": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
