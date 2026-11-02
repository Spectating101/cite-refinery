# Atlas interoperability benchmark 001 — real external execution

**Execution date:** 2026-11-02 (Asia/Taipei)
**Host:** Optiplex, Python 3.13.5, isolated virtual environment with system-site packages; no existing source-project dependency manifests modified
**Owner:** Atlas comparative evidence only; source-project owners retain admission authority
**Depends on:** #140 (typed discovery mapping); no merges or deployment

## Decision question

Can external capabilities found through Atlas do a task we actually need, on comparable fixed inputs, rather than merely describing compatible functions in upstream READMEs?

We tested (1) public PDF table extraction against source-checked **row + header + cell** ground truth, and (2) Nocturnal's existing native WARC writer against an independent archival reader, pywb indexing and replay.

**Do not interpret this as a full production benchmark.** Neither real user documents nor a live investigatory source was used; there was no source repo deployment, migration or change.

## PDF: extraction and cell evidence

Source fixtures and oracle: [LydiaTools/pdf-table-traps](https://github.com/LydiaTools/pdf-table-traps), pinned **`c63aab8884671aa4c789f08d0891f1a3f0ee5f5d`** (MIT). Three upstream-original PDFs and rules:
- `ruled.pdf`: three specific row/header/value assertions + table count.
- `borderless.pdf`: wrapped-row, borderless table with three price assertions + table count.
- `prose.pdf`: expected zero tables (false-positive negative control).

The independently maintained `table_traps check --format tables-json` evaluates each extractor's **unaltered string cells**. Missing or ambiguous values are `unknown`, not passes. No OCR, prompts, post-hoc cell repairs or extraction tuning beyond a disclosed mode selection.

| Engine + selected configuration | Pass | Fail | Unknown | Sum of extraction times, ms |
| --- | ---: | ---: | ---: | ---: |
| **img2table 2.0.0, borderless_tables=True** | **9** | **0** | **0** | 1276.8 |
| pdfplumber 0.11.9, extract_tables defaults | 5 | 1 | 3 | 115.2 |
| PyMuPDF 1.28.2, find_tables defaults | 5 | 1 | 3 | 123.1 |
| Camelot 1.0.9, lattice | 5 | 1 | 3 | 1440.7 |
| img2table 2.0.0, borderless_tables=False | 5 | 1 | 3 | 763.1 |
| Camelot 1.0.9, stream | 2 | 1 | 6 | 713.1 |

The three cases contain nine total checks. Every engine configuration used the same upstream source PDF and keyed-cell assertions. The time measurements include imports/first use within this single run, so are **comparative observations, not stabilized throughput or cost claims**.

Per-fixture:
- `img2table borderless`: **pass/pass/pass** (ruled/borderless/prose).
- `pdfplumber`, `PyMuPDF`, Camelot lattice, img2table ruled: **pass/fail/pass**; borderless table not extracted (one count failure, three unknown cells).
- Camelot stream: **unknown/unknown/fail**; falsely extracted a table from prose.

**Significant distinction:** An extractor yielding all digits somewhere in a file is not passing keyed original-cell validation. In this three-fixture trial, img2table's borderless mode was the only configuration to satisfy every supplied oracle check.

### Harness re-run and error correction

The first benchmark returned the published 9/9 for img2table borderless. A subsequent strict input-normalization revision temporarily produced **5/9** because the *harness*, not the engine, treated nullable DataFrame `NaN` placeholders as forbidden numeric conversions and replaced the complete table with an empty result. This was diagnosed by comparing unchanged original PDF hashes and the raw extracted table JSON. The harness was repaired to convert **only missing NaN values** to empty cells while still rejecting genuine numeric cell values that would erase the original formatting.

The final repeat against the unchanged upstream fixtures returned **9/9** again. There is a focused offline regression test for this exact NaN/null distinction. This is an honest benchmark-harness incident, not evidence that img2table randomly fails.

## Research Drive native baseline

A separate **live call** to the existing Research Drive function `prove_query_smoke` on `ruled.pdf`, using `backend: local_file`, returned:

    {"ok":false, "error":"metadata_only_backend", "rows":0,
     "revision_id":"rev_benchmark_fixture"}

This is correct conservative behavior for a data-acquisition/query path that has no approved structured PDF table reader. Accordingly **there was no verified native Research Drive PDF parsing engine to compare**. The external tools were compared with other external/generic local parsers. This is a potential *new bounded extraction capability*, not a claim that Research Drive's existing parser was beaten.

## Nocturnal: native WARC interoperability

Nocturnal already implements `EvidenceCustodyAdapter` with a native `EvidenceArchiver.write_warc_snapshot` and an **optional ArchiveBox CLI** integration. The benchmark imported those unmodified native modules from the operator's local read-only checkout, and injected one synthetic HTML source at an intentionally non-resolving `example.invalid` URL. ArchiveBox and Wayback lookups were disabled. No external website was fetched.

1. Native Nocturnal custody wrote a compressed WARC response artifact (**520 bytes**, native execution **22.3 ms**).
2. Independent [warcio](https://github.com/webrecorder/warcio) **1.8.2** parsed the actual HTTP/WARC response. Record type `response`, target URL, status `200`, exact HTML payload and declared SHA-256 all matched.
3. Independent [pywb](https://github.com/webrecorder/pywb) **2.11.0** successfully indexed that *same* WARC in its own temporary archive collection (observed indexing time **1203.7 ms**).
4. A pywb server bound to **127.0.0.1 only**, with **no live-web recording**, replayed the archive with HTTP **200**; its returned payload SHA-256 exactly matched the original fixture. The local process was terminated after validation.
5. Existing independent Nocturnal interop tests: **9 passed** (two local test modules). External PDF Table Traps tests: **16 passed** (original upstream tests).

This establishes native compressed WARC → independent indexer → offline archive replay **for one simple synthetic HTML fixture**. It does **not** demonstrate robust capture of social media, JavaScript-heavy sites, authentication, revision evidence, missing pages, permissions or editorial validity.

## License and operating considerations

- img2table 2.0.0: MIT. The PDF Table Traps fixture/checker: MIT.
- Camelot 1.0.9: PyPI package reports MIT; legacy `atlanhq/camelot` GitHub listing does not itself assert an SPDX identifier.
- pywb 2.11.0: GPL-3.0 source-repository listing (package reports GPL). **Review licensing/compliance before distributing a combined application**; standalone operator-local evaluation is not automatic distribution approval.
- PyMuPDF has a dual AGPL/commercial licensing model; any packaged reuse requires separate review.
- Third-party components were installed only in `/tmp/atlas-interop-bench-20261102/venv`; native source repositories, releases and project lockfiles were not modified.
- Initial attempt to install old pywb 2.9.1 failed under Python 3.13; the later compatible 2.11.0 installed. This is a nontrivial compatibility/maintenance observation, not a runtime correctness finding.
- The Nocturnal runner uses the module present at inspected local Nocturnal commit `d7f914f6e3b57f6cc65c827de868c284673b8876`; this may differ from latest GitHub main or work-in-progress feature branches. Exact source commit should be pinned in future repeated tests.

## Decisions (not merges)

**Research Drive:** `BENCHMARK_SUPPORTED_CANDIDATE` for **img2table 2.0.0 configured with `borderless_tables=True`**, limited to these digitally readable, source-checked PDFs. Next: isolated optional extractor feeding immutable originals + independent keyed-cell validation; benchmark against real permitted financial/academic PDFs; reject silent format normalization and broad claims of OCR coverage.

**Nocturnal:** `NATIVE_REUSE_CONFIRMED_FOR_SYNTHETIC_WARC`. Retain its existing WARC writer and capture/custody receipts. `pywb` is an optional **archive replay** component if investigators need historical render, not a replacement capture system or a reason to build another archiver.

**Atlas:** `BENCHMARK_RECEIPT` may be linked to a **typed candidate edge** only with exact fixture, source/version, mode, correctness measurements, limits and an owner review. It is not an automatic VERIFIED or ADOPT promotion.

## Reproduction (operator-authorized machine only)

Use a private scratch dir; clone the MIT fixture repository at the exact commit and set up external packages in an isolated virtual environment.

    python3 -m venv --system-site-packages /tmp/atlas-interop-bench/venv
    /tmp/atlas-interop-bench/venv/bin/python -m pip install 'pdfplumber==0.11.9' 'camelot-py==1.0.9' 'img2table==2.0.0' 'pywb==2.11.0' 'warcio==1.8.2'

    /tmp/atlas-interop-bench/venv/bin/python scripts/interop_pdf_benchmark.py \
      --fixture-root /tmp/atlas-interop-bench/pdf-table-traps \
      --out /tmp/atlas-interop-bench/pdf-results

    /tmp/atlas-interop-bench/venv/bin/python scripts/interop_warc_benchmark.py \
      --nocturnal-repo /path/to/authorized/nocturnal-oversight-checkout \
      --out /tmp/atlas-interop-bench/nocturnal-results

The runner refuses existing output dirs; keep raw cell extraction and source metadata locally, not in the public PR. A synthetic offline CI test validates the benchmark runner's result contracts without needing private repos, Internet access or those optional packages.

### Limit of conclusion

The user asked to validate tool interoperability. These tests do so on **actual native Nocturnal code + independently maintained open-source tools and fixtures**. The PDF results concern proposed additions to a currently metadata-only Research Drive PDF query path. Broader performance, cross-project use and independent generalization remain unverified.
