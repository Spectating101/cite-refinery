# Phase 3: model-authored portfolio dossiers — implementation, not yet a validated result

The new `portfolio_autonomous_dossier.py` consumes **the actual Phase 1 Atlas JSON receipt** (including original graph `packet`) and invokes a configured OpenAI-compatible text-generation endpoint for each public project. There are NO prewritten portfolio conclusions in its prompts. A model-generated dossier covers capabilities, limitations, integration hypotheses, competitor substitution hypotheses, a provisional build/hold/retire/investigate decision and questions for verification.

## Run

First produce the actual source-verified Atlas receipt with `python -m cite_refinery.portfolio_public_dogfood --manifest research_materials/portfolio_dogfood/public_source_manifest_2026_10_23.json --out /tmp/public-atlas.json --semantic`.

Then, with a specifically authorized provider and key:

```bash
export PORTFOLIO_MODEL_API_KEY='...'
python -m cite_refinery.portfolio_autonomous_dossier \
  --atlas-receipt /tmp/public-atlas.json \
  --output /tmp/public-dossiers.json \
  --model YOUR_MODEL_ID \
  --endpoint https://YOUR_TRUSTED_PROVIDER/v1/chat/completions \
  --allow-remote-inference
```

**Privacy:** only use a public-only receipt. This is opt-in remote transmission, not appropriate for private repository evaluations or unapproved model providers. API keys never go into the repository.

**Validation boundaries:** model claims must cite node IDs from that project's evidence scope. Self-reported/contradicted verdicts require an exact source quote. The deterministic validator verifies quote membership, **not entailment or independent truth**; commercial outcomes, physical tests and scientific accuracy cannot be certified by README or CI metadata. A reviewer must inspect source claims and fill independently blinded tasks under Phase 2 before asserting useful autonomous analysis. No hidden ground-truth outcomes or prior analyst grades are supplied to the model.

**Remaining:** Run inference on all eight real source snapshots, repair any schema noncompliance, review claims by humans, run the Phase 2 sealed evaluator, compare to plain GitHub + a capable research model, extend to authorized private local sources. Current repo commits contain source and synthetic unit tests only, NOT a completed model run or independent competitive result.
