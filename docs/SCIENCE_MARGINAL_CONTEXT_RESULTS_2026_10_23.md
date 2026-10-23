# Science metadata reuse: completed marginal-value experiment

**2026-10-23 — first source-pinned, provider-executed finding.** This is a bounded software-*metadata* comparison, not a software execution, Semantic Atlas, commercial value, or human time-savings benchmark.

## Provenance and testing

- Parent benchmark: <https://github.com/Spectating101/cite-refinery/actions/runs/39928095138>, original frozen **1,287 GitHub repository** survey; **398 Science index identity matches** and **889 explicit nonmatches**.
- This benchmark: <https://github.com/Spectating101/cite-refinery/actions/runs/39941506464>. Original 1,287-source artifact was downloaded from the immutable parent GitHub Actions run and checked against both the complete source-repo SHA-256 and the complete response artifact's canonical SHA-256.
- Reproducible, precommitted SHA-256 sample: **20 matched** Science project IDs, plus **20 unmatched** GitHub repositories as controls. This *deterministic development sample is not a random draw*, so don't generalize the 20-project fetch-success percentage to all 398 matched IDs.
- All seven new focused source-provenance/adversarial tests passed. The complete-repository CI remains red due to separate optional Antigravity CLI and missing optional dependencies already observed in earlier runs; this is **not** the same as the focused experiment failing.

## Actual live provider results

| Distinct measurement | Observed |
|---|---:|
| Original Science-matched repository identities in cohort | 20 |
| Project context endpoints returning a structurally valid original project record | **11 / 20** |
| Matched catalog identities whose context returned HTTP 404 | **9 / 20** |
| Of the 11 returned, with package relationship metadata | **9** |
| Of the 11 returned, with indexed direct-dependency records | **10** |
| Of the 11 returned, with at least one language record | **10** |
| Of the 11 returned, with multiple description records | **2** |
| Frozen GitHub snapshot descriptions present for matched cohort | **20 / 20** |
| Frozen GitHub snapshot descriptions present for unmatched controls | **20 / 20** |
| Context reads where returned canonical repo URL agreed with original matched repo | **11 / 11** |
| Accepted evidence/implementation validity graph edges | **0** |

All nine provider failures were HTTP 404 for original Science project IDs that had nevertheless appeared in the complete Science bulk identity lookup. Thus an **identity lookup success is not a guarantee that the project's richer source record remains retrievable**. This is an actionable catalog-consistency issue. Do not interpret 404 as a deleted GitHub repo, a nonfunctional project, or a provider-wide outage.

The working Science contexts genuinely provide *metadata fields missing from our GitHub-only survey*: original project-to-package relationships and recorded dependency graphs. However, the GitHub snapshot already contained a description for every sampled matched and unmatched repository. More descriptions in Science are not automatically better writing or source verification.

## Where the original source survey overlaps

The full-census overlap is category-dependent. These counts are **identity lookups**, not independently verified source usefulness, and original repository categories overlap (1,360 category memberships across 1,287 repositories):

| Original Refinery category | Science matches / original category repositories |
|---|---:|
| Materials | 27 / 33 |
| Climate | 24 / 33 |
| Computational chemistry | 23 / 33 |
| Energy | 22 / 33 |
| Bioinformatics | 19 / 33 |
| Scientific computing | 18 / 33 |
| Water | 15 / 29 |
| PCB | 1 / 33 |
| Digital identity | 1 / 29 |
| Blockchain analytics | 1 / 22 |

This shows where the external science database is *more likely* to enrich existing candidate records, but does not mean a project in a high-overlap category is good for the user's problem. PCB, digital identity, blockchain analytics and similar areas still need the original GitHub/other discovery route.

## Actual consolidation decision

**Adopt Science as an optional enrichment source, not as a primary or sole discovery index.**

In the original source qualification pipeline:
1. Start with a known, original source GitHub identity, original commit and rights metadata.
2. Look up a Science project identity. If absent/ambiguous, retain the GitHub source and mark external coverage unknown or absent; do **not** exclude the repository.
3. If Science returns a candidate project ID, attempt a bounded original Science project-context read. A 404 or malformed response retains the existing GitHub source with an explicit catalog-availability receipt; never claim the repository is invalid or its software unusable.
4. Where Science context is retrievable and original repository identity consistent, attach only attributed read-only package/dependency/institution/research metadata. Preserve timestamps, provider identity and license obligations. Treat dependency-indexing timestamp absence as *unknown coverage*.
5. Keep original source-code execution, pinned function tests, scientific-paper entailment, safety fit, independent adoption barriers, Nocturnal publication controls and human review under Cite–Refinery's own authority.
6. Do not invent a custom package relationship index now. Investigate whether Science/Repos plus Software Heritage cover our needs in a separate, actual-use-case experiment.

This is a **source-backed narrowing of duplicate work**, not proof that Atlas automatically reasons across all three maps. **No new Atlas corpus records, held-out Academic identities, approved Nocturnal cases, grants or investor leads were promoted**.

## ORKG gate now resolved at transport level

A separately completed live smoke test at <https://github.com/Spectating101/cite-refinery/actions/runs/39941384564> retrieved **three ORKG scholarly-paper candidates** alongside three Science software candidates for the same test query. The cause of the earlier 400 was an incorrect shared generic-JSON fetcher selecting the ORKG legacy paper controller; the corrected route uses **`Accept: application/vnd.orkg.paper.v2+json`**. The shared adapter's dedicated tests passed.

Successful ORKG response parsing is *not* proof of original paper scientific conclusions or a completed ORKG graph integration. Keep original scholarly source verification and use ORKG for candidate metadata, not authoritative truth.

## Next meaningful quality test

Instead of building more catalog code, select a small fixed set of *source-qualified* implementation questions, evaluate source-verifiable actual package/dependency coverage versus GitHub alone, then run a controlled analyst-workflow comparison. Only then can we claim time saved or better technical qualification; the present count comparison cannot establish that.
