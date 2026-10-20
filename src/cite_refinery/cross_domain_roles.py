"""Domain-neutral evidence-role adjudication for practical, academic and program maps.

LLM performs semantic reading; code validates source fingerprints, exact quote
receipts, role claims, and module IDs. An official URL is a publisher address
NOT proof of government implementation or measured impact.
"""
from __future__ import annotations

import hashlib
import json

ROLES={"practical_problem_report","academic_finding","academic_method",
       "program_guidance_or_proposal","documented_implementation",
       "measured_program_outcome","background_only","off_topic"}
FITS={"direct","adjacent","off_topic"}
PERSPECTIVES={"practical","academic","program","cross_perspective"}

def evidence_role_prompt(question,modules,sources):
    if not sources or not modules:raise ValueError("Source text and problem modules required")
    inp={
      "question":question,
      "modules":[{"id":m["id"],"title":m["title"],"summary":m["summary"],
                  "perspective":m["perspective"]} for m in modules],
      "sources":[{"id":s["id"],"url":s["url"],"origin_type":s["origin_type"],
                  "text":s["text"],"source_scope":s.get("source_scope","")} for s in sources],
    }
    return (
      "You are the EVIDENCE-ROLE EXAMINER for a semantic graph research map. "
      "Judge each source based on WHAT THE TEXT SHOWS, not by institution name, "
      "URL domain, perceived authority, or matching buzzwords. "
      "Interpret causal scope, geography, population, time, whether a paper "
      "reports findings vs methods, a policy merely recommends actions, "
      "whether a program demonstrably operates, and whether any evaluation "
      "actually measured downstream outcomes. A WHO-hosted article can be "
      "an academic commentary instead of an implemented WHO program. "
      "A treatment recommendation is never proof of actual deployment or impact. "
      "Only label implemented/evaluated when directly asserted in the source quote. "
      "For off-topic items return no quote, no matched modules, off_topic role. "
      "Keep adjacent context out of primary source coverage, unless it genuinely "
      "answers a distinct part of the research question. Do not invent citations. "
      "Return JSON only: {\"assessments\":[{\"source_id\":\"...\","
      "\"fit\":\"direct|adjacent|off_topic\","
      "\"role\":\"practical_problem_report|academic_finding|academic_method|"
      "program_guidance_or_proposal|documented_implementation|measured_program_outcome|"
      "background_only|off_topic\","
      "\"module_ids\":[\"...\"],\"quote\":\"exact span from the source\","
      "\"why\":\"semantic reasoning explaining role, scope and uncertainty\","
      "\"limitations\":\"what source does not demonstrate\"}]}. "
      "Assess every source exactly once. Direct or adjacent sources require "
      "a meaningful verbatim quote (25+ characters). "
      "Do not equate proximity to the term 'program' with program outcome evidence. INPUT:\n"+
      json.dumps(inp,ensure_ascii=False,separators=(",",":"))
    )

def validate_roles(raw, question, modules, sources):
    if not isinstance(raw,dict) or not isinstance(raw.get("assessments"),list):
        raise ValueError("Semantic source review requires assessments array")
    mapping={s["id"]:s for s in sources}; mids={m["id"]:m for m in modules}
    if len(mapping)!=len(sources) or len(mids)!=len(modules):
        raise ValueError("Duplicate source or module ID")
    results=[];seen=set()
    for row in raw["assessments"]:
        if not isinstance(row,dict):raise ValueError("Malformed assessment")
        sid=row.get("source_id")
        if sid not in mapping or sid in seen:raise ValueError("Unknown or duplicate reviewed source ID")
        seen.add(sid)
        role=row.get("role");fit=row.get("fit")
        if fit not in FITS or role not in ROLES:raise ValueError("Unsupported source role or fit")
        selected=row.get("module_ids");quote=row.get("quote");why=row.get("why");limitations=row.get("limitations")
        if not isinstance(selected,list) or any(m not in mids for m in selected):
            raise ValueError("Source role references unknown problem module")
        if not isinstance(why,str) or len(why.strip())<18 or not isinstance(limitations,str) or len(limitations.strip())<16:
            raise ValueError("Source interpretation lacks scope/limitations")
        if fit=="off_topic":
            if role!="off_topic" or selected or quote not in ("",None):
                raise ValueError("Off-topic source cannot claim support or matched modules")
            quote=""
        else:
            if role=="off_topic" or not selected:
                raise ValueError("Relevant source requires appropriate semantic role and module scope")
            if not isinstance(quote,str) or not 25<=len(quote)<=1200 or " ".join(quote.split()).casefold() not in " ".join(mapping[sid]["text"].split()).casefold():
                raise ValueError("Source-role classification is not backed by verbatim evidence")
            if role in {"documented_implementation","measured_program_outcome"}:
                if not any(mids[m]["perspective"] in ("program","cross_perspective") for m in selected):
                    raise ValueError("Operational/outcome proof needs a program-relevant module")
        results.append({
            "source_id":sid,"url":mapping[sid]["url"],"origin_type":mapping[sid]["origin_type"],
            "source_sha256":hashlib.sha256(mapping[sid]["text"].encode()).hexdigest(),
            "fit":fit,"role":role,"module_ids":sorted(set(selected)),
            "quote":quote,"why":why.strip(),"limitations":limitations.strip(),
            "source_identity_boundary":"Publisher website and source citation do not independently establish truth or implementation.",
            "authority":"neutral_semantic_role_candidate",
        })
    if seen!=set(mapping):raise ValueError("Unreviewed source remains")
    return {
      "schema":"cite_refinery.cross_domain_evidence_roles.v1",
      "question":question,
      "results":results,
      "coverage":coverage_matrix(modules,results),
      "authority":"candidate_semantic_role_only",
    }

def coverage_matrix(modules,rows):
    coverage={}
    for m in modules:
        exact=[r for r in rows if m["id"] in r["module_ids"] and r["fit"]=="direct"]
        adjacent=[r for r in rows if m["id"] in r["module_ids"] and r["fit"]=="adjacent"]
        roles={r["role"] for r in exact}
        required={
            "practical":{"practical_problem_report","academic_finding"},
            "academic":{"academic_finding","academic_method"},
            "program":{"program_guidance_or_proposal","documented_implementation","measured_program_outcome"},
            "cross_perspective":ROLES-{"off_topic","background_only"},
        }[m["perspective"]]
        matched=[r for r in exact if r["role"] in required]
        coverage[m["id"]]={
          "perspective":m["perspective"],
          "direct_source_ids":[r["source_id"] for r in exact],
          "role_matching_source_ids":[r["source_id"] for r in matched],
          "adjacent_source_ids":[r["source_id"] for r in adjacent],
          "direct_roles":sorted(roles),
          "source_coverage_status":("role_specific_direct_source" if matched
                else "topic_mentioned_without_perspective_evidence" if exact
                else "gap_no_direct_source"),
          "implementation_reported_in_source":m["perspective"]=="program" and bool(roles & {"documented_implementation","measured_program_outcome"}),
          "measured_outcome_reported_in_source":m["perspective"]=="program" and "measured_program_outcome" in roles,
          "implementation_independently_verified":False,
          "independent_field_replication":False,
        }
    return coverage
