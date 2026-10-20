# External source reuse and corpus freeze gate (v1, 2026-10-20)

## Decision: STOP corpus/feature expansion; reuse existing discovery infrastructure

This branch is stacked on draft PR #70. Its purpose is **reuse-first external reconnaissance** rather than building yet another standalone research tool. Further source collection, new models, ontology expansion, polished interface work and automatic graph promotion are **frozen pending evaluation**. This is a working-scope decision documented in the repository, **not** a GitHub branch-protection rule or a claim that other agents have stopped.

The experimental corpus remains fixed at **232 unique records** (63 earlier plus 169 eligible new): 103 development and **66 sealed held-out**. The holdout includes 29 records in whole reserved housing/transport strata and 37 individual held-out records. The sealed SHA-256 receipt is tracked in `research_materials/external_landscape/reuse_registry_v1.json`. The PR #70 immutable manifest, private archive, and held-out annotation packet are **not modified or read by these adapters**.

### Permitted work while frozen
1. Finish mapping **development-only** records, preserving exact IDs/source boundaries.
2. Obtain blinded human annotations on the sealed holdout; do not inspect it during development.
3. Benchmark the same base assistant and tool access **with and without** Cite–Refinery; grade false source roles, unsupported program outcomes, false semantic relations, useful new discoveries, reproducibility and researcher time.
4. Fix bugs/security defects; introduce only limited **read-only external source adapters** that substitute existing infrastructure, without adding to the frozen evaluation corpus.
5. Evaluate the technical and legal suitability of existing implementations before writing replacement code.

### Not permitted until passing the evaluation gate
- Additional academic/policy/implementation corpora mixed into frozen split.
- New hand-built thematic modules, acceptance models or automatic problem-solution authority.
- More standalone product/UI layers without measured incremental researcher value.
- Promoting GitHub stars, DPG Registry listing, policy case study or dataset metadata into verified implementation impact.

## Reuse registry

Machine-readable inventory: [research_materials/external_landscape/reuse_registry_v1.json](../research_materials/external_landscape/reuse_registry_v1.json).

It records 30 discovery, research, institutional, repository and infrastructure options. These are **market references and candidate integrations**, not 30 completed connectors or 30 benchmarked vendors. The list includes GitTrend, OSS Insight, Elicit, Scite, Open Knowledge Maps, 3ie Gap Maps, MoyoMap, Open Sustainable Technology, OECD OPSI, Digital Public Goods, Dimensions, Overton, Data Commons, OpenAIRE, OpenAlex, ecosyste.ms, GitHub, GraphRAG, LightRAG, Neo4j, Lens, Product Hunt, AlternativeTo, OpenAlternative, StackShare, Hugging Face Spaces, EU OSOR, Hypothesis Atlas, SOLVED, and Wikidata.

Compare novelty against capabilities rather than site names:
- **Discovery/curation:** GitTrend, product directories. Do not rebuild GitHub rankers.
- **Research & policy graphs:** Open Knowledge Maps, 3ie, Elicit, Scite, Dimensions, Overton. Generic topic graphs and research-policy links are already established.
- **Implementation evidence:** OECD OPSI, DPG, Open Sustainable Technology, GitHub and ecosyste.ms. Registrations, README claims, code commits and stars do not establish observed outcomes.
- **Graph/RAG engines:** Microsoft GraphRAG, LightRAG, Neo4j GraphRAG. Evaluate reusable components before custom framework engineering.

## Actually implemented here

The earlier separate read-only topic pilot was **cherry-picked into this PR #70 child branch** instead of duplicating it:
- `cite-refinery-topics "urban heat" --with-openalex` — Wikidata and optional OpenAlex topic navigation.
- `cite-refinery-landscape scan "urban heat"` — Wikidata + OpenAIRE scholarly metadata. Change `--sources wikidata,openalex,openaire,dpg` to opt into other providers. DPG does local lexical filtering of a full catalog, **not** a provider-side semantic search; its network endpoint timed out during initial live smoke so external availability is not certified.
- `cite-refinery-landscape repo ecosyste-ms/repos` — exact GitHub repo lookup via ecosyste.ms.
- `cite-refinery-landscape scan "urban heat" --sources openaire --module-id urban_heat --module-title "Urban heat"` — include an isolated **neutral DISCOVERED_FOR candidate packet** for manual review; no authority and no auto-ingest.

All requests are URL-encoded to fixed HTTPS provider endpoints. Fetches are one-shot, bounded, do not follow redirects, and return partial/error status. No credentials, background jobs, automatic crawls, updates to projects, PR #70 frozen materials, or accepted evidence/semantic relations. Live smoke reached OpenAIRE and ecosyste.ms on 2026-10-20; the DPG adapter is covered by mock tests but its live endpoint was unavailable at the time of testing. Wikidata/OpenAlex were inherited from an existing pilot and no new availability claim is made here.

Source specifications:
- [OpenAIRE V4 research-products API](https://graph.openaire.eu/docs/apis/graph-api-v4/research-products/examples/) (v4 availability/schema may change).
- [Digital Public Goods Alliance API](https://github.com/DPGAlliance/dpg-api) (public listing; trailing slash required).
- [ecosyste.ms Repositories API](https://docs.ecosyste.ms/docs/services/data-services/repositories/).
- [Wikidata MediaWiki API](https://www.wikidata.org/w/api.php).
- [OpenAlex topics API](https://help.openalex.org/data/topics/).

For all imported candidate records: `authority=navigation_candidate_only`, `evidence_layer=null`, `promotion_authorized=false`, and where applicable `outcomes_verified=false`. External metadata is untrusted. No rights to rehost full papers, scrape protected sites, or transfer copyrighted materials are inferred.

## Approval gate for any later feature

Before proposing a substantive new feature, record: (i) the user problem and real decision being improved; (ii) closest existing tool/platform in the registry; (iii) why integration fails or would be insufficient; (iv) same-model/equivalent-access assistant baseline; (v) proposed task metric and acceptance threshold; (vi) permission/privacy/licensing constraints; and (vii) a low-cost stopping rule. **No major new feature by default** until it demonstrably improves independent task performance, reliability or economically meaningful usefulness.

Specifically for Cite–Refinery: prioritize **substantiated cross-source discrepancies** (e.g., intervention claims whose evidence only supports process coverage) over graph node counts, publication coverage or UI polish. If mapped relationships cannot beat an equivalently equipped assistant in reproducible blinded assessment, retain the ingestion/provenance/permission machinery as Research Drive/Refinery services and stop standalone product expansion.

## Validation notes

- Unit tests cover provider normalization, type/URL validation, failure classification, non-promotion flags and documented freeze receipt.
- Real OpenAIRE and ecosyste.ms metadata endpoints responded in a bounded Optiplex smoke check. This does **not** validate scientific or project outcomes.
- The corpus and model holdout remain entirely separate from discovery lead results.
- Draft, unmerged and undeployed; independent annotator and user-utility results are still absent.
