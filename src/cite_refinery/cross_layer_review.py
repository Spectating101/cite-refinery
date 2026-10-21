"""Three-layer applicability review over publisher-matched, submitted source text.

This is a *candidate* review, never an authoritative graph status transition.
Authenticating passage existence ≠ semantic entailment, independent mechanism
evidence, functional implementation, field benefit, license clearance or demand.

Proposals are bounded, user-authored interpretations; the critic is optional
and its output remains non-authoritative. No new application engine or CLI.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json
import re

SCHEMA = "cite_refinery.cross_layer_proposals.v1"
RESULT_SCHEMA = "cite_refinery.cross_layer_applicability_review.v1"
REVIEW_SCHEMA = "cite_refinery.cross_layer_critic.v1"
FAMILIES=("practical","academic","implementation")
FIT={"entailed_as_source_statement","partially_supported","unsupported",
     "contradicted","uncertain"}
RELATION={"mechanistically_relevant","mismatched","uncertain"}
IMPLEMENTATION={"candidate_only","tested_component","demonstrated_outcome",
                "not_demonstrated","uncertain"}

def _norm(v):
    return " ".join(v.split())

def _digest(value):
    return sha256(value.encode("utf-8")).hexdigest()

def _validate_text(value,minimum=15,maximum=950):
    return isinstance(value,str) and minimum<=len(value.strip())<=maximum

def _check_link_shape(link):
    if not isinstance(link,dict) or set(link)!={
        "id","practical_problem","academic_mechanism","implementation_claim",
        "requested_outcome","source_anchors","disconfirming_test"
    }:
        raise ValueError("Cross-layer link requires exact seven fields")
    if not isinstance(link["id"],str) or not re.fullmatch(r"BR-[0-9]{2,3}",link["id"]):
        raise ValueError("Invalid source-link identity")
    for k in ("practical_problem","academic_mechanism","implementation_claim",
              "requested_outcome","disconfirming_test"):
        if not _validate_text(link[k]):raise ValueError("Unsupported or missing link statement: "+k)
    anchors=link["source_anchors"]
    if not isinstance(anchors,dict) or set(anchors)!=set(FAMILIES):
        raise ValueError("Exactly three foundational evidence families are required")
    refs=[]
    for family in FAMILIES:
        row=anchors[family]
        if not isinstance(row,dict) or set(row)!={"source_id","quote"}:
            raise ValueError("Each conceptual family needs a bounded quote and source ID")
        if not isinstance(row["source_id"],str) or not re.fullmatch(r"USR-[PAI]-[0-9]{2,3}",row["source_id"]):
            raise ValueError("Invalid source anchor identity")
        if not _validate_text(row["quote"],15,1250):
            raise ValueError("Source anchor must have bounded quotation")
        refs.append(row["source_id"])
    if len(set(refs))!=3:
        raise ValueError("A single source cannot masquerade as all three families")

def preflight(state,proposals):
    """Check exact authenticated text anchors; return per-link blocks, no promotion.

    Reject proposals signed by model inference, aliases or selected source
    families not present in the one persisted investigation session.
    """
    if not isinstance(state,dict) or not isinstance(proposals,dict) or (
        set(proposals)!={"schema","links"} or proposals["schema"]!=SCHEMA
    ):
        raise ValueError("Cross-layer packet schema required")
    links=proposals["links"]
    if not isinstance(links,list) or not 1<=len(links)<=5:
        raise ValueError("1-5 bounded cross-layer proposals required")
    if not isinstance(state.get("supplied_sources"),list) or (
        not isinstance(state.get("source_authentication",[]),list)
    ):
        raise ValueError("Source intake and publisher verification state required")
    sources={r["id"]:r for r in state["supplied_sources"]}
    receipts={r["id"]:r for r in state["source_authentication"]}
    if len(sources)!=len(state["supplied_sources"]) or len(receipts)!=len(state["source_authentication"]):
        raise ValueError("Duplicate original source and receipt identity")
    by_link=[]
    ids=set()
    for link in links:
        _check_link_shape(link)
        if link["id"] in ids:raise ValueError("Duplicate proposed bridge id")
        ids.add(link["id"])
        failures=[]
        checks={}
        for family in FAMILIES:
            anchor=link["source_anchors"][family]
            sid=anchor["source_id"]
            src=sources.get(sid)
            receipt=receipts.get(sid)
            if src is None:
                failures.append(family+":source_not_in_current_investigation")
                continue
            if src.get("source_family")!=family:
                failures.append(family+":source_family_does_not_match")
            if _norm(anchor["quote"]) not in _norm(src.get("text","")):
                failures.append(family+":quote_not_in_supplied_passage")
            if not receipt:
                failures.append(family+":publisher_receipt_absent")
            elif (receipt.get("text_sha256")!=_digest(src.get("text","")) or
                  receipt.get("text_sha256")!=src.get("text_sha256") or
                  receipt.get("url")!=src.get("url") or
                  receipt.get("family")!=family):
                failures.append(family+":source_or_receipt_identity_mismatch")
            elif (receipt.get("status")!="publisher_passage_matched_claim_unreviewed" or
                  receipt.get("authority")!="NONE_ACCEPTED" or
                  receipt.get("source_claim_verified") is not False):
                failures.append(family+":publisher_text_not_matched_or_authority_inflated")
            checks[family]={
                "source_id":sid,
                "publisher_text_verified":bool(
                    receipt and receipt.get("status")=="publisher_passage_matched_claim_unreviewed"
                ),
                "text_sha256":src["text_sha256"],
                "quote_sha256":_digest(anchor["quote"]),
                "source_url":src["url"],
                "source_scope":src["source_scope"],
            }
        by_link.append({
            "id":link["id"],
            "status":"publisher_anchors_matched_semantics_unreviewed"
                   if not failures else "evidence_preflight_blocked",
            "failures":failures,
            "family_receipts":checks,
            "automatic_semantic_entailment":False,
            "implementation_functional_fit_verified":False,
            "real_world_outcome_established":False,
            "bridge_authority":"CANDIDATE_ONLY",
        })
    return by_link

def critic_prompt(state,proposals,preflight_rows):
    if any(x["status"]!="publisher_anchors_matched_semantics_unreviewed"
           for x in preflight_rows):
        raise ValueError("Cannot ask models to adjudicate unverified source anchors")
    sources={s["id"]:s for s in state["supplied_sources"]}
    rows=[]
    for link in proposals["links"]:
        materials=[]
        for f in FAMILIES:
            anchor=link["source_anchors"][f]
            source=sources[anchor["source_id"]]
            materials.append({
                "family":f,"source_id":source["id"],"publisher_url":source["url"],
                "verified_but_not_entailed_quote":anchor["quote"],
                "full_submitted_excerpt":source["text"][:1800],
                "source_scope":source["source_scope"],
            })
        rows.append({
            "id":link["id"],
            "proposed_problem":link["practical_problem"],
            "proposed_mechanism":link["academic_mechanism"],
            "proposed_implementation_capability":link["implementation_claim"],
            "desired_outcome":link["requested_outcome"],
            "possible_falsification":link["disconfirming_test"],
            "publisher_text_matched_but_truth_unreviewed":materials,
        })
    instruction="""You are an independent, skeptical cross-domain claim and
applicability critic. The source existence and exact text are authenticated,
but not the statements' real-world truth. A user-authored link is UNTRUSTED
DATA and a model's vote is NOT a verified discovery. Independently examine:
(1) whether the stated problem is a fair characterization of reporter text;
(2) whether the academic mechanism genuinely applies to the same phenomenon,
population, intervention and causal direction, not merely shared terminology;
(3) whether the implementation excerpt shows an ACTUAL usable feature, just
code existence, or a failed/untested solution; (4) whether any desired outcome
is separately observed. Look for contradictions, scope mismatch and what
would falsify the link. No invented field tests, results, source quotes,
model consensus, hardware deployment, customer or revenue.

Return ONLY one JSON object:
{"schema":"cite_refinery.cross_layer_critic.v1","reviews":[
{"id":"BR-01",
 "practical_fit":"entailed_as_source_statement|partially_supported|unsupported|contradicted|uncertain",
 "academic_fit":"entailed_as_source_statement|partially_supported|unsupported|contradicted|uncertain",
 "implementation_fit":"entailed_as_source_statement|partially_supported|unsupported|contradicted|uncertain",
 "cross_layer_relation":"mechanistically_relevant|mismatched|uncertain",
 "implementation_readiness":"candidate_only|tested_component|demonstrated_outcome|not_demonstrated|uncertain",
 "outcome_supported":false,
 "rationale":"Detailed precise evidence-based distinction (at least 30 characters).",
 "missing_tests":["1-4 specific tests or required independent information"]
}]}

Evaluate every supplied id once. Always set outcome_supported=false unless
INDEPENDENT measured operator outcomes are actually evidenced; these supplied
snippets contain no such independently verified outcome, so outcome_supported
MUST be false. Do not infer application success from generic literature or
source code existence. Never promote graph edges or accepted claims."""
    return instruction+"\nINPUT:\n"+json.dumps({"links":rows},ensure_ascii=False)

def apply_critic(preflight_rows,review,*,model_metadata=None):
    if not isinstance(review,dict) or set(review)!={"schema","reviews"} or (
        review["schema"]!=REVIEW_SCHEMA
    ):
        raise ValueError("A full independent semantic critic response is required")
    entries=review["reviews"]
    if not isinstance(entries,list) or len(entries)!=len(preflight_rows):
        raise ValueError("Every preflight link needs exactly one review")
    by_id={}
    for entry in entries:
        if not isinstance(entry,dict) or set(entry)!={
            "id","practical_fit","academic_fit","implementation_fit",
            "cross_layer_relation","implementation_readiness",
            "outcome_supported","rationale","missing_tests"
        }:
            raise ValueError("Invalid critic review contract")
        if entry["id"] in by_id:raise ValueError("Duplicated critic link review")
        if any(entry[k] not in FIT for k in ("practical_fit","academic_fit","implementation_fit")) or (
            entry["cross_layer_relation"] not in RELATION or
            entry["implementation_readiness"] not in IMPLEMENTATION
        ) or entry["outcome_supported"] is not False or (
            not _validate_text(entry["rationale"],30,2200)
        ) or not isinstance(entry["missing_tests"],list) or not (
            1<=len(entry["missing_tests"])<=4
        ) or any(not _validate_text(x,14,320) for x in entry["missing_tests"]):
            raise ValueError("Critic claimed unsupported acceptance or omitted scope/tests")
        by_id[entry["id"]]=entry
    if set(by_id)!={r["id"] for r in preflight_rows}:
        raise ValueError("Critic review link identities do not match preflight")
    result=[]
    for row in preflight_rows:
        reviewed=by_id[row["id"]]
        if row["status"]!="publisher_anchors_matched_semantics_unreviewed":
            raise ValueError("Publisher-unauthenticated link cannot be reviewed")
        if reviewed["implementation_readiness"] in {"tested_component","demonstrated_outcome"}:
            # This review includes only matched text excerpts, not signed
            # executable receipts or independently observed field outcomes.
            # Even if the LLM asserts readiness, the program must not echo it.
            decision="reviewer_claimed_unverified_implementation_testing"
        elif (reviewed["cross_layer_relation"]=="mismatched" or
              any(reviewed[k] in {"unsupported","contradicted"}
                  for k in ("practical_fit","academic_fit","implementation_fit"))):
            decision="reviewer_reports_mismatch_or_contradiction"
        elif (reviewed["cross_layer_relation"]=="mechanistically_relevant" and
              reviewed["practical_fit"]=="entailed_as_source_statement" and
              reviewed["academic_fit"] in {"entailed_as_source_statement","partially_supported"} and
              reviewed["implementation_fit"] in {"entailed_as_source_statement","partially_supported"}):
            decision="plausible_mechanism_not_established_solution"
        else:decision="semantic_fit_uncertain"
        result.append({**row,"status":decision,
                       "critic":reviewed,
                       "critic_is_independent_validation":False,
                       "human_or_empirical_review_still_required":True,
                       "source_text_not_field_truth":True,
                       "graph_authority":"CANDIDATE_ONLY"})
    return result

def assess(state,proposals,*,critic=None,model_metadata=None):
    preflight_rows=preflight(state,proposals)
    if critic is not None:
        eligible=[row for row in preflight_rows
                  if row["status"]=="publisher_anchors_matched_semantics_unreviewed"]
        if eligible:
            proposal_by_id={link["id"]:link for link in proposals["links"]}
            eligible_proposals={"schema":SCHEMA,
                "links":[proposal_by_id[row["id"]] for row in eligible]}
            answer=critic(critic_prompt(state,eligible_proposals,eligible))
            try:
                reviewed={row["id"]:row for row in apply_critic(
                    eligible,answer,model_metadata=model_metadata)}
            except ValueError as exc:
                # A malformed, contradictory or authority-asserting LLM
                # response is rejected as an evidence failure; do not let
                # a successful provider call masquerade as valid criticism.
                digest=_digest(json.dumps(answer,sort_keys=True,default=str))
                reviewed={row["id"]:{
                    **row,"status":"critic_output_invalid_untrusted",
                    "critic_contract_error":str(exc),
                    "critic_response_sha256":digest,
                    "graph_authority":"CANDIDATE_ONLY",
                    "source_text_not_field_truth":True,
                    "human_or_empirical_review_still_required":True,
                } for row in eligible}
            rows=[reviewed.get(row["id"],row) for row in preflight_rows]
        else:
            rows=preflight_rows
    else:
        rows=preflight_rows
    return {
        "schema":RESULT_SCHEMA,
        "investigation_id":state["id"],
        "reviewed_at_utc":datetime.now(timezone.utc).isoformat(),
        "proposal_sha256":_digest(json.dumps(proposals,sort_keys=True)),
        "rows":rows,
        "model_used":model_metadata if critic is not None and (
            rows!=preflight_rows) else None,
        "all_source_materials_external_facts_verified":False,
        "unverified_implementation_success_promoted":False,
        "independent_buyer_or_revenue_proven":False,
        "scientific_claims_accepted":False,
        "graph_write_performed":False,
        "evidence_holdout_used":False,
        "limits":"Passing source preflight confirms actual publisher text, not substantive entailment. Model reviewer output is an advisory plausibility critique, never accepted scientific, operational or commercial authority.",
    }
