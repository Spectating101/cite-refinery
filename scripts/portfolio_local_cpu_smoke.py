"""Run real local open-weight inference; always retain a diagnostic receipt.

This is a low-capacity smoke test, not model quality/portfolio intelligence proof.
"""
import json
import os
from pathlib import Path
from hashlib import sha256
from cite_refinery.portfolio_autonomous_dossier import (
    evidence_index, project_evidence, make_prompt, validate_dossier
)
from cite_refinery.portfolio_public_dogfood import run_public_portfolio

def main():
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    model_id = "Qwen/Qwen2.5-0.5B-Instruct"
    manifest_path = Path("research_materials/portfolio_dogfood/public_source_manifest_2026_10_23.json")
    receipt_dir = Path(os.environ["RUNNER_TEMP"])
    receipt = run_public_portfolio(json.loads(manifest_path.read_text()), token=os.environ.get("GITHUB_TOKEN"))
    assert receipt["private_repositories_included"] == 0
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float32).eval()
    index = evidence_index(receipt)
    results = []
    for row in receipt["source_snapshots"]:
        repo = row["repo"]
        local = project_evidence(receipt, repo, index)
        system, prompt = make_prompt(repo, local)
        # Extremely compact generation to demonstrate actual model execution
        # before running costly full-length reasoning with a capable provider.
        user = (
            "Read the following public repository source evidence. Output a JSON object "
            "with capabilities, limitations, integration_candidates, "
            "competitor_substitutions as empty arrays; decision='investigate', "
            "decision_rationale describing that independent field evidence is missing, "
            "and unanswered_questions with one question. Do not assert deployment.\n"
            + prompt[:3600]
        )
        messages = [{"role":"system","content":system}, {"role":"user","content":user}]
        serialized = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        input_ids = tokenizer(serialized, return_tensors="pt", truncation=True, max_length=2300).input_ids
        with torch.no_grad():
            generated = model.generate(input_ids, max_new_tokens=360, do_sample=False,
                                       pad_token_id=tokenizer.eos_token_id)
        raw = tokenizer.decode(generated[0][input_ids.shape[1]:], skip_special_tokens=True)
        result = {"repo":repo, "model_executed":True, "raw":raw,
                  "output_sha256":sha256(raw.encode()).hexdigest()}
        try:
            draft = json.loads(raw)
            result["dossier"] = validate_dossier(repo, draft, local)
            result["schema_valid"] = True
        except (ValueError, TypeError, KeyError) as exc:
            result["schema_valid"] = False
            result["validation_error"] = str(exc)[:300]
        results.append(result)
        print("LOCAL_MODEL_RESULT", json.dumps({"repo":repo,"schema_valid":result["schema_valid"]}),flush=True)
    out = {"schema":"cite_refinery.local_cpu_portfolio_smoke.v1",
           "model":model_id, "real_model_execution":True,
           "full_autonomous_analysis_proven":False,
           "independent_gold_graded":False, "projects":results}
    (receipt_dir/"portfolio-cpu-smoke.json").write_text(json.dumps(out,indent=2))
    print("MODEL_EXECUTION",json.dumps({"count":len(results),
                                       "schema_valid":sum(x["schema_valid"] for x in results)}))


if __name__ == "__main__":
    main()
