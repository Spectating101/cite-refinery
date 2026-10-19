"""Summarize independent external-engine smoke tests without inflating success.

No frozen text is required to run the independent tests except the source
URLs embedded in each test. Summary uses observed result files and an explicit
literal quote check; missing engine results remain unavailable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from cite_refinery.external_evidence_audit import detect_explicit_link_misread

HYDROSOS_ASSERTION = (
    "HydroSOS is the backbone supporting the Early Warnings for All initiative "
    "for hydrological disasters"
)


def summarize(grounding: Path, docling: Path | None, lightrag: Path | None) -> dict:
    g = json.loads(grounding.read_text(encoding="utf-8"))
    pages = {s["id"]: s for s in g["source_passages"]}
    source = dict(pages["WMO-HYDROSOS"],url="https://wmo.int/activities/hydrosos")
    q = next(x for x in g["questions"] if x["id"] == "explicit-link")
    quote = detect_explicit_link_misread(
        source, model_decision=q["grounded"]["decision"],
        exact_span=HYDROSOS_ASSERTION, subject="HydroSOS",
        object_name="Early Warnings for All",
    )
    if not quote["literal_relationship_signal"]:
        raise ValueError("WMO literal source-span check did not reproduce; do not publish result")
    d = (json.loads(docling.read_text(encoding="utf-8"))
         if docling is not None and docling.exists() else None)
    l = (json.loads(lightrag.read_text(encoding="utf-8"))
         if lightrag is not None and lightrag.exists() else None)
    return {
        "trial_date": "2026-10-20",
        "trial_type": "real runtime smoke, n=2 WMO questions + one independently parsed PDF",
        "wmo_source_refs": g["sources"],
        "model": q["grounded"]["model"],
        "closed_book_response_count": len(g["questions"]),
        "closed_book_explicit_decisions": sum(
            x["closed_book"]["decision"] in {"yes", "no"} for x in g["questions"]),
        "grounded_correct_binary_decisions": sum(
            x["grounded"]["decision"] == x["expected"] for x in g["questions"]),
        "grounded_questions": len(g["questions"]),
        "source_span": {
            "explicit_relationship_stated": quote["literal_relationship_signal"],
            "model_answer_conflicts_with_explicit_span": quote["potential_source_contradiction"],
            "quote_present": quote["quote_check"]["literal_quote_found"],
            "review_status": quote["status"],
            "source_url": quote["quote_check"]["source_url"],
        },
        "model_results": [{
            "id": r["id"], "expected": r["expected"],
            "closed_book_decision": r["closed_book"]["decision"],
            "grounded_decision": r["grounded"]["decision"],
            "closed_book_answer": r["closed_book"]["answer"][:650],
            "grounded_answer": r["grounded"]["answer"][:650],
            "source_audit": "manual_review_required",
        } for r in g["questions"]],
        "docling": d if d is not None else {"state": "not_run_or_result_unavailable"},
        "lightrag": l if l is not None else {"state": "result_not_yet_confirmed"},
        "interpretation": [
            "The source-backed model still gave an incorrect negative about a literally explicit WMO relationship.",
            "The model correctly did not assert a source-specific measured mortality outcome.",
            "Do not promote model results to evidence-supported relations on source URLs alone.",
            "A numeric token overlap against a second parser, if measured, is only a retention proxy.",
            "Single-case test and source availability cannot establish superiority of any research engine.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grounding",type=Path,required=True)
    parser.add_argument("--docling",type=Path)
    parser.add_argument("--lightrag",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    summary=summarize(args.grounding,args.docling,args.lightrag)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("SOURCE_CHECK",summary["source_span"])
    print("GROUNDING",summary["grounded_correct_binary_decisions"],"of",summary["grounded_questions"])
    print("DOCLING",summary["docling"].get("numeric_overlap_recall_proxy"))
    print("LIGHTRAG",summary["lightrag"].get("state"))
    print("OUT",args.out)


if __name__=="__main__":
    main()
