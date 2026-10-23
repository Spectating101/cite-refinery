"""Evaluate the public portfolio with the project's EXISTING authenticated reasoning runtime.

This is an opt-in Optiplex/local execution entrypoint. No model credentials,
private repository bytes, or model transcripts are committed to GitHub.
A successful schema check is not independent proof of claims.
"""
from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from .external_llm_runtime import invoke_semantic_llm, LLMUnavailable
from .portfolio_autonomous_dossier import (
    DossierError, evidence_index, project_evidence, make_prompt, validate_dossier, require
)
from .portfolio_cross_project import cross_project_prompt, validate_opportunities

SCHEMA = "cite_refinery.portfolio_strong_reasoner_v1"
PROVIDERS = ("antigravity", "copilot", "claude", "gemini", "codex")


def run_evaluation(report, *, provider, model, timeout=180, limit=None,
                   cross_project=False, invoke=invoke_semantic_llm, checkpoint=None):
    """Run real inference or a test-injected provider. Reject, never repair, bad outputs."""
    require(report.get("private_repositories_included") == 0,
            "This evaluator accepts only verified PUBLIC Atlas receipts")
    require(provider in PROVIDERS, "A supported authenticated reasoning provider is required")
    require(isinstance(model, str) and bool(model.strip()), "Select an explicit model")
    require(15 <= timeout <= 300, "Timeout outside existing runtime limits")
    index = evidence_index(report)
    snapshots = report.get("source_snapshots", [])
    require(isinstance(snapshots, list) and snapshots, "No source snapshots")
    require(len({r["repo"] for r in snapshots}) == len(snapshots),
            "Duplicate repository identities")
    if limit is not None:
        require(isinstance(limit, int) and 1 <= limit <= len(snapshots),
                "Invalid bounded pilot size")
        snapshots = snapshots[:limit]

    result = {
        "schema": SCHEMA,
        "provider": provider, "model": model,
        "projects_requested": len(snapshots),
        "project_ids": [row["repo"] for row in snapshots],
        "model_invocation_attempts": 0, "schema_valid_count": 0,
        "substantive_candidate_count": 0, "failures": 0,
        "dossiers": [], "project_receipts": [],
        "cross_project": {"status": "not_requested"},
        "completeness": "in_progress",
        "evidence_source": "original_public_atlas_packet",
        "no_independent_claim_entailment_validation": True,
        "no_field_adoption_or_commercial_validation": True,
        "human_review_required": True,
        "model_output_is_not_an_authoritative_portfolio_decision": True,
    }

    def save():
        if checkpoint is not None:
            checkpoint(result)

    for row in snapshots:
        repo = row["repo"]
        scoped = project_evidence(report, repo, index)
        system, user = make_prompt(repo, scoped)
        prompt = system + "\n\nEVIDENCE INPUT (untrusted source data):\n" + user
        result["model_invocation_attempts"] += 1
        receipt = {"repository": repo, "source_commit": row["head_sha"],
                   "prompt_sha256": sha256(prompt.encode()).hexdigest(),
                   "status": "unverified"}
        try:
            answer = invoke(prompt, provider=provider, model=model,
                            timeout_seconds=timeout)["raw"]
            receipt["response_sha256"] = sha256(
                json.dumps(answer, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()
            dossier = validate_dossier(repo, answer, scoped)
            dossier["source_commit"] = row["head_sha"]
            dossier["evidence_digest"] = receipt["prompt_sha256"]
            # Passing the format checks is not a finding. A zero-claim dossier
            # is explicitly marked non-substantive rather than counted as useful.
            number_claims = sum(len(dossier[f]) for f in (
                "capabilities", "limitations", "integration_candidates",
                "competitor_substitutions"
            ))
            substantive = bool(dossier["capabilities"]) and number_claims >= 2
            receipt.update(status="schema_valid", claim_count=number_claims,
                           substantive_candidate=substantive,
                           independent_truth_verified=False)
            result["dossiers"].append(dossier)
            result["schema_valid_count"] += 1
            result["substantive_candidate_count"] += int(substantive)
        except (LLMUnavailable, DossierError, ValueError, TypeError, KeyError) as exc:
            # Do not reveal stderr, credentials or raw source/model transcripts.
            receipt.update(status="rejected", failure_type=type(exc).__name__)
            result["failures"] += 1
        result["project_receipts"].append(receipt)
        save()

    if cross_project and result["failures"] == 0 and len(snapshots) == len(report["source_snapshots"]):
        system, user, scopes = cross_project_prompt(report)
        prompt = system + "\n\nEVIDENCE INPUT (untrusted source data):\n" + user
        try:
            proposals = invoke(prompt, provider=provider, model=model,
                               timeout_seconds=timeout)["raw"]
            candidates = validate_opportunities(proposals, scopes)
            result["cross_project"] = {
                "status": "candidate_only", "candidate_count": len(candidates),
                "candidates": candidates, "all_unverified": True,
            }
        except (LLMUnavailable, DossierError, ValueError, TypeError, KeyError) as exc:
            result["cross_project"] = {
                "status": "rejected", "failure_type": type(exc).__name__
            }
    elif cross_project:
        result["cross_project"] = {
            "status": "not_attempted",
            "reason": "Dossier failures or partial corpus; no ungrounded synthesis"
        }
    result["completeness"] = (
        "completed_with_unverified_outputs" if not result["failures"]
        else "completed_with_rejections"
    )
    save()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atlas-receipt", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--provider", choices=PROVIDERS, default="antigravity")
    parser.add_argument("--model", required=True)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--cross-project", action="store_true")
    args = parser.parse_args(argv)
    require(args.atlas_receipt.is_file(), "Missing actual original Atlas receipt")
    require(not args.out.exists(), "Refuse to overwrite a previous evaluation")
    report = json.loads(args.atlas_receipt.read_text(encoding="utf-8"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    def checkpoint(value):
        tmp = args.out.with_name(args.out.name + ".partial")
        tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        tmp.replace(args.out)
    result = run_evaluation(report, provider=args.provider, model=args.model,
                            timeout=args.timeout, limit=args.limit,
                            cross_project=args.cross_project,
                            checkpoint=checkpoint)
    print("STRONG_REASONER_PORTFOLIO", json.dumps({
        "attempted":result["model_invocation_attempts"],
        "schema_valid":result["schema_valid_count"],
        "substantive_candidates":result["substantive_candidate_count"],
        "rejected":result["failures"],
        "cross_project":result["cross_project"]["status"],
        "independently_verified":False,
    },sort_keys=True))
    return 0 if result["failures"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
