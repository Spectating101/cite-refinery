"""Run real model over atomic Atlas tasks. Never repair incorrect answers."""
import json
import os
from pathlib import Path
from cite_refinery.portfolio_atomic_tasks import validate_atomic_answer

def run(tasks_path, out_path):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    model_id="Qwen/Qwen2.5-0.5B-Instruct"
    tokenizer=AutoTokenizer.from_pretrained(model_id)
    model=AutoModelForCausalLM.from_pretrained(model_id,torch_dtype=torch.float32).eval()
    tasks=json.loads(Path(tasks_path).read_text())["tasks"]
    assert len(tasks)==32
    responses=[]
    for task in tasks:
        # No target verdict is placed in prompt; the model chooses, then the
        # independently defined source-coverage contract evaluates its answer.
        input_data={k:task[k] for k in ("id","question","allowed_evidence_ids","evidence_text")}
        prompt=("Answer the question from ONLY the provided repository maintainer evidence. "
                "The maintainer describing something is not independent verification of "
                "physical tests, adoption or profit. Return one plain JSON object with "
                "id, verdict (self_reported or insufficient), evidence_id, and quote. "
                "For insufficient use evidence_id null and quote empty. "
                "For self_reported quote an EXACT substring at least 12 characters. "
                "Do not use markdown.\n"+json.dumps(input_data))
        msgs=[{"role":"user","content":prompt}]
        encoded=tokenizer.apply_chat_template(msgs,tokenize=False,add_generation_prompt=True)
        inputs=tokenizer(encoded,return_tensors="pt",truncation=True,max_length=1300)
        with torch.no_grad():
            out=model.generate(**inputs,max_new_tokens=180,do_sample=False,
                               pad_token_id=tokenizer.eos_token_id)
        raw=tokenizer.decode(out[0][inputs["input_ids"].shape[1]:],skip_special_tokens=True)
        record={"id":task["id"],"raw":raw,"model_executed":True,"contract_valid":False}
        try:
            draft=json.loads(raw)
            validated=validate_atomic_answer(task,draft)
            record.update({"contract_valid":True,"validated":validated})
        except (ValueError,TypeError,KeyError) as exc:
            record["error"]=str(exc)[:250]
        responses.append(record)
        print("ATOMIC_MODEL",json.dumps({"id":task["id"],"valid":record["contract_valid"]}),flush=True)
    receipt={"schema":"cite_refinery.atomic_model_execution.v1","model":model_id,
             "tasks_total":len(responses),
             "contract_valid_count":sum(x["contract_valid"] for x in responses),
             "independently_verified_entailments":0,
             "automated_gold_not_proof_of_model_quality":True,
             "results":responses}
    Path(out_path).write_text(json.dumps(receipt,indent=2)+"\n")

if __name__=="__main__":
    run(os.environ["ATOMIC_TASKS_PATH"],os.environ["ATOMIC_ANSWERS_PATH"])
