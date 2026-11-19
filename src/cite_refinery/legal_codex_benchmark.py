"""First three-case Global Legal Codex integration gate.

Source leads are curated, not independently authenticated. All outputs are
neutral candidates for Cite-Refinery, not verified legal or causal findings.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "legal_codex.benchmark.v1"


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def records(items, kind):
    if not isinstance(items, list) or not items:
        raise ValueError(f"{kind} must be nonempty")
    out = {}
    for item in items:
        key = item.get("id")
        if not isinstance(key, str) or not key or key in out:
            raise ValueError(f"invalid or repeated {kind} ID")
        out[key] = item
    return out


def checked(bundle):
    if bundle.get("schema") != SCHEMA:
        raise ValueError("unsupported schema")
    src = records(bundle.get("sources"), "source")
    cases = records(bundle.get("cases"), "case")
    claims = records(bundle.get("claims"), "claim")
    mechanisms = records(bundle.get("mechanisms"), "mechanism")
    if len(cases) < 3:
        raise ValueError("three independent cases required")
    for key, s in src.items():
        url = urlsplit(s.get("url", ""))
        if url.scheme != "https" or not url.netloc or url.username or url.password:
            raise ValueError(f"{key}: invalid source URL")
        date.fromisoformat(s["published"])
        if (not isinstance(s.get("excerpt"), str) or len(s["excerpt"]) < 12
                or sha(s["excerpt"]) != s.get("excerpt_sha256")):
            raise ValueError(f"{key}: missing or altered excerpt")
        if s.get("custody") != "excerpt_only_unverified":
            raise ValueError(f"{key}: unsupported authenticated-source claim")
    for key, case in cases.items():
        date.fromisoformat(case["anchor_date"])
        if not case.get("failure_modes") or case.get("primary_claim") not in claims:
            raise ValueError(f"{key}: missing case facts")
        if claims[case["primary_claim"]].get("case_id") != key:
            raise ValueError(f"{key}: primary claim belongs to another case")
    for key, c in claims.items():
        if c.get("case_id") not in cases:
            raise ValueError(f"{key}: unknown case")
        if c.get("review") != "unreviewed":
            raise ValueError(f"{key}: cannot manufacture editorial approval")
        if c.get("kind") not in {"incident", "legal_rule", "institutional_action", "outcome"}:
            raise ValueError(f"{key}: causal effects and personal blame require expert assessment")
        if len(c.get("statement", "")) < 15 or not c.get("support"):
            raise ValueError(f"{key}: incomplete claim")
        for ref in c["support"]:
            if ref.get("source_id") not in src:
                raise ValueError(f"{key}: unknown source")
            q = ref.get("quote")
            if not isinstance(q, str) or not q or q not in src[ref["source_id"]]["excerpt"]:
                raise ValueError(f"{key}: quoted passage not found")
        if c["kind"] == "legal_rule":
            if not c.get("jurisdiction") or not c.get("effective_from"):
                raise ValueError(f"{key}: law lacks jurisdiction/date")
            date.fromisoformat(c["effective_from"])
    for key, m in mechanisms.items():
        if m.get("supporting_claim") not in claims or not m.get("addresses"):
            raise ValueError(f"{key}: unsupported mechanism")
        date.fromisoformat(m["available_from"])
        if m.get("effect_estimate") is not None:
            raise ValueError(f"{key}: invented policy impact estimate")
    return src, cases, claims, mechanisms


def evaluate(bundle):
    sources, cases, claims, mechanisms = checked(bundle)
    result = []
    for case in sorted(cases.values(), key=lambda x: x["id"]):
        anchor = date.fromisoformat(case["anchor_date"])
        alternatives, later = [], []
        for m in sorted(mechanisms.values(), key=lambda x: x["id"]):
            overlap = sorted(set(case["failure_modes"]) & set(m["addresses"]))
            if not overlap or m.get("source_case") == case["id"]:
                continue
            candidate = {"mechanism_id": m["id"], "matched_issues": overlap,
                         "effect_estimate": None, "status": "unreviewed_candidate"}
            if date.fromisoformat(m["available_from"]) > anchor:
                later.append({**candidate, "reason": "not_available_at_case_date"})
            else:
                alternatives.append(candidate)
        valid_rules = [
            c["id"] for c in claims.values()
            if c["case_id"] == case["id"] and c["kind"] == "legal_rule"
            and c["jurisdiction"] == case["jurisdiction"]
            and date.fromisoformat(c["effective_from"]) <= anchor
        ]
        result.append({"case_id": case["id"], "jurisdiction": case["jurisdiction"],
                       "candidate_alternatives": alternatives, "later_alternatives": later,
                       "applicable_rule_candidates": sorted(valid_rules),
                       "causal_effect": None, "personal_culpability": "not_established",
                       "publication": "hold_for_independent_review"})
    return {"schema": "legal_codex.benchmark_result.v1", "cases": result,
            "source_count": len(sources), "claim_count": len(claims),
            "source_authentication": "not_performed",
            "authority": "neutral_candidate_only", "publication_authorized": False,
            "input_digest": sha(json.dumps(bundle, ensure_ascii=False, sort_keys=True))}


def semantic_packet(bundle, result):
    if result["input_digest"] != sha(json.dumps(bundle, ensure_ascii=False, sort_keys=True)):
        raise ValueError("stale result/changed sources")
    sources, cases, claims, mechanisms = checked(bundle)
    nodes, edges = [], []
    for s in sources.values():
        nodes.append({"key": "source-" + s["id"],
                      "statement": s["url"], "kind": "source", "layer": "neutral",
                      "source_refs": [s["url"]],
                      "provenance": {"excerpt_sha256": s["excerpt_sha256"],
                                     "custody": "excerpt_only_unverified"}})
    for case in cases.values():
        nodes.append({"key": "case-" + case["id"], "statement": case["title"],
                      "kind": "concept", "layer": "neutral"})
    for c in claims.values():
        nodes.append({"key": "claim-" + c["id"], "statement": c["statement"],
                      "kind": "observation", "layer": "neutral",
                      "source_refs": [sources[r["source_id"]]["url"] for r in c["support"]],
                      "provenance": {"editorial_review": "unreviewed",
                                     "boundary": "quote containment is not entailment"}})
        edges.append({"source": "case-" + c["case_id"], "target": "claim-" + c["id"],
                      "relation": "CONTEXT_FOR", "status": "candidate"})
        for ref in c["support"]:
            edges.append({"source": "source-" + ref["source_id"],
                          "target": "claim-" + c["id"], "relation": "SUPPORTS",
                          "status": "candidate"})
    for case in result["cases"]:
        for m in case["candidate_alternatives"]:
            edges.append({"source": "claim-" + mechanisms[m["mechanism_id"]]["supporting_claim"],
                          "target": "case-" + case["case_id"], "relation": "ADAPTABLE_TO",
                          "status": "candidate"})
    return {"schema": "cite_refinery.semantic_graph.v1",
            "source_system": "legal-codex-benchmark", "clusters": [],
            "nodes": nodes, "edges": edges}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--output", default="legal_codex_result.json")
    parser.add_argument("--packet", help="Optional output of Cite-Refinery graph packet")
    args = parser.parse_args(argv)
    bundle = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = evaluate(bundle)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.packet:
        Path(args.packet).write_text(
            json.dumps(semantic_packet(bundle, result), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
    print(json.dumps({"cases": len(result["cases"]), "publication_authorized": False,
                      "causal_effects_estimated": 0}))


if __name__ == "__main__":
    main()
