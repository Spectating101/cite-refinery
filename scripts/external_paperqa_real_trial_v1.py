"""Actual PaperQA2 offline-source test for Cite-Refinery on a peer-reviewed review.

Source: Europe PMC full-text XML for DOI 10.1371/journal.pone.0144830,
pre-extracted to a local text file in a disposable directory. Uses LiteLLM
Ollama, no external LLM API; neutral research staging only. The workflow
first verifies Docs.aadd then attempts source-grounded Docs.aquery.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import time
from pathlib import Path


async def run(path: Path, out: Path, *, index_only: bool, query_timeout: int, model: str):
    os.environ["PQA_HOME"]="/tmp/cite-refinery-paperqa-sandbox-home"
    os.environ["OLLAMA_API_BASE"]="http://127.0.0.1:11434"
    from paperqa import Docs, Settings
    from paperqa.settings import AgentSettings, AnswerSettings, ParsingSettings
    from importlib.metadata import version

    settings=Settings(
        llm="ollama/" + model,
        summary_llm="ollama/" + model,
        embedding="sparse",
        agent=AgentSettings(agent_llm="ollama/" + model,
                            search_count=2, max_timesteps=2),
        parsing=ParsingSettings(use_doc_details=False, multimodal=False),
        answer=AnswerSettings(
            evidence_k=3,
            evidence_skip_summary=True,
            max_concurrent_requests=1,
            answer_max_sources=2,
        ),
    )
    assert path.is_file() and path.stat().st_size < 2_000_000
    docs=Docs()
    start=time.monotonic()
    output={
        "engine":"PaperQA2",
        "version":version("paper-qa"),
        "source_doi":"10.1371/journal.pone.0144830",
        "source_pmcid":"PMC4684217",
        "source_url":"https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4684217/fullTextXML",
        "source_text_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "llm":"local Ollama " + model,
        "embedding":"PaperQA2 sparse",
        "metadata_policy":"use_doc_details=False; no external Semantic Scholar/Crossref requests",
        "state":"starting",
        "limits":"Standalone local document test; no acceptance or verified citations.",
    }
    def save():
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n")
    save()
    try:
        document_id=await asyncio.wait_for(
            docs.aadd(str(path),
                citation="Belo et al. (2015), Population Estimation Methods for Free-Ranging Dogs: A Systematic Review",
                title="Population Estimation Methods for Free-Ranging Dogs: A Systematic Review",
                doi="10.1371/journal.pone.0144830",settings=settings),timeout=100)
        output.update({"state":"index_complete","document_id":str(document_id),
                       "index_elapsed_seconds":round(time.monotonic()-start,2)})
        print("PAPERQA_INDEX_COMPLETE",output["index_elapsed_seconds"],flush=True)
        save()
        if not index_only:
            query=("Which free-ranging dog abundance estimation methods does the review "
                   "discuss, and what detection or sampling limitations should be addressed? "
                   "Do not infer evidence of intervention effectiveness.")
            start_query=time.monotonic()
            resp=await asyncio.wait_for(docs.aquery(query,settings=settings),timeout=query_timeout)
            output.update({
                "state":"query_complete",
                "question":query,
                "answer":str(getattr(resp,"answer", "") or "")[:18000],
                "formatted_answer":str(getattr(resp,"formatted_answer","") or "")[:18000],
                "context":str(getattr(resp,"context","") or "")[:18000],
                "query_elapsed_seconds":round(time.monotonic()-start_query,2),
                "status":"model_draft_with_unverified_citation_spans",
            })
            print("PAPERQA_QUERY_COMPLETE",output["query_elapsed_seconds"],
                  output["answer"][:300].replace("\n"," "),flush=True)
            save()
    except Exception as exc:
        output.update({"state":"failed","error_type":type(exc).__name__,
                       "error":str(exc)[:1000],
                       "total_elapsed_seconds":round(time.monotonic()-start,2)})
        print("PAPERQA_FAILED",repr(exc),flush=True)
        save()
    return output


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("input",type=Path)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--index-only",action="store_true")
    p.add_argument("--timeout",type=int,default=125)
    p.add_argument("--model",default="llama3.2:3b")
    args=p.parse_args()
    asyncio.run(run(args.input,args.out,index_only=args.index_only,query_timeout=args.timeout,model=args.model))
