"""Blinded-to-gold, source-level semantic claim adjudication for the three-layer atlas.

This probes whether previously collected research abstracts actually entail
specific claims, rather than whether quote substrings exist. It is a *model
diagnostic*, not human validation and never promotes a native evidence status.
No sealed/held-out sources, source full-text payloads, or raw LLM output are
written to committed research artifacts.
"""
from __future__ import annotations

from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .external_llm_runtime import invoke_semantic_llm,LLMUnavailable

CASEBOOK="cite_refinery.entailment_casebook.v1"
SOURCE="cite_refinery.open_corpus.v1"
LABELS={"entailed","overreach","contradicted","unresolved"}

def normalize(value:str)->str:
    return " ".join(value.split()).casefold()

def bounded_excerpt(source:str, excerpt:str)->str:
    if not isinstance(excerpt,str) or not 8 <= len(excerpt.split()) <= 24:
        raise ValueError("quote must be between 8 and 24 source words")
    if len(excerpt)>300 or normalize(excerpt) not in normalize(source):
        raise ValueError("supporting or contradicting excerpt not found in original source")
    return excerpt.strip()

def prepare(casebook:dict[str,Any],corpus:dict[str,Any])->list[dict[str,Any]]:
    if casebook.get("schema")!=CASEBOOK or corpus.get("schema")!=SOURCE or \
       corpus.get("material_type")!="unclassified_source_records":
        raise ValueError("not the authorized development source corpus")
    if not isinstance(casebook.get("cases"),list) or not 8<=len(casebook["cases"])<=48:
        raise ValueError("bounded diagnostic casebook required")
    originals={r["id"]:r for r in corpus.get("sources",[])}
    if len(originals)!=len(corpus.get("sources",[])):
        raise ValueError("duplicate source identity")
    seen=set()
    packets=defaultdict(list)
    for case in casebook["cases"]:
        key=case["id"]
        if key in seen or not re.fullmatch("[A-Z][A-Z0-9]{1,9}",key):
            raise ValueError("duplicate or invalid case id")
        seen.add(key)
        sid=case["source_id"]
        if sid not in originals or case.get("expected") not in LABELS:
            raise ValueError("case lacks matching original or valid reference label")
        source=originals[sid]
        text=source.get("text")
        if not isinstance(text,str) or not 100<=len(text)<=12500:
            raise ValueError("source scope outside bounded abstract range")
        digest=hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest!=source.get("sha256") or not source["url"].startswith("https://"):
            raise ValueError("source identity and SHA mismatch")
        if not isinstance(case.get("claim"),str) or not 35<=len(case["claim"])<=550:
            raise ValueError("bounded claim required")
        packets[sid].append({
            "id":key,"source_id":sid,"domain":case["domain"],
            "claim":case["claim"],"source_url":source["url"],
            "source_title":source["title"],"original_sha256":digest,
            "abstract_text":text,
            "source_scope":source["source_scope"],
        })
    # One source per sealed judgement unit prevents comparing unrelated papers
    # or using external guesses instead of the source given to the judge.
    return [dict(source_id=sid,cases=items) for sid,items in sorted(packets.items())]

def judge_prompt(packet:dict[str,Any])->str:
    if not isinstance(packet.get("cases"),list) or not 1<=len(packet["cases"])<=8:
        raise ValueError("bounded same-source case packet")
    first=packet["cases"][0]
    if any(r["source_id"]!=first["source_id"] or
           r["original_sha256"]!=first["original_sha256"] for r in packet["cases"]):
        raise ValueError("judgments must share one original source")
    return (
        "TASK: BLIND SOURCE-ENTAILMENT REVIEW FOR AN EVIDENCE GRAPH. "
        "You have only an abstract/excerpt, not the full underlying article. "
        "Do not browse or use other publications. Evaluate each claim against "
        "the EXACT supplied source text, preserving population, geography, "
        "design (model, observational, intervention), measured outcome, "
        "timeframe, causal vs correlational language, and effect size. "
        "The investigator's prior conclusion is NOT shown. "
        "LABELS: entailed=the source as supplied directly establishes the claim "
        "AS WRITTEN; contradicted=source explicitly says the reverse or conflicts "
        "with a quantified statement; overreach=plausible but not established "
        "by this source, generalizes or turns correlations/models into proof; "
        "unresolved=abstract is genuinely too ambiguous to decide. "
        "For every case, COPY EXACTLY an 8-to-24 word contiguous quote from "
        "the supplied source text supporting your judgment or showing the "
        "critical study-scope limitation (not necessarily supporting the claim). "
        "Do not invent a quote. Explain why it entails/conflicts/overreaches, "
        "and identify one missing piece of evidence to test the claim or a "
        "scope condition that matters (at least 20 characters). "
        "Return JSON only: "
        '{"judgments":[{"id":"CASEID","label":"entailed|overreach|contradicted|unresolved",'
        '"quote":"exact 8-24 word contiguous excerpt",'
        '"reason":"grounded semantic rationale",'
        '"scope_caveat":"population/design/outcome/transfer caveat"}]}. '
        "Answer each case exactly once. Source statements may be claims from "
        "a paper's abstract and are not externally independently verified. "
        "SOURCE_ID="+first["source_id"]+"; SOURCE_SCOPE="+first["source_scope"]+
        "; ORIGINAL_ABSTRACT="+first["abstract_text"]+
        "; CLAIMS="+json.dumps([
            {"id":r["id"],"claim":r["claim"]} for r in packet["cases"]
        ],ensure_ascii=False,separators=(",",":"))
    )

def adjudicate(packet:dict[str,Any],response:dict[str,Any])->dict[str,Any]:
    if not isinstance(response,dict) or not isinstance(response.get("judgments"),list):
        raise ValueError("incomplete model judgment")
    expected={x["id"]:x for x in packet["cases"]}
    if len(response["judgments"])!=len(expected):
        raise ValueError("incomplete source-level adjudication is invalid")
    result=[]
    seen=set()
    for raw in response["judgments"]:
        if not isinstance(raw,dict) or raw.get("id") not in expected or raw["id"] in seen:
            raise ValueError("duplicate/unlisted judgment")
        seen.add(raw["id"])
        case=expected[raw["id"]]
        if raw.get("label") not in LABELS:
            raise ValueError("unknown source-level entailment decision")
        quote=bounded_excerpt(case["abstract_text"],raw.get("quote"))
        for key in ("reason","scope_caveat"):
            value=raw.get(key)
            if not isinstance(value,str) or not 20<=len(value.strip())<=720:
                raise ValueError(f"missing bounded {key}")
        result.append({
            "id":raw["id"],"source_id":case["source_id"],
            "domain":case["domain"],
            "claim":case["claim"],
            "label":raw["label"],"quote":quote,
            "reason":raw["reason"].strip(),
            "scope_caveat":raw["scope_caveat"].strip(),
            "source_url":case["source_url"],
            "original_sha256":case["original_sha256"],
            "validation":"source_identity_and_quote_checked_judgment_not_human_verified",
            "native_status_change_authorized":False,
        })
    if set(seen)!=set(expected):
        raise ValueError("missing case")
    return {"schema":"cite_refinery.entailment_model_judgments.v1",
            "source_id":packet["source_id"],
            "judgments":sorted(result,key=lambda x:x["id"]),
            "authority":"MODEL_REVIEW_DIAGNOSTIC_ONLY",
            "source_kind":"original_retrieved_abstract_not_full_paper"}

def evaluate(casebook:dict[str,Any],packets:list[dict[str,Any]],
             audits:list[dict[str,Any]])->dict[str,Any]:
    gold={x["id"]:x for x in casebook["cases"]}
    observed={}
    packet_ids={c["id"] for p in packets for c in p["cases"]}
    if packet_ids!=set(gold):
        raise ValueError("case set changed during review")
    for a in audits:
        if a.get("schema")!="cite_refinery.entailment_model_judgments.v1":
            raise ValueError("adjudication must use safe validated packet schema")
        for v in a["judgments"]:
            if v["id"] in observed or v["id"] not in gold or v.get("native_status_change_authorized") is not False:
                raise ValueError("duplicate or promoted audit case")
            observed[v["id"]]=v
    if set(observed)!=set(gold):
        raise ValueError("all 24 blinded cases required")
    details=[]
    confusion=defaultdict(Counter)
    for key in sorted(gold):
        a=gold[key];b=observed[key]
        confusion[a["expected"]][b["label"]]+=1
        details.append({
            "id":key,"domain":a["domain"],"source_id":a["source_id"],
            "claim":a["claim"],"reference":a["expected"],
            "model_label":b["label"],"agreement":a["expected"]==b["label"],
            "reason":b["reason"],"scope_caveat":b["scope_caveat"],
            "quote":b["quote"],"source_url":b["source_url"],
            "gold_reason":a["gold_reason"],
            "human_adjudication_complete":False,
            "commercial_or_scientific_status_promoted":False,
        })
    return {
        "schema":"cite_refinery.entailment_diagnostic_report.v1",
        "observed_at":datetime.now(timezone.utc).isoformat(),
        "n_cases":len(gold),
        "agreement_count":sum(x["agreement"] for x in details),
        "false_entailment_count":sum(x["model_label"]=="entailed" and x["reference"]!="entailed" for x in details),
        "false_contradiction_count":sum(x["model_label"]=="contradicted" and x["reference"]!="contradicted" for x in details),
        "abstentions":sum(x["model_label"]=="unresolved" for x in details),
        "reference_classes":dict(Counter(x["reference"] for x in details)),
        "confusion":{k:dict(v) for k,v in sorted(confusion.items())},
        "cases":details,
        "graph_promotion_allowed":False,
        "authority":"investigator_authored_labels_vs_independent_model_reading_of_original_retrieved_abstracts",
        "validity_limit":"Small, intentionally balanced diagnostic set; no independently recruited gold annotators, no sealed holdout or out-of-domain validation. Agreement is not model accuracy across literature, science verification or field applicability.",
    }

def render_markdown(report:dict[str,Any])->str:
    if report.get("schema")!="cite_refinery.entailment_diagnostic_report.v1":
        raise ValueError("unsupported result")
    out=[
        "# Three-layer semantic evidence diagnostic — original abstracts, not snippets", "",
        "The judgments below compare investigator-authored atomic claims with an "
        "independent AI reading of the **retrieved development-source abstracts**. "
        "They are **not** independent human research reviews or validated intervention results.","",
        f"Cases: {report['n_cases']}; agreement with investigator-drafted reference labels: "
        f"{report['agreement_count']}; falsely accepted non-entailed claims: "
        f"{report['false_entailment_count']}; model abstentions: {report['abstentions']}. "
        "Do not extrapolate these figures to external performance.", "",
        "## Disagreements and important caveats", "",
    ]
    issues=[x for x in report["cases"] if not x["agreement"]]
    if not issues:
        out.append("No label disagreements in this deliberately small casebook. "
                   "This is **not** a demonstration of independent semantic validity.")
    for x in issues:
        out += ["- **"+x["id"]+"** — reference "+x["reference"]+", model "+x["model_label"]+
                ". "+x["reason"]+"; source: "+x["source_url"]]
    out+=["","## Source-scoped checks by field",""]
    groups=defaultdict(list)
    for x in report["cases"]:groups[x["domain"]].append(x)
    for domain,rows in sorted(groups.items()):
        out+=["### "+domain.replace("_"," ").title(),""]
        for row in rows:
            out+=["- **"+row["id"]+" / "+row["model_label"]+"**: "+row["claim"]+
                  " Scope: "+row["scope_caveat"]+" [Source]("+row["source_url"]+")"]
        out.append("")
    out+=["## Gate outcome","",
          "**No autonomous graph-promotion authorized.** All these judgments "
          "remain diagnostic source interpretations. Model verdict and literal quote "
          "do not replace a human source/methodology review, independent replication, "
          "repository execution, or commercial validation. The 66-source sealed holdout "
          "was not read or used.",""]
    return "\n".join(out)

def main(argv:list[str]|None=None)->int:
    import argparse
    p=argparse.ArgumentParser(prog="cite-refinery-entailment-diagnostic")
    p.add_argument("--casebook",type=Path,required=True)
    p.add_argument("--corpus",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--markdown",type=Path,required=True)
    p.add_argument("--local-results",type=Path,required=True)
    p.add_argument("--provider",default="antigravity")
    p.add_argument("--model",default="gemini-3.8-flash-medium")
    args=p.parse_args(argv)
    cases=json.loads(args.casebook.read_text(encoding="utf-8"))
    corpus=json.loads(args.corpus.read_text(encoding="utf-8"))
    packets=prepare(cases,corpus)
    args.local_results.mkdir(parents=True,exist_ok=True)
    audits=[]
    for i,source in enumerate(packets,1):
        path=args.local_results/(source["source_id"]+".json")
        if path.exists():
            model_reply=json.loads(path.read_text(encoding="utf-8"))
        else:
            reply=invoke_semantic_llm(judge_prompt(source),provider=args.provider,
                                      model=args.model,timeout_seconds=125)
            model_reply=reply["raw"]
            # Save raw results only to the private local research dump.
            path.write_text(json.dumps(model_reply,ensure_ascii=False,indent=2)+"\n")
        audit=adjudicate(source,model_reply)
        audits.append(audit)
        print(f"Source {i}/{len(packets)}: {source['source_id']},"
              f" {len(audit['judgments'])} validated quote-bounded verdicts",flush=True)
    outcome=evaluate(cases,packets,audits)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(outcome,ensure_ascii=False,indent=2)+"\n")
    args.markdown.write_text(render_markdown(outcome),encoding="utf-8")
    print("Diagnostic outcomes: agreement",outcome["agreement_count"],"of",
          outcome["n_cases"],"false entailments",outcome["false_entailment_count"],flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
