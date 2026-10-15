# Scale study — Nocturnal → Cite → Refinery

Date: 2026-10-16

## Scope

This iteration tests whether the three-layer Cite-Refinery architecture still makes sense when shaped like the current Nocturnal China/India development programmes rather than a two-observation fixture.

The integration test uses a schema-faithful synthetic corpus with **50 matters and 203 observations**, divided across two countries and five problem domains. That shape mirrors the inspected development corpus without copying private empirical case content into this public repository.

This is an **integration-scale contract**, not a claim that all three private canonical applications were executed together on one host. During this study the authorized execution host was unavailable. The current private repositories and interfaces were inspected directly; Cite-Refinery itself is validated by its public CI.

## What failed in v0

### 1. Raw TRACE cases did not contain literature-query hints

The first Nocturnal adapter expected enriched research packets where observations already carried `literature_queries`. Raw TRACE empirical case files instead carry country, domain, cohort, quality state, stages, sources, trace edges and actor roles, but usually no literature query.

At scale this meant Cite-Refinery could ingest the problem corpus but could not create a research brief without a manually supplied question.

**Repair:** preserve the TRACE case metadata and derive a small set of clearly labelled `structural_fallback` research questions from explicit problem structure only when upstream literature hints are absent. These are search prompts, not findings or evidence.

### 2. One flat research prompt is the wrong unit

Country programmes preserve domain, cohort and quality boundaries for a reason. Flattening all observations into one Cite prompt would mix heterogeneous questions, make prompt size unpredictable, and erase development/holdout distinctions.

**Repair:** `research-agenda` groups by `country / domain / cohort`, keeps each matter atomic, and chunks only when a brief would exceed the configured observation bound. Grounding also has explicit character budgets and records truncation/omission diagnostics.

### 3. Refinery search is currently literal, not semantic

Passing a complete natural-language capability requirement as the only query can yield false negatives even when a matching capability exists under a shorter name/tag.

**Repair:** solution mapping first tries the full requirement. If that returns no candidates, Cite-Refinery issues transparent literal probes derived from explicit tags and significant terms, records every probe, and deduplicates the returned candidates. No semantic-rank claim is made.

## Scale invariants

The 50-matter / 203-observation test requires:

1. all empirical observations remain `robs:*` objects and no academic claim is synthesized merely by ingestion or research grounding;
2. country, domain, cohort and quality metadata survive import;
3. the corpus forms ten bounded country/domain research briefs at the tested load;
4. raw cases with zero literature-query hints remain researchable through labelled structural fallback questions;
5. Cite prompts stay within the configured character budget and the system records any omitted/truncated material;
6. a literal Refinery miss can recover through an auditable probe without pretending the result is semantic retrieval;
7. the scale report surfaces low literature-query coverage, heterogeneous empirical quality and zero-candidate solution mapping as warnings rather than silently treating them as success.

## Current verdict boundary

The architecture is strongest as a **provenance-preserving control plane**. Nocturnal already provides a credible structured problem layer; Cite-Refinery can now turn that layer into bounded research work without collapsing empirical and academic evidence.

The weak side is downstream depth. Cite grounding quality still depends on the actual literature working set and research acquisition path. Refinery can only map what its registry knows, and its current discovery surface is deliberately conservative. A clean orchestration graph therefore does not mean every practical problem has a grounded intervention or an existing executable implementation.

The next meaningful scale gate is not another object model. It is end-to-end supply depth: run the agenda through a live Cite research acquisition/synthesis workflow, convert supported intervention/mechanism findings into explicit capability requirements, expand/refine the Refinery capability supply, and measure requirement coverage and validated executable matches.
