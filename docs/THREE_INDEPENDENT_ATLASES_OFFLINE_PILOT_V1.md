# Three standalone maps — offline research workspace pilot

**22 October 2026 · draft, unmerged.** This is the first user-facing browse experience built from the three separately audited map inventories, not a new graph inference system.

## Deliverable

A single portable `index.html` with embedded public-safe metadata, plus an `atlas.json` evidence packet and `README.txt`. Open HTML locally: no hosted service, API key, database, model dependency, browser network fetch or original-source corpus download is needed.

The page provides three separate Practical / Academic / Implementation tabs, literal phrase filtering inside a selected map, **source-evidenced field/category filters with occurrence counts**, evidence-class filters, inline source-class/coverage gaps, paginated records, record-level source URLs and source provenance, defensible authority statements, original test-case details where available, and copyable/downloadable source-specific JSON dossiers **plus filtered original-source cohort exports**. Category labels describe the original collection taxonomy or reported genre, not a validated scientific classification. No separate monolithic research ontology and **zero automated cross-layer edges**. Original author wording is displayed as *metadata or unverified reports*, not automatically promoted to established truth.

Expected release artefact when building with the frozen existing sources:

| Map | Public-safe read-only records | Boundary |
|---|---:|---|
| Practical | **57** | 9 unverified reported cases + 48 separate procurement notice records. No private Nocturnal snapshot included |
| Academic | **150** | 103 development-only original research source identities + 47 **separately classified older abstract leads**; sources may overlap. **66 sealed holdout documents excluded** |
| Implementation | **1,290** | 1,287 surveyed repository leads + 3 separately labeled historical tested assets, explicitly *outside* the survey sample. Source-pinned functionality currently tested for 2 of the 1,287. |

The selected original Implementation function replays contain 32 explicitly registered synthetic test cases, **31 pass, 1 fail** (LEF/DEF commented reference false positive). The test receipts remain scoped to their original pinned source revision; they are not independent evidence of live deployment or qualified reuse rights.

This is not representative worldwide coverage, scientific knowledge verification, a contradiction adjudicator, a business conversion list, or a recommendation engine. Academic development records currently have zero independently validated scientific findings. Real Nocturnal data are **not** silently imported.

## Create the pilot from previously checked standalone map outputs

The existing `map-foundations` CI builds and validates the independent source atlas JSON inputs. For a manually created local workspace:

```bash
python -m cite_refinery.standalone_workspace \
  --foundation /tmp/standalone_layer_foundations.json \
  --academic /tmp/academic_original_source_enriched_atlas.json \
  --implementation /tmp/implementation_capability_evidence_atlas.json \
  --out-dir /tmp/cite-refinery-research-pilot

# Open /tmp/cite-refinery-research-pilot/index.html in a browser
```

The output directory must be new; overwrite is refused. CI uploads the generated site along with the frozen index/receipt artifacts under `standalone-research-pilot/` as part of the `cite-refinery-three-layer-foundations` GitHub Actions artifact.

### Optional approved Nocturnal public data

Only if a **separately release-approved** Practical Atlas JSON exists, supply `--approved-practical /path/to/nocturnal_public_atlas.json`. Nonfictional snapshot inclusion is gated on the publisher-approved flag **and** external manifest fingerprint pin; a fictional test snapshot must be labeled as fictional. Without these conditions the pilot refuses it. We do not ship or synthesize private case ledgers.

## What the browser does not do

- It never invokes LLMs or automatically interprets a topical match as a research answer. Literal search results are source leads that a human can inspect and cite.
- It never writes to Commons, approves a claim, modifies a Nocturnal public record, or changes the Academic holdout.
- It does not mirror full-text, GitHub repository source or source bodies. Links open original sites and can be externally accessed only when clicked.
- User-facing original metadata is rendered with text-only DOM methods; JSON embedded into HTML escapes potentially dangerous script delimiters. An injected `</script>` title should remain data, not executable content.
- It has no server-side identity or production authorization. A local, portable HTML file is a **research preview**, not a multiuser deployment.

## Acceptance criteria and next release gap

Focused regression tests cover the actual 63-source original foundations, 103+66 frozen research split, 1,287 original Implementation inventory, 3 historic off-survey trial records, read-only output and script-injection attempts. The CI builds a wheel, generates the HTML/JSON site from source-checked artefacts, and asserts the record counts and 2/32 original-source test results.

The next release step is a bounded pilot evaluation with real independent research questions, source clicks, factual citation verification and observed user tasks; then a locally hosted authenticated experience. **Do not merge or describe it as deployed until review of this draft PR and successful GitHub Actions artifact inspection.**
