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

## Repeated holdout on the post-verification bridge branch

The same five original BIS/arXiv public files and original SHA-256 digests were replayed with the current Research Drive optional extraction path, keeping the same two selected physical pages per source. The isolated word/period verifier never runs if extraction itself errors. The result remained **2/5 successful parser executions, 3/5 parser exceptions**: two upstream strict-zip text-alignment errors and one deliberately rejected invalid cell geometry. Full source bytes were not committed and no developer patched away upstream errors.

A new [sanitized heterogeneous regression receipt](../examples/discovery/heterogeneous_pdf_regression_replay_20261103.json) records each original source hash, page selection, status, exception and local execution time. This is a repeat run on the **same** five sources, not five additional independent documents; it does **not** expand the corpus denominator or establish semantic accuracy of successful candidates. The release decision remains **HOLD**.

## Page-specific candidate recovery (unapproved, not a fixed parser)

A new optional Research Drive `--allow-partial` mode uses the existing img2table parser **once per selected original physical page**, preserving exact original SHA/page IDs, instead of requiring a successful extraction across all selected pages together. Replaying the *same* five BIS/arXiv PDFs produced **7 successfully processed pages out of 10 requested, with proposed tables on 6 pages**, with all **three failed pages** explicitly identified, and at least one unapproved candidate page in each of the five documents. Only **two documents** have complete requested-page coverage; **131 total candidate cells** are unvalidated. The selected strict-mode benchmark remains 2/5 complete-document executions. This is an increase in recoverable candidate-page coverage, **not** a semantic accuracy or table-precision claim. Source rows from failed pages remain entirely absent (not zero-valued).

See the independently rerunnable [`interop_partial_page_acceptance.py`](../scripts/interop_partial_page_acceptance.py) and [pinned real-file result](../examples/discovery/heterogeneous_partial_page_acceptance_20261103.json). The three failures are upstream text alignment on BIS 138 page 6 and arXiv 2604 page 9, and invalid cell geometry on arXiv 2506 page 6. Unsupported/unknown exceptions remain strict failures. HOLD publication.

## Recovered candidates are not source truths — original-page cell audit

Manual visual inspection exposed a **different** source-quality failure after page-level extraction was made recoverable. Some BIS table hypotheses consisted of chart axes and legends; another arXiv results block contained multiple observations fused into one parser row. The new Research Drive conservative `optional_pdf_layout_audit` only identifies single-line text labels paired with atomic decimal/currency values in explicitly selected candidate columns. It never grants `PDFScope` or issuer-origin authority.

The same **five** PDF originals yielded seven proposed table regions with **33 candidate rows** (from 131 proposed parser cells). **25 rows abstained by structural shape; eight progressed only to original-source review.** The eight reviewable rows were in a Manulife financial fact-sheet example reproduced as *Figure 5 on physical page 11 of arxiv2506*. Eight operator-transcribed printed values and the `1Q24` header were checked against the paper's original PDF word locations: **6/8 independently matched; 2 abstained** because the parser merged spaces in the `New business` labels. This is not new primary data: the academic PDF reproduces an issuer fact sheet and **is not the issuer's original filing**. No publisher-issued original hash, external second reviewer or trusted dataset approval was established.

The [replay script](../scripts/heterogeneous_source_cell_acceptance.py), [manual original-page oracle](../examples/discovery/heterogeneous_original_source_cell_oracle_20261103.json) and [sanitized acceptance receipt](../examples/discovery/heterogeneous_source_cell_quality_20261103.json) preserve these separate denominations: 131 *parser cells*, 33 *candidate rows*, eight *shape candidates*, six *source-word matches*, zero *trusted issuer values*. Neither figure/legend artifacts nor flattened multiline cells should be counted as successful observation extraction. Release gate stays HOLD.

## Reconciliation to the issuer's EDGAR original exhibits

The reproduced Manulife source cells have now been manually mapped and independently verified against locally SHA-pinned issuer-authored **SEC EDGAR HTML Exhibit 99.1** originals, not Manulife's inaccessible primary PDF. The 2024 first-quarter shareholder-report source matched all 8 checked issuer rows and units; the issuer's separate earnings release matched 7 overlapping values; and the reported general-expenses qualifier C$1,102 million matched the total-expenses C$1,679 million context. Explicit unit arithmetic confirms C$1,883 million APE sales rounds to C$1.9 billion in the reproduction. This adds original issuer filing evidence but **does not repair** the original arXiv PDF parser's two whitespace-fused label errors, supply a second human reviewer, or authorize dataset publication. See `FINANCIAL_SOURCE_CELL_ACCEPTANCE_20261103.md` and the new issuer oracle/receipt. The earlier three failed heterogeneous pages are still failures; HOLD.


## Three previously failing pages — operator-cropped native fallback

All three original failed physical pages were rendered and inspected. BIS 138 p6 is a **Graph 3 chart-only negative control**, not an observation table. arXiv 2506 p6 and arXiv 2604 p9 have real tables. Rather than change img2table's strict PDFium/geometry errors, Research Drive now reuses its native pdfplumber parser within **manually declared original-PDF crop bounds** and performs separate original-word/geometry checks on chosen cells. The old img2table errors still reproduce on every page.

On the exact SHA-pinned original pages, the Table 2 cost-comparison crop yielded **4/4** selected printed label/value/header source matches; the Table 12 LLM-results crop yielded **4/4**. The two cropped grids contain **135 unverified candidate cells**, not 135 accepted observations. This is an operator-selected **8-cell source-location acceptance**, not default parser repair, independent semantic adjudication or trusted data. See the [operator oracle](../examples/discovery/operator_cropped_failed_pdf_pages_20261103.json), [replay](../scripts/failed_page_native_crop_acceptance.py) and [sanitized receipt](../examples/discovery/failed_page_native_crop_acceptance_20261103.json). The original five-document corpus denominator remains unchanged and the release decision remains **HOLD**.
