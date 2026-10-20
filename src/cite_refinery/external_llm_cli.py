"""Experimental LLM-first semantic review: prepare, run, inspect, stage.

The consumer may use a locally authenticated Claude/Gemini CLI, local Ollama,
or this ChatGPT session via an exported prompt and pasted JSON response.
No automatic accepted-graph writes. Source texts must be supplied explicitly.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from cite_refinery.external_llm_reasoner import (make_input, build_prompt, inspect_answer,
    build_second_pass_prompt, inspect_second_pass)
from cite_refinery.external_llm_packets import llm_review_packet
from cite_refinery.external_llm_runtime import invoke_semantic_llm


def main():
    p=argparse.ArgumentParser(description="Source-grounded LLM semantic reasoning -> isolated candidate review packet")
    p.add_argument("--sources",type=Path,required=True,help="JSON list of {id,url,text,source_scope,origin_type}")
    p.add_argument("--modules",type=Path,required=True,help="JSON list of {id,title,summary}")
    p.add_argument("--out",type=Path,required=True,help="Directory to write prompt and review artifacts")
    p.add_argument("--provider",choices=["manual","ollama","claude","gemini"],default="manual")
    p.add_argument("--model",default=None)
    p.add_argument("--response-json",type=Path,
                   help="Already supplied LLM reasoning JSON, e.g. output from ChatGPT")
    p.add_argument("--timeout",type=int,default=105)
    p.add_argument("--critic-response-json",type=Path,
                   help="A separate LLM critic JSON response; never an automatic acceptance gate")
    p.add_argument("--critic-provider",choices=["ollama","claude","gemini"])
    p.add_argument("--critic-model")
    args=p.parse_args()
    sources=json.loads(args.sources.read_text(encoding="utf-8"))
    modules=json.loads(args.modules.read_text(encoding="utf-8"))
    payload=make_input(sources,modules)
    prompt=build_prompt(payload)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"prompt.txt").write_text(prompt,encoding="utf-8")
    (args.out/"input.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("PREPARED_LLM_PROMPT",args.out/"prompt.txt",len(prompt),"chars")
    if args.response_json is None and args.provider=="manual":
        print("REVIEW_PENDING: supply an LLM JSON response via --response-json; no invented model completion")
        return
    if args.response_json is not None:
        response=json.loads(args.response_json.read_text(encoding="utf-8"))
        provider_used="external-model-output-provided-by-user"
    else:
        execution=invoke_semantic_llm(prompt,provider=args.provider,model=args.model,
                                      timeout_seconds=args.timeout)
        response=execution["raw"]
        provider_used=execution["provider"]+":"+execution["model"]
    (args.out/"model_response.json").write_text(json.dumps(response,indent=2,ensure_ascii=False)+"\n",
                                                encoding="utf-8")
    report=inspect_answer(payload,response)
    report["provider"]=provider_used
    (args.out/"review_result.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",
                                                 encoding="utf-8")
    critique_prompt=build_second_pass_prompt(payload,report)
    (args.out/"critic_prompt.txt").write_text(critique_prompt,encoding="utf-8")
    if args.critic_response_json is not None or args.critic_provider:
        if args.critic_response_json:
            second=json.loads(args.critic_response_json.read_text(encoding="utf-8"))
        else:
            second=invoke_semantic_llm(critique_prompt,provider=args.critic_provider,
                     model=args.critic_model,timeout_seconds=args.timeout)["raw"]
        critical=inspect_second_pass(payload,report,second)
        (args.out/"second_opinion.json").write_text(json.dumps(critical,indent=2,ensure_ascii=False)+"\n")
        print("INDEPENDENT_ENTAILMENT_CRITIQUE",len(critical["propositions"]),
              "propositions",len(critical["bridges"]),"bridges; authority NONE")
    packet=llm_review_packet(payload,report)
    (args.out/"candidate_packet.json").write_text(json.dumps(packet,indent=2,ensure_ascii=False)+"\n",
                                                   encoding="utf-8")
    print("LLM_PROPOSITIONS",len(report["propositions"]),"CANDIDATE_BRIDGES",len(report["bridges"]),
          "REJECTED",len(report["rejected"]),"UNRESOLVED",len(report["open_questions"]))
    print("CANDIDATE_GRAPH",len(packet["nodes"]),"nodes",len(packet["edges"]),"edges")
    print("AUTHORITY","NONE_ACCEPTED")
    print("ARTIFACT",args.out/"candidate_packet.json")


if __name__=="__main__":
    main()
