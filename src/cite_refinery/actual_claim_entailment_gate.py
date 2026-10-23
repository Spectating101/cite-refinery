"""Evaluate a real NLI inference model on frozen source-derived claim/evidence pairs.

A conservative review triage, NOT independent scientific adjudication.
Source excerpts and expected labels were hand-curated by investigators in the
existing 2026-10-20 regression set. CrossEncoder is never passed gold labels.
No graph state, Nocturnal private files, Academic sealed holdout or claims
are promoted by this module.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Callable
import argparse
import json
import math
import re

SCHEMA="cite_refinery.nli_original_source_claim_triage.v1"
SOURCE="cite_refinery.adjudication_benchmark.v1"
DOI="10.14202/vetworld.2026.2816-2849"
FROZEN_PAPER_SHA="4210e7ebc871f3db31dee6cb761f09d82e4f29f49aceed6a860c268e74176b7e"
MODEL="cross-encoder/nli-MiniLM2-L6-H768"
REVISION="f3b1e8aac2451320dfe2ce56673b3f2ec63e6f03"
LABELS=("contradiction","entailment","neutral")
EXPECTED={"entailed":8,"contradicted":8,"overreach":3,"unresolved":2}
# Precommitted; changing this after viewing predictions would invalidate the
# test as a first-pass developer evaluation.
CONFIDENCE_THRESHOLD=0.90
MARGIN_THRESHOLD=0.20
MAX_CASES=30
SWAPS=(
    ("SWAP-01","B01","B09"),
    ("SWAP-02","B06","B01"),
    ("SWAP-03","B12","B08"),
    ("SWAP-04","B19","B10"),
)


def _require(condition,reason):
    if not condition: raise ValueError(reason)


def _canon(data):
    return json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(",",":"))


def _sha(data):
    return sha256(_canon(data).encode("utf-8")).hexdigest()


def _check_source(data):
    _require(isinstance(data,dict) and data.get("schema")==SOURCE
             and data.get("source_doi")==DOI
             and data.get("source_sha256")==FROZEN_PAPER_SHA
             and data.get("gold_annotation")=="curated_source_anchored_not_independent_human_gold",
             "Wrong/unknown historical original article source casebook")
    records=data.get("cases")
    _require(isinstance(records,list) and len(records)==21,
             "Historical 21-case source excerpt set incomplete")
    by_id={}
    for x in records:
        _require(isinstance(x,dict) and isinstance(x.get("id"),str)
                 and re.fullmatch(r"B(0[1-9]|1[0-9]|2[01])",x["id"])
                 and x["id"] not in by_id
                 and isinstance(x.get("claim"),str) and 15<=len(x["claim"])<=900
                 and isinstance(x.get("evidence"),str) and 20<=len(x["evidence"])<=2200
                 and x.get("expected") in EXPECTED
                 and isinstance(x.get("gold_reason"),str)
                 and len(x["gold_reason"])>=12,
                 "Malformed or duplicated historical source case")
        by_id[x["id"]]=x
    _require(set(by_id)=={"B"+str(i).zfill(2) for i in range(1,22)}
             and Counter(x["expected"] for x in records)==EXPECTED,
             "Source casebook labels/identities changed")
    return records,by_id


def _blind_pairs(data):
    records,by_id=_check_source(data)
    # ID/label references never reach the actual model input array.
    standard=[{
        "id":r["id"],"claim":r["claim"],"evidence":r["evidence"],
        "source_kind":"original_or_source_derived_curated_excerpt",
        "source_evidence_sha256":sha256(r["evidence"].encode()).hexdigest(),
    } for r in records]
    for identifier,claim_id,evidence_id in SWAPS:
        claim=by_id[claim_id]["claim"]
        passage=by_id[evidence_id]["evidence"]
        standard.append({
            "id":identifier,"claim":claim,"evidence":passage,
            "source_kind":"deliberately_cross_swapped_different_claim_source_negative_control",
            "source_evidence_sha256":sha256(passage.encode()).hexdigest(),
        })
    _require(len(standard)==25 and len({x["id"] for x in standard})==25,
             "NLI evaluation cases incomplete")
    return standard,by_id


def real_model(pairs):
    """Actual CPU CrossEncoder: exact pinned HF revision, no fake scorer fallback."""
    from sentence_transformers import CrossEncoder
    import numpy as np
    model=CrossEncoder(MODEL,device="cpu",max_length=512,revision=REVISION)
    # HF model's own published config is the only authority for class order.
    mapping={int(i):str(x).lower() for i,x in model.model.config.id2label.items()}
    _require([mapping.get(i) for i in range(3)]==list(LABELS),
             "Unexpected NLI label order; refuse interpretation")
    inputs=[(r["evidence"],r["claim"]) for r in pairs]
    values=np.asarray(model.predict(inputs,batch_size=8,
                      convert_to_numpy=True,show_progress_bar=False),dtype=float)
    _require(values.shape==(25,3) and np.isfinite(values).all(),
             "NLI returned malformed or nonfinite original logits")
    return values.tolist()


def _softmax(logits):
    _require(isinstance(logits,(list,tuple)) and len(logits)==3
             and all(type(x) in (float,int) and math.isfinite(x) for x in logits),
             "NLI must return three finite raw logits")
    mx=max(logits)
    e=[math.exp(v-mx) for v in logits]
    total=sum(e)
    return [x/total for x in e]


def _triage(logits):
    probabilities=_softmax(logits)
    best=max(range(3),key=lambda i:probabilities[i])
    runner=sorted(probabilities,reverse=True)[1]
    # Never give 'entailed' authority automatically; high-confidence
    # supports/contradictions are candidate-review classes only.
    if (probabilities[best]<CONFIDENCE_THRESHOLD
            or probabilities[best]-runner<MARGIN_THRESHOLD
            or LABELS[best]=="neutral"):
        triage="abstain_needs_original_source_review"
    elif LABELS[best]=="entailment":
        triage="candidate_supported_requires_original_source_review"
    else:
        triage="candidate_contradicted_requires_original_source_review"
    return triage, dict(zip(LABELS,[round(x,6) for x in probabilities]))


def evaluate(data, *, infer: Callable=real_model, model_name=MODEL):
    pairs,by_id=_blind_pairs(data)
    # A future injected mock/model backend must be clearly distinguished.
    _require(isinstance(model_name,str) and 5<len(model_name)<160,
             "Model label required")
    logits=infer(pairs)
    _require(isinstance(logits,(list,tuple)) and len(logits)==25,
             "NLI prediction array missing or incomplete")
    results=[]
    tally=Counter()
    for row,raw in zip(pairs,logits):
        status,probs=_triage(raw)
        label=by_id[row["id"]]["expected"] if row["id"] in by_id else "source_swap_unrelated_control"
        accepted=status=="candidate_supported_requires_original_source_review"
        contradicted=status=="candidate_contradicted_requires_original_source_review"
        tally["total"]+=1
        tally["candidate_support"]+=int(accepted)
        tally["candidate_contradiction"]+=int(contradicted)
        tally["abstained"]+=int(status=="abstain_needs_original_source_review")
        tally["true_supported_candidate"]+=int(accepted and label=="entailed")
        tally["unsafe_false_candidate_support"]+=int(accepted and label!="entailed")
        tally["false_candidate_contradiction"]+=int(contradicted and label!="contradicted")
        tally["correct_contradiction_candidate"]+=int(contradicted and label=="contradicted")
        tally["unresolved_abstained"]+=int(label=="unresolved" and status.startswith("abstain"))
        tally["overreach_abstained"]+=int(label=="overreach" and status.startswith("abstain"))
        tally["source_swaps_abstained"]+=int(label=="source_swap_unrelated_control" and status.startswith("abstain"))
        results.append({
            "id":row["id"],"source_kind":row["source_kind"],
            "reference_label":label, "model_label":max(probs,key=probs.get),
            "triage":status,"normalized_model_scores":probs,
            "source_evidence_sha256":row["source_evidence_sha256"],
            "claim_sha256":sha256(row["claim"].encode("utf-8")).hexdigest(),
            "source_text_sha_verified_against_original_published_fulltext_in_this_run":False,
            "verified_original_source_entailment":False,
            "human_approved":False,
        })
    _require(tally["total"]==25 and
             tally["candidate_support"]+tally["candidate_contradiction"]+tally["abstained"]==25,
             "Unaccounted NLI outputs")
    return {
        "schema":SCHEMA,
        "source_casebook_sha256":_sha(data),
        "source_doi":DOI, "reported_original_article_text_sha256":FROZEN_PAPER_SHA,
        "model":model_name,"model_revision":REVISION if infer is real_model else "injected_test_only",
        "inference_mode":"real_pretrained_cpu_cross_encoder" if infer is real_model else "injected_test_only",
        "model_labels":list(LABELS),
        "predeclared_policy":{"candidate_min_softmax":CONFIDENCE_THRESHOLD,
                              "minimum_top_probability_margin":MARGIN_THRESHOLD,
                              "neutral_always_abstains":True},
        "historical_reference_labels":EXPECTED,
        "source_derived_case_count":21,
        "deliberately_mismatched_source_negatives":4,
        "counts":dict(sorted(tally.items())),
        "false_supported_cases":[r["id"] for r in results if r["triage"].startswith("candidate_supported") and r["reference_label"]!="entailed"],
        "unresolved_cases":[r for r in results if r["reference_label"]=="unresolved"],
        "source_mismatch_cases":[r for r in results if r["reference_label"]=="source_swap_unrelated_control"],
        "case_results":results,
        "independent_gold_labels_available":False,
        "original_article_sha_independently_checked_this_run":False,
        "actual_source_claim_support_independently_human_validated":False,
        "support_or_contradiction_automatically_promoted":False,
        "cross_layer_claims_created":0,
        "functional_code_suitability_verified":False,
        "reliably_safe_abstention_generalized_to_other_domains":False,
        "note":"Curated source excerpt comparisons only; NLI is an imperfect candidate triage signal, not a reviewer or source-of-truth.",
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args(argv)
    _require(args.cases.is_file() and not args.cases.is_symlink()
             and args.cases.stat().st_size<100_000,
             "Missing/oversized historical source casebook")
    _require(not args.out.exists(),"Never overwrite original inference result")
    result=evaluate(json.loads(args.cases.read_text("utf-8")))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n","utf-8")
    print("REAL_SOURCE_NLI_GATE",json.dumps({
        "model":result["model"],"model_revision":result["model_revision"],
        "cases":result["source_derived_case_count"],
        "source_swap_controls":result["deliberately_mismatched_source_negatives"],
        "counts":result["counts"],
        "false_supported_cases":result["false_supported_cases"],
        "no_promotion":not result["support_or_contradiction_automatically_promoted"],
    },sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
