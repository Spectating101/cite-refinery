"""Execute source-grounded hypothesis discriminator; do not make causal claims."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .discriminating_tests import review_material,design_prompt,validate_design,stage_plan
from .external_llm_runtime import invoke_semantic_llm


def main(argv=None):
    p=argparse.ArgumentParser(prog="cite-refinery-discriminate")
    p.add_argument("--workspace",required=True)
    p.add_argument("--investigation-id",required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--provider",choices=["copilot","antigravity","codex","claude","gemini","ollama"],default="copilot")
    p.add_argument("--model",default=None)
    p.add_argument("--timeout",type=int,default=180)
    p.add_argument("--model-output",type=Path,help="Validate externally captured JSON; no inference call")
    p.add_argument("--raw-response-out",type=Path,help="Optional local-only raw response for diagnosing schema failures")
    p.add_argument("--stage",action="store_true",help="Add candidate protocol only, never accepted effects")
    a=p.parse_args(argv)
    _,review=review_material(a.workspace,a.investigation_id)
    if a.model_output:
        raw=json.loads(a.model_output.read_text())
        provenance="externally_supplied_model_output_unverified_identity"
    else:
        execution=invoke_semantic_llm(design_prompt(review),provider=a.provider,
                                      model=a.model,timeout_seconds=a.timeout)
        raw=execution["raw"]
        provenance=f'{execution["provider"]}:{execution["model"]}'
    if a.raw_response_out:
        a.raw_response_out.parent.mkdir(parents=True,exist_ok=True)
        a.raw_response_out.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+"\n")
    design=validate_design(raw,review)
    design["generation_provenance"]=provenance
    if a.stage:
        staged=stage_plan(a.workspace,design)
        design["local_graph_receipt"]=staged["receipt"]["id"]
        design["declared_graph_nodes"]=staged["nodes_declared"]
        design["declared_graph_edges"]=staged["edges_declared"]
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(design,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"path":str(a.out),"mechanisms":len(design["mechanisms"]),
                     "tests":len(design["tests"]),
                     "identifiability":design["current_identifiability"],
                     "staged":bool(a.stage),
                     "graph_receipt":design.get("local_graph_receipt"),
                     "provenance":provenance},indent=2))


if __name__=="__main__":main()
