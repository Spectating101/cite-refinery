"""LLM-first semantic research contract: build prompts, validate bounded proposals.

An LLM decomposes source text into atomic *propositions* and proposes semantic
connections between them. The graph remains authoritative: even quotations
literally found in source text do not prove that a proposition is entailed.

Do not promote model assertions to Practical, Academic, or Program evidence
until the source-passage semantics, population, geography and mechanism are
independently reviewed. This component is provider-independent and stdlib-only.
"""
from __future__ import annotations
import hashlib
import json
import re
from typing import Any

RELATIONS = {"CONTEXT_FOR", "RELATED_TO", "PROVIDES_DATA_FOR",
             "QUALIFIES", "REQUIRES_REVIEW_WITH"}
CLAIM_TYPES = {"observation", "research_finding", "method", "measurement",
               "program_capability", "definition", "reported_limitation"}
_DIRECT = "direct_source_quote_candidate_unverified_entailment"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _text(x: Any) -> str:
    return " ".join(str(x or "").split())


def make_input(sources: list[dict], modules: list[dict]) -> dict:
    """Keep the entire cited text, module ontology, and source type distinct."""
    if not 1 <= len(sources) <= 12 or not 1 <= len(modules) <= 100:
        raise ValueError("Expected 1-12 sources and 1-100 candidate modules")
    source_ids, module_ids = set(), set()
    records = []
    for source in sources:
        sid = source.get("id")
        url = source.get("url")
        body = source.get("text")
        if not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z0-9_:-]{2,80}", sid) or sid in source_ids:
            raise ValueError("Each source requires a unique stable ID")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError("Source URLs must be HTTPS")
        if not isinstance(body, str) or not 20 <= len(body) <= 16000:
            raise ValueError("Source text must be 20..16000 characters")
        source_ids.add(sid)
        records.append({
            "id": sid, "url": url, "text": body,
            "text_sha256": _digest(body),
            "origin_type": str(source.get("origin_type") or "unknown"),
            "source_scope": _text(source.get("source_scope") or "not independently established"),
            "parent_source_url": str(source.get("parent_source_url") or ""),
            "same_study_as_parent":bool(source.get("same_study_as_parent",False)),
        })
    topic_list = []
    for m in modules:
        mid = m.get("id")
        if not isinstance(mid, str) or not re.fullmatch(r"[A-Z]{2,5}-[0-9]{2,3}", mid) or mid in module_ids:
            raise ValueError("Each module needs a unique uppercase module ID")
        if not _text(m.get("title")) or not _text(m.get("summary")):
            raise ValueError("Module title and summary required")
        module_ids.add(mid)
        topic_list.append({"id": mid, "title": _text(m["title"]), "summary": _text(m["summary"])})
    return {"task_schema": "cite_refinery.llm_semantic_review.v1",
            "sources": records, "modules": topic_list,
            "review_state": "UNREVIEWED_LLM_GENERATION_INPUT",
            "constraints": ["Quote exactly, or state an open question instead.",
                            "Never equate access or program existence with outcomes.",
                            "Cross-field inference is not proof of causal effect."]}


def build_prompt(review_input: dict) -> str:
    """Model is the semantic reasoner; evidence constraints are part of request."""
    if review_input.get("task_schema") != "cite_refinery.llm_semantic_review.v1":
        raise ValueError("Unknown review input schema")
    instructions = '''
You are the semantic RESEARCH REASONER, not a word-similarity ranker.
Given independently sourced passages and a broad candidate problem ontology:

1. Read the source assertions thoroughly. Decompose material into ATOMIC,
   semantically exact propositions (observation, research finding, method,
   measurement, program capability, definition, limitation).
2. For each proposition, distinguish what the source explicitly states from
   what it does not establish. Provide a VERBATIM source quote and its source_id,
   *not just a source URL*. Preserve population/geography/measurement scope.
3. Do not treat an abstract and method excerpts from the SAME publication as
   independent confirmation: check parent_source_url and same_study_as_parent.
4. Link the proposition to relevant modules by their IDs, which is an
   INTERPRETATION, not automatic evidence the entire problem is proven.
5. Compare atomic propositions across sources: propose typed links between
   proposition IDs, qualify alternatives, missing preconditions, and uncertainty.
   The permitted relations are CONTEXT_FOR, RELATED_TO, PROVIDES_DATA_FOR,
   QUALIFIES, REQUIRES_REVIEW_WITH. NO implied CAUSES, ADDRESSES, IMPLEMENTS,
   PROVES_EFFECTIVE, or field outcome claims.
6. Unsupported hypotheses, apparent contradictions without direct evidence,
   absent measurements and unknown effects go ONLY to open_questions.
7. Explicitly surface competing explanations and scope mismatch; do not
   invent sources, policy outcomes, impact percentages or citations.

Return a JSON object with exactly these main arrays:
{"propositions":[{
  "id":"P1","statement":"single precise atomic source assertion",
  "claim_type":"definition|observation|research_finding|method|measurement|program_capability|reported_limitation",
  "module_ids":["WA-06"],"support":[{"source_id":"WMO","quote":"EXACT source substring"}],
  "scope":"population/geography/time or uncertainty","limitation":"what this does NOT establish"
}], "bridges":[{
  "from":"P1","to":"P2","relation":"CONTEXT_FOR",
  "reason":"semantically argued proposed association, *not asserted fact*",
  "limitations":"what must be separately checked"
}], "open_questions":[{"question":"specific unresolved issue",
"module_ids":["WA-06"],"why_unresolved":"missing evidence or counterargument"}]}
Do not write markdown or other text outside JSON.
'''
    return instructions + "\nINPUT:\n" + json.dumps(
        {"sources": review_input["sources"], "modules": review_input["modules"]},
        ensure_ascii=False, separators=(",", ":"))


def _contains_quote(text: str, quote: str) -> bool:
    # Literal span with whitespace normalized, not lexical/semantic entailment.
    return _text(quote).casefold() in _text(text).casefold()


def inspect_answer(review_input: dict, answer: dict) -> dict:
    """Reject invalid citations/IDs and fabricated confidence before staging."""
    if not isinstance(answer, dict):
        raise ValueError("LLM reply must be a JSON object")
    allowed_modules={m["id"] for m in review_input["modules"]}
    allowed_sources={s["id"]: s for s in review_input["sources"]}
    if not all(isinstance(answer.get(k),list) for k in ("propositions","bridges","open_questions")):
        raise ValueError("Required propositions, bridges and open_questions arrays")
    if len(answer["propositions"]) > 100 or len(answer["bridges"]) > 120 or len(answer["open_questions"]) > 100:
        raise ValueError("Output exceeds review limits")
    accepted, rejected, open_questions = [], [], []
    keys=set()
    for p in answer["propositions"]:
        if not isinstance(p,dict):
            rejected.append({"reason":"not_object","item":str(p)[:180]});continue
        pid=p.get("id")
        modules=p.get("module_ids")
        evidence=p.get("support")
        if not isinstance(pid,str) or not re.fullmatch(r"P[0-9]{1,3}",pid) or pid in keys:
            rejected.append({"reason":"invalid_or_duplicate_proposition_id","item":str(pid)[:80]});continue
        keys.add(pid)
        if (p.get("claim_type") not in CLAIM_TYPES or
            not isinstance(modules,list) or not modules or not set(modules) <= allowed_modules or
            not isinstance(evidence,list) or not evidence or len(evidence)>8 or
            not 12 <= len(_text(p.get("statement"))) <= 1500 or
            not _text(p.get("scope")) or not _text(p.get("limitation"))):
            rejected.append({"reason":"invalid_statement_scope_or_modules","item":pid});continue
        checks=[]
        for e in evidence:
            if not isinstance(e,dict) or e.get("source_id") not in allowed_sources:
                break
            quote=e.get("quote")
            source=allowed_sources[e["source_id"]]
            if not isinstance(quote,str) or not 12 <= len(quote) <= 1200 or not _contains_quote(source["text"], quote):
                break
            checks.append({"source_id": e["source_id"],"quote":quote,
                           "source_url":source["url"],"source_sha256":source["text_sha256"]})
        if len(checks)!=len(evidence):
            rejected.append({"reason":"source_quote_missing_or_invented","item":pid});continue
        accepted.append({
            "id":pid, "statement":_text(p["statement"]),
            "claim_type":p["claim_type"],"module_ids":sorted(set(modules)),
            "support":checks,"scope":_text(p["scope"]), "limitation":_text(p["limitation"]),
            "review_status":_DIRECT,
        })
    valid={p["id"] for p in accepted}
    bridges=[]
    for b in answer["bridges"]:
        if (not isinstance(b,dict) or b.get("from") not in valid or
            b.get("to") not in valid or b.get("from")==b.get("to") or
            b.get("relation") not in RELATIONS or
            not 12 <= len(_text(b.get("reason"))) <= 1600 or
            not _text(b.get("limitations"))):
            rejected.append({"reason":"unverified_relation_or_missing_endpoint","item":str(b)[:140]})
            continue
        bridges.append({
            "from":b["from"],"to":b["to"],"relation":b["relation"],"status":"candidate",
            "reason":_text(b["reason"]), "limitations":_text(b["limitations"]),
            "review_status":"llm_semantic_proposal_not_verified_entailment",
        })
    for question in answer["open_questions"]:
        if not isinstance(question,dict):continue
        ids=question.get("module_ids")
        if not isinstance(ids,list) or not set(ids)<=allowed_modules or not _text(question.get("question")):
            continue
        open_questions.append({
            "question":_text(question["question"])[:1200],
            "module_ids":sorted(set(ids)),"why_unresolved":_text(question.get("why_unresolved"))[:1200],
        })
    return {
        "schema":"cite_refinery.llm_semantic_review_result.v1",
        "status":"LLM_PROPOSITIONS_REQUIRING_INDEPENDENT_SEMANTIC_REVIEW",
        "source_digest":_digest(json.dumps(review_input["sources"],sort_keys=True)),
        "propositions":accepted,"bridges":bridges,"open_questions":open_questions,
        "rejected":rejected,
        "qualification":"Quotes matched literally; semantic entailment, geography, causal direction and intervention outcomes have NOT been established.",
    }


REVIEW_VERDICTS = {"entailed", "partially_supported", "contradicted", "unsupported", "uncertain"}
BRIDGE_VERDICTS = {"plausible", "unsupported", "contradicted", "uncertain"}


def build_second_pass_prompt(review_input: dict, inspected: dict) -> str:
    """Independent critic tests semantic entailment; generator answer is untrusted."""
    if inspected.get("status") != "LLM_PROPOSITIONS_REQUIRING_INDEPENDENT_SEMANTIC_REVIEW":
        raise ValueError("First pass must be inspected before critique")
    mini={
        "sources":review_input["sources"],
        "propositions":[{
            "id":p["id"], "statement":p["statement"],
            "scope":p["scope"],"limitation":p["limitation"],
            "support":[{"source_id":x["source_id"],"quote":x["quote"]}
                       for x in p["support"]]
        } for p in inspected["propositions"]],
        "bridges":inspected["bridges"],
    }
    instruction = '''
Act as a skeptical source-entailment REVIEWER, not the proposition generator.
Independently read the original source text. An exact quotation can be real and
STILL NOT logically entail the proposed claim. Compare precise source meaning,
actors, quantifiers, geography, time, direction, omitted preconditions, and
alternative explanations. Do not regard a source's program existence as proof
that an intervention worked.

Return a single JSON object:
{"reviews":[{"proposition_id":"P1",
  "verdict":"entailed|partially_supported|contradicted|unsupported|uncertain",
  "quote":"verbatim substring or empty string",
  "rationale":"source-specific semantic rationale",
  "scope_risks":"overgeneralization or absent evidence"}],
 "bridge_reviews":[{"from":"P1","to":"P2",
  "verdict":"plausible|unsupported|contradicted|uncertain",
  "rationale":"reasoning beyond co-occurrence and remaining alternatives"}]}
Review every proposal; do NOT invent citations, measured impacts, or missing data.
This is a review aid; the authoritative graph remains unchanged.
'''
    return instruction+"\nREVIEW_INPUT:\n"+json.dumps(mini,ensure_ascii=False,separators=(",",":"))


def inspect_second_pass(review_input: dict, inspected: dict, critic_response: dict) -> dict:
    if not isinstance(critic_response, dict):
        raise ValueError("Reviewer response must be an object")
    raw=critic_response.get("reviews")
    raw_bridges=critic_response.get("bridge_reviews")
    if not isinstance(raw,list) or not isinstance(raw_bridges,list):
        raise ValueError("Missing second-pass reviews")
    expected={p["id"] for p in inspected["propositions"]}
    actual_sources={s["id"]:s for s in review_input["sources"]}
    accepted={p["id"]:p for p in inspected["propositions"]}
    reviewed={}
    for row in raw:
        if not isinstance(row,dict) or row.get("proposition_id") not in expected:
            continue
        pid=row["proposition_id"]
        if pid in reviewed or row.get("verdict") not in REVIEW_VERDICTS:
            continue
        quote=row.get("quote")
        support_ids={x["source_id"] for x in accepted[pid]["support"]}
        span_matched=bool(isinstance(quote,str) and len(quote)>=12 and
                          any(_contains_quote(actual_sources[sid]["text"], quote)
                              for sid in support_ids))
        verdict=row["verdict"]
        if verdict in {"entailed","partially_supported"} and not span_matched:
            verdict="uncertain"
        reviewed[pid]={
            "proposition_id":pid,"reviewer_verdict":verdict,
            "literal_span_matched":span_matched,
            "rationale":_text(row.get("rationale"))[:1300],
            "scope_risks":_text(row.get("scope_risks"))[:1300],
            "authority":"NONE_ACCEPTED",
        }
    # Incomplete reviews don't get a free affirmative verdict.
    for pid in sorted(expected-set(reviewed)):
        reviewed[pid]={"proposition_id":pid,"reviewer_verdict":"uncertain",
                       "literal_span_matched":False,"rationale":"No valid second opinion",
                       "scope_risks":"unreviewed","authority":"NONE_ACCEPTED"}
    valid_edges={(e["from"],e["to"]) for e in inspected["bridges"]}
    edge_review={}
    for row in raw_bridges:
        if not isinstance(row,dict):continue
        pair=(row.get("from"),row.get("to"))
        if pair not in valid_edges or pair in edge_review or row.get("verdict") not in BRIDGE_VERDICTS:
            continue
        verdict=row["verdict"]
        if any(reviewed[k]["reviewer_verdict"] in {"uncertain","unsupported","contradicted"}
               for k in pair):
            verdict="uncertain"
        edge_review[pair]={
            "from":pair[0],"to":pair[1],"reviewer_verdict":verdict,
            "rationale":_text(row.get("rationale"))[:1300],
            "authority":"NONE_ACCEPTED",
        }
    for pair in valid_edges-set(edge_review):
        edge_review[pair]={"from":pair[0],"to":pair[1],
                           "reviewer_verdict":"uncertain",
                           "rationale":"No valid bridge critique",
                           "authority":"NONE_ACCEPTED"}
    return {
        "schema":"cite_refinery.llm_semantic_second_opinion.v1",
        "state":"CRITICAL_SECOND_PASS_NOT_AUTHORITY",
        "propositions":list(reviewed.values()),
        "bridges":list(edge_review.values()),
        "caveat":"Second LLM agreement is not independent empirical replication or human verification. Even an entailed label is not accepted evidence.",
    }
