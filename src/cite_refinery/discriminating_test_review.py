"""Check a proposed research protocol against identifiability and field feasibility.

A second LLM review is *not* independent expert validation and cannot promote
any mechanism from hypothesis to measured outcome.
"""
from __future__ import annotations

import json

REVIEW_STATES={"conditionally_useful","not_discriminating","uncertain"}


def critique_prompt(plan):
    if plan.get("schema")!="cite_refinery.mechanism_discrimination_plan.v1":
        raise ValueError("Unknown mechanism plan")
    compact={"tests":[{k:v for k,v in t.items() if k!="source_receipts"} for t in plan["tests"]],
             "mechanisms":[{"id":m["id"],"mechanism":m["mechanism"]} for m in plan["mechanisms"]],
             "evidence_gap":plan["missing_input"],
             "status":plan["current_identifiability"]}
    return (
      "You are an adversarial reviewer of a proposed CANINE FIELD MEASUREMENT PROTOCOL. "
      "You are NOT judging evidence that a hypothesis occurred. Identify unmeasured "
      "detectability, uncertain individual ID attribution, open population assumptions, "
      "spatial confounding, ethical/animal-welfare constraints, and the possibility that "
      "two mechanisms co-occur. Do not request sensitive household data without "
      "privacy minimization. A non-executed observational design is not a replicated "
      "empirical causal effect. Choose one verdict per test: conditionally_useful, "
      "not_discriminating, uncertain. Include one mandatory improvement and "
      "the precise observation that would remain insufficient even if proposed "
      "data were collected. Some planned contrasts can be only conditionally "
      "identifying, and model fit is not proof of truth. "
      "Return only JSON {\"reviews\":[{\"id\":\"T1\","
      "\"verdict\":\"conditionally_useful|not_discriminating|uncertain\","
      "\"limitation\":\"...\",\"required_revision\":\"...\"}],"
      "\"design_decision\":\"protocol_only_unexecuted\","
      "\"independence\":\"same_model_family_reviewer_not_external_truth\"}. "
      "Review EVERY test. Don't assume all pass. INPUT:\n"+
       json.dumps(compact,ensure_ascii=False,separators=(",",":"))
    )


def validate_critique(raw,plan):
    if not isinstance(raw,dict) or raw.get("design_decision")!="protocol_only_unexecuted" or raw.get("independence")!="same_model_family_reviewer_not_external_truth":
        raise ValueError("Review must not claim implemented study or external authority")
    actual=raw.get("reviews")
    if not isinstance(actual,list) or len(actual)!=len(plan["tests"]):
        raise ValueError("Every test must receive one review")
    expected={x["id"] for x in plan["tests"]}
    seen=set();results=[]
    for r in actual:
        if not isinstance(r,dict) or r.get("id") not in expected or r["id"] in seen or r.get("verdict") not in REVIEW_STATES:
            raise ValueError("Reviewer returned missing/duplicated test or invalid verdict")
        seen.add(r["id"])
        for key in ("limitation","required_revision"):
            if not isinstance(r.get(key),str) or not 24<=len(r[key].strip())<=2400:
                raise ValueError("Missing or oversize substantive review field "+key)
        results.append({"id":r["id"],"verdict":r["verdict"],"limitation":r["limitation"],
                        "required_revision":r["required_revision"]})
    if seen!=expected:raise ValueError("Reviewer did not cover all tests")
    return {"schema":"cite_refinery.discrimination_protocol_review.v1",
            "original_plan_digest":plan["source_digest"],
            "reviews":results,
            "review_kind":"second_llm_same_model_family_not_independent_field_validation",
            "approved_scientific_effect_claims":0,
            "review_boundary":"Reviewer evaluates proposed field design only; no field measurements, validation panel or model-independent assessment."}


def review_gate(plan,review):
    """Summarize an LLM critique as a required-revision gate, never field approval."""
    if (plan.get('schema')!='cite_refinery.mechanism_discrimination_plan.v1' or
        review.get('schema')!='cite_refinery.discrimination_protocol_review.v1' or
        review.get('original_plan_digest')!=plan.get('source_digest')):
        raise ValueError('Critique not bound to the supplied source-specific protocol')
    states={x['id']:x['verdict'] for x in review['reviews']}
    if set(states)!={t['id'] for t in plan['tests']}:
        raise ValueError('Not every proposed test is reviewed')
    status=('revision_required' if 'not_discriminating' in states.values()
            else 'expert_methods_review_required' if 'uncertain' in states.values()
            else 'external_field_design_review_required')
    return {
        'schema':'cite_refinery.mechanism_discrimination_decision.v1',
        'readiness':status,'current_causal_identifiability':'not_identifiable',
        'tests_by_status':states,
        'required_revisions':[{'id':x['id'],'limitation':x['limitation'],
                               'revision':x['required_revision']}
                              for x in review['reviews'] if x['verdict']!='conditionally_useful'],
        'approved_field_protocols':0,
        'human_methods_review_completed':False,
        'statistical_model_reproduction_completed':False,
        'boundary':'No Gemini model review, positive or negative, constitutes human field-protocol approval or observed mechanism attribution.',
    }
