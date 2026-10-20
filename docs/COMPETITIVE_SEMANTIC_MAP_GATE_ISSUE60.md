# Issue #60 Competitive Semantic-Map Gate — Cross-Family Evaluation & KEEP / NARROW / ABSORB Receipt

- **Issue:** `Spectating101/cite-refinery#60`
- **Casebook SHA-256:** `66d1f112d6578d8abe9dbd440b6036ffd5e03aa218d22b089b78c0a716fb0ed0` (10 frozen cross-domain & adversarial cases)
- **Proposer Family:** `gpt` (`gpt-6.1-sol`)
- **Independent Judge Families:** `claude, gemini` (`cross_family_enforced=True`)

## 1. Arm A (Cite-Refinery 3-Layer + Cross-Family Gate) vs. Arm B (Naive Quote-Matched Baseline)

| Metric | Arm A: Cite-Refinery 3-Layer + Cross-Family Gate | Arm B: Naive Verbatim-Quote Baseline |
|---|---|---|
| Exact label match (`entailed` / `overreach` / `contradicted` / `unresolved`) | **10/10 (100%)** | 3/10 (30%) |
| Accurate bounded support (`CG09`, `CG10`) | **2/2** | 2/2 |
| Wrong direction / overclaim caught (`CG01`–`CG06`, `CG08`) | **7/7** | 0/7 |
| Missing Practical data abstention (`CG07`) | **1/1** | 1/1 |
| Adversarial trap catch rate (`CG01`–`CG08`) | **8/8** | 1/8 |
| Unsafe false entailments (overclaim accepted as supported) | **0** | 7 |

## 2. Per-Model Cross-Family Critic Performance

| Judge Model | Family | Exact Match | False Entailments | Adversarial Catch | Latency (ms) |
|---|---|---|---|---|---|
| `claude-opus-5-5` | `claude` | 10/10 | 0 | 8/8 | 19471 |
| `claude-sonnet-5-5` | `claude` | 10/10 | 0 | 8/8 | 11650 |
| `gemini-3.8-flash-medium` | `gemini` | 10/10 | 0 | 8/8 | 17773 |
| `gemini-4-argon-medium` | `gemini` | 10/10 | 0 | 8/8 | 17826 |

## 3. Per-Case Adversarial & Cross-Domain Breakdown

| Case | Domain | Adversarial Trap / Category | Gold | Arm A (Cite-Refinery) | Arm B (Quote Baseline) |
|---|---|---|---|---|---|
| `CG01` | `context_transfer` | `stale_or_mismatched_context` | **overreach** | **overreach** | entailed |
| `CG02` | `statistical_scope` | `contradicted_statistical_significance` | **contradicted** | **contradicted** | entailed |
| `CG03` | `inverse_quote_adversarial` | `literally_correct_quote_for_inverse_claim` | **contradicted** | **contradicted** | entailed |
| `CG04` | `same_publisher_fake_independence` | `same_publisher_fake_independence` | **overreach** | **overreach** | entailed |
| `CG05` | `unsupported_quantitative_leap` | `unsupported_quantitative_leap` | **overreach** | **overreach** | entailed |
| `CG06` | `noncausal_association` | `noncausal_association_to_clinical_outcome` | **overreach** | **overreach** | entailed |
| `CG07` | `missing_practical_data` | `missing_practical_data` | **unresolved** | **unresolved** | unresolved |
| `CG08` | `stale_mismatched_source_context` | `stale_or_mismatched_context` | **overreach** | **overreach** | entailed |
| `CG09` | `accurate_bounded_support` | `none_bounded_support` | **entailed** | **entailed** | entailed |
| `CG10` | `accurate_executable_defect_detection` | `none_bounded_support` | **entailed** | **entailed** | entailed |

## 4. Product Judgment: `KEEP_CORE_NARROW_CRITICS_ABSORB_OVERLAY_CLIS`

### KEEP (Verified Structural & Executable Value)
- Native three-layer SemanticGraph (Practical / Academic / Program) with digest-bound graph-review and existing-edge status-transition guards (#78)
- Deterministic source-identity, publisher, and git-commit deduplication (blocks fake multi-study independence such as CG04)
- Isolated SubprocessProbeRunner recording real rrun/rexp execution provenance and blocking capability promotion on failed/blocked requirements (#80)

### NARROW (Constrain Scope & Enforce Cross-Family Non-Promotion)
- LLM semantic entailment and cross-source mechanism critics (#79): must run cross-family (proposer family != judge family) as read-only review queues, never autonomous status promoters
- Open-corpus synthesis: restrict to source-bounded discrepancy and missing-measurement briefs rather than global absence claims (#71)

### ABSORB (Consolidate Sprawl into Core CLI)
- Consolidate standalone overlay/diagnostic CLI scripts into unified cite-refinery subcommands (three-layer-ingest, component-probe, competitive-gate)

## 5. Epistemic & Safety Boundaries
- Sealed 66-source holdout was **not** accessed (`sealed_holdout_touched=False`).
- No candidate edge was automatically promoted to `qualified` (`automatic_status_promotion_allowed=False`).
