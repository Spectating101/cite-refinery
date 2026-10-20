"""Blinded annotation material, not self-generated ground truth.

The questionnaire intentionally hides AI role labels, emergent clusters,
relations and classification decisions from the reviewer.
"""
from __future__ import annotations
import hashlib
import json
from collections import defaultdict
from pathlib import Path

def create_review_queue(corpus,*,per_origin=4):
    if corpus.get("schema")!="cite_refinery.open_corpus.v1":
        raise ValueError("Unrecognized evidence corpus")
    grouped=defaultdict(list)
    for source in corpus["sources"]:
        grouped[source["origin_type"]].append(source)
    entries=[]
    for role,items in sorted(grouped.items()):
        ranked=sorted(items,key=lambda x:hashlib.sha256(
            ("blind-selection-v1:"+x["id"]).encode()).hexdigest())
        for src in ranked[:per_origin]:
            entries.append({
                "source_id":src["id"],"source_url":src["url"],
                "retrieved_title":src["title"],
                "source_text":src["text"],
                "source_excerpt_digest":src["sha256"],
                "role_annotation":None,
                "focus_problem":None,
                "observed_intervention":None,
                "measured_outcome_type":None,
                "quote_supporting_role":None,
                "limitations":None,
                "reviewer_id":None,
            })
    return {"schema":"cite_refinery.blinded_corpus_annotations.v1",
            "review_status":"unassigned_no_human_gold_labels",
            "source_count":len(entries),
            "blinding":"No model source-role, cluster or graph labels shown.",
            "items":sorted(entries,key=lambda x:x["source_id"]),
            "role_choices":["practical_observation","academic_finding","academic_method",
                            "program_guidance","reported_implementation",
                            "measured_program_outcome","background_only","off_topic"],
            "boundary":"A blank blinded review queue is not independent annotation or measured semantic accuracy."}

def public_queue_stub(private_queue):
    return {"schema":"cite_refinery.blinded_review_manifest.v1",
            "source_count":private_queue["source_count"],
            "source_ids":[e["source_id"] for e in private_queue["items"]],
            "annotation_status":"not_started",
            "gold_label_count":0,"precision_recall_computed":False,
            "source_excerpts":"available_only_in_authorized_local_dump",
            "note":"Human reviewer must annotate raw passages without seeing model labels. No annotations exist yet."}
