# Cite-Refinery: blinded claim-support screen + live PaperQA2 trial

**Research stage only · 2026-10-20 · separate branch stacked on draft PR #52.** No accepted graph state, production API, classroom/manual projects, or parallel landscape research artifacts were changed.

## What was tested

We moved from import-contract tests to source-based execution with two independent lanes:

1. **Blinded claim-support screening:** eight deliberately intermixed candidate claims, drawn from four official pages (WMO HydroSOS and WHO rabies, ambient air pollution, drinking water). Four claims reflect explicit, bounded source relationships; four make unsupported quantitative or intervention-effectiveness assertions. Answers live in `gold_labels.json`, not in either LLM prompt. Exact URLs and page/passage SHA-256 values are recorded in `trial_results.json`. This tests whether a model *verifies supplied hypotheses*, **not** autonomous discovery of previously unknown links.
2. **PaperQA2 scholarly retrieval and question answering:** the authentic article *Population Estimation Methods for Free-Ranging Dogs: A Systematic Review* (DOI `10.1371/journal.pone.0144830`, PMCID `PMC4684217`) was acquired from Europe PMC's full-text XML feed. A 38,217-character local text corpus was built in a disposable environment; we store its hash, not a copied full paper. PaperQA2 **2026.8.12** was installed in a separate venv and configured for local, sparse retrieval.

## Measurements—not aspirations

| Test | Observed state | What we may conclude |
| --- | --- | --- |
| Qwen2.5 **7B** long response on the eight support cases | **HTTP read timeout at 230 s**, no completed classifications | No accuracy, precision or recall score. A stronger parameter count didn't yield a usable batch under the shared CPU Ollama workload |
| Qwen2.5 **7B** shorter boolean-JSON screen, same eight cases | **HTTP read timeout at 125 s** | No model comparison score; compacting response wasn't enough under resource contention |
| PaperQA2 local source ingestion | **Succeeded**, 8.63 seconds first indexing call | A peer-reviewed source can be parsed/indexed without a paid model API |
| PaperQA2 **sparse retrieval** from the indexed review | **Succeeded**; three source chunks returned. The new CLI invocation took **0.012 s measured internally** after Python/import startup | Source-grounded candidate passages can be retrieved rapidly; chunk relevance, factual claims and research conclusions still require independent checks |
| Initial PaperQA2 answer attempt | Failed, **Semantic Scholar HTTP 429** | Metadata enrichment is an unnecessary runtime dependency for locally supplied, pinned sources |
| PaperQA2 answer after disabling document metadata enrichment | Indexed successfully; **local Ollama/LiteLLM generation timed out at 125 s** | No citation-grounded answer to evaluate. The source-index path works independently of the LLM inference path |

There was an additional independent index-plus-retrieval smoke that returned three passages in approximately **0.27 s**. Do not mix this with wall-clock Python import startup or count it as an LLM-generated citation answer. The official source QA's earlier 3B error from PR #52 remains unresolved by these timeouts.

## Integration upgrade

`cite_refinery.external_engines.paperqa_retrieve_local()` is now an **actual native PaperQA2 library adapter**, not just a mock contract or a `pqa ask` subprocess:

- Accepts a **local** PDF/text/document, caller-supplied citation and question, and bounded result count.
- Uses PaperQA2's `Docs.aadd` and `Docs.retrieve_texts`, with `Settings(embedding="sparse", parsing=ParsingSettings(use_doc_details=False, multimodal=False))`.
- Explicitly avoids unneeded Semantic Scholar/Crossref enrichment, any OpenAI calls, LLM-generated answers, and source URL fetching in this mode.
- Records local source SHA-256, source chunk IDs, bounded excerpt text and a **review-required** status.
- Does **not** misrepresent source retrieval as an Academic-layer finding. The previous research graph and acceptance-gate invariants remain authoritative.

New CLI:

```bash
cite-refinery-external paperqa-retrieve /absolute/path/to/paper.txt \
  'Which limitations affect free-ranging dog population estimates?' \
  --citation 'Belo et al. 2015 systematic review' \
  --title 'Population Estimation Methods for Free-Ranging Dogs' \
  --doi 10.1371/journal.pone.0144830 \
  --limit 3 --output /tmp/refinery-dog-methods-retrieved.json
```

The full `paper-qa` package is optional and its dependency stack may be large. The new adapter leaves Cite-Refinery's default lightweight installation unchanged.

## Reproduce tests

```bash
PYTHONPATH=src:. python3 -m unittest discover -s tests -p 'test_semantic_holdout_benchmark_v1.py' -v
PYTHONPATH=src:. python3 -m unittest discover -s tests -p 'test_external_paperqa_retrieval_v1.py' -v
PYTHONPATH=src:. python3 -m unittest discover -s tests -q
```

Live model attempts use `scripts/external_semantic_holdout_benchmark_v1.py` and `scripts/external_semantic_binary_screen_v1.py`, with an *external hard timeout* recommended. The direct PaperQA source test is `scripts/external_paperqa_real_trial_v1.py`. Their output is recorded in `research_materials/runtime_trials/holdout_20261020/trial_results.json`. No code auto-promotes outputs to accepted graph edges.

## Gate / next decision

**Enable native PaperQA2 sparse retrieval behind an optional dependency, but do not enable its local agentic answer stage or LightRAG/Ollama 7B batch by default.** The verified constraint is machine-level model throughput and shared workload contention, not lack of useful document parsing or evidence retrieval.

For scientifically meaningful comparative evidence: use an inference backend with predictable latency (isolated GPU or a configured model provider), run the *same pinned blind cases* across engines, compare classification, quote accuracy, relation direction/type, outcome overclaims, refusal/coverage, costs and wall-clock latency, and only then consider authorizing supervised graph edge proposals. None of this trial establishes general model accuracy, intervention effectiveness or autonomous knowledge discovery.
