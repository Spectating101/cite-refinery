"""Small real-model evidence calibration comparison (NOT portfolio intelligence proof).

Runs a held-out style mixed subset across four real pinned PUBLIC projects.
The model sees only question and source evidence. Task-kind labels stay hidden.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from collections import Counter

from cite_refinery.portfolio_atomic_tasks import tasks_from_receipt, validate_atomic_answer
from cite_refinery.portfolio_public_dogfood import run_public_portfolio

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
# Exactly two direct source attributions and six verification-dependent questions.
SELECTED = (
    "hardware-splicer:self_description",
    "hardware-splicer:physical_validation",
    "yzu-cluster:adoption",
    "gauntlet-blowback:commercial",
    "cite-refinery:self_description",
    "cite-refinery:adoption",
    "Invisible-ledger:commercial",
    "citation-engine:physical_validation",
)

def parse_generated(raw):
    """A fenced JSON response may be decoded, NEVER converted into a pass."""
    value = raw.strip()
    fence = value.startswith("```")
    if fence:
        lines = value.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            value = "\n".join(lines[1:-1])
    return json.loads(value), fence


def score_one(task, raw):
    observation={"id":task["id"],"raw":raw,"model_executed":True,
                 "parsed":False,"contract_valid":False,"fenced":False}
    try:
        draft, fenced=parse_generated(raw)
        observation["parsed"]=True
        observation["fenced"]=fenced
        observation["predicted_verdict"]=draft.get("verdict")
        observation["predicted_evidence_id"]=draft.get("evidence_id")
        validated=validate_atomic_answer(task,draft)
        observation["contract_valid"]=validated["contract_valid"]
    except (ValueError,TypeError,KeyError,AttributeError) as exc:
        observation["validation_error"]=str(exc)[:350]
    # Not a real-world negative. Gold asks whether this evidence packet
    # establishes the claim, not whether the project has achieved it.
    observation["requires_independent_proof"]=task["task_kind"]=="requires_independent_evidence"
    observation["false_source_approval"]=(observation["requires_independent_proof"]
                  and observation.get("predicted_verdict")=="self_reported")
    return observation


def run(out):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    torch.set_num_threads(2)
    manifest=json.loads(Path("research_materials/portfolio_dogfood/public_source_manifest_2026_10_23.json").read_text())
    receipt=run_public_portfolio(manifest, token=os.environ.get("GITHUB_TOKEN"))
    pack=tasks_from_receipt(receipt)
    indexed={t["id"]:t for t in pack["tasks"]}
    tasks=[indexed[key] for key in SELECTED]
    tokenizer=AutoTokenizer.from_pretrained(MODEL)
    model=AutoModelForCausalLM.from_pretrained(MODEL,torch_dtype=torch.bfloat16).eval()
    results=[]
    for task in tasks:
        # No gold labels, task kind or baseline decision shown to inference.
        evidence={"id":task["id"],"question":task["question"],
                  "source_id":task["allowed_evidence_ids"][0],
                  "maintainer_source":task["evidence_text"][:650]}
        instruction=(
          "Respond in ONE valid JSON object. No markdown. Keys must be "
          "id, verdict, evidence_id, quote. EXACT id must equal question id. "
          "Allowed verdicts: self_reported, insufficient. 'self_reported' "
          "means the maintainer source explicitly describes a capability; "
          "it does NOT prove independently measured outcomes. 'insufficient' "
          "means supplied source does not independently establish what the "
          "question asks. For self_reported, evidence_id must be source_id "
          "and quote must be an exact substring of source text, >=12 chars. "
          "For insufficient, evidence_id must be null and quote empty. "
          "Distinguish a relevant README from independent adoption, physical "
          "measurement and paying revenue. Do not invent evidence.\n"
          +json.dumps(evidence,sort_keys=True))
        tokens=tokenizer.apply_chat_template(
            [{"role":"user","content":instruction}],tokenize=False,
            add_generation_prompt=True)
        inputs=tokenizer(tokens,return_tensors="pt",truncation=True,max_length=1024)
        with torch.no_grad():
            generated=model.generate(**inputs,max_new_tokens=150,do_sample=False,
                                     pad_token_id=tokenizer.eos_token_id)
        raw=tokenizer.decode(generated[0][inputs["input_ids"].shape[1]:],
                             skip_special_tokens=True)
        item=score_one(task,raw)
        results.append(item)
        print("CALIBRATION_QUESTION",json.dumps({"id":task["id"],
             "parsed":item["parsed"],"valid":item["contract_valid"],
             "false_source_approval":item["false_source_approval"]}),flush=True)
    result={"schema":"cite_refinery.stronger_model_calibration_pilot.v1",
            "model":MODEL,"model_inference_completed":True,
            "projects_covered":len({t["repo"] for t in tasks}),
            "questions":len(results),
            "contract_valid":sum(x["contract_valid"] for x in results),
            "source_false_approvals":sum(x["false_source_approval"] for x in results),
            "model_responses":results,
            "not_independent_gold_or_product_assessment":True,
            "result_scope":"source_attribution_and_insufficient_evidence_only"}
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("CALIBRATION_SUMMARY",json.dumps({k:result[k] for k in
          ("questions","contract_valid","source_false_approvals")},sort_keys=True))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    assert not args.out.exists()
    run(args.out)

if __name__=="__main__":
    main()
