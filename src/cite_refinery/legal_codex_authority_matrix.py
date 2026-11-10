"""Versioned procurement-authority questions, not a guilt or employment classifier.

A statute allocates duties to *offices*. A particular person's power requires
a contemporaneous appointment or delegation instrument for the actual funding
stream, procurement package, and date. This runner will not guess that missing
instrument from a job title, a later witness statement or graph proximity.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "legal_codex.procurement_authority_matrix.v1"
_ROLES = {"PA", "KPA", "PPK", "Pokja", "PejabatPengadaan"}
_ACTIONS = {
    "technical_specification", "price_estimate", "draft_contract", "contract_oversight",
    "procurement_plan", "appoint_ppk", "delegate_budget", "select_supplier",
}
_PRECISIONS = {"day", "month", "year"}
_ID = re.compile(r"[a-z][a-z0-9_]{2,79}\Z")


def _date(value):
    if not isinstance(value, str):
        raise ValueError("date must be ISO")
    return date.fromisoformat(value)


def _period(value, precision):
    if precision == "day":
        d = _date(value)
        return d, d
    if precision == "month":
        if not re.fullmatch(r"\d{4}-\d{2}", value):
            raise ValueError("month requires YYYY-MM")
        first = _date(value + "-01")
        if first.month == 12:
            last = date(first.year + 1, 1, 1).toordinal() - 1
        else:
            last = date(first.year, first.month + 1, 1).toordinal() - 1
        return first, date.fromordinal(last)
    if precision == "year":
        if not re.fullmatch(r"\d{4}", value):
            raise ValueError("year requires YYYY")
        return date(int(value), 1, 1), date(int(value), 12, 31)
    raise ValueError("invalid date precision")


def _ids(rows, label):
    if not isinstance(rows, list) or not rows:
        raise ValueError("nonempty " + label + " list required")
    out = {}
    for row in rows:
        key = row.get("id") if isinstance(row, dict) else None
        if not isinstance(key, str) or not _ID.fullmatch(key) or key in out:
            raise ValueError(f"invalid or duplicate {label} ID")
        out[key] = row
    return out


def _url(u):
    try:
        p = urlsplit(u)
        return p.scheme == "https" and bool(p.hostname) and not p.username and not p.password
    except (TypeError, ValueError):
        return False


def validate(bundle):
    if not isinstance(bundle, dict) or bundle.get("schema") != SCHEMA:
        raise ValueError("unsupported procurement authority matrix")
    sources = _ids(bundle.get("legal_sources"), "source")
    rules = _ids(bundle.get("role_rules"), "rule")
    decisions = _ids(bundle.get("decision_questions"), "decision")
    if bundle.get("person_assignments") != []:
        raise ValueError("person assignments require signed appointment records; none supplied")
    for key, source in sources.items():
        if not _url(source.get("url")) or source.get("jurisdiction") != "Indonesia":
            raise ValueError(f"{key}: invalid source or jurisdiction")
        if source.get("original_bytes_captured") is not False:
            raise ValueError(f"{key}: cannot imply original source capture")
        _date(source.get("effective_from"))
        if source.get("effective_until") is not None:
            _date(source["effective_until"])
    for key, rule in rules.items():
        ref = sources.get(rule.get("source_id"))
        if ref is None or rule.get("role") not in _ROLES:
            raise ValueError(f"{key}: unknown legal role or source")
        if rule.get("authority") not in _ACTIONS:
            raise ValueError(f"{key}: unsupported role authority")
        if not isinstance(rule.get("article"), str) or not rule["article"].startswith("Pasal "):
            raise ValueError(f"{key}: missing article")
        if rule.get("state") != "candidate_statuory_duty_unreviewed":
            raise ValueError(f"{key}: rule may not self-certify legal applicability")
        if rule.get("scope") != "government_procurement_APBN_or_APBD":
            raise ValueError(f"{key}: unsupported statutory scope")
        if not isinstance(rule.get("text_basis"), str) or len(rule["text_basis"]) < 20:
            raise ValueError(f"{key}: missing statutory text description")
        if rule["source_id"] != "perpres_2018" and rule["source_id"] != "perpres_2021":
            raise ValueError(f"{key}: unsupported statutory version")
    if {x["source_id"] for x in rules.values()} != {"perpres_2018", "perpres_2021"}:
        raise ValueError("both historical rule versions required")
    for key, question in decisions.items():
        if question.get("authority") not in _ACTIONS:
            raise ValueError(f"{key}: invalid decision function")
        if question.get("event_date_precision") not in _PRECISIONS:
            raise ValueError(f"{key}: invalid event date precision")
        first, last = _period(question.get("event_date"), question["event_date_precision"])
        if first > last:
            raise ValueError(f"{key}: invalid date range")
        if question.get("provenance_status") != "source_reported_not_adjudicated":
            raise ValueError(f"{key}: decision may not be presumed verified")
        if question.get("named_authority_holder") is not None:
            raise ValueError(f"{key}: cannot infer named authority holder from allegation")
        if question.get("funding_stream") not in {"APBN", "DAK", "unknown"}:
            raise ValueError(f"{key}: unknown funding")
        if not isinstance(question.get("source_ref"), str) or not _url(question["source_ref"]):
            raise ValueError(f"{key}: missing question provenance")
    return sources, rules, decisions


def evaluate(bundle):
    sources, rules, questions = validate(bundle)
    findings = []
    for q in sorted(questions.values(), key=lambda x: x["id"]):
        first, last = _period(q["event_date"], q["event_date_precision"])
        matching = []
        for r in rules.values():
            if r["authority"] != q["authority"]:
                continue
            s = sources[r["source_id"]]
            beginning = _date(s["effective_from"])
            ending = _date(s["effective_until"]) if s.get("effective_until") else date.max
            if beginning <= last and first <= ending:
                matching.append({
                    "role_rule_id": r["id"], "statutory_role": r["role"],
                    "article": r["article"], "legal_source": s["url"],
                    "role_not_person": True,
                })
        matching.sort(key=lambda x: x["role_rule_id"])
        distinct_sources = {r["legal_source"] for r in matching}
        findings.append({
            "decision_id": q["id"],
            "event_date": q["event_date"], "event_date_precision": q["event_date_precision"],
            "funding_stream": q["funding_stream"],
            "possible_statutory_roles": matching,
            "version_uncertainty": "amendment_boundary_intersects_date" if len(distinct_sources) > 1 else
                                   "no_matching_candidate_rule" if not matching else "none_in_curated_rules",
            "actual_authority_holder": None,
            "delegation_instrument": None,
            "signed_specification_or_contract": None,
            "person_officially_linked_to_procurement": False,
            "legal_violation_established": False,
            "source_claim_review": "pending",
        })
    return {
        "schema": "legal_codex.procurement_authority_result.v1",
        "case_family": "indonesia_chromebook_procurement",
        "decisions": findings,
        "source_count": len(sources),
        "rule_count": len(rules),
        "appointment_records_verified": 0,
        "identity_assignments_inferred": 0,
        "role_matching_is_not_individual_attribution": True,
        "rule_coverage_is_not_comprehensive_legal_opinion": True,
        "publication_authorized": False,
    }


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--output", default="legal_codex_authority_matrix_result.json")
    args = p.parse_args(argv)
    result = evaluate(json.loads(Path(args.input).read_text(encoding="utf-8")))
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision_questions": len(result["decisions"]),
        "named_officials_inferred": 0,
        "publication_authorized": False,
    }))


if __name__ == "__main__":
    main()
