# Executed 32-question model failure audit — 2026-10-23

**Observed run:** https://github.com/Spectating101/cite-refinery/actions/runs/39977825494

Eight public, pinned-repository sources were actually processed. The real `Qwen/Qwen2.5-0.5B-Instruct` inference job executed 32 source-scoped prompts and uploaded an artifact with the raw model responses and exact validation failures.

## Inspected output results

- 32/32 prompts executed. 0/32 model responses passed the strict citation/verdict contract.
- All 32 outputs were Markdown-fenced; after independently removing fences *for diagnosis only*, 30/32 parsed as JSON.
- 23/24 prompts asking for independent evidence of physical validation, outside adoption or paying revenue were incorrectly classified `self_reported`. The remaining one correctly abstained.
- None of the parsed answers supplied the expected original Atlas graph evidence ID.
- Source-attribution tasks often returned repository IDs instead of question IDs; they failed identity and evidence checks.

These are **source-packet attribution verdicts**, not real-world proof that a project lacks users, revenue or physical testing.

## Benchmark flaw

The 32-question suite also has a major limitation: eight positive source-attribution questions and 24 negative/insufficient-proof probes. A deterministic non-model baseline can give the expected contract answer based on task type alone. The new `portfolio_atomic_benchmark.py` explicitly scores this baseline side-by-side, marks the suite **non-discriminating**, and prevents false model-superiority claims. It is a diagnostic calibration set, not a quality benchmark.

## Decision

Do not weaken the evidence requirements to claim a successful model run. Do not assess or retire portfolio projects based on these answers. Run a small more-capable-model calibration comparison, then build externally adjudicated mixed-evidence cases with genuinely supported, contradicted and insufficient items before returning to portfolio value judgments.
