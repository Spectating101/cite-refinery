# Cite-Refinery source-first semantic discovery diagnostic — October 20, 2026

**Status:** experimentally tested, review-only. **No** accepted problem claims, automatic cross-module relationships, merged code or production deployment. This branch is stacked on draft PR #53 and is deliberately independent of the other chat's graph-expansion branches.

## Why this experiment

Earlier experiments established that Docling and PaperQA2 **retrieval** work, but local Ollama models and LightRAG extraction time out or misread obvious WMO source statements. Rather than retry an overloaded generator or call node counts scientific coverage, we tested whether a **small offline semantic model** can map original institutional source paragraphs to specific candidate problem modules without an LLM.

## Honest results

We used four official WMO/WHO source paragraphs (HydroSOS; rabies One Health; ambient air pollution; drinking water) and the **54 original + eight new candidate module titles and definitions** (62 total). The eight endpoint expectations across four sample sources were written to `gold.json` **before embedding**. The existing hand-authored cross-field bridges were **not used for retrieval**. Sample includes human decisions about which modules each paragraph could reasonably relate to; **single-annotator labels can be disputed**, particularly whether post-exposure care maps to the broad primary-care access module.

| Metric | TF-IDF whole paragraph | Offline MiniLM whole paragraph | MiniLM sentence-specific diagnostic |
| --- | ---: | ---: | ---: |
| Source counts | 4 | 4 | 4 |
| Source sentence spans | n/a | n/a | 7 |
| Expected endpoint recall at five | **5/8 (62.5%)** | **4/8 (50%)** | **6/8 (75%)** |
| Both expected endpoints in top five | 1/4 | 0/4 | 2/4 |
| Four expected cross-field pairs auto-proposed | **0/4** | **0/4** | **not proposed** |
| Other speculative cross-field pairs proposed | 0 | **17** | **none** |

The sentence-specific follow-up is **post-hoc exploratory** and cannot be interpreted as an unbiased result against independent gold. Important qualitative examples:

- HydroSOS / early warnings: hydrological observation `WA-06` and disaster warnings `DR-01` both surface within the top three **when separate sentences are retrieved**.
- Drinking water: `WA-01` and healthcare access `PH-02` appear at ranks 1 and 5 respectively in the sentence-level diagnostic.
- Rabies / clinical care: `AW-03` ranks first, but the gold `PH-02` requirement is rank 27, demonstrating **an ontology/relevance mismatch** rather than proving health care is unrelated.
- Air pollution: `AQ-01` ranks first, while `PH-06` (NCD prevention) is outside the top ten, showing that two applicable subject areas are not guaranteed to be recoverable by a generic encoder.

**Interpretation:** retrieved topics do not themselves establish a problem, the direction of a causal mechanism, or a program's outcome. The original 17 MiniLM proposed bridges are a **false-connection risk** but are not all labeled false: the held-out set has only four reference pairs.

## What is now implemented

- `src/cite_refinery/external_semantic_discovery.py`: consumes existing module titles/descriptions from explicit external registry files, supports a simple TF-IDF baseline and an offline local MiniLM embedding model, ranks modules by source text similarity, and supplies bounded source-local candidate pairs. Additional helpers segment paragraphs into traceable sentence spans and max-pool module relevance **for diagnostics only**.
- `src/cite_refinery/external_requirement_graph.py`: builds a separate `cite_refinery.semantic_graph.v1` snapshot with **neutral module nodes and neutral source-span nodes**. Only candidate **source-to-module** `CONTEXT_FOR` edges are created, each preserving source URL, exact excerpt SHA-256, rank, similarity and review boundary. It **cannot create module-to-module edges**.
- `scripts/external_source_first_discovery_v1.py`: reproducible live/pinned source input and optional `--packet-out` isolated graph export; by default it stages **sentence granularity**, not whole-paragraph assertions.
- `research_materials/runtime_trials/source_discovery_20261020/gold.json`: independently frozen expected module endpoints for four hand-chosen source examples.
- `research_materials/runtime_trials/source_discovery_20261020/results.json`: reproducible scores, source URLs, source SHA-256, top-ranked candidate identifiers and uncertain proposed pairs **without copying long source texts**.

**Real isolated import test:** the sentence-level snapshot yielded **63 clusters, 69 nodes, 20 candidate source-to-module links, zero module-to-module links**. The graph imported successfully in a fresh Cite-Refinery project and replay was idempotent. This is **not production data ingestion**.

## Reproduce without needing stale private temporary files

From a checkout where the landscape research branches exist:

```bash
git show research/landscape-horizontal-wave2:research_materials/landscape_20261020/modules.json > /tmp/refinery-modules.json
git show research/landscape-horizontal-wave2:research_materials/landscape_20261020/horizontal_wave2/fields_and_bridges.json > /tmp/refinery-new-fields.json

HF_HUB_OFFLINE=1 PYTHONPATH=src:. python3 scripts/external_source_first_discovery_v1.py \
  --modules /tmp/refinery-modules.json \
  --new-fields /tmp/refinery-new-fields.json \
  --gold research_materials/runtime_trials/source_discovery_20261020/gold.json \
  --out /tmp/refinery-discovery.json \
  --packet-out /tmp/refinery-source-review-packet.json
```

With `--snapshot /path/to/pinned-source-snapshot.json`, the run uses pinned WMO/WHO HTML passages instead of re-fetching public pages. Without it, the script reads the four official URLs again and checks the known passage selectors; outcomes may differ if source contents changed. **Do not import this snapshot on top of an accepted research project.**

Install optional dependencies with `pip install -e '.[semantic_discovery]'` (this can pull large model dependencies). Runtime dependencies for experiment: NumPy, scikit-learn, a locally cached `sentence-transformers/all-MiniLM-L6-v2` model, and Python requests/BeautifulSoup for live source collection. These remain optional and are not added to the core zero-dependency package. No paid API keys or long-running Ollama model were used.

## Next real coverage gate

The experiment identifies a precise missing capability: source-to-requirement entailment. We can now collect reviewed problem **requirement nodes** (not broad module descriptions), trace exact source spans to each requirement, and test whether proposed semantic edges are supported **with a human-readable chain of reasons**. Only after that should we run blind cross-field discovery against new sources with independent reviewers. An algorithm's closest topic is not automatically a verified implementation gap, evidence-backed dependency, or causal intervention.
