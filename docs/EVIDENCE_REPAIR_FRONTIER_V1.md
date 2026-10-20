# Evidence repair frontier v1: from source audit to actionable investigation

**Cite-Refinery, October 20, 2026 — experimental, neutral review**

## Purpose

Previous research on the Anuradhapura CNVR paper (DOI 10.14202/vetworld.2026.2816-2849, PMC13500148, CC BY 4.0) detected two Table T2 sex-total inconsistencies, unsuccessful exact numerical reproduction of Table T3 from 12 alternative public-table negative-binomial fits, missing aligned data/code for Table T6C, and missing independent population or human-rabies outcome measurements. This branch turns these into **research questions**, not claims that the original paper is wrong.

The prepare command validates the original scholarly DOI, matching full-text/table SHA-256, source-row counts, model results and the existence of source-backed original propositions. It produces an inspectable frontier with five provenance-linked cases.

| Case | Workflow priority | Evidence dependency |
|---|---|---|
| 2023 Zone 3 Program 2: total 62 vs sex sum 58 | P1 | Author/publisher clarification |
| 2024 Zone 3 Program 1: total 120 vs sex sum 136 | P1 | Author/publisher clarification |
| No exact reproduction of Table T3 from 12 explicit alternate refits | P0 | Original analysis dataset and R scripts |
| Missing program-aligned exposure/design matrix for Table T6C | P0 | Original author data and code |
| Independent canine abundance and geographically matched bite/PEP/rabies outcomes | P1 | **Public scientific discovery possible** |

Priority does not measure causal significance or scientific confidence. **Only the fifth problem is routed into a new public-source investigation.** The four others remain recorded as external author/publisher dependencies to prevent repeated web searching for unavailable records.

## What the new system actually does

**Prepare:** validate full-text/table/model receipts from draft PRs #59 and #61 and produce a source-hashed five-issue frontier, including exact published row values and required evidence.

**Stage:** add 11 neutral review nodes (one original source, five issue nodes, five questions) and provisional edges to the isolated Cite-Refinery project. Links to original claims are only unresolved CONTEXT_FOR relationships where claims directly relate to the audit, not accepted contradictions. No original node or edge state is promoted or changed. Graph packets are idempotent.

**Fork:** start a new independent investigation with public full-text enrichment enabled, retaining the parent investigation ID, the source audit fingerprint, and a four-item external-dependency queue. The original completed two-round investigation is unchanged.

**Research:** can be explicitly advanced through the existing investigator step/run CLI when a capable authenticated provider is available. The planner is instructed that missing private author data cannot be reconstructed through general web search.

## Real Optiplex demonstration

The original source-backed investigation was ID 2ca16ed4bdde441cabb1 and remains in done state after two prior rounds. A live review import produced a revised, source-matched graph packet receipt sgpacket:fabe402d061f908f. The exact refined packet declares 11 neutral nodes and 15 context/review edges; a first broader test import is retained in the isolated audit history.

The new actionable investigation ID is 49ecd664b5044b24abfc in the local Optiplex workspace /tmp/refinery-investigator-first-demo. Its question is whether independently measured dog abundance and bite/PEP/rabies observations can evaluate the reported program effects. The four unavailable-record questions are stored separately in its external-dependency queue.

**Crucial live inference limitation:** Codex GPT-6.1 returned a real account usage-limit error, confirmed with a separate read-only smoke call. The new child therefore stays at plan and has not completed an autonomous LLM planning/retrieval/reasoning round. No fake model response was substituted. The controller persisted the failure and can be resumed by an explicit future user action.

## Reproduce

From the branch's repository root, with an existing source-backed investigation project:

1. Run cite-refinery-repair prepare with --workspace, --investigation-id, --table-quality, --replication-assessment, --fulltext-audit and --out.
2. Run cite-refinery-repair stage with --workspace, --investigation-id and --frontier.
3. Run cite-refinery-repair fork with --workspace, --investigation-id and --frontier.
4. When an authenticated provider is available, use cite-refinery-investigate step for the new child ID, with --provider codex and --model gpt-6.1-sol. Steps are never run automatically.

Reference input files are in research_materials/runtime_trials/fulltext_dog_20261020. The sanitized evidence_repair_frontier.json is committed, but the full local workspace and model authentication are not.

## Scientific limits

- An internal published-table arithmetic difference does not prove that the author's original operational data are wrong.
- A model failure to match under alternate aggregations does not establish a published estimation error.
- Study T2/T3/T6 information is not independent field replication; DOI, full text and its original abstract remain one publication.
- No independent canine census, disease incidence series, author raw data, external human adjudication or separate reasoning-provider confirmation has been obtained.
- All evidence-quality claims remain in neutral/candidate/unresolved status. Original accepted graph records are not altered.
- No emails or data requests have been sent, and no deployment or background job has occurred.

Next strong gate: run the new fork when authenticated inference is genuinely available; review retrieved field sources and provenance without accepting a causal claim. Separately request consented analysis-ready source data from the author, then reproduce the exact Table T3/T6 scripts.
