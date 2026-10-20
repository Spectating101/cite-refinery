# Argon + Opus 5.5 + Sonnet 5.5: authenticated Optiplex review route

21 October 2026 — draft follow-up to Cite–Refinery PR #80.

## Why

Cite–Refinery's graph has three conceptual layers (Practical, Academic, Implementation), but an earlier mechanism audit was both proposed and criticized through the same Gemini 3.8 Flash model. That is useful debugging but weak epistemic independence. User-provided Optiplex access now exposes two additional model provider families via the already authenticated **Antigravity `agy` catalog**.

Actual catalog discovery, `agy models`, exposed these valid IDs across low/medium/high: `gemini-4-argon`, `claude-opus-5-5`, `claude-sonnet-5-5`, and the existing `gemini-3.8-flash`. We added exact identifiers to the existing allowlist rather than substituting aliases, changing providers, importing credentials or rotating accounts. The existing CLI invocation keeps plan mode, sandbox flag and a strong no-tools instruction in the prompt, with a temporary unrelated working directory. This is **not** an OS-enforced proof that every model capability or network route is disabled; no repository operations were requested and no graph write is permitted through the adapter.

This is not a new user-facing general chat-agent or a claim that Opus and Sonnet are independent model *families*: they are two Claude models versus the Gemini/Argon family.

## Actual authenticated calls

All three selected medium models were contacted on the authorized Optiplex and asked to inspect **the same known, source-pinned synthetic accounting issue** from [lingrany/EverBatt-LFP-Recycling-Analysis](https://github.com/lingrany/EverBatt-LFP-Recycling-Analysis) at commit `246c4d478f9ceb05c580856720ca56a66064e205`.

Supplied code:
- `fee_rev = -battery_fee * throughput * 1000`
- `if fee_rev > 0: revenue += fee_rev`
- `profit = revenue - total_cost`

Supplied actual prior source-execution figures for 10,000 tonnes/year, 2019 assumptions:
- At fee -$2/kg: modeled profit $52,197,581.38 (positive fee income recognized).
- At fee $0/kg: modeled profit $32,197,581.38.
- At fee +$1/kg: modeled profit still $32,197,581.38, even though the documented sign convention means it is a cost.

Independent model requests (neither saw the others' answers):

| Model ID | Real call outcome | Assessment against executed reference |
|---|---|---|
| `gemini-4-argon-medium` | Structured reply succeeded, about 22 seconds | Correctly identified omitted positive fee expenses and −$10m expected delta |
| `claude-opus-5-5-medium` | Structured reply succeeded, about 15 seconds | Same defect and delta; noted dependence on sign convention |
| `claude-sonnet-5-5-medium` | Long structured response **rejected** by strict JSON parser; short independent retry succeeded in about 6 seconds | Correctly identified omission, expected −$10m and observed $0 on retry |

The comparison tool verifies model answers **against the already executed functional check**, not by majority vote. The three successful structured replies agree with the deterministic test. The initial Sonnet format failure is intentionally not omitted or counted as an agreement.

The agreement is reassuring for the model routing and explanation task; **it adds no new scientific proof**. The original execution and accounting invariant establish the bounded source behavior. There are no real recycling-site inputs, safety economics, buyers or investments evaluated.

## How to employ the models next

For a multi-model source/implementation review, use explicitly separate responsibilities and independent contexts:

- **Argon:** propose and challenge cross-domain problem-mechanism links; explain candidate transfer and geography/time boundaries. Make it find *missing* explanations, not just attractive correlations.
- **Opus 5.5:** independently falsify the proposed link; flag causal leaps, unsafe assumptions, counterexamples, license or economic omissions. Do not show the proposer output when independence matters.
- **Sonnet 5.5:** inspect actual repository interfaces/tests and formulate short machine-checkable executable contracts or repair candidates. Start with smaller strict JSON output schemas, since the first long contract failed.
- **Gemini Flash:** still useful for high-volume source extraction and initial triage with lower effort, but it must not adjudicate its own outputs as accepted evidence.

These assignments are **initial roles, not proven comparative benchmarks**. Measure task success, unsupported claims, runtime, budget and schema compliance across a larger development set before optimizing routing.

Always separate `model_proposed`, `source_text_checked`, `independently_executed`, `expert_reviewed` and `buyer_verified`. Three model responses cannot promote any Practical/Academic/Implementation edge, override a failed functional test, or prove economic arbitrage.

## Reproduction and outputs

The opt-in runner is the existing `invoke_semantic_llm(prompt,provider="antigravity",model="...")`, now with exact catalog IDs. There is no silent fallback if a model or quota is unavailable.

- Structured, reference-checked aggregate (not raw transcripts): `research_materials/opportunity_atlas/multimodel_fee_review.json`.
- Readable result: `research_materials/opportunity_atlas/MULTIMODEL_FEE_REVIEW.md`.
- Pure validator and CLI: `cite-refinery-cross-model-review`.
- Individual raw model responses and short test driver remain privately on the authorized host under the separate research scratch directory.

The benchmark uses existing bounded component test results from #80; no private research holdout or original third-party source code was committed and no graph status was promoted. The PR remains draft, stacked on #80, not a production deployment.
