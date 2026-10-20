"""Semantic-coverage-driven source recovery. No hardcoded research bibliography.

Recovered passages are stored in the user's local investigation workspace,
not committed as externally licensed full documents or proof of program impact.
"""
from __future__ import annotations
import json
from pathlib import Path
from .investigation_controller import validate_plan
from .investigation_sources import collect_sources

def recovery_prompt(question,modules,review,prior_plan):
    problems=[]
    ids={m["id"]:m for m in modules}
    for key,row in review["coverage"].items():
        if row["source_coverage_status"]!="role_specific_direct_source":
            problems.append({
                "module_id":key,
                "title":ids[key]["title"],
                "perspective":row["perspective"],
                "problem":"No source directly documents the specific evidence type the perspective requires.",
                "previous_roles":row["direct_roles"],
            })
        elif row["perspective"]=="program" and not row["implementation_reported_in_source"]:
            problems.append({
                "module_id":key,"title":ids[key]["title"],"perspective":"program",
                "problem":"Only plans/guidance or background; operational implementation and measured evaluation still missing.",
                "previous_roles":row["direct_roles"],
            })
    return (
      "You are an AUTONOMOUS RESEARCH SEARCH-RECOVERY PLANNER. "
      "The first discovery phase searched publisher sites and found many irrelevant "
      "official results. A semantic evidence-role critic identified specific holes. "
      "Find verifiable independent PUBLIC sources to fill evidence-role gaps. "
      "Use short, topic-specific searches, not long Boolean conglomerates. "
      "A source on WHO/CDC/UN cannot be assumed an implemented project; "
      "prioritize an actual report with audited operating dates or measured effects, "
      "not general guidance. If no such evidence can be found, preserve the gap. "
      "Do not provide URLs, quotes or invented results; the retriever must discover. "
      "Return only JSON with focus, reason, hypotheses (1-4), queries (2-5). "
      "Each query has lane academic or official; cover BOTH lanes. "
      "Vary search terms and avoid repeating earlier queries. "
      "INPUT:\n"+json.dumps({
        "question":question,"modules":modules,"evidence_gaps":problems,
        "previous_plan":prior_plan,"previous_sources":[{
            "url":x["url"],"fit":x["fit"],"role":x["role"],
        } for x in review["results"]]
      },ensure_ascii=False,separators=(",",":"))
    )

def retrieve_recovery(raw_plan,prior_sources):
    plan=validate_plan(raw_plan)
    acquired=collect_sources(plan["queries"],per_query=2,max_sources=8)
    known_urls={s["url"] for s in prior_sources}
    known_id={s["id"] for s in prior_sources}
    fresh=[s for s in acquired["sources"] if s["url"] not in known_urls and s["id"] not in known_id]
    return {"plan":plan,"sources":fresh[:8],"attempted_queries":len(plan["queries"]),
            "source_failures":acquired["failures"],
            "note":"Unreviewed additional source leads. Coverage must be reassessed semantically."}
