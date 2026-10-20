"""Freeze a truly unexposed test partition before running any mapper.

The holdout is *unseen by this Cite-Refinery pipeline*, not unseen by
pretrained language models or universally independent research.
"""
from __future__ import annotations
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from .richer_public_sources import SCHEMA

SPLIT_SCHEMA="cite_refinery.frozen_corpus_partition.v1"
DOMAIN_HOLDOUT={"s10","s11"}
SEED="cite-refinery-2026-10-multidomain-freeze-v1"

def _sha(raw):return hashlib.sha256(raw.encode("utf8")).hexdigest()
def _clean_title(title):
    return " ".join(re.findall(r"[a-z0-9]+",title.lower()))

def _canonical(url):
    p=urlparse(str(url or ""))
    if p.hostname in {"doi.org","dx.doi.org"}:
        return "doi:"+p.path.lower().strip("/").replace("%2f","/")
    return (p.netloc+p.path).lower().rstrip("/")

def _aliases(item):
    urls=[item.get("canonical_url"),item.get("doi"),item.get("source_location")]
    known={"url:"+_canonical(url) for url in urls if url and _canonical(url)}
    title=_clean_title(item.get("title",""))
    if len(title)>24:known.add("title:"+title)
    return known

def _old_aliases(baseline):
    alias=set()
    for item in baseline["sources"]:
        alias.update(_aliases({"canonical_url":item.get("url"),
                                "title":item.get("title"),
                                "doi":item.get("doi")}))
    return alias

def _choose(value,seed=SEED):
    return int(_sha(seed+":"+value)[:14],16)

def freeze(new,baseline,directory):
    if new.get("schema")!=SCHEMA:raise ValueError("Invalid richer corpus")
    if baseline.get("schema")!="cite_refinery.open_corpus.v1":
        raise ValueError("Previous corpus baseline required to prevent exact-source leakage")
    dest=Path(directory);dest.mkdir(parents=True,exist_ok=True)
    # Refuse to overwrite an existing holdout. Benchmark partitions are immutable.
    frozen=dest/"frozen_split_receipt.json"
    if frozen.exists():raise FileExistsError("Already froze holdout; never reshuffle evaluated material")
    excluded=[];eligible=[];seen=_old_aliases(baseline)
    for record in sorted(new["sources"],key=lambda r:r["id"]):
        alias=_aliases(record)
        collision=seen & alias
        if collision:
            excluded.append({"id":record["id"],"reason":"matches_baseline_or_prior_new",
                             "alias_types":sorted({s.split(":",1)[0] for s in collision})})
            continue
        seen |=alias
        eligible.append(record)
    domains=[];mixed=[]
    for row in eligible:
        if row["collection_quota"] in DOMAIN_HOLDOUT:
            domains.append(row)
        else:mixed.append(row)
    groups=defaultdict(list)
    for row in mixed:groups[(row["collection_quota"],row["type"])].append(row)
    dev=[];document_holdout=[]
    for key,items in sorted(groups.items()):
        ranked=sorted(items,key=lambda v:_choose(v["id"]))
        # 20%, at least one from each meaningful stratum; never all holdout.
        count=min(len(ranked)-1,max(1,(len(ranked)+4)//5)) if len(ranked)>1 else 0
        document_holdout.extend(ranked[:count])
        dev.extend(ranked[count:])
    holdout=domains+document_holdout
    ids_dev={x["id"] for x in dev}
    ids_test={x["id"] for x in holdout}
    if ids_dev & ids_test:raise ValueError("Source ID leak")
    if not holdout or not dev:raise ValueError("Insufficient split for honest benchmark")
    if ids_dev|ids_test!={x["id"] for x in eligible}:
        raise ValueError("Unassigned eligible source")
    if any(x["collection_quota"] in DOMAIN_HOLDOUT for x in dev):
        raise ValueError("Domain-held-out material visible to dev")
    dev_alias=set()
    for x in dev:
        if dev_alias & _aliases(x):raise ValueError("Near identical aliases in development")
        dev_alias.update(_aliases(x))
    if any(dev_alias & _aliases(x) for x in holdout):
        raise ValueError("Development shares document aliases with held-out sources")
    private={
        "schema":SPLIT_SCHEMA,"seed":SEED,"development":sorted(dev,key=lambda r:r["id"]),
        "held_out":sorted(holdout,key=lambda r:r["id"]),
        "excluded_known":excluded,
        "domain_holdout_quotas":sorted(DOMAIN_HOLDOUT),
        "purpose":"Holdout never supplied to model mapping, query feedback or prompt construction.",
    }
    (dest/"private_partition.json").write_text(json.dumps(private,indent=2,ensure_ascii=False)+"\n")
    # Model must only be pointed to the development file, never the private partition.
    dev_data={"schema":"cite_refinery.richer_development_materials.v1",
              "sources":private["development"],"source_count":len(dev),
              "holdout_text_not_in_this_file":True,
              "unseen_topic_strata":sorted(DOMAIN_HOLDOUT)}
    (dest/"development_only.json").write_text(json.dumps(dev_data,indent=2,ensure_ascii=False)+"\n")
    counts=lambda rows:dict(sorted(Counter(r["type"] for r in rows).items()))
    fingerprint=_sha("\n".join(
        sorted(r["id"]+" "+r["text_sha256"]+" "+r["canonical_url"] for r in eligible)))
    seal=_sha("\n".join(sorted(r["id"]+" "+r["text_sha256"] for r in holdout)))
    metadata={
        "schema":"cite_refinery.richer_corpus_public_manifest.v1",
        "previous_sources":baseline["source_count"],
        "new_records_queried":len(new["sources"]),
        "excluded_previous_overlap":len(excluded),
        "eligible_new_materials":len(eligible),
        "development_count":len(dev),
        "holdout_count":len(holdout),
        "whole_domain_holdout_count":len(domains),
        "document_holdout_count":len(document_holdout),
        "holdout_quotas":sorted(DOMAIN_HOLDOUT),
        "development_type_counts":counts(dev),
        "holdout_type_counts":counts(holdout),
        "eligible_type_counts":counts(eligible),
        "development_word_count":sum(x["word_count"] for x in dev),
        "holdout_word_count":sum(x["word_count"] for x in holdout),
        "prior_63_source_overlap_excluded":True,
        "text_seen_by_mapper_at_freeze":0,
        "unseen_input_not_training_data":True,
        "source_fingerprint_sha256":fingerprint,
        "holdout_seal_sha256":seal,
        "seed_fingerprint":_sha(SEED),
        "holdout_status":"sealed_not_mapped_not_reviewed",
        "accuracy_scores_available":False,
        "boundary":"Blind within this pipeline only. Model pretraining may know publications. No human labels and no measured generalization accuracy.",
    }
    frozen.write_text(json.dumps(metadata,indent=2)+"\n")
    return metadata
