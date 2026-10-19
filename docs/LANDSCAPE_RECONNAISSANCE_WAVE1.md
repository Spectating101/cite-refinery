# Deep Research reconnaissance — first graph-ingestion wave (2026-10-20)

**Purpose:** use the user's *Cite-Refinery Breadth-First Semantic Landscape* as input to a **map**, not as a definitive report or a selected research target. This wave depends on the earlier exploratory graph in draft PR #46 but is independently importable into a fresh project.

## Deliverables

| Path | Purpose |
| --- | --- |
| `research_materials/landscape_20261020/modules.json` | All **54** candidate modules from the user's report, grouped into the original **nine** fields; twelve explicitly marked as wave-one anchors |
| `research_materials/landscape_20261020/module_index.csv` | Machine-readable 54-module index with **actual source-linked claim counts** per Practical/Academic/Program lane |
| `research_materials/landscape_20261020/sources.json` | **23** normalized publication/provider pointers with dates, original/secondary classification, scope, limitations and review level |
| `research_materials/landscape_20261020/claims_and_bridges.json` | **24** source-attributed, bounded evidence summaries and **11** candidate relationships |
| `examples/landscape_reconnaissance_wave1.json` | Deterministic `cite_refinery.semantic_graph.v1` packet: **64 clusters, 78 nodes, 35 candidate edges** |
| `scripts/build_landscape_research_wave1.py` | Rebuilds graph and CSV from the ledger; validates identifiers and provenance |
| `tests/test_landscape_research_wave1.py` | Structural, epistemic-boundary, idempotence and isolated-ingestion tests |

The graph contains **54 neutral module/question nodes** and **24 source-linked evidence nodes** (10 Practical, 5 Academic, 9 Program). The 42 second-ring modules have **no evidence claims yet**. The twelve anchor modules have uneven layer coverage by design. For example, `CO-01` has all three lanes represented; `DP-03` currently has only Academic; `FS-01` currently has only Practical. These counts are *represented-source counts*, not measures of global knowledge, severity, or intervention efficacy.

## Why this is not a three-source-per-module corpus

The pasted Deep Research result names source packs and says a downloadable 54-node CSV exists, with three URLs per module. **That CSV was not included in the supplied text.** We did not invent or claim to reconstruct it. Instead, we individually recovered a smaller source ledger from publicly accessible publication pages, abstracts and official/provider documentation. The 54 module names and summaries are report-derived; the 23 URLs in the ledger are separately identified sources. No original underlying statistical datasets, site-level evaluations, or full-text systematic reviews were downloaded and independently audited in this wave.

A source can be **about** a module without establishing a causal mechanism or proving a solution. Program nodes include a monitoring database, a published scenario, an operating survey app, and a policy/measurement framework. They are not equivalent to an effective intervention. For instance:

- `CO-01`: ITU's six dimensions of meaningful connectivity are a practical framework; an academic review describes digital inequity; ITU DataHub offers statistics. This does not establish that an inclusion intervention worked.
- `WA-06`: WMO's 2025 hydrological report describes abnormal flows and observation gaps; HydroSOS documents a monitoring initiative. The local forecast skill or operational coverage is **not** established.
- `EN-03`: IEA's ACCESS scenario is a **modelled pathway**, not a deployed electricity-access program.
- `AW-01`: Taiwan's 2024 national survey, a population-estimation methods review, and Talea documentation occupy different layers. The guide does **not** establish an individual-identification estimator or successful population control.
- `DP-03`: an academic foundation-model privacy review does not prove an actual data leak or a deployed protection system. The Practical and Program lanes remain empty here.

## Map topology and boundaries

The root has nine field clusters, each with six candidate problem modules. Every module has a neutral question node. Only twelve anchor modules receive evidence nodes in this wave. Evidence nodes connect to their module using **candidate** `CONTEXT_FOR` or `RELATED_TO` relations; no `SUPPORTS`, `CAUSES`, `IMPLEMENTS`, `PRODUCES`, `ADDRESSES`, or `PARTIALLY_ADDRESSES` assertions are made.

Eleven candidate bridges connect modules. Examples:

- `CO-01` **DEPENDS_ON** `EN-03`: electricity reliability is a candidate enabling constraint on meaningful connectivity, not proof that power explains every usage gap.
- `CO-01` **CONTEXT_FOR** `ED-05`: educational connectivity is related to, but not identical with, general connectivity.
- `WA-06` **PROVIDES_DATA_FOR** `FS-03`: hydrological observations may inform agricultural adaptation, without validating any specific intervention.
- `FS-01` **CONTEXT_FOR** `PH-06`: healthy-diet affordability is relevant to NCD prevention; no quantitative causal link is asserted.
- `HO-01` **CONTEXT_FOR** `PH-01`: housing cost and health spending can interact through household resources; local evidence is not yet attached.

All bridges remain **candidate**, including those suggested as qualified in the Deep Research prose: publication-level co-occurrence and general context are not sufficient to assert a location-specific causal dependency. Similar terms in different fields have **not** been merged into a shared entity.

## Import, inspect, and regenerate

```bash
python3 scripts/build_landscape_research_wave1.py
PYTHONPATH=src:. python3 -m unittest discover -s tests -p 'test_landscape_research_wave1.py' -v
PYTHONPATH=src:. python3 -m unittest discover -s tests -q
```

Create a **new isolated Cite-Refinery project**, then ingest `examples/landscape_reconnaissance_wave1.json` through `SemanticGraph.ingest_packet` or the existing `graph-ingest` CLI. Do not ingest into the frozen acceptance-case projects or conflate this research corpus with the earlier exploratory seed.

## What remains before this becomes a reliable landscape

The source ledger is still heavily institutional and English-language; underrepresented local sources, regions and disciplines are missing. Many source summaries are from abstracts or institutional reports; they have not been independently replicated. All 42 second-ring modules are **report-only placeholders**. Some source pointers describe a framework, not an observation or an implementation. No module has independently validated intervention efficacy, field-wide completeness, or reliable causal attribution.

The next expansion should: acquire the actual downloadable 54-module CSV if available; inspect underlying datasets and full-text methods for each anchor; add representative local Practical material and actual Program deployments with outcome evidence; expand the 42 second-ring modules; resolve duplicates only after checking semantic identity; then review the cross-field edges and their limitations. **Do not pick a winning field yet.**

A missing lane or broken path means *not established in this represented corpus*, never *absent in the world*.
