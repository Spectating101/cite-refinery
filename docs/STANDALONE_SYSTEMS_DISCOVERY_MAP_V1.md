# Standalone app/system discovery and cluster mapping — v1

**Goal:** Cite–Refinery should discover applications, repositories, services, tools and systems **as an independent intelligence atlas**, not as a satellite of Hardware Splicer or of the maintainer's portfolio.

## What has been added

`src/cite_refinery/standalone_systems_catalog.py` is a self-contained Program-supply feeder. It reuses the existing external reuse registry and authenticated model adapter.

1. **Discover:** A bounded, read-only GitHub repository search over *arbitrary* operator-supplied search queries. Search metadata is a navigation lead; no README claim, stars, popularity, scientific correctness or deployment status is verified.
2. **Catalog:** Normalize the existing 30-item reusable-system registry and optional fresh discovery records, deduplicate source URLs, attach provenance and retain bounded system descriptions. It does not ingest/modify portfolio repositories or any held-out scientific material.
3. **Source-category navigation:** Build a usable, explicitly source-labeled categorical navigation map without AI. The categories were supplied in the existing registry and are **not emergent semantic discoveries**.
4. **Functional clustering:** An opt-in existing strong-model route receives app/system descriptions *without the source categories*. It proposes overlapping clusters, or leaves weakly related systems unplaced. Every membership cites an exact substring of the corresponding source description. Membership and functional similarity remain unverified hypotheses.
5. **Graph projection:** Produce `cite_refinery.semantic_graph.v1` Program nodes (source-reported functionality), candidate cluster memberships and **zero invented program-to-program compatibility edges**. Nothing is imported automatically.

This is the beginning of a standing independent Program map. The practical and academic maps can later link to it, but neither is required to collect and classify software systems.

## Actual source inventory

The first **source-navigation** snapshot is checked in at
`research_materials/standalone_systems/reference_navigation_map_2026_10_28.json`.

- 30 existing external systems / services / directories from the reuse registry as of October 20.
- 3 independently identified public GitHub systems from official maintainer documentation, added October 28: `getzep/graphiti` (temporal knowledge graphs), `topoteretes/cognee` (agent memory and graph retrieval), `assafelovic/gpt-researcher` (automated research pipeline).
- 33 listed entities, 24 **source-labeled navigation buckets**, zero verified functional equivalence / integration relations.
- This snapshot is reference browsing, **not** a successful model-derived current cluster map. A strong model has not been invoked in this chat and the repositories have not been independently executed or assessed.

The three discoveries are in `research_materials/standalone_systems/source_discovery_examples_2026_10_28.json` as nonauthoritative records. Their capability descriptions paraphrase maintainer documentation and do not constitute confirmed outcomes.

## Reproduce locally without CI

On a machine with this branch checked out and Python 3.11+:

```bash
export PYTHONPATH=src

# Base catalog: 30 existing reference systems + 3 newer public app leads.
python -m cite_refinery.standalone_systems_catalog catalog \
  --registry research_materials/external_landscape/reuse_registry_v1.json \
  --discovery research_materials/standalone_systems/source_discovery_examples_2026_10_28.json \
  --out /tmp/refinery-external-systems-catalog.json

# A read-only, source-category navigation packet. No AI, no graph import.
python -m cite_refinery.standalone_systems_catalog map \
  --catalog /tmp/refinery-external-systems-catalog.json \
  --out /tmp/refinery-external-system-navigation-packet.json

# Unbiased-to-source-label LLM clustering prompt, NO live model call.
python -m cite_refinery.standalone_systems_catalog propose \
  --catalog /tmp/refinery-external-systems-catalog.json \
  --prompt-only --out /tmp/refinery-program-cluster-prompt.json

# Actual strong-model functional clustering — opt-in on authenticated Optiplex.
python -m cite_refinery.standalone_systems_catalog propose \
  --catalog /tmp/refinery-external-systems-catalog.json \
  --provider antigravity --model gemini-4-argon-medium \
  --out /tmp/refinery-program-functional-proposal.json

# Candidate-only, source-scoped functional map after review.
python -m cite_refinery.standalone_systems_catalog map \
  --catalog /tmp/refinery-external-systems-catalog.json \
  --proposal /tmp/refinery-program-functional-proposal.json \
  --out /tmp/refinery-functional-system-map.json
```

**Expand beyond any predefined topic:**

```bash
cat > /tmp/system-queries.json <<'JSON'
[
  "evidence synthesis reproducible research",
  "graph knowledge bases temporal memory",
  "open source lab instrumentation",
  "civic data transparency software"
]
JSON
python -m cite_refinery.standalone_systems_catalog discover \
  --queries /tmp/system-queries.json --per-query 6 \
  --out /tmp/github-systems-discovery.json

python -m cite_refinery.standalone_systems_catalog catalog \
  --registry research_materials/external_landscape/reuse_registry_v1.json \
  --discovery /tmp/github-systems-discovery.json \
  --out /tmp/refinery-expanded-systems-catalog.json
```

The queries above are **examples**, not hardcoded constraints or evidence that those topics are most important.

## Follow-on milestone: persistent cluster map

Run an actual authenticated strong-model discovery pass on the catalog; independently inspect the candidate clusters for false equivalents and missing systems. Repeat source discovery by an explicit schedule/cadence only when separately authorized. Diff successive source-catalog snapshots by URL/identity, source labels and evidence; retain prior revisions and temporal changes rather than overwriting the map.

Future ranking dimensions: type of system (directory versus actual software), task and capability, inputs/outputs, restrictions/licensing, integrations/requirements, implementation maturity and independent usage evidence. Those **must be measured and source-backed**, not inferred from a similar README phrase.

No CI configuration, scheduler, import into existing graphs, user-portfolio integration, automatic authority promotion or corpus/holdout modifications are part of this branch.
