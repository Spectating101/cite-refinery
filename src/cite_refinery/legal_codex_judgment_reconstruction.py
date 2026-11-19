"""Milestone 012: source-anchored three-judgment reconstruction.

A source locator and human-selected paragraph are not archived, authenticated
judgment bytes or machine-proven semantic entailment. Neither a foreign court's
reasoning nor a later act is treated as applicable law in another jurisdiction.
This tool emits reviewed-location CANDIDATES for independent legal adjudication.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

SCHEMA = "legal_codex.judgment_reconstruction.v1"

PINNED = {
    "hamilton_2021": {
        "jurisdiction": "England and Wales",
        "docket": "[2021] EWCA Crim 577",
        "url": "https://www.judiciary.uk/wp-content/uploads/2022/07/Hamilton-Others-v-Post-Office-judgment-230421.pdf",
        "date": "2021-04-23",
        "format": "pdf",
        "allowed_paragraphs": {"121", "136", "137", "440", "447"},
    },
    "dutch_3535": {
        "jurisdiction": "Netherlands",
        "docket": "ECLI:NL:RVS:2019:3535",
        "url": "https://www.raadvanstate.nl/uitspraken/@118143/201900753-1-a2/",
        "date": "2019-10-23",
        "format": "html",
        "allowed_paragraphs": {"8.11", "9", "10"},
    },
    "dutch_3536": {
        "jurisdiction": "Netherlands",
        "docket": "ECLI:NL:RVS:2019:3536",
        "url": "https://www.raadvanstate.nl/uitspraken/@118142/201802802-1-a2/",
        "date": "2019-10-23",
        "format": "html",
        "allowed_paragraphs": {"5.6", "5.12", "5.14", "6", "7"},
    },
}
KIND = {
    "reliability_and_disclosure": ("hamilton_2021", "121"),
    "prosecution_abuse": ("hamilton_2021", "137"),
    "individual_motive_not_adjudicated": ("hamilton_2021", "136"),
    "case_specific_exception": ("hamilton_2021", "440"),
    "mixed_appeal_disposition": ("hamilton_2021", "447"),
    "proportionate_entitlement": ("dutch_3535", "8.11"),
    "entitlement_remittal": ("dutch_3535", "9"),
    "entitlement_no_final_amount": ("dutch_3535", "10"),
    "third_party_liability_nonretroactive": ("dutch_3536", "5.6"),
    "proportionate_recovery": ("dutch_3536", "5.12"),
    "case_specific_disproportion": ("dutch_3536", "5.14"),
    "recovery_remittal": ("dutch_3536", "6"),
    "recovery_deadline": ("dutch_3536", "7"),
}
GROUNDS = {
    "hamilton_2021": {"criminal_prosecution_disclosure", "horizon_evidentiary_reliability",
                      "abuse_of_process"},
    "dutch_3535": {"wko_1_7", "wko_1_52", "awb_3_4", "awb_7_12"},
    "dutch_3536": {"awir_26", "awir_33_3", "awb_3_4", "awb_7_12"},
}
EXPECTED_OUTCOMES = {
    "hamilton_2021": ("mixed_quashing_and_dismissal", 42, 39, 3, False),
    "dutch_3535": ("remittal_for_new_entitlement_decision", None, None, None, False),
    "dutch_3536": ("remittal_for_new_recovery_decision", None, None, None, False),
}
REQUIRED_EXCLUSIONS = {
    "dutch_nationality_profiling_adjudicated",
    "dutch_dpa_fine_ordered_by_2019_judgments",
    "uk_2024_act_used_in_2021_judgment",
    "individual_compensation_amount_proven",
    "foreign_case_law_directly_applied",
    "indonesia_ppk_signature_established",
}
_ID = re.compile(r"[a-z][a-z0-9_]{2,64}\Z")
_PARA = re.compile(r"[1-9]\d*(?:\.[1-9]\d*)?\Z")


def _digest(bundle):
    return hashlib.sha256(json.dumps(
        bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def _date(value):
    if not isinstance(value, str):
        raise ValueError("date must be an ISO string")
    return date.fromisoformat(value)


def _rows(data, kind):
    if not isinstance(data, list) or not data:
        raise ValueError(kind + " nonempty list required")
    result = {}
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("invalid " + kind)
        ident = item.get("id")
        if not isinstance(ident, str) or not _ID.fullmatch(ident) or ident in result:
            raise ValueError("duplicate or malformed " + kind + " id")
        result[ident] = item
    return result


def validate(bundle):
    if not isinstance(bundle, dict) or bundle.get("schema") != SCHEMA:
        raise ValueError("unsupported judgment reconstruction schema")
    if (bundle.get("original_judgment_bytes_archived") is not False or
            bundle.get("independent_legal_review_completed") is not False or
            bundle.get("causal_policy_effect_measured") is not False or
            bundle.get("personal_culpability_established") is not False or
            bundle.get("publication_authorized") is not False):
        raise ValueError("unverified sources, effects or publication promoted")
    _date(bundle["as_of"])
    docs = _rows(bundle.get("judgments"), "judgment")
    if set(docs) != set(PINNED):
        raise ValueError("three distinct primary judgments required")
    for ident, doc in docs.items():
        pinned = PINNED[ident]
        if any(doc.get(x) != pinned[y] for x,y in (
                ("jurisdiction","jurisdiction"), ("docket","docket"),
                ("source_url","url"), ("decided_on","date"),
                ("source_format","format"))):
            raise ValueError("court identity or original locator mismatch")
        if (doc.get("source_type") != "official_court_judgment" or
                doc.get("source_bytes_archived") is not False or
                doc.get("original_sha256") is not None or
                doc.get("source_authenticity_certified") is not False or
                doc.get("text_review_state") != "public_court_webview_read_no_byte_archive"):
            raise ValueError("original document custody falsely asserted")
        if not isinstance(doc.get("court"), str) or len(doc["court"]) < 12:
            raise ValueError("court metadata absent")
        if not _date(doc["decided_on"]) <= _date(bundle["as_of"]):
            raise ValueError("future court event")
        outcome = doc.get("outcome")
        if not isinstance(outcome, dict):
            raise ValueError("disposition absent")
        expected = EXPECTED_OUTCOMES[ident]
        if (outcome.get("status"), outcome.get("appellants"),
                outcome.get("appeals_allowed"), outcome.get("appeals_dismissed"),
                outcome.get("individual_compensation_verified")) != expected:
            raise ValueError("case-specific judicial disposition mismatch")
        if outcome.get("automatic_restitution_awarded") is not False:
            raise ValueError("court judgment does not establish cash restitution")
        if ident != "hamilton_2021":
            if (outcome.get("new_decision_required") is not True or
                    outcome.get("new_decision_deadline_weeks") != 26):
                raise ValueError("Dutch court remitted for further administrative decision")
        else:
            if outcome.get("new_decision_required") is not False or outcome.get("new_decision_deadline_weeks") is not None:
                raise ValueError("UK conviction quashing is not Dutch remittal")
    holdings = _rows(bundle.get("holdings"), "holding")
    if set(x["kind"] for x in holdings.values()) != set(KIND):
        raise ValueError("missing or duplicated holding types")
    if len(holdings) != len(KIND):
        raise ValueError("each selected holding has exactly one source anchor")
    by_kind = {}
    for row in holdings.values():
        kind = row.get("kind")
        ident, para = KIND.get(kind, (None, None))
        if not ident or row.get("judgment_id") != ident or row.get("paragraph") != para:
            raise ValueError("source/paragraph cannot be moved between courts or holdings")
        by_kind[kind] = row
        if not _PARA.fullmatch(str(row["paragraph"])):
            raise ValueError("paragraph anchor format invalid")
        if (row.get("source_url") != docs[ident]["source_url"] or
                row.get("docket") != docs[ident]["docket"] or
                row.get("court_statement_status") != "researcher_paraphrase_to_verify" or
                row.get("independent_text_entailment_checked") is not False):
            raise ValueError("holding provenance or editorial approval overclaimed")
        if not isinstance(row.get("summary"), str) or len(row["summary"]) < 65:
            raise ValueError("holding insufficiently described")
        basis = row.get("domestic_legal_bases")
        if not isinstance(basis, list) or not basis or not set(basis).issubset(GROUNDS[ident]):
            raise ValueError("legal basis cannot come from foreign or later law")
        if row.get("foreign_law_applied") is not False or row.get("causal_effect_size") is not None:
            raise ValueError("foreign legal transfer or impact fabricated")
    gaps = _rows(bundle.get("open_record_questions"), "gap")
    if {row.get("judgment_id") for row in gaps.values()} != set(docs):
        raise ValueError("every judgment needs independent validation questions")
    if not all(isinstance(row.get("question"), str) and len(row["question"]) > 35
               and row.get("answered") is False for row in gaps.values()):
        raise ValueError("missing unanswered validation questions")
    comparison = _rows(bundle.get("comparisons"), "comparison")
    if len(comparison) != 3:
        raise ValueError("three bounded comparisons required")
    unique_pairs = set()
    for row in comparison.values():
        l,r=row.get("left_holding"),row.get("right_holding")
        if l not in holdings or r not in holdings or l == r or (l,r) in unique_pairs:
            raise ValueError("comparison reference invalid")
        unique_pairs.add((l,r))
        a,b=holdings[l],holdings[r]
        if a["judgment_id"] == b["judgment_id"]:
            raise ValueError("comparisons require distinct judicial decisions")
        if row.get("transfer_status") not in {"analogy_only", "remedies_non_equivalent", "distinct_domestic_procedures"}:
            raise ValueError("comparison cannot automatically determine legal applicability")
        if (row.get("equivalence_established") is not False or
                row.get("measured_effect_difference") is not None or
                row.get("foreign_rule_applied") is not False or
                not isinstance(row.get("analysis"), str) or len(row["analysis"]) < 65):
            raise ValueError("unreviewed comparison cannot claim causal or legal equivalence")
    if set(bundle.get("expressly_not_adjudicated", [])) != REQUIRED_EXCLUSIONS:
        raise ValueError("scope exclusion guardrails missing")
    return docs, holdings, comparison, gaps


def evaluate(bundle):
    docs, holdings, comparison, gaps = validate(bundle)
    results = []
    for ident, doc in sorted(docs.items()):
        hs = sorted((h for h in holdings.values() if h["judgment_id"] == ident),
                    key=lambda h: h["paragraph"])
        results.append({
            "judgment_id": ident, "docket": doc["docket"],
            "jurisdiction": doc["jurisdiction"], "decided_on": doc["decided_on"],
            "source_url": doc["source_url"], "original_bytes_captured": False,
            "paragraph_holdings": [{
                "paragraph": h["paragraph"], "kind": h["kind"],
                "attributed_summary": h["summary"],
                "domestic_basis": h["domestic_legal_bases"],
                "text_entailment_independently_verified": False,
                "source_url": h["source_url"],
            } for h in hs],
            "outcome": doc["outcome"],
            "outcome_denominator_is_this_judgment_only": True,
            "individual_culpability_newly_established": False,
            "open_questions": [g["question"] for g in gaps.values()
                               if g["judgment_id"] == ident],
        })
    return {
        "schema": "legal_codex.judgment_reconstruction_result.v1",
        "judgment_count": len(docs), "jurisdiction_count": len({d["jurisdiction"] for d in docs.values()}),
        "holding_count": len(holdings), "comparison_count": len(comparison),
        "judgments": results,
        "comparisons": [{
            "id": c["id"], "left_holding": c["left_holding"],
            "right_holding": c["right_holding"],
            "transfer_status": c["transfer_status"],
            "analysis": c["analysis"],
            "foreign_legal_applicability": False,
            "same_remedy_proven": False, "causal_difference_estimated": False,
        } for c in comparison.values()],
        "expressly_not_adjudicated": sorted(REQUIRED_EXCLUSIONS),
        "document_bytes_authenticated": False, "legal_source_entailment_verified": False,
        "independent_legal_review_completed": False, "legal_guilt_inferred": False,
        "causal_preventive_effect_measured": False, "publication_authorized": False,
        "input_digest": _digest(bundle),
    }


def semantic_packet(bundle, result):
    if result.get("input_digest") != _digest(bundle):
        raise ValueError("source data changed since evaluation")
    docs, holdings, comparisons, _ = validate(bundle)
    nodes, edges = [], []
    for ident, doc in docs.items():
        nodes.append({"key":"judgment-"+ident, "kind":"source", "layer":"neutral",
                      "statement":doc["docket"]+" - "+doc["court"],
                      "source_refs":[doc["source_url"]],
                      "provenance":{"original_bytes_archived":False,
                                    "source_authenticity_certified":False}})
    for ident,h in holdings.items():
        nodes.append({"key":"holding-"+ident, "kind":"observation", "layer":"neutral",
                      "statement":h["summary"],"source_refs":[h["source_url"]],
                      "provenance":{"docket":h["docket"],"paragraph":h["paragraph"],
                                    "editorial_review":"pending",
                                    "foreign_law_applied":False}})
        edges.append({"source":"judgment-"+h["judgment_id"],
                      "target":"holding-"+ident,"relation":"ATTRIBUTED_JUDICIAL_PARAGRAPH",
                      "status":"candidate"})
    for comp in comparisons.values():
        edges.append({"source":"holding-"+comp["left_holding"],
                      "target":"holding-"+comp["right_holding"],
                      "relation":"COMPARABLE_LEGAL_MECHANISM_CANDIDATE",
                      "status":"candidate",
                      "provenance":{"foreign_law_applied":False,
                                    "same_remedy_proven":False,
                                    "causal_effect_established":False}})
    return {"schema":"cite_refinery.semantic_graph.v1",
            "source_system":"legal-codex-judgment-reconstruction-012",
            "clusters":[], "nodes":nodes, "edges":edges}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--output", default="legal_codex_judgment_012_result.json")
    p.add_argument("--packet")
    args=p.parse_args(argv)
    bundle=json.loads(Path(args.input).read_text(encoding="utf-8"))
    out=evaluate(bundle)
    Path(args.output).write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    if args.packet:
        Path(args.packet).write_text(
            json.dumps(semantic_packet(bundle,out),indent=2,ensure_ascii=False)+"\n",
            encoding="utf-8")
    print(json.dumps({"judgments":out["judgment_count"],"holdings":out["holding_count"],
                      "source_byte_authentication":False,"publication_authorized":False}))


if __name__=="__main__":
    main()
