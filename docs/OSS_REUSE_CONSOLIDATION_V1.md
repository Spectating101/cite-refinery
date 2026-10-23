# OSS reuse consolidation — source-first, no duplicate Atlas engines

**October 23, 2026.** Non-promoting discovery integration on an isolated branch from `main`. Not a merged release, not a semantic-accuracy benchmark, not a verified commercial product.

## Overlap assessed

The existing 30-item reuse registry already covered OpenAlex, OpenAIRE, the general ecosyste.ms repository service, Microsoft GraphRAG, LightRAG, PaperQA2, Docling, GROBID and W3C PROV. It missed material substitutes:

| Existing project | Duplicated capability | Consolidation decision |
|---|---|---|
| [ecosyste.ms Science](https://github.com/ecosyste-ms/science) | Cross-domain research software discovery, scientific classification and JOSS/repository links | **Reuse metadata API**. No cloned database or new science-score engine |
| [ORKG](https://orkg.org/) | Scientific paper/contribution knowledge graph and structured comparison | **Reuse paper metadata API** for candidate scholarly connections. Do not equate ORKG verified flag with article conclusion |
| [OpenAleph](https://github.com/openaleph/openaleph) and [FollowTheMoney](https://github.com/opensanctions/followthemoney) | Practical investigative document indexing, cross-dataset investigative entity ontology | **Preview schema compatibility** for local exports; do not import persons/cases, replicate OpenAleph service, or bypass Nocturnal publication rules |
| [PaperQA2](https://github.com/future-house/paper-qa) | Academic local source retrieval and citation candidates | **Already integrated** as optional sparse retrieval. Local answer step was still timed out in 2026-10-20 trial |
| [Cognee](https://github.com/topoteretes/cognee), [Graphiti](https://github.com/getzep/graphiti) | Generic/temporal knowledge graphs | **Compare later**, after current three-map semantic evaluation; don't install parallel graph engines now |
| [OpenScholar](https://github.com/akariasai/openscholar) | Grounded scholarly answer synthesis | **External benchmark**, not another custom QA engine |
| [OpenSSF Scorecard](https://github.com/ossf/scorecard), [Zoekt](https://github.com/sourcegraph/zoekt) | Repository quality/security signal and code search | **Possible downstream Refinery modules**, not capability verification or automated deployment |

New source listings were added as bounded metadata in the *existing* `reuse_registry_v1.json`. All frozen split numbers, holdout digest and source data remain intact.

## What is actually implemented

There is **no replacement Atlas subsystem**. The existing `cite-refinery-landscape` command now supports:

```sh
cite-refinery-landscape reuse "flood" --sources science,orkg --limit 6
cite-refinery-landscape reuse "flood" --sources science,orkg --limit 6 \
  --module-id flood-risk --module-title "Flood monitoring"
cite-refinery-landscape ftm-preview ./authorized_public_entities.json \
  --dataset-id public_investigation_01
```

**Science:** fixed HTTPS `/api/v1/software/search` with literal project/name substring matching, bounded `limit`, fixed page and explicit `after_id` support programmatically; optional exact `/software/lookup` for named DOI, PURL or repo identity. Results preserve project IDs, matching evidence, source API records, possible GitHub URLs, project-science scores and reported fields. Science scores, citations, package names, institutional connections and repository links are **not** proof of code execution, effective intervention, scientific findings or adoption.

**ORKG:** fixed read-only `/api/papers` with title filter, page 0 and bounded size. If the endpoint has a newer response format, the adapter refuses it rather than producing false results. Paper IDs and reported DOI/year are candidates for *subsequent original-source checks*. An ORKG `verified: true` flag does not establish that a particular scientific claim is true.

**FollowTheMoney:** bounded local *summary only* of entity schemas and counts, with raw-file SHA-256 and caller-declared dataset identity. Does **not** export names, subject properties or sensitive identities; does not stage entities into any Atlas graph. No auto-publication, no reading Nocturnal private ledgers, and no inference that a person mentioned in a record is culpable. A future Nocturnal FTM bridge requires separate privacy, source rights, jurisdiction and correction/retraction reviews.

**Neutral consolidation:** `consolidate_discovery()` retains providers independently; if one fails, the result is `partial` with typed errors, not a false global no-result. Optional `stage_landscape_packet()` uses existing neutral `DISCOVERED_FOR` candidate edges only, with zero accepted Academic, Practical, or Implementation claims. Nothing adds records to the 232-source research freeze, 1,497-card browser, 66 held-out Academic records, or the promoted graph.

## Validation rules

A dedicated focused regression suite tests URL/identity formation, paginated Science IDs, ORKG DOI mapping, failure propagation, neutral packet non-promotion and local FTM privacy. A separate CI live smoke is allowed to query only the listed public Science and ORKG endpoints; it must **record provider availability**. If either API is inaccessible or its deployed schema differs, mark the provider unavailable (404/parse failure) and leave its interface in **adapter-code-only** state rather than calling integration complete.

The original `external_solution_sources._fetch_json` blocks HTTP redirects, bounds response size, requires JSON, and uses a short timeout. New imports are lightweight stdlib; no AGPL code was copied. The science.ecosyste.ms API data is advertised CC BY-SA 4.0, so a commercial redistribution product would need license attribution, share-alike review and separate terms checks; project source code is AGPL-3.0. No rights for full article republishing or sealed investigation ingestion follow from an accessible API.

## Reuse acceptance and stopping

1. **Science pilot:** Compare overlap with 20 known Refinery research repos by exact repo URL; separately inspect missed coverage and classify true use. Do not assume 60k indexed projects imply 60k production-grade implementations.
2. **ORKG pilot:** Match 20 frozen Academic development paper identities by DOI, then independently check whether structured conclusions align with original source passages; avoid touching sealed holdouts.
3. **FTM/Nocturnal compatibility:** With *authorized public demo fixtures only*, test mapping of simple organizations, people and legal entities; don't ingest private cases into Cite–Refinery.
4. **Competitive test:** Run the same user tasks with ordinary search/AI, existing OSS individually and Atlas plus selected APIs, under equal source access. Measure evidence accuracy, verified original code functionality, unsupported claims, and researcher time.
5. **Stop:** If the third-party tool alone does as well as Atlas on independently labeled tasks, keep it as an external service and limit Atlas to missing evidence-qualification capabilities. Don't duplicate a graph engine for a cosmetic performance difference.

**No feature or market superiority has been established by this adapter PR.**
