"""Prepare an actually blinded expert adjudication and cross-rater agreement gate.

This DOES NOT create or simulate independent human annotations. It provides
the packet, provenance contract, and executable reconciliation algorithm for
authorized outside reviewers.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json

from .adjudication_benchmark import LABELS


def blind_packet(cases,source_doi):
    if not cases or not source_doi:raise ValueError("Missing source-case material")
    public=[{"id":x["id"],"claim":x["claim"],"evidence":x["evidence"]} for x in cases]
    digest=hashlib.sha256(json.dumps(public,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return {
        "schema":"cite_refinery.blind_expert_review.v1","source_doi":source_doi,
        "packet_digest":digest,"cases":public,
        "instructions":{
            "entailed":"The passage establishes the statement as written, within stated scope.",
            "contradicted":"The passage directly conflicts with the statement or its numerical claim.",
            "overreach":"The statement goes beyond evidence, without a direct negation.",
            "unresolved":"The passage leaves insufficient information to decide whether it is true or false.",
        },
        "boundary":"References/gold explanations withheld; independent reviewer identities and independence must be established outside this file.",
    }


def reviewer_template(packet):
    return {
        "schema":"cite_refinery.independent_review_submission.v1",
        "source_packet_digest":packet["packet_digest"],"reviewer_id":"",
        "cases":[{"id":c["id"],"label":None,"rationale":""} for c in packet["cases"]],
        "submission_note":"Complete locally as an unaffiliated reviewer; do not consult curated gold labels.",
    }


def _read_submission(packet,submission):
    if submission.get("schema")!="cite_refinery.independent_review_submission.v1":
        raise ValueError("Unexpected reviewer submission format")
    if submission.get("source_packet_digest")!=packet["packet_digest"]:
        raise ValueError("Review was not performed against the current blinded evidence packet")
    rid=submission.get("reviewer_id")
    if not isinstance(rid,str) or not 2<=len(rid)<=80:
        raise ValueError("Reviewer ID must be recorded")
    received={}
    for row in submission.get("cases",[]):
        if (not isinstance(row,dict) or row.get("id") in received
            or row.get("id") not in {x["id"] for x in packet["cases"]}
            or row.get("label") not in LABELS
            or not isinstance(row.get("rationale"),str) or len(row["rationale"])<12):
            raise ValueError("Incomplete or invalid blinded annotation")
        received[row["id"]]=row
    if set(received)!={c["id"] for c in packet["cases"]}:
        raise ValueError("All blind cases must receive a reasoned review, including abstentions")
    return rid,received


def agreement(packet,a,b):
    aid,first=_read_submission(packet,a)
    bid,second=_read_submission(packet,b)
    if aid==bid:raise ValueError("A second, distinct reviewer is required")
    keys=[c["id"] for c in packet["cases"]]
    same=sum(first[k]["label"]==second[k]["label"] for k in keys)
    ca=Counter(first[k]["label"] for k in keys);cb=Counter(second[k]["label"] for k in keys)
    observed=same/len(keys)
    expected=sum(ca[label]*cb[label] for label in LABELS)/(len(keys)*len(keys))
    kappa=(observed-expected)/(1-expected) if expected<1 else (1.0 if observed==1 else None)
    disputed=[{"id":k,"reviewer_a":first[k]["label"],
               "reviewer_b":second[k]["label"],
               "rationale_a":first[k]["rationale"],"rationale_b":second[k]["rationale"]}
              for k in keys if first[k]["label"]!=second[k]["label"]]
    return {"schema":"cite_refinery.blind_review_agreement.v1",
            "source_packet_digest":packet["packet_digest"],
            "reviewer_ids":[aid,bid],
            "cases":len(keys),"agreements":same,"disagreements":len(disputed),
            "raw_agreement":observed,"cohen_kappa":kappa,
            "disagreements_for_adjudication":disputed,
            "matched_case_labels":[{"id":k,"label":first[k]["label"]}
                for k in keys if first[k]["label"]==second[k]["label"]],
            "accepted_gold":False,
            "boundary":"Two reviewer submissions and kappa are not independent-source verification; disagreements require genuine human adjudication and conflict-of-interest checks."}
