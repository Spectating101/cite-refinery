# Cite-Refinery external engines v1 — adopt, don't replace

This branch adds **working integration boundaries** for public research tools to Cite-Refinery's existing `cite_refinery.semantic_graph.v1` format. It deliberately does **not** replace the three-layer semantic graph or automatically promote external research output into accepted findings. It is an independent branch based on `origin/main` so the separate breadth-expansion branch can continue.

## What is implemented

| External project | Connection | Verified in this branch | Not yet verified |
| --- | --- | --- | --- |
| **PyAlex / OpenAlex** (MIT) | Actual `pyalex.Works().search().get()` call; normalized candidate bibliography with abstracts and DOI; CLI `openalex` supports neutral source-packet staging | PyAlex installed in isolated environment; fake-client contract and staging/import tests passed | Live anonymous OpenAlex returned HTTP **429**; free `OPENALEX_API_KEY` needed for dependable search |
| **Docling** (MIT) | Local-file `DocumentConverter.convert()` and `export_to_markdown()` with SHA-256 provenance and extraction boundary | Converter interface exercised with a fake; local-file safety test | Real Docling pip installation initially failed downloading the ~555 MB PyTorch dependency; full converter runtime is *not* counted as validated until actual conversion succeeds |
| **PaperQA2** (Apache 2.0) | Actual `pqa ask` subprocess interface in an explicit local paper directory, no shell interpolation, bounded timeout, unaccepted answer status | CLI argv and failure modes tested with an executable stand-in | `paper-qa` not installed on baseline; needs configured model/embedding provider, PDF corpus and citation verification |
| **LightRAG** (MIT) | Async `rag.ainsert()` / `rag.aquery(..., QueryParam(mode='hybrid'))` adapter for configured instance; parses JSON, rejects unknown modules/sources and strong relation assertions | Async protocol tested with fake configured engine, rejected 3 invalid proposals | No configured real LLM + embeddings + LightRAG instance used here, no empirical discovery accuracy claim |
| **ExecutableClaims** (MIT) | Loopback-only `POST /api/v1/analyze`, optionally `GET /api/v1/analysis/{id}`; explicitly `generate_capsules=false` | Actual route/payload and no code-execution contract tested with fake HTTP client | External backend not running in test; labels returned by service are not accepted in graph |
| **GROBID** (Apache 2.0) | Loopback-only `POST /api/processFulltextDocument`; accepts only local PDFs and returns TEI XML | Upload/form/response shape tested with fake HTTP client | GROBID Java service not started; no scientific PDF parsed through actual GROBID server yet |
| **Python PROV** (MIT) | Real W3C PROV JSON entity/wasDerivedFrom lineage; packet -> portable provenance | Library installed, full 213-node graph exported to 80 KB PROV JSON, provenance tests pass | External provenance consumers not tested |
| **Cytoscape.js** (MIT) | Pinned **v3.30.4** vendored minified JS + license; generated **offline** graph explorer with search, layer filters, edge style and provenance/source inspector | Generated 213-node/206-edge page; **real headless Chrome rendered three graph canvases and `data-graph-ready=true`** | Frontend perf with huge graphs/mobile usability not benchmarked |

**Not copied/replaced:** Graphiti/Cognee/GraphRAG are alternative graph infrastructure, not needed to implement these adapters. GROBID and ExecutableClaims are service integrations, not vendored code. Do not conflate adapter existence with installing every large runtime.

## Install only what you need

The default Cite-Refinery package retains **zero** mandatory dependencies. Install optional extras in isolated environments:

```bash
python -m pip install -e '.[openalex,provenance,services]'
# heavy engines, separately as needed:
python -m pip install -e '.[documents]'
python -m pip install -e '.[paperqa]'
python -m pip install -e '.[lightrag]'
```

The separate packages may bring large transitive dependencies and require model weights, API keys or their own services. Docling can reuse an existing compatible PyTorch environment but full model/format support must be smoke-tested locally. OpenAlex publishes a free API key and its API rate limits; supply via `OPENALEX_API_KEY`, never commit keys.

## End-to-end staging commands

```bash
# Installed/available engines in current interpreter:
cite-refinery-external engines

# Academic *source leads*, NOT verified Academic claims:
export OPENALEX_API_KEY=...  # user-managed; do not commit
cite-refinery-external openalex 'hydrological observing gaps' --limit 8 \
  --module-id WA-06 --module-title 'Hydrological observation gaps' \
  --output /tmp/wa06-leads.json

# Local (not URL) PDF document extraction:
cite-refinery-external docling /absolute/path/to/paper.pdf --output /tmp/paper-extraction.json

# A PaperQA2 answer draft from a local PDF directory:
cite-refinery-external paperqa /absolute/path/to/papers \
  'What observation bias affects free-roaming dog population estimates?' \
  --output /tmp/draft-answer.json

# GROBID TEI from your own loopback service:
cite-refinery-external grobid /absolute/path/to/paper.pdf \
  --endpoint http://127.0.0.1:8070 --output /tmp/tei-result.json

# ExecutableClaims analysis through your own loopback service:
cite-refinery-external claims 'Population density decreases by 20 percent.' \
  --endpoint http://127.0.0.1:8000 --fetch-result \
  --output /tmp/candidate-claim-assessment.json

# Existing semantic packet -> W3C PROV:
cite-refinery-external prov examples/free_roaming_dog_semantic_pilot.json \
  --output /tmp/refinery-provenance.json

# Offline graph explorer using pinned Cytoscape:
cite-refinery-external explore examples/free_roaming_dog_semantic_pilot.json \
  /tmp/refinery-graph-explorer
# open /tmp/refinery-graph-explorer/index.html locally
```

OpenAlex staged source leads are emitted as neutral `source` nodes joined by `DISCOVERED_FOR` *candidate* edges; they cannot satisfy the graph's Academic lane until somebody checks a specific passage/claim.

### LightRAG, programmatic adapter

Use an **already configured** `LightRAG` instance with working LLM and embedding functions (its own docs detail async initialization). Cite-Refinery does not quietly choose an LLM provider or submit sensitive data:

```python
from lightrag import QueryParam
from cite_refinery.external_engines import lightrag_propose
from cite_refinery.external_packets import relation_proposal_packet

result = await lightrag_propose(
    configured_rag,
    source_text=reviewed_source_text,
    module_ids={"WA-06", "FS-03"},
    source_refs={"https://wmo.int/activities/hydrosos"},
    query_param=QueryParam(mode="hybrid"),
)
candidate_packet = relation_proposal_packet(
    {"WA-06": "Hydrological observations", "FS-03": "Climate-resilient production"},
    result["proposals"],
)
# Import candidate_packet into a *new review workspace* only.
```

You can also stage previously exported `module_titles.json` and `proposals.json` with:

```bash
cite-refinery-external relations module_titles.json proposals.json \
  --output /tmp/relation-proposal-packet.json
```

The generated candidate packet is **not** the same as authority promotion. Even references in the `source_refs` allowlist may be about the topic rather than directly supporting the proposed edge.

## Browser / security boundaries

- Cytoscape.js is pinned and bundled with the upstream MIT license; **offline export**, no CDN, no external JS, no network fetch and no bearer-token capture. Source statements render using DOM `textContent`, and embedded JSON escapes HTML-significant characters.
- GROBID and ExecutableClaims endpoints require explicit loopback HTTP addresses, not arbitrary public domains; document adapters never fetch a URL from source contents.
- PaperQA2 invocation uses an argument list and no shell; prompt, parser output and citations are untrusted research drafts.
- LightRAG may generate candidate relationships only, requires exact known module identifiers and existing source refs, and rejects unsupported strong relation verbs.
- PROV records source-to-node **derivation**, not semantic truth, causality or effective interventions.
- The new modules do not change accepted research, production API permissions, Nocturnal bridges, existing schemas or UI defaults.

## Tests and current status

```bash
PYTHONPATH=src:. python3 -m unittest discover -s tests -p 'test_external_*.py' -v
PYTHONPATH=src:. python3 -m unittest discover -s tests -q
```

Contract tests cover data and source restrictions, no shell injection, local services only, neutral source-lead staging, idempotent candidate graph ingestion, provenance exports and HTML injection protection. Runtime checks additionally exercise PyAlex/PROV optional installations and Chromium offline explorer rendering.

**Acceptance criteria for the next phase:** run Docling on a real PDF, PaperQA2 and LightRAG on a review-safe corpus with explicitly configured models, and an ExecutableClaims backend against the same scientific assertions. Blind candidate-relations review should then compare against existing semantic edges without leaking gold labels, scoring output quality rather than node count. No comparative performance improvement is claimed by this branch.
