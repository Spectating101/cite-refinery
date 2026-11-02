# Real financial/academic PDF operator pilot — 3 November 2026

**Decision: HOLD.** This is an empirical stress test on original public documents, not a statement that either parser is correct or safe for automatic data ingestion. Independent fixture tests already exist in acceptance #002; this pilot extends them to real publisher PDFs using the existing Research Drive parser paths.

Five different official/public PDFs were downloaded to a private temporary working directory, identified by source URL and original-file SHA-256, and evaluated on two explicitly selected physical pages each. Files were never committed. The exact source IDs, hashes, chosen pages, timing, return statuses and counts are in `examples/discovery/real_pdf_operator_pilot_20261103.json`.

| Public source | Native pdfplumber tables | Optional img2table 2.0.0 | Result |
|---|---:|---:|---|
| BIS Bulletin 106 — private credit | 6 | 1 | Both executed; native largely chart grids |
| BIS Bulletin 116 — NBFIs | 6 | 3 | Both executed; substantial chart false-positive risk |
| BIS Bulletin 138 — chokepoints | 6 | failed | Upstream `PdfOCR.of` strict `zip()` length mismatch |
| arXiv 2604.12047 — financial PDF parsing | 5 | failed | Upstream `PdfOCR.of` strict `zip()` length mismatch |
| arXiv 2506.05182 — multi-structured finance docs | 9 | failed | Candidate correctly rejected empty/inverted cell geometry |

The optional parser completed **2/5** selected-page evaluations, with one to three candidate regions. This is not 2/5 accuracy. The native helper returned many graph regions as tables; it completed **5/5 execution attempts**, not 5/5 correct data extraction. Both engines remain `NOT_SEMANTICALLY_VERIFIED`.

## Pipeline implications

1. **Research Drive:** retain native `recorded_fetch.HELPER.pdf_tables` and its independent `PDFScope`/source evidence path; do not install the optional CV parser into the serving desk. The new `CandidateReviewScope` intentionally cannot be passed directly to `write_evidence_table`. This stops a parser-generated value being promoted as source-confirmed data before review.
2. **Upstream:** the observed `zip(..., strict=True)` failure occurred inside `img2table/document/pdf.py → PdfOCR.of`, not in Research Drive's wrapper. Do not work around it by fabricating or truncating source rows. The geometry failure originated from a deliberately strict wrapper guard; do not weaken the guard without independently validating the affected PDF cells.
3. **Atlas:** record a typed `EXECUTION_ONLY` result. Chart false positives, PDF parser exceptions, and missing operator ground truth must count as abstentions or failures, never as verified wins.
4. **Nocturnal:** separately review its fixed WARC payload hashing and per-observation immutable custody from PR #114; the PDF pilot does not validate web capture correctness.

## What is not yet measured

There are **zero independently adjudicated ground-truth source cells** in this real-document pilot. Table counts, timings and source hashes cannot establish numerical correctness, header continuity, or chart/table distinction. The benchmark is deliberately negative evidence about integration readiness, not a replacement for a ground-truth corpus.

The next acceptance should scope actual data tables, with visual checks of exact cell strings, negative values, footnotes, repeated or missing page headers and per-cell abstention. Require meaningful successful source-cell review against 5–10 documents **before** any move toward production. Even then, the checker must independently reparse approved original bytes rather than treating the optional parser's hypothesis as authority.
