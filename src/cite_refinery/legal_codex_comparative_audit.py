"""Milestone 011: source-attributed comparative legal audit, not a legal oracle.

This runner compares institutional failure modes and remedies across case families.
An official locator is not archived evidence; an institutional statement is not
an independent causal or individual-liability finding. Foreign legal instruments
are never applied to another jurisdiction merely because mechanisms resemble one
another. All graph edges are candidates pending source and expert review.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

SCHEMA = "legal_codex.comparative_audit.v1"
_SOURCE_HOSTS = {
    "statute": {"legislation.gov.uk"},
    "independent_review_body": {"ccrc.gov.uk"},
    "statutory_inquiry": {"postofficehorizoninquiry.org.uk"},
    "parliamentary_report": {"tweedekamer.nl"},
    "regulator_enforcement": {"autoriteitpersoonsgegevens.nl"},
}
_FINDING_KINDS = {
    "official_review", "institutional_critique", "regulatory_determination",
    "legislative_response", "statutory_inquiry_finding",
}
_MECHANISM_POWERS = {
    "independent_case_review": "review_referral",
    "statutory_quashing": "criminal_conviction_relief",
    "statutory_inquiry": "institutional_fact_finding",
    "parliamentary_scrutiny": "institutional_fact_finding",
    "regulator_enforcement": "administrative_sanction",
}
_REQUIRED = {
    "bundle": {"schema", "as_of", "original_documents_archived",
               "independent_editorial_review", "cases", "sources", "findings",
               "interventions", "comparisons", "evidence_gaps"},
    "case": {"id", "title", "jurisdiction", "failure_period_start",
             "failure_period_end", "failure_modes", "institutions"},
    "institution": {"id", "name", "role"},
    "source": {"id", "case_id", "url", "published_on", "kind",
               "jurisdictions", "custody", "original_bytes_verified"},
    "finding": {"id", "case_id", "source_id", "institution_id", "kind",
                "observed_on", "statement", "attribution",
                "original_document_read", "independent_causal_effect"},
    "intervention": {"id", "case_id", "source_id", "source_finding_id",
                     "mechanism", "power", "effective_on", "jurisdictions",
                     "scope_note", "individual_remedy_proven",
                     "measured_preventive_effect", "claims_foreign_applicability"},
    "comparison": {"id", "left_case_id", "right_case_id", "left_intervention_id",
                   "right_intervention_id", "failure_mode", "transfer_status",
                   "analysis", "equivalence_proven", "effect_size"},
    "gap": {"id", "case_id", "record_needed", "question", "priority"},
}
_ID = re.compile(r"[a-z][a-z0-9_]{2,70}\Z")


def _expect(row, kind):
    if not isinstance(row, dict) or set(row) != _REQUIRED[kind]:
        raise ValueError(f"{kind}: missing or unsupported fields")


def _indexed(items, kind):
    if not isinstance(items, list) or not items:
        raise ValueError(f"{kind}: nonempty list required")
    result = {}
    for row in items:
        _expect(row, kind)
        key = row["id"]
        if not isinstance(key, str) or not _ID.fullmatch(key) or key in result:
            raise ValueError(f"{kind}: duplicate or invalid ID")
        result[key] = row
    return result


def _date(raw):
    if not isinstance(raw, str):
        raise ValueError("date must be ISO text")
    return date.fromisoformat(raw)


def _text(raw, minimum=20):
    return isinstance(raw, str) and len(raw.strip()) >= minimum


def _jurisdictions(raw):
    return (isinstance(raw, list) and bool(raw) and
            len(raw) == len(set(raw)) and
            all(_text(v, 4) for v in raw))


def _digest(data):
    return hashlib.sha256(json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def validate(bundle):
    _expect(bundle, "bundle")
    if bundle["schema"] != SCHEMA:
        raise ValueError("unsupported comparative audit schema")
    if bundle["original_documents_archived"] is not False:
        raise ValueError("unarchived original files cannot be promoted")
    if bundle["independent_editorial_review"] is not False:
        raise ValueError("independent reviewer approval not established")
    as_of = _date(bundle["as_of"])
    cases = _indexed(bundle["cases"], "case")
    if len(cases) < 2 or len({c["jurisdiction"] for c in cases.values()}) < 2:
        raise ValueError("comparative audit requires two distinct jurisdictions")
    institutions = {}
    for case in cases.values():
        first, last = _date(case["failure_period_start"]), _date(case["failure_period_end"])
        if first > last or last > as_of:
            raise ValueError("invalid historical failure period")
        if not _text(case["title"]) or not _text(case["jurisdiction"], 4):
            raise ValueError("incomplete case")
        if (not isinstance(case["failure_modes"], list) or
                len(case["failure_modes"]) < 2 or
                len(set(case["failure_modes"])) != len(case["failure_modes"]) or
                not all(isinstance(m, str) and _ID.fullmatch(m) for m in case["failure_modes"])):
            raise ValueError("case failure modes are incomplete")
        case_institutions = _indexed(case["institutions"], "institution")
        if not all(_text(v["name"], 4) and _text(v["role"], 8)
                   for v in case_institutions.values()):
            raise ValueError("institutional role lacks attribution")
        for inst_id, inst in case_institutions.items():
            if inst_id in institutions:
                raise ValueError("institution IDs must be unambiguous across cases")
            institutions[inst_id] = (case["id"], inst)
    sources = _indexed(bundle["sources"], "source")
    for src in sources.values():
        if src["case_id"] not in cases:
            raise ValueError("source references unknown case")
        if (src["custody"] != "public_locator_unarchived" or
                src["original_bytes_verified"] is not False):
            raise ValueError("source page must not impersonate archived original")
        parsed = urlsplit(src["url"])
        allowed = _SOURCE_HOSTS.get(src["kind"])
        if (not allowed or parsed.scheme != "https" or parsed.hostname.removeprefix("www.") not in allowed or
                parsed.username or parsed.password or parsed.port not in (None, 443) or
                not parsed.path or parsed.path == "/"):
            raise ValueError("source host/type provenance invalid")
        if not _jurisdictions(src["jurisdictions"]) or cases[src["case_id"]]["jurisdiction"] not in src["jurisdictions"]:
            raise ValueError("source jurisdiction cannot cover case")
        if _date(src["published_on"]) > as_of:
            raise ValueError("future official source cannot support this audit")
    findings = _indexed(bundle["findings"], "finding")
    for f in findings.values():
        c, s, inst = cases.get(f["case_id"]), sources.get(f["source_id"]), institutions.get(f["institution_id"])
        if c is None or s is None or inst is None or s["case_id"] != f["case_id"] or inst[0] != f["case_id"]:
            raise ValueError("finding has crossed case/source/institution boundaries")
        if (f["kind"] not in _FINDING_KINDS or
                f["attribution"] != "official_body_statement_not_our_finding" or
                f["original_document_read"] is not False or
                f["independent_causal_effect"] is not None or
                not _text(f["statement"], 35)):
            raise ValueError("unsupported or overclaimed finding")
        kinds = {
            "official_review": "independent_review_body",
            "institutional_critique": "parliamentary_report",
            "regulatory_determination": "regulator_enforcement",
            "legislative_response": "statute",
            "statutory_inquiry_finding": "statutory_inquiry",
        }
        if s["kind"] != kinds[f["kind"]]:
            raise ValueError("finding impersonates a different type of authority")
        when = _date(f["observed_on"])
        if when != _date(s["published_on"]) or when > as_of:
            raise ValueError("finding date must equal the cited official publication date; no backdating")
    interventions = _indexed(bundle["interventions"], "intervention")
    for action in interventions.values():
        c, s = cases.get(action["case_id"]), sources.get(action["source_id"])
        f = findings.get(action["source_finding_id"])
        if (c is None or s is None or f is None or
                f["case_id"] != action["case_id"] or
                f["source_id"] != action["source_id"] or
                s["case_id"] != action["case_id"]):
            raise ValueError("intervention not grounded in same-case source and finding")
        if (action["mechanism"] not in _MECHANISM_POWERS or
                action["power"] != _MECHANISM_POWERS[action["mechanism"]] or
                not _jurisdictions(action["jurisdictions"]) or
                c["jurisdiction"] not in action["jurisdictions"] or
                not set(action["jurisdictions"]).issubset(s["jurisdictions"]) or
                not _text(action["scope_note"], 35)):
            raise ValueError("intervention power or jurisdiction not supported")
        if (action["individual_remedy_proven"] is not False or
                action["measured_preventive_effect"] is not None or
                action["claims_foreign_applicability"] is not False):
            raise ValueError("unverified remedy, impact or foreign-law transfer")
        when = _date(action["effective_on"])
        if when != _date(s["published_on"]) or when != _date(f["observed_on"]) or when > as_of:
            raise ValueError("intervention cannot be backdated beyond official publication")
        expected = {
            "statutory_quashing": "legislative_response",
            "independent_case_review": "official_review",
            "statutory_inquiry": "statutory_inquiry_finding",
            "parliamentary_scrutiny": "institutional_critique",
            "regulator_enforcement": "regulatory_determination",
        }
        if f["kind"] != expected[action["mechanism"]]:
            raise ValueError("mechanism incompatible with institutional source")
    comparisons = _indexed(bundle["comparisons"], "comparison")
    seen_pairs = set()
    for comp in comparisons.values():
        a, b = cases.get(comp["left_case_id"]), cases.get(comp["right_case_id"])
        x, y = interventions.get(comp["left_intervention_id"]), interventions.get(comp["right_intervention_id"])
        if (a is None or b is None or x is None or y is None or
                a["id"] == b["id"] or a["jurisdiction"] == b["jurisdiction"] or
                x["case_id"] != a["id"] or y["case_id"] != b["id"]):
            raise ValueError("comparison requires distinct case-local mechanisms")
        if comp["failure_mode"] not in a["failure_modes"] or comp["failure_mode"] not in b["failure_modes"]:
            raise ValueError("comparison lacks a shared failure mode")
        if (comp["transfer_status"] not in {"analogy_only", "non_equivalent_remedies"} or
                comp["equivalence_proven"] is not False or
                comp["effect_size"] is not None or
                not _text(comp["analysis"], 70)):
            raise ValueError("comparison cannot certify legal equivalence or causal effect")
        pair = (x["id"], y["id"])
        if pair in seen_pairs:
            raise ValueError("duplicated comparative mechanism pair")
        seen_pairs.add(pair)
    gaps = _indexed(bundle["evidence_gaps"], "gap")
    for gap in gaps.values():
        if (gap["case_id"] not in cases or
                gap["priority"] not in {"critical", "important"} or
                not _text(gap["record_needed"], 15) or
                not _text(gap["question"], 25)):
            raise ValueError("unusable evidence-gathering request")
    if {g["case_id"] for g in gaps.values()} != set(cases):
        raise ValueError("each case needs original-record gaps")
    if {f["case_id"] for f in findings.values()} != set(cases):
        raise ValueError("each case needs source-linked findings")
    return cases, institutions, sources, findings, interventions, comparisons, gaps


def evaluate(bundle):
    cases, institutions, sources, findings, interventions, comparisons, gaps = validate(bundle)
    case_rows = []
    for c in sorted(cases.values(), key=lambda c: c["id"]):
        relevant_actions = [a for a in interventions.values() if a["case_id"] == c["id"]]
        case_rows.append({
            "case_id": c["id"], "jurisdiction": c["jurisdiction"],
            "failure_period": [c["failure_period_start"], c["failure_period_end"]],
            "institutions": [
                {"id": i["id"], "name": i["name"], "source_attributed_role": i["role"],
                 "individual_liability_found": False}
                for i in c["institutions"]
            ],
            "official_source_locators": sorted(s["url"] for s in sources.values() if s["case_id"] == c["id"]),
            "attributed_findings": [
                {"id": f["id"], "kind": f["kind"], "statement": f["statement"],
                 "source_url": sources[f["source_id"]]["url"],
                 "editorially_verified": False}
                for f in sorted(findings.values(), key=lambda f: f["id"])
                if f["case_id"] == c["id"]
            ],
            "interventions": [
                {"id": a["id"], "mechanism": a["mechanism"], "legal_power": a["power"],
                 "effective_on": a["effective_on"],
                 "time_relative_to_failure": "post_failure_period" if _date(a["effective_on"]) > _date(c["failure_period_end"]) else "overlaps_failure_period",
                 "scope": a["scope_note"], "source_url": sources[a["source_id"]]["url"],
                 "demonstrated_preventive_effect": False, "individual_redress_verified": False}
                for a in sorted(relevant_actions, key=lambda a: a["id"])
            ],
            "unresolved_record_requests": [
                {"id": g["id"], "record_needed": g["record_needed"],
                 "research_question": g["question"], "priority": g["priority"]}
                for g in sorted(gaps.values(), key=lambda g: g["id"]) if g["case_id"] == c["id"]
            ],
        })
    comparison_rows = []
    for comp in sorted(comparisons.values(), key=lambda comp: comp["id"]):
        comparison_rows.append({
            "id": comp["id"], "cases": [comp["left_case_id"], comp["right_case_id"]],
            "failure_mode": comp["failure_mode"],
            "interventions": [comp["left_intervention_id"], comp["right_intervention_id"]],
            "transfer_status": comp["transfer_status"], "analysis": comp["analysis"],
            "foreign_law_applicable": False, "legal_equivalence_established": False,
            "policy_effect_estimate": None,
        })
    return {
        "schema": "legal_codex.comparative_audit_result.v1",
        "as_of": bundle["as_of"], "case_count": len(cases),
        "institution_count": len(institutions), "source_locator_count": len(sources),
        "attributed_finding_count": len(findings),
        "intervention_count": len(interventions), "comparison_count": len(comparisons),
        "cases": case_rows, "comparisons": comparison_rows,
        "source_byte_integrity_verified": False, "independent_editorial_review": False,
        "named_person_culpability_established": False, "causal_policy_effect_estimated": False,
        "cross_jurisdiction_law_applied": False, "publication_authorized": False,
        "input_digest": _digest(bundle),
    }


def semantic_packet(bundle, result):
    if result.get("input_digest") != _digest(bundle):
        raise ValueError("comparative audit result is stale")
    cases, institutions, sources, findings, interventions, comparisons, _ = validate(bundle)
    nodes, edges = [], []
    for c in cases.values():
        nodes.append({"key": "case-" + c["id"], "kind": "concept",
                      "layer": "neutral", "statement": c["title"]})
    for s in sources.values():
        nodes.append({"key": "source-" + s["id"], "kind": "source", "layer": "neutral",
                      "statement": s["url"], "source_refs": [s["url"]],
                      "provenance": {"custody": s["custody"],
                                     "original_bytes_verified": False}})
    for inst_id, (case_id, inst) in institutions.items():
        nodes.append({"key": "institution-" + inst_id, "kind": "concept", "layer": "neutral",
                      "statement": inst["name"] + ": " + inst["role"],
                      "provenance": {"individual_culpability_established": False}})
        edges.append({"source": "case-" + case_id,
                      "target": "institution-" + inst_id,
                      "relation": "INSTITUTIONAL_CONTEXT", "status": "candidate"})
    for f in findings.values():
        nodes.append({"key": "finding-" + f["id"], "kind": "observation", "layer": "neutral",
                      "statement": f["statement"], "source_refs": [sources[f["source_id"]]["url"]],
                      "provenance": {"review": "source_attributed_unreviewed",
                                     "source_original_archived": False,
                                     "causal_effect_established": False}})
        for origin, rel in (
            ("case-" + f["case_id"], "CONTEXT_FOR"),
            ("source-" + f["source_id"], "REPORTS"),
            ("institution-" + f["institution_id"], "SOURCE_ATTRIBUTES_TO_INSTITUTION"),
        ):
            edges.append({"source": origin, "target": "finding-" + f["id"],
                          "relation": rel, "status": "candidate"})
    for a in interventions.values():
        nodes.append({"key": "intervention-" + a["id"], "kind": "concept", "layer": "neutral",
                      "statement": a["scope_note"], "source_refs": [sources[a["source_id"]]["url"]],
                      "provenance": {"mechanism": a["mechanism"], "power": a["power"],
                                     "legal_scope": a["jurisdictions"],
                                     "foreign_applicability": False}})
        edges.append({"source": "finding-" + a["source_finding_id"],
                      "target": "intervention-" + a["id"],
                      "relation": "DESCRIBES_REPORTED_INTERVENTION", "status": "candidate"})
    for cmp in comparisons.values():
        edges.append({
            "source": "intervention-" + cmp["left_intervention_id"],
            "target": "intervention-" + cmp["right_intervention_id"],
            "relation": "COMPARABLE_MECHANISM_CANDIDATE",
            "status": "candidate",
            "provenance": {"foreign_law_applicable": False,
                           "legal_equivalence_established": False,
                           "causal_effect_established": False},
        })
    return {"schema": "cite_refinery.semantic_graph.v1",
            "source_system": "legal-codex-comparative-audit-011",
            "clusters": [], "nodes": nodes, "edges": edges}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--output", default="legal_codex_comparative_011_result.json")
    p.add_argument("--packet", help="Optional candidate-only semantic graph JSON")
    args = p.parse_args(argv)
    bundle = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = evaluate(bundle)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.packet:
        Path(args.packet).write_text(json.dumps(
            semantic_packet(bundle, result), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "cases": result["case_count"], "comparisons": result["comparison_count"],
        "foreign_law_applied": False, "causal_effect_estimated": False,
        "publication_authorized": False,
    }))


if __name__ == "__main__":
    main()
