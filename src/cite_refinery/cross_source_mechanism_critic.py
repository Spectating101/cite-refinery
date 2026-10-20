"""Second semantic pass: challenge synthesized mechanisms using original abstracts.

This is a deliberately adverse model review of interpretation, not original
source authentication or independent expert acceptance. It surfaces unsupported
leaps in the actual 3-layer dossier, not only constructed diagnostic statements.
"""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from .external_llm_runtime import invoke_semantic_llm
from .semantic_entailment_diagnostic import normalize,bounded_excerpt

LABELS={"bounded_support","partial_support","unresolved","scope_conflict"}

def inputs(primary:dict[str,Any],corpus:dict[str,Any])->list[dict[str,Any]]:
    if primary.get("schema")!="cite_refinery.primary_mechanism_graph.v1" or \
       corpus.get("schema")!="cite_refinery.open_corpus.v1":
        raise ValueError("must inspect source-bounded original mechanisms")
    originals={s["id"]:s for s in corpus["sources"]}
    results=[]
    for brief in primary["briefs"]:
        referenced=[]
        for r in brief["primary_sources"]:
            source=originals.get(r["id"])
            if source is None or source["url"]!=r["url"]:
                raise ValueError("mechanism citation identity unsupported by originals")
            full=source["text"]
            digest=hashlib.sha256(full.encode()).hexdigest()
            if digest!=source["sha256"] or digest!=r["original_sha256"] or \
               normalize(r["quote"]) not in normalize(full):
                raise ValueError("tampered source or original quotation")
            referenced.append({
                "id":source["id"],"title":source["title"],
                "url":source["url"],"scope":source["source_scope"],
                "sha256":digest,"abstract":full,
            })
        if len(referenced)<2:
            raise ValueError("cannot assess cross-source dossier using single citation")
        lead=brief["implementation_lead"]
        results.append({
            "id":brief["id"],"problem":brief["problem"],
            "mechanism":brief["mechanism"],
            "capability_contract":brief["capability_contract"],
            "proposed_implementation":({
                "id":lead["id"],"readme_excerpt":lead["readme_anchor"],
                "scope_gap":lead["component_gap"],
                "status":"unexecuted README claim",
            } if lead else None),
            "sources":referenced,
        })
    return results

def prompt(packet:dict[str,Any])->str:
    if not 2<=len(packet.get("sources",[]))<=7:
        raise ValueError("bounded mechanism sources")
    return (
        "You are an adversarial scientific scope and mechanism checker. "
        "The author created an aggregate problem/mechanism and a possible technical "
        "component using multiple separate retrieved ABSTRACTS. Investigate whether "
        "the mechanism actually follows from those sources, or combines separate "
        "studies into an unjustified joint inference. No browsing or tool use. "
        "Preserve observational vs modeled vs intervention, sample geography, "
        "measured outcome, temporal scope, and contradictions. "
        "Choose overall 'bounded_support' ONLY if supplied abstracts collectively "
        "directly establish the mechanism exactly AS WRITTEN, without adding "
        "untested context or causal effects; 'partial_support' when parts follow "
        "but critical extrapolations remain; 'unresolved' when text inadequate; "
        "'scope_conflict' when source evidence directly rules out a key part. "
        "Critically: no generic adjacent research counts as proof that an OSS "
        "component solves the operational problem. "
        "Select exactly one real source citation with source_id and copy an "
        "8-to-24-word VERBATIM snippet from the original abstract illustrating "
        "the crucial supported or limiting evidence. "
        "Return JSON ONLY with exact keys: "
        '{"id":"mechanism:...",'
        '"assessment":"bounded_support|partial_support|unresolved|scope_conflict",'
        '"source_id":"one exactly supplied ID","quote":"8-24 consecutive source words",'
        '"what_is_supported":"specific limited supported proposition",'
        '"unsupported_leap":"strongest unwarranted inference or missing relationship",'
        '"next_decisive_check":"specific external data, code execution or study that would discriminate",'
        '"implementation_scope":"what selected README component proves or does not prove; or explain no candidate",'
        '"cross_source_warning":"population, study-design, context or endpoint mismatch"}'
        ". Avoid broad claims of absence, profitability, clinical efficacy, "
        "or licensing. These are retrieved abstracts, not independently checked "
        "full text. CASE:\n"+json.dumps(packet,ensure_ascii=False,separators=(",",":"))
    )

def validate(packet:dict[str,Any],answer:dict[str,Any])->dict[str,Any]:
    if not isinstance(answer,dict) or answer.get("id")!=packet["id"] or \
       answer.get("assessment") not in LABELS:
        raise ValueError("unidentified or unsupported mechanism verdict")
    source={s["id"]:s for s in packet["sources"]}.get(answer.get("source_id"))
    if source is None:
        raise ValueError("model invented source identity")
    quote=bounded_excerpt(source["abstract"],answer.get("quote"))
    for k in ("what_is_supported","unsupported_leap","next_decisive_check",
              "implementation_scope","cross_source_warning"):
        value=answer.get(k)
        if not isinstance(value,str) or not 25<=len(value.strip())<=900:
            raise ValueError(f"missing substantive assessment field {k}")
    return {
        "id":packet["id"],"assessment":answer["assessment"],
        "source_id":source["id"],"source_url":source["url"],
        "original_sha256":source["sha256"],"quote":quote,
        **{k:answer[k].strip() for k in (
            "what_is_supported","unsupported_leap","next_decisive_check",
            "implementation_scope","cross_source_warning")},
        "source_quote_checked":True,
        "independently_human_validated":False,
        "accepted_academic_edge":False,
        "validated_implementation":False,
        "commercial_conversion_confirmed":False,
        "authority":"adversarial_model_interpretation_not_authoritative_entailment",
    }

def summarize(results:list[dict[str,Any]])->dict[str,Any]:
    if not 1<=len(results)<=20 or len({x["id"] for x in results})!=len(results):
        raise ValueError("bounded unique mechanism review required")
    from collections import Counter
    counts=dict(Counter(x["assessment"] for x in results))
    if any(x.get("accepted_academic_edge") is not False or
           x.get("validated_implementation") is not False for x in results):
        raise ValueError("model review is forbidden from promoting the graph")
    return {
        "schema":"cite_refinery.cross_source_mechanism_review.v1",
        "observed_at":datetime.now(timezone.utc).isoformat(),
        "assessments":sorted(results,key=lambda x:x["id"]),
        "counts":counts,
        "promotion_allowed":False,
        "status":"adversarial_model_review_requires_independent_expert_or_source_methodology_confirmation",
        "boundary":"Original retrieved abstracts only. Stronger than quote matching, but model-led and no independent human gold, code tests, original complete papers or deployed outcomes; no graph status changed.",
    }

def markdown(report:dict[str,Any])->str:
    if report.get("schema")!="cite_refinery.cross_source_mechanism_review.v1":
        raise ValueError("wrong cross-source review")
    out=["# Eight synthesized mechanisms under adversarial source review","",
         "These are model assessments of cross-source inference using the original "
         "retrieved abstracts, not human-approved scientific or technical results.",""]
    for x in report["assessments"]:
        out+=["## "+x["id"].removeprefix("mechanism:").replace("_"," ").title(),"",
              "**Source-scope assessment:** "+x["assessment"].replace("_"," ")+".","",
              "**Bounded support:** "+x["what_is_supported"],"",
              "**Critical unsupported leap:** "+x["unsupported_leap"],"",
              "**Different populations / endpoints:** "+x["cross_source_warning"],"",
              "**Unexecuted implementation:** "+x["implementation_scope"],"",
              "**Decisive next test:** "+x["next_decisive_check"],"",
              "Source excerpt: *"+x["quote"]+"* ([retrieved abstract]("+x["source_url"]+")).",""]
    out+=["## Authority boundary","",
          "No Academic node or implementation relation has been promoted. "
          "This is source-dependent model interpretation and must be checked "
          "against full methods, conflicting findings and independent operation.",""]
    return "\n".join(out)

def main(argv:list[str]|None=None)->int:
    import argparse
    p=argparse.ArgumentParser(prog="cite-refinery-mechanism-critic")
    p.add_argument("--primary",required=True,type=Path)
    p.add_argument("--corpus",required=True,type=Path)
    p.add_argument("--local-results",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--markdown",required=True,type=Path)
    p.add_argument("--provider",default="antigravity")
    p.add_argument("--model",default="gemini-3.8-flash-medium")
    a=p.parse_args(argv)
    def load(path):return json.loads(path.read_text(encoding="utf-8"))
    cases=inputs(load(a.primary),load(a.corpus))
    a.local_results.mkdir(parents=True,exist_ok=True)
    records=[]
    for i,case in enumerate(cases,1):
        path=a.local_results/(case["id"].removeprefix("mechanism:")+".json")
        if path.exists():raw=load(path)
        else:
            raw=invoke_semantic_llm(prompt(case),provider=a.provider,
                                    model=a.model,timeout_seconds=160)["raw"]
            path.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+"\n")
        outcome=validate(case,raw)
        records.append(outcome)
        print(f"{i}/{len(cases)} {case['id']}: {outcome['assessment']}; "
              f"adjudication still pending",flush=True)
    result=summarize(records)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    a.markdown.write_text(markdown(result),encoding="utf-8")
    print("Model mechanism review:",result["counts"],flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
