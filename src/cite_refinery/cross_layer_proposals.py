"""Model-proposed cross-layer alignments over development-only source readings.

All source roles/interpretations from the prior mapper are UNVERIFIED.
The model may propose semantic relationships, but the validator forbids
source-invented IDs, role crossover, causal-outcome authority, and global
negative claims. Works with *no* hand-seeded thematic modules.
"""
from __future__ import annotations

import json
import re
import hashlib
from copy import deepcopy
from typing import Any

ROLE_LAYERS = {
    "practical_observation": "practical",
    "academic_finding": "academic",
    "academic_method": "academic",
    "program_guidance": "program",
    "reported_implementation": "program",
    "measured_program_outcome": "program",
}
ALL_LAYERS = ("practical", "academic", "program")
_UNSCOPED_ABSENCE = re.compile(r"\b(?:no|none|nothing|never|does not exist|not available)\s+"
    r"(?:verified|measured|effective|operational|deployed|implemented|documented|solution|intervention|program|evidence)", re.I)
_SCOPE_WORDS = re.compile(r"\b(?:these|this|retrieved|provided|sampled|given|limited)\s+"
    r"(?:sources|records|corpus|sample|material|evidence)\b", re.I)
_OUTCOME_CERTAINTY = re.compile(r"\b(?:proves?|guarantees?|definitively establishes|demonstrates causally)\b", re.I)
_DIRECT_BRIDGE = re.compile(
    r"\b(?:directly implements?|independently validates?|proves? the (?:scientific|academic) "
    r"(?:model|hypothesis)|confirms? the (?:scientific|academic) hypothesis)\b", re.I)



def _text(x: Any, *, field: str, minimum: int = 15, maximum: int = 1600) -> str:
    if not isinstance(x, str):
        raise ValueError(f"{field} must be text")
    value = " ".join(x.split())
    if not minimum <= len(value) <= maximum:
        raise ValueError(f"{field} length out of bounds")
    if _UNSCOPED_ABSENCE.search(value) and not _SCOPE_WORDS.search(value):
        raise ValueError(f"{field}: unscoped absence assertion")
    if _OUTCOME_CERTAINTY.search(value):
        raise ValueError(f"{field}: outcome certainty prohibited in candidate map")
    if _DIRECT_BRIDGE.search(value):
        raise ValueError(f"{field}: unsubstantiated direct cross-source implementation or validation link")
    return value


def selected_readings(provisional: dict[str, Any], atlas: dict[str, Any], *,
                      domain: str) -> dict[str, Any]:
    if provisional.get("schema") != "cite_refinery.open_corpus_provisional_map.v1":
        raise ValueError("expected original development provisional map")
    if atlas.get("schema") != "cite_refinery.open_corpus_atlas.v1":
        raise ValueError("expected original development atlas")
    matches = [a for a in atlas.get("domains", []) if a.get("label") == domain]
    if len(matches) != 1:
        raise ValueError("unknown or ambiguous domain")
    scoped = matches[0]
    by_id = {r["source_id"]: r for r in provisional.get("readings", [])}
    if len(by_id) != len(provisional["readings"]):
        raise ValueError("duplicate source ID")
    if not set(scoped["source_ids"]) <= by_id.keys():
        raise ValueError("domain refers to missing sources")
    entries = []
    for sid in scoped["source_ids"]:
        item = by_id[sid]
        if item.get("role") not in ROLE_LAYERS:
            continue
        if not str(item.get("source_url", "")).startswith("https://"):
            raise ValueError("invalid source reference")
        entries.append({
            "id": sid, "layer": ROLE_LAYERS[item["role"]], "candidate_role": item["role"],
            "claim": str(item.get("statement", ""))[:1500],
            "scope": str(item.get("scope", ""))[:700],
            "caveat": str(item.get("caveat", ""))[:700],
            "source_url": item["source_url"],
            "source_sha256": item["source_sha256"],
            "mapper_status": "unverified_model_paraphrase",
        })
    return {"schema": "cite_refinery.cross_layer_model_input.v1",
            "topic": domain, "records": entries,
            "source_set_status": "development_only_previous_model_readings_unverified",
            "boundary": "No raw source passages or fresh independent annotations are included. " +
                        "Source role and candidate claims must be independently checked."}


def attach_original_excerpts(selected: dict[str, Any], corpus: dict[str, Any]) -> dict[str, Any]:
    """Optionally ground candidates in authorized development-source excerpts.

    No holdout files or new source identities are accessed by this function.
    Caller supplies the local development-only source dump explicitly.
    """
    if selected.get("schema") != "cite_refinery.cross_layer_model_input.v1":
        raise ValueError("unknown selected readings")
    if corpus.get("schema") != "cite_refinery.open_corpus.v1" or corpus.get("material_type") != "unclassified_source_records":
        raise ValueError("only the development-only public open-corpus format is accepted")
    originals = {row["id"]: row for row in corpus.get("sources", [])}
    if len(originals) != len(corpus.get("sources", [])):
        raise ValueError("duplicate original identity")
    enriched = deepcopy(selected)
    for record in enriched["records"]:
        orig = originals.get(record["id"])
        if not orig or orig.get("url") != record["source_url"] or orig.get("sha256") != record["source_sha256"]:
            raise ValueError("source identity or SHA-256 mismatch")
        text = orig.get("text")
        if not isinstance(text, str) or not 30 <= len(text) <= 16000:
            raise ValueError("missing or oversized source text")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != record["source_sha256"]:
            raise ValueError("development source content digest mismatch")
        record["original_text"] = text
        record["original_source_scope"] = str(orig.get("source_scope") or "")[:300]
    enriched["original_text_attached"] = True
    enriched["boundary"] = "Original development excerpts included; role labels still model-generated and causal claims unverified."
    return enriched


def alignment_prompt(selected: dict[str, Any]) -> str:
    if selected.get("schema") != "cite_refinery.cross_layer_model_input.v1":
        raise ValueError("invalid input")
    return (
        "You are a problem-centered CROSS-LAYER SEMANTIC REASONER. "
        "The supplied entries are previously generated candidate SOURCE READINGS, not verified conclusions. "
        "Reconstruct only semantically justified, explicitly source-bounded connections among "
        "real-world practical observations, academic research/methods, and actual reported "
        "programs/implementations. Do not fill a missing layer merely to achieve a complete stack. "
        "Do not match sources solely by shared vocabulary. Compare (a) mechanism and causal "
        "hypothesis, (b) population/time/geography and endpoint scope, (c) program capability "
        "versus methodological requirement, (d) alternative explanations and counterevidence. "
        "Never say a technical pilot directly implements another academic model or validates a "
        "separate study unless the underlying document explicitly establishes that dependency; "
        "otherwise call it a potentially relevant implementation. "
        "Differentiate a reported activity/output from a measured outcome, and an observational "
        "association from a causal finding. If this selected source set has no layer, say so. "
        "Do not make worldwide negative claims about missing programs. Do not invent source IDs. "
        "Generate at most 4 actionable connections, fewer or ZERO if they are not justified. "
        "When original_text is supplied, provide exact verbatim support quotes for EVERY source ID "
        "used in each alignment in a citations array of {source_id,quote}; a quote must be a literal "
        "substring of that source original_text and NOT a restatement. "
        "Every candidate must cite at least one academic source ID and one non-academic layer "
        "source ID, using IDs with the EXACT provided layer. The model cannot promote evidence. "
        "Return ONLY one JSON object: "
        '{"alignments":[{"practical_ids":["source-id or empty"],'
        '"academic_ids":["source-id"],"program_ids":["source-id or empty"],'
        '"mechanism":"specific mechanism linking the observations",'
        '"interpretation":"how these source-scoped claims connect and why",'
        '"solution_fit":"what the actual reported implementation does and does NOT establish",'
        '"evidence_tension":"contradiction, scope mismatch or outcome limitation",'
        '"counterargument":"plausible alternative explanation or rival approach",'
        '"next_test":"specific data/review/implementation test that would resolve the issue",'
        '"citations":[{"source_id":"one of the cited source IDs","quote":"exact original_text substring"}]}],'
        '"missing_layers":["practical|academic|program"],'
        '"boundary":"acknowledge source set, secondhand readings, and uncertain entailment"}'
        "} INPUT:\n"+json.dumps(selected, ensure_ascii=False, separators=(",", ":"))
    )


def inspect_alignments(selected: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    if selected.get("schema") != "cite_refinery.cross_layer_model_input.v1":
        raise ValueError("unexpected model input")
    if not isinstance(answer, dict) or not isinstance(answer.get("alignments"), list):
        raise ValueError("model did not produce alignments")
    if len(answer["alignments"]) > 4:
        raise ValueError("too many proposed alignments")
    by_id = {x["id"]: x for x in selected["records"]}
    available = {x["layer"] for x in by_id.values()}
    missing = set(ALL_LAYERS) - available
    if not isinstance(answer.get("missing_layers"), list) or set(answer["missing_layers"]) != missing or len(answer["missing_layers"]) != len(missing):
        raise ValueError("must disclose missing evidence layer(s) exactly")
    alignments, rejected = [], []
    for i, candidate in enumerate(answer["alignments"]):
        try:
            if not isinstance(candidate, dict):
                raise ValueError("candidate must be object")
            ids_by_layer = {}
            for layer in ALL_LAYERS:
                raw = candidate.get(layer + "_ids")
                if not isinstance(raw, list) or len(raw) > 4 or len(raw) != len(set(raw)):
                    raise ValueError("invalid candidate source IDs")
                if any(not isinstance(sid, str) or sid not in by_id or by_id[sid]["layer"] != layer for sid in raw):
                    raise ValueError("source assigned to wrong perspective")
                ids_by_layer[layer] = raw
            if not ids_by_layer["academic"] or not (ids_by_layer["practical"] or ids_by_layer["program"]):
                raise ValueError("cannot support a cross-layer alignment with only academic sources")
            fields = {k: _text(candidate.get(k), field=k) for k in (
                "mechanism", "interpretation", "solution_fit", "evidence_tension", "counterargument", "next_test")}
            if ids_by_layer["program"] == [] and any(word in fields["solution_fit"].lower()
                        for word in ("implemented", "deployed", "successful", "achieved")):
                raise ValueError("claimed program capability without program source")
            support = []
            cited = {sid for rows in ids_by_layer.values() for sid in rows}
            if selected.get("original_text_attached"):
                claims = candidate.get("citations")
                if not isinstance(claims, list) or not 1 <= len(claims) <= 12:
                    raise ValueError("original-source quotes required")
                seen_support = set()
                for item in claims:
                    if not isinstance(item, dict) or item.get("source_id") not in cited:
                        raise ValueError("citation refers to unselected source")
                    sid = item["source_id"]
                    quote = item.get("quote")
                    if (not isinstance(quote, str) or not 14 <= len(quote) <= 800 or
                            " ".join(quote.split()).casefold() not in
                            " ".join(by_id[sid]["original_text"].split()).casefold()):
                        raise ValueError("quote not present in original development source")
                    seen_support.add(sid)
                    support.append({"source_id": sid, "quote": quote,
                                    "source_url": by_id[sid]["source_url"]})
                if seen_support != cited:
                    raise ValueError("every linked source needs an original-text quote")
            alignments.append({
                "original_source_quotes": support,
                "source_text_checked": bool(selected.get("original_text_attached")),
                "id": "alignment-"+str(i+1),
                "perspectives": {layer: [{
                    "source_id": sid,
                    "source_url": by_id[sid]["source_url"],
                    "source_reading": by_id[sid]["claim"],
                    "source_scope": by_id[sid]["scope"],
                    "source_caveat": by_id[sid]["caveat"],
                } for sid in ids_by_layer[layer]] for layer in ALL_LAYERS},
                **fields, "complete_three_layer_stack": all(ids_by_layer.values()),
                "status": "llm_candidate_requires_independent_source_review",
                "outcome_verified": False,
            })
        except (ValueError, TypeError) as exc:
            rejected.append({"candidate": i+1, "reason": str(exc)})
    return {
        "schema": "cite_refinery.cross_layer_alignment.v1",
        "topic": selected["topic"], "alignments": alignments,
        "rejected_candidates": rejected, "missing_layers": sorted(missing),
        "authority": "MODEL_GENERATED_HYPOTHESIS_ONLY",
        "boundary": ("Original source excerpts and quote existence were checked, but semantic "
                     "entailment is NOT independently validated. " if selected.get("original_text_attached") else
                     "A second LLM interpreted first-pass LLM source readings, not original documents. ") +
                    "No independent causal validation or field outcome approval.",
    }
