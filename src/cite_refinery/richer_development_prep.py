"""Prepare development-only evidence for existing LLM semantic mapper.

Never accepts a private full-partition containing held-out observations as map
input. Every exported mapping record explicitly lacks collection quota IDs.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import hashlib
import json
from .frozen_corpus_split import SPLIT_SCHEMA

ORIGINS={
    "full_text_jats":"scholarly_open_access_fulltext_unverified",
    "report_extracted_text":"institutional_report_fulltext_unverified",
    "dataset_metadata":"public_dataset_catalog_metadata_not_underlying_data",
}

def build_development_map_input(dev):
    if dev.get("schema")!="cite_refinery.richer_development_materials.v1" or not dev.get("holdout_text_not_in_this_file"):
        raise ValueError("Only a frozen development-only partition may enter the mapper")
    result=[]
    for item in dev["sources"]:
        doc_type=item["type"]
        if doc_type not in ORIGINS:raise ValueError("Unknown material genre")
        content=" ".join(item["text"].split())
        # Bound individual model passages. Reference the excerpt hash, while
        # original document SHA and complete sections remain in private corpus.
        excerpt=content[:9000]
        if len(excerpt)<700:continue
        result.append({
            "id":item["id"],"url":item["canonical_url"],
            "text":excerpt,"title":item["title"],"origin_type":ORIGINS[doc_type],
            "source_scope":item["source_scope"]+" Mapping excerpt limited to 9k characters.",
            "retrieval_url":item.get("retrieval_url") or "",
            "source_record":item["id"],"year":(item.get("document_date") or "")[:4],
            "sha256":hashlib.sha256(excerpt.encode()).hexdigest(),
        })
    if not result:raise ValueError("No rich development evidence")
    return {
        "schema":"cite_refinery.open_corpus.v1",
        "material_type":"frozen_development_only_unclassified",
        "source_count":len(result),"sources":sorted(result,key=lambda x:x["id"]),
        "collection_not_a_map":True,"collection_queries":[],
        "heldout_sources_in_this_file":False,
        "source_original_text_not_embedded":False,
        "note":"Development excerpts only. Held-out domains/documents were filtered and are absent.",
    }

def _public_source(r):
    return {k:r[k] for k in ("id","canonical_url","title","type","field",
                            "text_sha256","word_count","source_scope","document_date")
            if k in r}

def prepare(partition_dir,export_dir):
    root=Path(partition_dir)
    dev=json.loads((root/"development_only.json").read_text())
    model_input=build_development_map_input(dev)
    dest=Path(export_dir);dest.mkdir(parents=True,exist_ok=True)
    (dest/"development_mapper_input.json").write_text(json.dumps(model_input,ensure_ascii=False,indent=2)+"\n")
    sanitized={
        "schema":"cite_refinery.richer_development_manifest.v1",
        "development_source_count":dev["source_count"],
        "map_ready_source_count":model_input["source_count"],
        "material_by_type":dict(sorted(Counter(x["type"] for x in dev["sources"]).items())),
        "documents":[_public_source(x) for x in dev["sources"]],
        "heldout_source_records_exposed":0,
        "model_given_collection_quota_labels":False,
        "model_given_previous_problem_modules":False,
        "subject_to_new_heldout_evaluation":True,
        "scientific_truth_validated":False,
    }
    (dest/"shareable_dev_manifest.json").write_text(json.dumps(sanitized,ensure_ascii=False,indent=2)+"\n")
    return sanitized
