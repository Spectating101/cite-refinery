# Phase 3 — Use the EXISTING authenticated reasoning backend, not small Qwen models

The 0.5B and 1.5B Qwen runs were useful as negative engineering controls. They are **not** the Atlas reasoning benchmark or the intended release architecture. In the actual 32-task run, the 0.5B model passed 0/32 strict answer contracts and incorrectly approved 23/24 independent-proof questions. The task set was also non-discriminating (its expected outputs can be predicted from task kind), so these numbers do not prove a stronger model or Atlas product wins.

## Existing model access — don't rebuild

Cite–Refinery already has `src/cite_refinery/external_llm_runtime.py`, which executes isolated, tool-restricted, opt-in local provider calls and rejects unavailable sessions rather than silently switching to a weak model. On Oct 21 the Optiplex successfully ran these exact Antigravity catalog IDs on a separate executed accounting reference:

- `gemini-4-argon-medium`
- `claude-opus-5-5-medium`
- `claude-sonnet-5-5-medium`

That was observed capability *at that time*, not a claim that the credentials/quota work this minute. The same module also supports Copilot, Claude, Codex and Gemini CLIs; those providers require their own current authentication and allowed models. No API-key or Copilot quota entitlement is inferred.

## New portfolio adapter

`python -m cite_refinery.portfolio_strong_reasoner` uses the preexisting `invoke_semantic_llm` rather than spinning up Ollama or a new provider stack.

- Uses the actual source-verified eight-public-project Atlas receipt, with exact pinned commit identities. The model sees only a project's scoped graph evidence for each dossier.
- Generates portfolio dossiers using the existing Phase 3 prompts and strict `validate_dossier` evidence-ID and exact-quotation checks.
- Optionally proposes cross-project opportunities only when the full eight-project evaluation has no dossier failures; these remain **candidates**, not proven integrations.
- Writes per-project checkpoint receipts; quota/auth errors do not erase accepted earlier results. They are **not** silently repaired with Qwen or another account.
- Marks empty/generic dossiers non-substantive, even if they happen to satisfy JSON and citation-format checks.
- Rejects receipts indicating private repositories. The public mode must never be used as a backdoor for source-private evaluation.

**Authenticated Optiplex execution:**

```bash
cd /path/to/cite-refinery
git fetch origin feature/portfolio-autonomous-dossier-v3
# Use your normal isolated worktree / branch checkout procedure.
python -m cite_refinery.portfolio_public_dogfood \
  --manifest research_materials/portfolio_dogfood/public_source_manifest_2026_10_23.json \
  --out /tmp/public-portfolio-atlas-source.json

# Verify the provider works on two projects before spending more model quota.
python -m cite_refinery.portfolio_strong_reasoner \
  --atlas-receipt /tmp/public-portfolio-atlas-source.json \
  --out /tmp/portfolio-argon-pilot.json \
  --provider antigravity --model gemini-4-argon-medium \
  --limit 2

# After reviewing the first output, independently analyze all eight.
python -m cite_refinery.portfolio_strong_reasoner \
  --atlas-receipt /tmp/public-portfolio-atlas-source.json \
  --out /tmp/portfolio-argon-full.json \
  --provider antigravity --model gemini-4-argon-medium \
  --cross-project

# Independent critique / second model (separate output and context):
python -m cite_refinery.portfolio_strong_reasoner \
  --atlas-receipt /tmp/public-portfolio-atlas-source.json \
  --out /tmp/portfolio-opus-review.json \
  --provider antigravity --model claude-opus-5-5-medium \
  --cross-project
```

These are reproduction commands, **not a claim that the above runs have already executed**. Do not commit model transcripts or private source material.

## Acceptance criteria

Before promoting Atlas as a genuine automated portfolio assessor:

1. At least two strong model families produce independently generated, source-anchored claims; record real model IDs, requests, failure and output checks.
2. Independent graders verify source *entailment*, not merely that a cited quotation exists.
3. Add blind mixed supported / contradicted / insufficient claim cases with nontrivial labels and independently adjudicated evidence.
4. Evaluate genuinely useful weaknesses, substitutable tooling, cross-project integration and expected human effort against plain GitHub + a capable general AI researcher.
5. Do not use README/CI as proof of hardware measurement, institutional adoption, scientific correctness or profitable revenue.

Repository-wide test suite and PR stacking must be independently green before merging. Optiplex access was unavailable from the current chat due to Desktop Commander quota; do not fabricate live runs.
