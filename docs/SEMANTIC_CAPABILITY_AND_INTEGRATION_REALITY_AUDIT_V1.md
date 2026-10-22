# Semantic Capability & Integration Reality Audit

**22 October 2026 — reproducible development diagnostic, not blind scientific evaluation.**

## Verdict

**Semantic inference exists in Cite–Refinery's legacy experimental workflows, but is NOT currently wired into the new three-map research browser.** The browser is a sound **source-metadata navigation and scoped engineering-test inspection interface**, not an evidence-grounded semantic question-answering system. Passing the repository's 596 unit tests proves contract functionality, not interpretation or field usefulness.

## Actual paired-question experiment on the generated product

Audit uses the **1,497-record** offline pilot produced by the source-bounded `standalone_workspace`, reproduces its actual JavaScript search fields and match rule, and applies ten investigator-selected paired tasks across all three original source layers. For each task, the direct phrase and a semantically similar but lexically different query have the *same preselected original source ID* as their relevance target.

| Layer | Literal query | Meaning-preserving natural question | Target recall |
|---|---|---|---|
| Practical | `surplus food` | routing unsold meals to hungry households | direct yes / paraphrase no |
| Practical | `Anuradhapura` | stray animals immunized and sterilized over several years | yes / no |
| Practical | `Ban Kao Many` | villagers receive advance alerts before river inundation | yes / no |
| Academic | `lithium-ion battery` | whether processing discarded electric car packs pays off | yes / no |
| Academic | `concentration` | pupils lose focus when classroom atmosphere is stale | yes / no |
| Academic | `coastal cities` | stormwater threats to Indian seafront municipalities | yes / no |
| Academic | `heatwaves` | do extreme temperature alerts prevent deaths | yes / no |
| Implementation | `EDAgent` | identify phantom wiring layer in comments on chip layout files | yes / no |
| Implementation | `blisspixel` | classify patterns in host naming for externally visible systems | yes / no |
| Implementation | `WeixuanZ` | protect sensor monitoring from invalid river gauge readings | yes / no |

**Observed literal target retrieval: 10/10. Paraphrased target retrieval: 0/10.** These are not independent human-gold semantic benchmark scores: the target alignment was manually constructed after observing the present source index. Several natural questions could be relevant to additional sources, and the benchmark does not score precision/recall across all 1,497 cards, multi-source synthesis, claim entailment or model reasoning. The purpose is to prove the **current literal search cannot bridge common paraphrases**.

A **source retrieval hit does not establish entailment or answer correctness**. For example, the Coimbra classroom paper reports an observational association for concentration. Neither that source nor the browser proves that installing monitors reduces asthma. Likewise, an EDA checker that fails a synthetic commented-layer fixture is not a general field-chip engineering validation.

## Real model-specific evidence already present (separate path)

- A historical Gemini 3.8 Flash Medium source-level diagnostic recorded **23/24 agreement** with investigator-authored entailment/overreach/contradiction labels, **zero false entailed classifications** relative to those labels in that constructed 24-item development sample.
- The separately recorded eight-source-family mechanism audit contained **seven partial-support and one bounded-support** model judgments. These were opinions about different study/source combinations, not independent human validation, actual intervention effectiveness, or whole-implementation testing.
- Cite–Refinery includes `external_llm_reasoner` (source-to-atomic-propositions), `semantic_entailment_diagnostic` (bounded source-level entailment), `cross_source_mechanism_critic` (source-scope cross-claim review), `external_llm_runtime` (explicit opt-in CLI/Ollama backends), candidate graph packet bridges and a native review-only graph route.
- All eight archived source IDs can be matched to the browser's **older 47-abstract subindex**, with their original source URLs agreeing. None joins by that original source ID to the **new 103-source Academic development inventory**, and **zero archived model verdicts are attached to the UI**. This is promising evidence that a small, provenance-safe legacy semantic *adapter* could be built, not proof that one currently operates.
- However, the current offline `standalone_workspace` and `standalone_atlas_template.html` do **not call any model**, do not open original full-text to adjudicate questions, do not import archived judgments into the new 103-source Academic map, and deliberately perform **zero** cross-layer inference.
- No live authenticated model run is performed by this audit. Historical output is checked against its own counts, but not independently replayed against original source-body text here. **23/24 is not the new browser's reasoning score**.

## Structural evidence gaps

- Six **identical original URLs** occur in records spanning multiple layers. The same paper appearing under both Practical and Academic must not be counted as two independently corroborating witnesses.
- Practical currently indexes **nine unverified reported cases and 48 procurement-context notices**, not approved live Nocturnal source matter data. The upstream private publication contract has unresolved CI failure.
- Academic has **103** development source identities, but no independently validated scientific findings and its **66-document holdout remains sealed**.
- Implementation has **1,287** source-repository leads, **44** pinned revisions, **39** SHA-qualified source-code inspections, and **two** truly executed source modules with 31/32 passing preregistered synthetic cases. This cannot establish operating-device performance or integration suitability.
- The evidence UI is **metadata-level, not passage-level**. The original extracted article/report bodies are not in its safe browser output, meaning a model added on top of the current JSON alone could only reason over provisional summaries. Full-text retrieval should be permissioned and independent of browser metadata.
- Semantic candidate edges in earlier three-layer graph projections are explicitly **not validated**, and are not connected to the standalone 1,497-record source dataset by stable review receipts.

## Recommended semantic integration acceptance gate (NOT yet passed)

The next phase should be a *bounded semantic vertical slice*, not generic embeddings and not cross-layer conversion ranking:

1. **One map at a time**, enable authenticated model inference over original allowed passage text, with text SHA, source ID, exact cited span, population/outcome/design scope, and explicit abstention. No full source text or sealed holdout in any user-visible public bundle.
2. **Query paraphrases, scope traps and negations**. Reuse these 10 development pairs for a smoke test, but reserve **independent blinded tasks** for actual quantitative quality. Score retrieval relevance separately from claim entailment and source quote accuracy.
3. Distinguish same DOI/source appearing in different layers from independent corroboration. Cross-source comparisons remain candidates, never established causal relationships.
4. **Route source-based model verdicts to inspectable review receipts**, not native automatic promotion. Operator checks field and technical fit; an original executable synthetic-test pass remains a bounded component fact.
5. Explicit capability gate: no fabricated citations, no claimed clinical/field effectiveness from only abstracts, correct abstention for unavailable evidence, verified source-version identity, benchmark run/source hash, and independent reference labels.
6. Only after independent layers work semantically should a cross-map question (Practical↔Academic↔Implementation) be attempted using separately checked source grounds; no automatic asserted bridges.

## Reproduction

```bash
python -m cite_refinery.semantic_integration_reality_audit \
  --pilot /tmp/standalone-research-pilot/atlas.json \
  --archived-entailment research_materials/opportunity_atlas/semantic_entailment_diagnostic_results.json \
  --archived-semantic-queue research_materials/opportunity_atlas/academic_semantic_review_queue.json \
  --template src/cite_refinery/standalone_atlas_template.html \
  --workspace-source src/cite_refinery/standalone_workspace.py \
  --report-out /tmp/semantic_integration_reality_audit.json
```

This command creates an inspectable machine-readable, deliberately **non-promoting** diagnostic receipt. A passing CI job means the audit correctly identified and preserved the observed semantic gap, **not** that the semantic readiness gate passed.
