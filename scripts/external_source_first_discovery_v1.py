"""Compare live-source module retrieval against independent frozen endpoint labels.

This is a diagnostic *module-retrieval* benchmark, not a causal discovery test.
Labels are not used by the embedding model or TF-IDF when ranking the modules.
Source text is supplied from a separately captured, URL/hash-pinned snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

from cite_refinery.external_semantic_discovery import (
    encode_documents, load_embedder, proposal_pairs, read_module_catalog,
)


class TFIDFEncoder:
    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1,2))
    def encode(self,texts,normalize_embeddings=True,convert_to_numpy=True):
        return self.vectorizer.fit_transform(texts).toarray()


def read_snapshot(path_or_data):
    snap=(json.loads(Path(path_or_data).read_text(encoding="utf-8"))
          if isinstance(path_or_data, (str,Path)) else path_or_data)
    source_ledger=snap["source_ledger"]
    parsed={}
    for sid,row in source_ledger.items():
        p=row["passages"][0]
        if not p or not row["url"].startswith("https://"):
            raise ValueError("Pinned source URL and passage required")
        parsed[sid]={
            "id":sid,"url":row["url"],"text":p,
            "source_page_sha256":row.get("source_sha256"),
            "source_passage_sha256":hashlib.sha256(p.encode()).hexdigest(),
        }
    return [parsed[k] for k in sorted(parsed)]


def evaluate(ranked, proposed, gold):
    exp=gold["gold"]
    rows=[]
    for line in ranked:
        sid=line["source_id"]
        targets=exp[sid]
        ranks={v["module_id"]:v["rank"] for v in line["ranked_modules"]}
        pairs={frozenset([x["source"],x["target"]]) for x in proposed if x["source_id"]==sid}
        target_pair=frozenset(targets)
        rows.append({
            "source_id":sid,"expected_relevant_endpoints":targets,
            "ranks":{x:ranks[x] for x in targets},
            "both_in_top_3":all(ranks[x]<=3 for x in targets),
            "both_in_top_5":all(ranks[x]<=5 for x in targets),
            "both_in_top_10":all(ranks[x]<=10 for x in targets),
            "expected_pair_in_candidate_queue":target_pair in pairs,
            "candidate_cross_field_pair_count":sum(x["source_id"]==sid for x in proposed),
        })
    n=len(rows)
    return {
        "source_count":n,
        "endpoint_recall_at_3":sum(sum(rank<=3 for rank in a["ranks"].values()) for a in rows)/(2*n),
        "endpoint_recall_at_5":sum(sum(rank<=5 for rank in a["ranks"].values()) for a in rows)/(2*n),
        "endpoint_recall_at_10":sum(sum(rank<=10 for rank in a["ranks"].values()) for a in rows)/(2*n),
        "both_endpoints_in_top_5":sum(a["both_in_top_5"] for a in rows),
        "expected_pairs_queued":sum(a["expected_pair_in_candidate_queue"] for a in rows),
        "candidate_pair_count":len(proposed),
        "rows":rows,
        "warning":"Module endpoint recall is not semantic relation precision, entailment, causal strength or scientific coverage.",
    }


def build(modules,source_snapshot,gold_file,*,top_k=8,min_score=.35):
    if top_k<2 or top_k>15:raise ValueError("top_k range 2..15")
    catalog=read_module_catalog(*modules)
    sources=read_snapshot(source_snapshot)
    print("INPUT",len(catalog),"modules",len(sources),"pinned source paragraphs",flush=True)
    engines={
        "tfidf":TFIDFEncoder(),
        "minilm":load_embedder(),
    }
    results={}
    for name,engine in engines.items():
        start=time.monotonic()
        ranking=encode_documents(catalog,sources,embedder=engine)
        proposals=proposal_pairs(ranking,top_k=top_k,min_score=min_score if name=="minilm" else .08)
        # Read label file after the embedding operation is complete, never sent as inference input.
        gold=json.loads(Path(gold_file).read_text(encoding="utf-8"))
        if set(gold["gold"])!={p["id"] for p in sources}:
            raise ValueError("Benchmark gold-source alignment failed")
        metrics=evaluate(ranking,proposals,gold)
        results[name]={
            "duration_seconds":round(time.monotonic()-start,3),
            "metrics":metrics,
            "ranked_modules":{
                line["source_id"]:line["ranked_modules"][:15] for line in ranking
            },
            "candidate_pairs":proposals,
        }
        print("ENGINE",name,"top5_endpoint_recall",metrics["endpoint_recall_at_5"],
              "gold_pairs_proposed",metrics["expected_pairs_queued"],"total_pairs",len(proposals),
              flush=True)
    return {
        "experiment":"source_first_semantic_discovery_v1",
        "status":"candidate_module_co_retrieval_only",
        "module_count":len(catalog), "source_count":len(sources),
        "sources":[{k:v for k,v in s.items() if k!="text"} for s in sources],
        "model":"sentence-transformers/all-MiniLM-L6-v2 (locally cached CPU) vs TF-IDF",
        "ranking_query":"Full source paragraph; no target module IDs or accepted relations in embedding query",
        "labels_used_for_training":False,
        "top_k":top_k,"min_score_minilm":min_score,
        "engines":results,
        "limits":[
            "Sample is four English official public-source paragraphs and 62 pre-existing candidate problem modules.",
            "Gold module IDs were human-authored before embeddings; single reviewer and debatable endpoint definitions.",
            "Every proposed candidate pair is a co-retrieval hypothesis from one paragraph, never evidence that a relation exists.",
            "A high similarity score does not establish semantic entailment, causal direction, deployed interventions or social importance.",
            "This is not a universal coverage estimate or independent invention of new problem modules.",
        ],
    }


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--modules",type=Path,required=True)
    p.add_argument("--new-fields",type=Path,required=True)
    p.add_argument("--snapshot",type=Path,help="Optional pinned local snapshot; otherwise fetch four live official pages")
    p.add_argument("--gold",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--packet-out",type=Path)
    p.add_argument("--packet-granularity",choices=["sentence","paragraph"],default="sentence")
    p.add_argument("--top-k",type=int,default=8)
    p.add_argument("--min-score",type=float,default=.35)
    args=p.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE","1")
    if args.snapshot is None:
        from scripts.external_semantic_holdout_benchmark_v1 import source_pack
        snapshot={"source_ledger":source_pack()}
    else:
        snapshot=args.snapshot
    result=build((args.modules,args.new_fields),snapshot,args.gold,
                 top_k=args.top_k,min_score=args.min_score)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("WROTE",args.out,flush=True)
    if args.packet_out:
        from cite_refinery.external_requirement_graph import stage_source_module_review
        from cite_refinery.external_semantic_discovery import read_module_catalog
        catalog=read_module_catalog(args.modules,args.new_fields)
        sources=read_snapshot(snapshot)
        if args.packet_granularity=="sentence":
            from cite_refinery.external_semantic_discovery import sentence_fragments
            sources=sentence_fragments(sources)
        ranking=encode_documents(catalog,sources,embedder=load_embedder())
        packet=stage_source_module_review(catalog,sources,ranking,top_k=4,min_score=.35)
        args.packet_out.parent.mkdir(parents=True,exist_ok=True)
        args.packet_out.write_text(json.dumps(packet,indent=2,ensure_ascii=False)+"\n")
        print("STAGED_NEUTRAL_PACKET",len(packet["nodes"]),"nodes",len(packet["edges"]),"candidate source links",args.packet_out,flush=True)
