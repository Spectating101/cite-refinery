"""CPU-bounded blind screen of eight source-to-problem claims.

Unlike the initial long-output benchmark this deliberately asks only for a
small JSON classification map. No answer labels are supplied before inference.
No source text or findings are promoted to Cite-Refinery.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def run(source_snapshot: Path, label_file: Path, out: Path, model: str, timeout: int):
    import requests
    snapshot=json.loads(source_snapshot.read_text(encoding="utf-8"))
    cases=snapshot["case_inputs"]
    sid={c["source"]:{"source":c["source"],"passage":c["passage"]} for c in cases}
    prompt=("Examine source passages and decide whether each EXACT claim is explicitly supported by its specific excerpt. "
            "A source discussing a program does NOT show measurable outcomes; never infer numerical effects. "
            "Respond with ONLY a JSON object mapping each case ID to true or false. "
            "True = cited excerpt directly supports precise claim; false = not established by that excerpt. "
            "Every case must appear once; no explanation.\n\n")
    for k,s in sid.items():prompt+=f"SOURCE {k}: {s['passage'][:1000]}\n"
    prompt+="\nCASES:\n"
    for c in cases:prompt+=f"{c['id']} [{c['source']}]: {c['claim']}\n"
    out.parent.mkdir(parents=True,exist_ok=True)
    state={"model":model,"cases":[c["id"] for c in cases],"source_snapshot":str(source_snapshot),
           "source_digest":snapshot["source_ledger"],
           "prompt_tokens_approx_chars":len(prompt),
           "blindness":"Only source text, problem claim and ID in prompt; labels read after inference.",
           "status":"started","limits":"Eight hand-curated cases; candidate-support screening, not novel-edge discovery."}
    out.write_text(json.dumps(state,indent=2)+"\n")
    start=time.monotonic()
    try:
        resp=requests.post("http://127.0.0.1:11434/api/generate",
            json={"model":model,"prompt":prompt,"stream":False,"format":"json",
                  "keep_alive":"2m","options":{"temperature":0,"num_ctx":4096,"num_predict":240}},
            timeout=timeout)
        resp.raise_for_status()
        body=resp.json()
        raw=body.get("response","")
        try:pred=json.loads(raw)
        except ValueError:pred={}
        gold=json.loads(label_file.read_text())["gold"]
        counts={"tp":0,"tn":0,"fp":0,"fn":0,"invalid":0}
        graded=[]
        for c in cases:
            id=c["id"];got=pred.get(id);expect=gold[id]["supported"]
            if type(got) is not bool:counts["invalid"]+=1
            elif got and expect:counts["tp"]+=1
            elif not got and not expect:counts["tn"]+=1
            elif got:counts["fp"]+=1
            else:counts["fn"]+=1
            graded.append({"id":id,"expected_supported":expect,"predicted_supported":got})
        state.update({"status":"complete","elapsed_seconds":round(time.monotonic()-start,1),
                      "raw_response":raw,"scores":counts,"cases_scored":graded,
                      "correct_over_8":counts["tp"]+counts["tn"],
                      "observed_generated_tokens":body.get("eval_count")})
    except Exception as e:
        state.update({"status":"failed","elapsed_seconds":round(time.monotonic()-start,1),
                      "error_type":type(e).__name__,"error":str(e)[:700]})
    out.write_text(json.dumps(state,indent=2)+"\n")
    print("SCREEN_DONE",model,state["status"],state.get("scores"),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",type=Path,required=True)
    p.add_argument("--gold",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--model",required=True)
    p.add_argument("--timeout",type=int,default=165)
    a=p.parse_args()
    run(a.snapshot,a.gold,a.out,a.model,a.timeout)
