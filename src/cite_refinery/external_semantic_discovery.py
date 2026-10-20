"""Experimental source-first candidate-module retrieval. No graph authority changes.

Input is a 54-module registry plus optional disjoint new fields; no hand-authored
candidate bridge manifest is read. Text is the *source passage*, not a prompt
that includes ground truth modules. Ranked module hits are neutral hypotheses.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def read_module_catalog(existing: str | Path, new_fields: str | Path | None = None):
    old = json.loads(Path(existing).read_text(encoding="utf-8"))
    entries = [
        {"id": m["id"], "field_id": m["field_id"],
         "title": m["title"], "summary": m["summary"]}
        for m in old["modules"]
    ]
    if new_fields is not None:
        new = json.loads(Path(new_fields).read_text(encoding="utf-8"))
        for field in new["fields"]:
            entries.extend({"id": mid, "field_id": field["id"],
                            "title": title, "summary": summary}
                           for mid,title,summary in field["modules"])
    ids = [m["id"] for m in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate module identifiers")
    if not entries or any(not m["title"] or not m["summary"] for m in entries):
        raise ValueError("An explicit title and problem description are required")
    return entries


def encode_documents(modules, passages, *, embedder):
    """Return per-source ranked candidates. Embedder is callable .encode(...)."""
    import numpy as np
    if not modules or not passages:
        raise ValueError("Cannot search empty documents")
    texts = [f"Problem: {m['title']}. {m['summary']}" for m in modules]
    excerpts = [p["text"] for p in passages]
    vectors = embedder.encode(texts+excerpts, normalize_embeddings=True,
                             convert_to_numpy=True)
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.shape[0] != len(texts)+len(excerpts):
        raise ValueError("Embedding engine returned inconsistent result count")
    if not np.all(np.isfinite(vectors)):
        raise ValueError("Embedding engine returned NaN or infinity")
    scores = vectors[len(texts):] @ vectors[:len(texts)].T
    rows=[]
    for p,score_row in zip(passages,scores):
        ranking = sorted(range(len(modules)), key=lambda i:(-float(score_row[i]),modules[i]["id"]))
        rows.append({
            "source_id":p["id"], "source_url":p["url"],
            "source_passage_sha256":hashlib.sha256(p["text"].encode()).hexdigest(),
            "ranked_modules":[{
                "module_id":modules[i]["id"],
                "title":modules[i]["title"],
                "score":round(float(score_row[i]),6),
                "rank":rank+1,
            } for rank,i in enumerate(ranking)],
            "review_status":"semantic_similarity_only_not_claim_support",
        })
    return rows


def proposal_pairs(ranked, *, top_k=8, min_score=.3):
    """Generate contextual review queue; allow only distinct fields and pinned ref."""
    if not 2 <= top_k <= 15:
        raise ValueError("top_k must be 2..15")
    result=[]
    for row in ranked:
        choices=[m for m in row["ranked_modules"][:top_k] if m["score"] >= min_score]
        for i,a in enumerate(choices):
            for b in choices[i+1:]:
                if a["module_id"].split("-")[0] == b["module_id"].split("-")[0]:
                    continue
                result.append({
                    "source":a["module_id"], "target":b["module_id"],
                    "source_id":row["source_id"],"source_ref":row["source_url"],
                    "source_passage_sha256":row["source_passage_sha256"],
                    "relation":"CONTEXT_FOR", "status":"candidate",
                    "similarity_min":round(min(a["score"],b["score"]),6),
                    "rank_pair":[a["rank"],b["rank"]],
                    "boundary":"Co-retrieval on one source paragraph only. Does not prove the paragraph jointly entails the two module problems or their relationship.",
                    "review_status":"unverified_pair_requires_span_and_entailment_review",
                })
    return result


def load_embedder(model="sentence-transformers/all-MiniLM-L6-v2"):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model,device="cpu",local_files_only=True)


def sentence_fragments(passages, *, min_chars=30):
    """Subdivide institutional paragraphs into exact, hash-pinned sentences.

    Sentences are *review spans*, not standalone verified atomic propositions.
    Preserve source URL and parent paragraph SHA for retrieval backtracking.
    """
    import re
    output=[]
    for source in passages:
        paragraph=source["text"]
        segments=re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])",paragraph)
        for index,segment in enumerate(segments,1):
            if len(segment.strip())<min_chars:
                continue
            segment=segment.strip()
            output.append({
                "id":f"{source['id']}:sentence-{index}",
                "parent_source_id":source["id"],
                "url":source["url"],"text":segment,
                "parent_passage_sha256":hashlib.sha256(paragraph.encode()).hexdigest(),
                "sentence_sha256":hashlib.sha256(segment.encode()).hexdigest(),
                "boundary":"Sentence-local retrieval span, not an accepted semantic proposition.",
            })
    return output


def aggregate_sentence_rankings(sentence_rankings, modules):
    """Max-pool sentence relevance within each original source.

    Each selected module retains the exact *source sentence* responsible for
    its score. No source-to-source or module-to-module relation is created.
    """
    by_source={}
    for line in sentence_rankings:
        parent=line["source_id"].split(":sentence-",1)[0]
        target=by_source.setdefault(parent,{})
        for row in line["ranked_modules"]:
            mid=row["module_id"]
            score=row["score"]
            if mid not in target or score>target[mid]["score"]:
                target[mid]={"module_id":mid,"title":row["title"],"score":score,
                             "supporting_sentence_id":line["source_id"],
                             "supporting_sentence_sha256":line["source_passage_sha256"]}
    output=[]
    for parent,items in sorted(by_source.items()):
        ranked=sorted(items.values(),key=lambda row:(-row["score"],row["module_id"]))
        for i,r in enumerate(ranked,1):r["rank"]=i
        output.append({"source_id":parent,"ranked_modules":ranked,
                       "review_status":"sentence_max_similarity_only_not_entailment"})
    return output
