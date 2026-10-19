"""Explicit opt-in LightRAG+Ollama proof-of-runtime on two official WMO passages.

Heavy runtime, intentionally NOT run by unit tests. Uses offline MiniLM
embeddings and an already installed Ollama model; stores all output in /tmp.
This can produce proposed associations, not accepted causal facts.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
import time
from pathlib import Path

from scripts.external_grounding_trial_v1 import build_corpus


async def exercise(timeout_s: int = 220) -> dict:
    os.environ["HF_HUB_OFFLINE"] = "1"
    from sentence_transformers import SentenceTransformer
    from lightrag import LightRAG, QueryParam
    from lightrag.llm.ollama import ollama_model_complete
    from lightrag.utils import EmbeddingFunc
    from cite_refinery.external_engines import lightrag_propose

    src = build_corpus()
    # The real source text and IDs are injected at runtime, never fabricated by an LLM.
    corpus = "\n\n".join(f"Official WMO source ID: {d['id']} ({d['url']}). {d['text']}"
                         for d in src)
    started = time.monotonic()
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2",
                                device="cpu", local_files_only=True)
    async def embed(texts, **kwargs):
        values = await asyncio.to_thread(
            model.encode, texts, normalize_embeddings=True, convert_to_numpy=True)
        return values

    with tempfile.TemporaryDirectory(prefix="cite-refinery-lightrag-trial-") as d:
        rag = LightRAG(
            working_dir=d,
            llm_model_func=ollama_model_complete,
            llm_model_name="llama3.2:3b",
            llm_model_kwargs={"host": "http://127.0.0.1:11434",
                              "options": {"num_ctx": 4096, "num_predict": 330}},
            embedding_func=EmbeddingFunc(embedding_dim=384,
                                         max_token_size=256,
                                         model_name="all-MiniLM-L6-v2",
                                         func=embed),
            llm_model_max_async=1,
            entity_extract_max_gleaning=0,
            entity_extract_max_records=8,
            entity_extract_max_entities=7,
            chunk_token_size=540,
            chunk_overlap_token_size=40,
            summary_max_tokens=280,
            top_k=6,
            chunk_top_k=4,
            max_total_tokens=2800,
        )
        await rag.initialize_storages()
        try:
            print("LIGHTRAG_INSERT_BEGIN",len(corpus),flush=True)
            await asyncio.wait_for(rag.ainsert(corpus), timeout=timeout_s)
            labels = await asyncio.wait_for(rag.get_graph_labels(), timeout=30)
            print("LIGHTRAG_INSERT_DONE",len(labels),flush=True)
            # Research-only factual query. Retrieve text/edges but do not
            # auto-promote a candidate relationship into Cite-Refinery.
            q = await asyncio.wait_for(rag.aquery(
                "What explicit relationship does the WMO HydroSOS page describe between "
                "HydroSOS and Early Warnings for All? Does the page report an actual "
                "measured reduction in deaths from HydroSOS deployment?",
                param=QueryParam(mode="hybrid", only_need_context=True)),
                timeout=timeout_s,
            )
            return {
                "state": "completed", "engine": "LightRAG 1.5.7 with Ollama llama3.2:3b",
                "source_ids": [a["id"] for a in src],
                "embedded_source_digest": [a["passage_sha256"] for a in src],
                "graph_entity_label_count": len(labels),
                "graph_labels_preview": labels[:18],
                "retrieved_context_chars": len(str(q)),
                "context_preview": str(q)[:4000],
                "elapsed_seconds": round(time.monotonic()-started,1),
                "disclaimer": "Graph nodes and retrieved context are engine outputs, not source-verified semantic claims or established causal impacts.",
            }
        finally:
            await rag.finalize_storages()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out",default="/tmp/cite-refinery-real-lightrag-wmo.json")
    parser.add_argument("--timeout",type=int,default=220)
    args=parser.parse_args()
    try:
        result=asyncio.run(exercise(args.timeout))
    except Exception as e:
        result={"state":"failed", "error_type":type(e).__name__,
                "error":str(e)[:1200], "disclaimer":"This is an attempted real runtime, not a passing engine benchmark."}
        print("LIGHTRAG_REAL_RUNTIME_FAILED",repr(e),flush=True)
    Path(args.out).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("LIGHTRAG_RESULT",result["state"],args.out,flush=True)


if __name__=="__main__":
    main()
