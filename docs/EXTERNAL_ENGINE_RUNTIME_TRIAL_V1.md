# Cite-Refinery external-engine real-runtime trial — 2026-10-20

This is a **measured follow-up** to draft PR #51's adapter integration. The trial runs on an authorized Linux computer, on a separate branch; the ongoing field research and all accepted graph state remain untouched.

## Bottom line

| System | Real execution | Observation | Assessment |
|---|---|---|---|
| **Docling 2.70.0** | **Yes, actual PDF** | Parsed an existing one-page German electricity-sector financial PDF into 24,918 Markdown characters. A second parser (PyMuPDF) found 594 multi-character numerical tokens; all 594 appeared somewhere in Docling's output. | Promising numerical **retention proxy**; **not** evidence of correct cell values, row alignment or scientific extraction quality. OCR/table-model disabled. |
| **WMO official page retrieval** | **Yes, live public pages** | Parsed directly from official WMO HydroSOS and Early Warnings for All pages, saved URL and SHA-256 fingerprints. | Verifiable quote-level source input; WMO explicitly says HydroSOS supports Early Warnings for All **for hydrological disasters**. |
| **Ollama llama3.2:3b, closed-book** | **Yes** | The model abstained from giving explicit yes/no on both two-point questions. | Low decision coverage; not an evidence reliability test. |
| **Ollama llama3.2:3b, source-grounded** | **Yes** | Correctly said no verified local mortality impact was established; **incorrectly denied the literally explicit HydroSOS ↔ EW4All hydrological-disasters connection**. 1/2 expected binary classifications. | **Not reliable as autonomous semantic evidence judge.** Passing a source URL or even quoted context did not prevent an obvious misreading. |
| **LightRAG 1.5.7 + Ollama llama3.2:3b + offline MiniLM embeddings** | **Attempted real runtime** | Initialized real LightRAG storages, queued official WMO source text, started graph extraction, attempted embedding; did **not** complete indexing/query within a 200-second configured bound and still ran past 345 seconds. The isolated trial process was terminated; Ollama server left running. | **Failed performance gate.** No semantic graph discovery or retrieval-quality result; **do not** infer any uplift. |
| **PaperQA2** | Not run | LLM/embedding setup would require additional runtime configuration; model constraints exposed here are not solved by its CLI adapter. | No accuracy claim. |

Result file: `research_materials/runtime_trials/external_engine_runtime_trial_20261020.json`.

## The specific discovered failure

From WMO's official page, the relevant short literal fragment is:

> HydroSOS is the backbone supporting the Early Warnings for All initiative for hydrological disasters.

The 3B model's grounded answer nevertheless said that support **for hydrological disasters** was *not explicitly stated*, even though the quoted source says it explicitly.

A new `verify_source_span()` method therefore tests exact source-span inclusion, recording a source SHA-256 digest and a `verbatim_span_present_not_entailment` state; `detect_explicit_link_misread()` flags this narrow explicit-link/negative-answer conflict for manual review. Neither procedure proves broader semantic entailment, causality or intervention effectiveness.

The LightRAG adapter in `external_engines.py` now optionally accepts `source_passages`, requiring **exact, already-known source URLs and model-supplied verbatim excerpts**. Invalid/missing quotes are rejected. Even a passing quote is a **candidate** edge, not `SUPPORTS`, `CAUSES`, `ADDRESSES`, or a promoted graph fact.

CLI quote gate:

```bash
cite-refinery-external audit-span /path/to/source.json \
  'HydroSOS is the backbone supporting the Early Warnings for All initiative for hydrological disasters' \
  --subject HydroSOS --object-name 'Early Warnings for All' \
  --model-decision no
```

`source.json` should contain `{"id":"WMO-HYDROSOS","url":"https://wmo.int/activities/hydrosos","text":"...actual source passage..."}`; source text must be obtained and pinned separately.

## Repeatable trial tools

```bash
# Official live HTML + local Ollama source-grounding trial:
PYTHONPATH=src:. python3 scripts/external_grounding_trial_v1.py \
  --out /tmp/refinery-grounded-test.json

# Docling installed into an isolated environment with compatible existing torch:
PYTHONPATH=src:. python3 scripts/external_docling_pdf_trial_v1.py \
  /absolute/path/to/a-pdf.pdf --out /tmp/refinery-docling-test.json

# Computationally expensive LightRAG attempt; always enforce an external
# hard OS deadline, since asyncio cancellation of workers was not prompt:
timeout -s TERM -k 10s 180s python3 scripts/external_lightrag_live_trial_v1.py \
  --timeout 160 --out /tmp/refinery-lightrag-test.json

# Consolidated report preserving incompleteness:
PYTHONPATH=src:. python3 scripts/external_runtime_trial_summary_v1.py \
  --grounding /tmp/refinery-grounded-test.json \
  --docling /tmp/refinery-docling-test.json \
  --lightrag /tmp/refinery-lightrag-test.json \
  --out /tmp/refinery-runtime-summary.json
```

The attempt used existing Ollama `llama3.2:3b` and locally cached `sentence-transformers/all-MiniLM-L6-v2`, not paid APIs. Docling's original package installation downloaded massive CUDA/Torch dependencies and failed; it was successfully run in a disposable `--system-site-packages` environment with pre-existing torch and selectively installed compatible Docling dependencies. This is a machine-specific workaround, **not** a production installation recommendation.

## Acceptance decisions

- **Keep and expose Docling** as an optional source parser; do not label numerical or table extraction as verified.
- **Keep the W3C PROV and offline Cytoscape path** from PR #51; already independently demonstrated.
- **Treat the local 3B model as insufficient** for evidence-strength judgment. The failure is source semantic interpretation, not mere network availability.
- **Keep LightRAG available only as an opt-in experiment.** Do not default-enable extraction on the currently tested CPU/Ollama setup.
- **Never silently assert edges from an extracted source URL or an exact quote.** Literal quote verification is a *necessary* gate in strict mode, never sufficient.
- **Next meaningful benchmark:** a representative, manually scored sample across fields; a stronger configured model; separate precision of citation-span match, relation-direction/type, semantic entailment and real-world outcome claims; latency and resource use. The original 54-module/62-module research snapshots are not accepted gold labels.

## Validation

Unit tests in `tests/test_external_runtime_trial_v1.py` verify source digest and quote presence, source missingness, model-source contradiction flags, and optional LightRAG quote gating. The end-to-end trial results are empirical observations for **one** local case, not general performance results.
