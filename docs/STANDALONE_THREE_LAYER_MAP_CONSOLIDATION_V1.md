# Three standalone maps — consolidation baseline

**October 21, 2026 · Cite–Refinery · Read-only core mapping increment**

## Decision and scope

The immediate architectural priority is **quality, coverage, and utility of each foundational map in isolation**, before optimizing cross-layer opportunity discovery. This increment does **not** rank projects, infer needs from repository names, attach grants or customers, create native graph relationships, or claim underconversion.

The three foundations remain:

1. **Practical / Nocturnal:** what people, organizations, environments and institutions are actually experiencing, doing, measuring or failing to achieve.
2. **Academic / Cite:** what relevant scholarship establishes, investigates, explains, measures, contradicts and leaves uncertain.
3. **Implementation / Refinery:** which techniques, components, implementations and systems exist, what they demonstrably do, what rights/requirements they have, and where actual usable capability remains unverified.

The same scientific abstract may carry a *reported practical outcome* and also be a scholarly source. That creates two views of **one** original source, **not independent corroboration**. Every foundation record retains its URL and retrieved-text SHA-256 and remains explicitly provisional until independently reviewed.

## What is currently in the frozen sources

| Foundation | Actual source inventory | What is **not** established |
|---|---|---|
| Practical | **9** model-classified reported observations/implementations/outcomes from the 63-record corpus; **48** separately labeled published European procurement notices | Original operator field logs, independent measurements, an active customer, contract eligibility, demonstrated implementation effects |
| Academic | **47** Europe PMC / OpenAlex scholarly abstract or bibliographic leads; **8** source-linked but model-generated research areas; **6** source records deliberately left unplaced | Validated full texts and methods, contradiction/retraction checks, independent cluster quality, comprehensive disciplinary coverage |
| Implementation | **1,287 distinct** GitHub metadata leads from **753 primary + 605 lower-visibility** survey entries, with **71 overlapping repository identities**, across **44** original search categories and six umbrella categories | Full technical functionality, rights clearance, adoption or systematic quality qualification |
| Implementation category associations | **1,360** original repository–category memberships; **220** model-reviewed metadata relationships and **1,140** still unreviewed | The reviewed labels are not independent code checks; the remaining source categories may have ambiguous meanings |

These are **bounded source inventories**, not a census or calibrated percentage coverage of the world's problems, knowledge and available technology.

The previous corpus collection intentionally used **eight predefined query quotas**: dogs/rabies, heat adaptation, informal e-waste, food redistribution, flooding, lithium-ion batteries, school air quality and platform labor. Later model clusters were emergent **within that preselected collection**, not evidence of broad, unguided discovery across all fields.

Similarly, the 44 implementation categories reflect GitHub topic search framing. Terms such as *flood, repair, battery* can retrieve unrelated software mechanisms. Some of the existing 220 model metadata judgments specifically identify this polysemy. A repository's search appearance is not evidence that the project meets the category's actual engineering requirements.

## What was consolidated

The new `src/cite_refinery/layer_foundations.py` uses the existing canonical research and implementation source artifacts, **without new source crawlers or an additional installed console entry point**.

It:

- Validates that each published scholarly source reading matches its original URL and retrieved-text SHA-256, is unpromoted and belongs to the original manifest exactly once.
- Exposes the original eight provisional research areas, six unplaced original sources, abstract provenance, source scope and limitations. No model paraphrase is upgraded to confirmed science.
- Maintains separately: reported practical claims, official/procurement notice context and academic abstract source records. The last two do not silently become primary field observations.
- Deduplicates all original GitHub survey identities, checks for contradictory overlapping metadata, preserves all 1,360 category memberships and their four provisional review labels plus `not_reviewed`, and reports evidence deficits category by category.
- Provides **within-layer literal browsing only**, using collected research-theme or implementation-category facets. This is not semantic AI, technical qualification or cross-layer opportunity scoring.
- Creates a deterministic, **balanced backlog** of two currently unreviewed repository/category associations in each of the 44 original GitHub categories (**up to 88 source pairs**). Its contents are **not** review judgments; they are data to inspect. Do not count queue entries as completed semantic review.
- Preserves the full prior cross-layer discovery and conversion experiment work on other branches without treating those individual tests as systematic qualification of the 1,287-asset inventory.

### Canonical invocation

From the repository root (using the existing source paths as defaults):

```bash
cite-refinery investigate map-foundations \
  --json-out /tmp/layer_foundations.json \
  --markdown-out /tmp/layer_foundations.md \
  --review-backlog-out /tmp/unreviewed_implementation_pairs.json
```

Or browse one layer without inventing cross-layer relations:

```bash
cite-refinery investigate map-foundations \
  --layer implementation --facet finite_elements --terms analysis \
  --limit 15 \
  --json-out /tmp/fem_map_view.json \
  --markdown-out /tmp/fem_coverage.md
```

Other facets come from the actual collected academic themes and the 44 existing implementation categories. The command refuses pre-existing output files and cross-layer browsing requests. It reads local files only, does not contact source websites or call any LLM, and does not create an investigation workspace.

## The actual layer-by-layer upgrade sequence

### Practical: expand original observations

Collect independent operational or public-program evidence with clear date, place, affected group, denominator, concrete observed phenomenon, source owner and baseline. Distinguish actual operator/personal observations, peer-reviewed observational data, program reports, interviews, announcements, procurement and secondary commentary. Record contradictory accounts and outcomes without equating absence from a small corpus with absence in the world. *Until then, Practical remains the weakest map.*

### Academic: qualify studies and claims

Go beyond abstract summaries. Retrieve permissible full-text methods/results and evaluate study design, sample scope, measurement validity, confounding, effect or mechanism, disagreement and replication. Give specific primary evidence lines for accepted findings; keep contrary work and unplaced articles. Assess whether the eight themes themselves miss major lines of inquiry due to original search design. Independent reviewers, not merely an agreeing second model, must evaluate sampled interpretations.

### Implementation: inventory demonstrated capabilities, not just projects

Finish the metadata polysemy audit using a source-balanced sample, then systematically inspect original README/API/source/tests, license and installation requirements across unrelated software and non-software categories. Add source code forges beyond GitHub, open hardware, datasets, reusable research methods, institutional programs and maintained infrastructure. Mark individually tested components with exact revisions and bounded pass/fail receipts, but do not generalize them to entire projects.

### Within each layer: make exploration valuable

The intended standalone maps must support questions like: which problems recur in unrelated institutions? Which academic methods address similar measurement failures? Which source projects implement a specific capability? What alternatives, limitations, unresolved contradictions, or untested claims exist? More links between layers will not compensate for low source recall or incorrect labels within a single layer.

## Definition of a genuinely good foundation

Before resuming extensive cross-layer arbitrage ranking, measure:
- **Traceability:** exact original identities, excerpts/provenance, version, date, source license and measurement bounds.
- **Truthfulness:** known limitations, independent claim checks, false role/genre classification rate, explicit negative evidence.
- **Coverage and novelty:** source-family, geographic, domain and temporal bias; unseen-source/holdout evaluation instead of only self-affirming model outputs.
- **Structure:** useful themes, recurring within-layer mechanisms/capabilities, synonym/polysemy resolution, duplicates, dissenting sources and unplaced records.
- **Utility:** an unfamiliar investigator can locate genuinely relevant high-quality material and understand what is still unknown without being forced into an industry or commercial target.

**Do not claim these criteria are met merely because the consolidated command runs.** This PR fixes source inventory architecture and observability. The deeper collection, semantic review and independent validation work remains outstanding.

## Source and release boundaries

Original user/source data is drawn from the existing committed Oct 20–21 manifests and surveys; original long abstract text remains on the authorized computer and is not republished. The output can reconstruct public metadata, original URLs and SHA-256 references, but cannot use the digest alone to verify that a paraphrase is semantically entailed. No new funding awards, customers, physical devices, direct user data, or live institutional assessments are implied.

This branch is **draft consolidation**, based on the existing #97 draft. The original uncommitted Optiplex prototype exists separately but was inaccessible once its remote connection reached the usage limit. The GitHub work here was reconstructed directly from the committed source formats and must pass repository CI before being treated as release-ready.
