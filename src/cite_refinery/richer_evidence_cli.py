"""Reproducible rich-source acquisition, immutable holdout, and blind review prep."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
from .richer_public_sources import acquire,SCHEMA
from .frozen_corpus_split import freeze,SPLIT_SCHEMA
from .richer_development_prep import prepare

def blind_annotation_queue(partition):
    if partition.get("schema")!=SPLIT_SCHEMA:
        raise ValueError("Only an immutable previously frozen partition may be evaluated")
    items=[]
    for entry in partition["held_out"]:
        items.append({
            "source_id":entry["id"],"title":entry["title"],
            "url":entry["canonical_url"],"source_type":entry["type"],
            "text":entry["text"],"passage_sha256":entry["text_sha256"],
            "role":None,"focus_problem_node":None,
            "exact_supporting_quote":None,
            "measured_population_or_metric":None,
            "implementation_documented":None,
            "effect_actually_measured":None,
            "outcome_type":None,"source_limitations":None,
            "needs_more_source_material":None,
            "reviewer_identifier":None,
        })
    return {
        "schema":"cite_refinery.richer_blinded_holdout_annotation.v1",
        "status":"blank_no_external_ground_truth",
        "holdout_source_count":len(items),
        "model_classifications_visible":False,
        "annotator_rubric":{
            "roles":["practical_observation","academic_finding","academic_method",
                     "program_guidance","reported_implementation",
                     "measured_program_outcome","dataset_catalog_metadata_only",
                     "background_only","off_topic","insufficient_material"],
            "critical_rule":"Program launch != effect, abstract != complete study, dataset description != observed measurements.",
            "no_auto_agreement":"A model reviewing its own predictions is not a blinded external evaluator.",
            "privacy":"No person-level fields or real identifying data collected."
        },
        "items":sorted(items,key=lambda d:hashlib.sha256(d["source_id"].encode()).hexdigest()),
    }

def generate_blind_queue(root):
    root=Path(root)
    partition=json.loads((root/"private_partition.json").read_text())
    queue=blind_annotation_queue(partition)
    dest=root/"heldout_blinded_annotation_queue.json"
    if dest.exists():raise FileExistsError("An annotation queue is already frozen; don't overwrite")
    dest.write_text(json.dumps(queue,indent=2,ensure_ascii=False)+"\n")
    return {
        "schema":"cite_refinery.richer_blind_review_status.v1",
        "holdout_count":queue["holdout_source_count"],
        "annotation_count":0,
        "model_predictions_unavailable":True,
        "blind_annotations_created":False,
        "evaluation_status":"awaiting_independent_reviewer",
        "private_record_contents_not_public":True,
        "rule":"Do not expose held-out passages to development mapping agents.",
    }

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(prog="cite-refinery-rich-corpus")
    p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--previous-corpus",type=Path,help="Prior private 63-source corpus for deduplication")
    p.add_argument("action",choices=["collect","freeze","prepare","status","annotation-packet"])
    args=p.parse_args(argv)
    root=args.workspace
    root.mkdir(parents=True,exist_ok=True)
    if args.action=="collect":
        if (root/"frozen_split_receipt.json").exists():
            raise ValueError("A frozen evaluation split exists; do not silently recollect")
        data=acquire(root)
        result={"new_material_count":data["source_count"],
                "by_genre":dict(Counter(r["type"] for r in data["sources"])),
                "retrieval_failure_count":len(data["retrieval_failures"])}
    elif args.action=="freeze":
        if not args.previous_corpus:raise ValueError("--previous-corpus required for prior-data leakage check")
        new=json.loads((root/"new_private_materials.json").read_text())
        old=json.loads(args.previous_corpus.read_text())
        result=freeze(new,old,root)
    elif args.action=="prepare":
        result=prepare(root,root)
    elif args.action=="annotation-packet":
        result=generate_blind_queue(root)
    else:
        result={}
        for f in ("new_private_materials.json","frozen_split_receipt.json",
                  "shareable_dev_manifest.json"):
            path=root/f
            result[f]=("exists" if path.exists() else "missing")
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=="__main__":main()
