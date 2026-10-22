# Academic source-grounded semantic vertical slice v1

**Status:** prototype on stacked PR; no live authenticated model run is claimed by CI. This feature is not a scientific validation or a deployed research assistant.

## Purpose

The existing Cite–Refinery offline three-map browser has literal/metadata retrieval; it failed all ten hand-written paraphrase smoke tests despite finding all ten literal identifiers. Older, separate LLM entailment experiments had 23/24 agreement with investigator-authored development labels but were not connected to the new 103-source Academic inventory. This implementation creates a **real inference pathway that can be invoked with an authorized provider**, rather than relabeling lexical matches as semantics.

One Academic domain is the deliberate scope for the first vertical slice. Practical and Implementation retain their independent metadata maps; the first pipeline makes no autonomous cross-layer claims or graph writes.

## Authenticated execution pathway

1. Read the **original sealed 103-development-source Academic map** `academic_original_source_enriched_atlas.json`; refuse any map that reveals the 66 heldout documents, changes scientific authority, or changes 103 source identities.
2. Read only original `SOURCE_ID.txt` extracts intentionally placed in a private local directory. Require each full text to match the source's frozen `text_sha256` exactly. Unknown source IDs, private heldout names, symlinks, oversized or tampered texts fail. **No original text is committed or exposed in the public offline bundle.**
3. Ask an explicitly selected, already authenticated model to choose up to three source identities by **semantic relevance of question, title and documented scope**, not lexical matching. The current model sees only metadata for the subset whose original text is locally verified, so no guarantee of corpus-wide completeness.
4. Split the selected original texts into bounded, overlapping passages and ask the model to select at most eight relevant passage IDs from source previews.
5. Ask the model for a scope-aware candidate answer with zero to twelve individually stated claims. Every retained citation must point to a **selected original passage** and contain a **verbatim contiguous** 15–500 character quote found within the full SHA-checked original text. Record the precise character offsets, original file hash and quote hash; reject invented sources, misbound passage IDs and fabricated quotes.
6. When a **different semantic model family** is explicitly configured as critic, ask it to check causal overreach, negation, study setting, geography and whether the claims follow. Any unresolved, contradicted or overreaching critical result **abstains**, leaving a review receipt. Even a `grounded` second-model verdict remains an opinion requiring review.
7. Write an inspectable JSON record; **never** accept scientific status, assert commercial or technical effectiveness, write a graph edge or mark a source independently replicated.

### CLI

```bash
cite-refinery-semantic-answer \
  --academic-atlas /path/to/academic_original_source_enriched_atlas.json \
  --original-text-dir /secure/private/academic-original-extracts \
  --question "Does installing a CO2 monitor reduce asthma in classrooms?" \
  --provider antigravity --model gemini-3.8-flash-medium \
  --critic-provider copilot --critic-model <an_explicit_different_family_model> \
  --output /tmp/review-only-academic-semantic-answer.json
```

The CLI uses the existing `external_llm_runtime.invoke_semantic_llm` connector contract; a configured model binary **and valid session** are required. On unavailable inference, it fails closed to an abstention. This code is **not** permission to cycle between accounts or providers when a quota or authentication failure occurs. A separate critic is optional; without one, the primary model's answer remains a candidate, never independently accepted.

For an externally supplied handoff, use `--responses /path/to/rank_passages_answer.json` instead of `--provider`. The JSON must contain exactly three keys `rank_sources`, `select_passages`, `interpret_answer` with the schemas stated in code. This returns `operator_supplied_model_responses_unverified`, **not** `authenticated_live_model`. Such a trace is a harness/interop test, not evidence that the live model understood the question.

**Important:** `--original-text-dir` expects exact full original extracted text corresponding to the 103-index manifest's digest. Replacing it with snippets, fabricated abstracts, or files reconstructed independently will not pass the SHA check. The files are not published in GitHub; the authorized machine that collected them or another legitimately sourced extraction must supply them. No real production data is fetched by this module.

## Actual tests and honest limits

The unit tests assemble an authentic 103-source index shape from the frozen public development manifest and then replace two example text fingerprints **in test memory only**, clearly marking the associated passages as *synthetic*. A simulated model responds to stage prompts. The tests demonstrate the orchestration and authenticity gate: paraphrased question can select its source when the model selects it, exact quote offsets are verified, unknown source/holdout, wrong SHA and invented quotation are rejected, overreaching interpretations are blocked by critic, no evidence abstains, and unavailable authenticated model abstains.

**These tests cannot measure real model semantic retrieval accuracy, or validate real academic claims.** They are a contract test of the pipeline plumbing. An actual authenticated runtime and frozen original material are required for end-to-end capability evidence, and a blinded independent benchmark is required to estimate performance.

## Remaining gates

- Run the explicitly authenticated semantic provider on original text for a selected legal/public development subset; record provider/model version, answer receipt, latency and failure/abstention.
- Introduce independent source-level questions with paraphrases, negations, false premises and transfer claims; score retrieval, answer evidence alignment, abstention and false entailment separately.
- The first **optional Academic browser handoff is implemented**: `cite_refinery.standalone_workspace --academic-semantic-receipt /path/to/review-only-academic-semantic-answer.json` attaches the candidate as a **separate, conspicuously unapproved** Academic source-review dossier. Its source URLs, original text SHA-256, quote SHA-256, offsets and authority denials are checked against the actual Academic development map. The default public offline bundle attaches **zero** such receipts and preserves the base 1,497 index count; when one is supplied the Academic source count increases by one as an explicitly unapproved *review packet*, not an independent publication.
- Run a real operator review of source text and meaning before accepting a semantic conclusion. The existence of a UI card is not evidence that its model claim is true; imported simulated/manual replies are explicitly labeled unauthenticated.
- Validate real passage extraction for representative reports and full-text JATS articles; never treat DOI/title matches as source-text entailment.
- Expand the same evidence contract to Practical and Implementation independently, before any cross-layer meaning inference.

## Security/epistemic caveats

Model prompts include untrusted source text, which remains *data*, not executable instructions. Local model binaries are launched only under their respective existing, explicitly opt-in provider contracts. The answer is a non-authoritative research proposal. A real quotation can be **semantically irrelevant, misleading or misread**; exact-span verification does not establish entailment or scientific truth. The result includes that limitation explicitly and never promotes a Commons graph status.
