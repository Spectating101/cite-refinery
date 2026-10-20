"""Opt-in model execution for semantic reasoning; no model output can mutate a graph.

Cloud CLIs run with no tools and no session persistence, *only* when the
user's machine has valid authentication. Local Ollama is loopback-only and
has a hard request timeout. Never silently falls back to a weaker model.
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib import request,error


class LLMUnavailable(RuntimeError):
    pass


def _parse_response(payload):
    if isinstance(payload, dict) and all(k in payload for k in ("propositions","bridges","open_questions")):
        return payload
    if isinstance(payload, dict):
        result = payload.get("structured_output") or payload.get("result") or payload.get("response")
        if result is None:
            raise LLMUnavailable("Model wrapper lacks a result/structured_output")
        if isinstance(result, dict):
            return _parse_response(result)
        payload = result
    if not isinstance(payload, str) or len(payload)>250000:
        raise LLMUnavailable("Model did not return a bounded JSON string")
    cleaned=payload.strip()
    if cleaned.startswith("```"):
        cleaned=cleaned.split("\n",1)[1].rsplit("```",1)[0]
    try:
        result=json.loads(cleaned)
    except (ValueError,TypeError) as exc:
        raise LLMUnavailable("Model returned non-JSON output") from exc
    if not isinstance(result,dict):
        raise LLMUnavailable("Expected one structured research object")
    return result


def invoke_semantic_llm(prompt, *, provider, model=None, timeout_seconds=105):
    if not isinstance(prompt,str) or not 100<=len(prompt)<=180000:
        raise ValueError("Prompt size outside allowed range")
    if not 15<=timeout_seconds<=300:
        raise ValueError("Timeout must be 15..300 seconds")
    if provider=="ollama":
        # No remote endpoints or API keys; use existing local model only.
        target_model=model or "qwen2.5:1.5b-instruct"
        payload={"model":target_model,"prompt":prompt,"format":"json","stream":False,
                 "options":{"temperature":0,"num_ctx":8192,"num_predict":1300}}
        req=request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type":"application/json"},method="POST",
        )
        try:
            with request.urlopen(req,timeout=timeout_seconds) as resp:
                if resp.status!=200:
                    raise LLMUnavailable(f"Local model server returned HTTP {resp.status}")
                body=json.loads(resp.read(300000).decode("utf-8"))
            raw=_parse_response(body)
        except (error.URLError,TimeoutError,OSError,ValueError) as exc:
            raise LLMUnavailable(f"Ollama inference unavailable: {type(exc).__name__}") from exc
        return {"provider":"ollama","model":target_model,"raw":raw}
    if provider not in {"claude","gemini","codex"}:
        raise ValueError("provider must be ollama, claude, gemini or codex")
    with tempfile.TemporaryDirectory(prefix="cite-refinery-readonly-llm-") as directory:
        if provider=="codex":
            codex=os.environ.get("CITE_REFINERY_CODEX_BIN") or shutil.which("codex")
            if not codex:
                raise LLMUnavailable("Codex binary not found; set CITE_REFINERY_CODEX_BIN")
            result_file=str(Path(directory)/"codex_response.json")
            cmd=[codex,"exec","--skip-git-repo-check","--sandbox","read-only",
                 "--ephemeral","-c",'model_reasoning_effort="low"',
                 "--output-last-message",result_file]
            if model:cmd.extend(["--model",model])
            cmd.append("Do not use any tools. Return only one JSON object. " + prompt)
        elif provider=="claude":
            cmd=["claude","--print","--tools","","--no-session-persistence",
                 "--output-format","json"]
            if model:cmd+=["--model",model]
            cmd.append(prompt)
        else:
            cmd=["gemini","--approval-mode","plan","--output-format","json"]
            if model:cmd+=["--model",model]
            cmd+=["-p",prompt]
        try:
            proc=subprocess.run(cmd,cwd=directory,input="",capture_output=True,
                                text=True,timeout=timeout_seconds,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise LLMUnavailable(f"{provider} CLI unavailable: {type(exc).__name__}") from exc
        if proc.returncode!=0:
            # Avoid emitting CLI stderr that might contain local account metadata.
            raise LLMUnavailable(f"{provider} CLI exited {proc.returncode}; check authentication and permissions locally")
        try:
            if provider=="codex":
                candidate=Path(result_file)
                if not candidate.is_file() or candidate.stat().st_size>250000:
                    raise ValueError("Missing or oversized Codex response")
                raw=_parse_response(candidate.read_text(encoding="utf-8"))
            else:
                raw=_parse_response(json.loads(proc.stdout))
        except (ValueError,TypeError) as exc:
            raise LLMUnavailable(f"{provider} returned invalid structured JSON") from exc
        return {"provider":provider,"model":model or "cli-default","raw":raw}
