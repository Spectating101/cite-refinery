"""Opt-in model execution for semantic reasoning; no model output can mutate a graph.

Cloud CLIs run without model-accessible tools and without session
persistence, *only* when the user's machine has valid authentication.
GitHub Copilot CLI can use explicit per-account launchers. No silent account
cycling or fallback between providers is permitted. Local Ollama is loopback-only and
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


def _copilot_json_from_stdout(stdout):
    """Accept a last JSON object after Copilot informational banners.

    Some account wrappers prefix informational lines. The last valid JSON
    object must occupy the entire remaining stdout (apart from whitespace).
    Unrecognized output is rejected, not treated as a successfully completed
    analysis. Do not parse arbitrary tool-execution transcripts.
    """
    if not isinstance(stdout,str) or len(stdout)>250000:
        raise LLMUnavailable("Copilot reply absent or oversized")
    cleaned=stdout.strip()
    if cleaned.startswith("```"):
        return _parse_response(cleaned)
    decoder=json.JSONDecoder()
    for position in range(len(cleaned)):
        if cleaned[position]!="{" or (position and cleaned[position-1] not in "\n\r \t"):
            continue
        try:
            result,end=decoder.raw_decode(cleaned,position)
        except (ValueError,TypeError):
            continue
        if isinstance(result,dict) and not cleaned[end:].strip():
            return result
    raise LLMUnavailable("Copilot did not return one valid JSON research object")


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
    if provider not in {"claude","gemini","codex","copilot","antigravity"}:
        raise ValueError("provider must be ollama, claude, gemini, codex, copilot or antigravity")
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
        elif provider=="copilot":
            # GitHub Copilot CLI requires --allow-all-tools to run in
            # non-interactive mode, so restrict its *available* tool list to
            # empty. It cannot edit, search, execute commands or use MCP.
            # Select accounts explicitly using CITE_REFINERY_COPILOT_BIN;
            # do not rotate through wrappers on quota/auth errors.
            copilot=os.environ.get("CITE_REFINERY_COPILOT_BIN") or shutil.which("copilot")
            if not copilot:
                raise LLMUnavailable("GitHub Copilot CLI not found; set CITE_REFINERY_COPILOT_BIN")
            cmd=[copilot,"--disable-builtin-mcps","--allow-all-tools",
                 "--available-tools","","--disable-client-telemetry",
                 "--stream","off","--output-format","text","--silent"]
            cmd.extend(["--model",model or "auto"])
            cmd.extend(["-p","Do not use tools. Return ONLY one JSON object. "+prompt])
        elif provider=="antigravity":
            # Agy has its own authenticated model catalog. Avoid Gemini
            # Code Assist CLI, which rejects this consumer-authenticated host.
            agy=os.environ.get("CITE_REFINERY_ANTIGRAVITY_BIN") or shutil.which("agy")
            if not agy:
                raise LLMUnavailable("Antigravity CLI not found; set CITE_REFINERY_ANTIGRAVITY_BIN")
            selected=model or "gemini-3.8-flash-medium"
            if selected not in {"gemini-3.8-flash-low","gemini-3.8-flash-medium","gemini-3.8-flash-high"}:
                raise ValueError("Select a verified Gemini 3.8 Flash tier")
            cmd=[agy,"--mode","plan","--sandbox","--disable-slash-commands",
                 "--model",selected,"--output-format","json",
                 "--print-timeout",f"{max(10,timeout_seconds-5)}s",
                 "--print","Do not use tools. Return one JSON object only. "+prompt]
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
        # Wrappers may swallow the Copilot subprocess exit code, so examine
        # standardized provider failures even if the wrapper exits 0.
        if provider=="copilot":
            stderr=(proc.stderr or "")[:30000].lower()
            if any(term in stderr for term in (
                "exceeded your monthly quota", "hit your usage limit",
                "quota exceeded", "usage limit exceeded", "rate limit exceeded",
            )):
                raise LLMUnavailable("GitHub Copilot quota/usage limit reached for selected account")
        if proc.returncode!=0:
            # Never surface stderr, credentials, user metadata or session logs.
            raise LLMUnavailable(f"{provider} CLI exited {proc.returncode}; check authentication and quota locally")
        try:
            if provider=="antigravity":
                envelope=json.loads(proc.stdout)
                if not isinstance(envelope,dict) or envelope.get("status")!="SUCCESS":
                    raise ValueError("Antigravity did not complete successfully")
                raw=_parse_response(envelope)
            elif provider=="copilot":
                raw=_copilot_json_from_stdout(proc.stdout)
            elif provider=="codex":
                candidate=Path(result_file)
                if not candidate.is_file() or candidate.stat().st_size>250000:
                    raise ValueError("Missing or oversized Codex response")
                raw=_parse_response(candidate.read_text(encoding="utf-8"))
            else:
                raw=_parse_response(json.loads(proc.stdout))
        except (ValueError,TypeError) as exc:
            raise LLMUnavailable(f"{provider} returned invalid structured JSON") from exc
        return {"provider":provider,"model":model or ("auto" if provider=="copilot" else "gemini-3.8-flash-medium" if provider=="antigravity" else "cli-default"),"raw":raw}
