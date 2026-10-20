"""Blind(ish) independent-source semantic gate benchmark for Cite-Refinery.

The benchmark labels are written and frozen in a separate static JSON file
before inference. They are NEVER included in Ollama prompts. Test set is
intentionally tiny, not a representative validation. Official pages are
retrieved fresh and content hashes pinned; all answers remain unaccepted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

BENCHMARK_CASES = [
    {"id":"WMO-context", "source":"WMO", "from":"WA-06", "to":"DR-01",
     "claim":"WMO explicitly describes HydroSOS as supporting its Early Warnings for All initiative for hydrological disasters."},
    {"id":"Rabies-context", "source":"RABIES", "from":"AW-03", "to":"PH-02",
     "claim":"WHO includes access to human post-exposure prophylaxis alongside mass dog vaccination in dog-mediated rabies prevention."},
    {"id":"Air-context", "source":"AIR", "from":"AQ-01", "to":"PH-06",
     "claim":"WHO connects ambient particulate air pollution to cardiovascular and respiratory illness."},
    {"id":"Water-context", "source":"WATER", "from":"WA-01", "to":"PH-02",
     "claim":"WHO says inadequately managed water and sanitation expose patients and healthcare staff to health risks."},
    {"id":"WMO-overclaim", "source":"WMO", "from":"WA-06", "to":"DR-01",
     "claim":"The WMO page demonstrates that HydroSOS deployment reduced deaths by 20% in a controlled local impact evaluation."},
    {"id":"Rabies-overclaim", "source":"RABIES", "from":"AW-03", "to":"PH-02",
     "claim":"The WHO page establishes that dog vaccination alone removes every need for human post-exposure prophylaxis."},
    {"id":"Air-overclaim", "source":"AIR", "from":"AQ-01", "to":"EN-01",
     "claim":"The WHO page establishes that grid congestion mitigation measurably reduced ambient PM2.5 by 30%."},
    {"id":"Water-overclaim", "source":"WATER", "from":"WA-01", "to":"ED-01",
     "claim":"The WHO page documents a randomized trial proving drinking-water access increased children's reading scores."},
]
SOURCES = {
    "WMO":("https://wmo.int/activities/hydrosos",
           ("WMO’s Global Hydrological Status and Outlook System (HydroSOS)",)),
    "RABIES":("https://www.who.int/news-room/fact-sheets/detail/rabies",
             ("WHO and its global partners aim to end human deaths",)),
    "AIR":("https://www.who.int/news-room/fact-sheets/detail/ambient-(outdoor)-air-quality-and-health",
           ("Ambient (outdoor) air pollution in both cities and rural areas was estimated",)),
    "WATER":("https://www.who.int/news-room/fact-sheets/detail/drinking-water",
             ("Contaminated water and poor sanitation are linked",)),
}


def source_pack():
    import requests
    from bs4 import BeautifulSoup
    result={}
    for sid,(url,starts) in SOURCES.items():
        r=requests.get(url,timeout=18,headers={"User-Agent":"Mozilla/5.0 research citation audit"})
        r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        paragraphs=[" ".join(p.get_text(" ",strip=True).split()) for p in soup.find_all(["p","li"])]
        matched=[]
        for start in starts:
            matches=[p for p in paragraphs if p.casefold().startswith(start.casefold())]
            if not matches: raise RuntimeError(f"Could not locate exact expected passage {sid} {start!r}")
            matched.append(matches[0][:1500])
        result[sid]={"id":sid,"url":url,"passages":matched,
                     "source_sha256":hashlib.sha256(r.content).hexdigest(),
                     "passage_sha256":hashlib.sha256("\n".join(matched).encode()).hexdigest()}
    return result


def parse_model_output(response):
    # Structured Ollama JSON output, with no automatic retry/cherry picking.
    try:
        obj=json.loads(response)
        ans=obj.get("results")
        if not isinstance(ans,list):return {}, "missing_results_array"
        mapped={}
        for row in ans:
            if not isinstance(row,dict) or not isinstance(row.get("id"),str):continue
            if row["id"] not in mapped:mapped[row["id"]]=row
        return mapped, None
    except Exception as e:
        return {},type(e).__name__


def call_model(model, prompts, *, timeout_s=230):
    import requests
    prompt=("You are auditing whether a claim is EXPLICITLY SUPPORTED by a single quoted institution source excerpt. "
            "Be strict: adjacent relevance is not causal evidence and program documentation is not an impact evaluation. "
            "For each claim give 'supported' true ONLY if the stated claim is supported by the exact quoted excerpt. "
            "If supported, cite one exact verbatim quote from that excerpt (at least 15 characters). "
            "If unsupported, set supported false and quote to empty string; do not invent page numbers or sources. "
            "Return JSON object with 'results' array of {id,supported,quote}, preserving all case IDs. "
            "The inputs have no provided gold answers.\n\n")
    for c in prompts:prompt+=f"CASE {c['id']}  DOCUMENT {c['source']} URL {c['url']}\nPASSAGE: {c['passage']}\nCLAIM: {c['claim']}\n\n"
    started=time.monotonic()
    r=requests.post("http://127.0.0.1:11434/api/generate",
                    json={"model":model,"prompt":prompt,"format":"json","stream":False,
                          "keep_alive":"1m",
                          "options":{"temperature":0,"num_ctx":8192,"num_predict":780}},
                    timeout=timeout_s)
    r.raise_for_status();body=r.json()
    return {"model":model,"elapsed_seconds":round(time.monotonic()-started,1),
            "response":body.get("response",""),
            "total_duration_ns":body.get("total_duration"),
            "eval_count":body.get("eval_count")}


def grade(prompt_rows,output,gold):
    mapped,error=parse_model_output(output["response"])
    tally={"true_positive":0,"true_negative":0,"false_positive":0,"false_negative":0,
           "missing_or_invalid":0,"verbatim_supported_quotes":0,"false_quotes":0}
    rows=[]
    for c in prompt_rows:
        id=c["id"];expected=gold[id]["supported"];pred=mapped.get(id,{})
        valid=isinstance(pred.get("supported"),bool)
        quote=str(pred.get("quote") or "").strip()
        quote_valid=bool(quote and len(quote)>=15 and " ".join(quote.lower().split())
                         in " ".join(c["passage"].lower().split()))
        if not valid: tally["missing_or_invalid"]+=1
        elif pred["supported"] and expected: tally["true_positive"]+=1
        elif not pred["supported"] and not expected: tally["true_negative"]+=1
        elif pred["supported"]:tally["false_positive"]+=1
        else:tally["false_negative"]+=1
        if quote and quote_valid:tally["verbatim_supported_quotes"]+=1
        if quote and not quote_valid:tally["false_quotes"]+=1
        rows.append({"id":id,"expected_supported":expected,
                     "model_supported":pred.get("supported"),"decision_valid":valid,
                     "quote":quote[:400],"quote_present":quote_valid})
    totals=tally["true_positive"]+tally["true_negative"]+tally["false_positive"]+tally["false_negative"]
    tally["accuracy_over_8"]=round((tally["true_positive"]+tally["true_negative"])/len(prompt_rows),3)
    tally["precision_when_positive"]=(round(tally["true_positive"]/(tally["true_positive"]+tally["false_positive"]),3)
                                      if tally["true_positive"]+tally["false_positive"] else None)
    tally["recall_when_positive"]=(round(tally["true_positive"]/(tally["true_positive"]+tally["false_negative"]),3)
                                   if tally["true_positive"]+tally["false_negative"] else None)
    return {"score":tally,"cases":rows,"parse_error":error}


def run(*,models,output,truth):
    src=source_pack()
    case_map = {c["id"]:{**c,"url":src[c["source"]]["url"],
                         "passage":"\n".join(src[c["source"]]["passages"])}
                for c in BENCHMARK_CASES}
    # Stable interleaved presentation; no outcome labels appear in the model prompt.
    case_order = ["WMO-overclaim", "Air-context", "Water-overclaim", "Rabies-context",
                  "Air-overclaim", "WMO-context", "Rabies-overclaim", "Water-context"]
    cases = [case_map[key] for key in case_order]
    result={"experiment":"source-grounded-semantic-holdout-20261020",
            "design":"8 controlled examples, four source-supported and four unsupported impact-strength overclaims",
            "source_ledger":src,
            "case_inputs":cases,
            "blindness_boundary":"Only source excerpts and claim statements included in prompt. Answer labels stored in separate gold file not provided to inference.",
            "evaluations":{},
            "limitations":[
                "Small hand-authored fixture, not generalization or an unbiased estimate of model reliability.",
                "Sources chosen with matching spans, which makes extraction easier than ordinary discovery.",
                "Gold is manual interpretation of quoted statements, not independent multi-rater adjudication.",
                "A passing quote substring is not semantic entailment; no graph acceptance follows.",
                "This tests explicit support for candidate claims, not fully autonomous novel relation discovery.",
                "Runtime depends on local Ollama processor/memory contention and source access.",
            ]}
    output.parent.mkdir(parents=True,exist_ok=True)
    # Keep source snapshot even if generation times out or interrupted.
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    for model in models:
        try:
            raw=call_model(model,cases)
            # Load labels *after* inference has already completed for this model.
            gold=json.loads(truth.read_text())["gold"]
            grading=grade(cases,raw,gold)
            result["evaluations"][model]={
                "elapsed_seconds":raw["elapsed_seconds"],
                "raw_model_response":raw["response"],
                "llm_eval_token_count":raw["eval_count"],
                **grading,
            }
        except Exception as e:
            result["evaluations"][model]={"status":"failed",
                                          "error_type":type(e).__name__,
                                          "error":str(e)[:600]}
        output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
        print("MODEL_FINISHED",model,
              result["evaluations"][model].get("score"),
              flush=True)
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--model",action="append",default=[])
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--gold",type=Path,required=True)
    o=p.parse_args()
    run(models=o.model or ["qwen2.5:7b-instruct"],output=o.out,truth=o.gold)
