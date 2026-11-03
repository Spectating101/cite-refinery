# Financial source-cell accuracy gate — 3 November 2026

**Decision: retain optional img2table as an operator-assisted experimental candidate; no default ingestion or trusted data export.** This is a source-backed comparison of two **existing** Research Drive functions, not another PDF parser or new table-custody system.

## Corpus and chain of evidence

Five distinct public primary-source earnings PDFs from **three publishers** (Apple, Alphabet, Amazon) were retrieved over HTTPS. Their exact original PDF SHA-256 digests, publisher links, source page IDs and approved operator column maps are pinned in [`operator_reviewed_financial_cells_20261103.json`](../examples/discovery/operator_reviewed_financial_cells_20261103.json). No source PDF bytes are committed.

A single reviewer visually read full rendered original PDF pages (not the parser result) and transcribed **eight defined source cells per document, 40 total**. These pages contain comparative reporting-period columns, parenthesized negative numbers, quarterly/year-to-date values, footnotes and repeated numerical totals. No second independent reviewer or blinded random sampling was performed. Human inspection time was not measured and must not be fabricated.

This follow-up uses the five new documents **in addition to** the five-document BIS/arXiv execution stress test in [`REAL_PDF_OPERATOR_PILOT_20261103.md`](REAL_PDF_OPERATOR_PILOT_20261103.md); those earlier documents were not cell-adjudicated and must not be mixed into the 40-cell denominator.

### Verification rule

The benchmark runs Research Drive's existing `recorded_fetch.HELPER.pdf_tables` (pdfplumber) and `optional_pdf_candidates.extract_candidates` (img2table 2.0.0). The checker is a **comparison harness**, not a trusted Research Drive PDF verifier.

- Exact SHA-256 of the original source PDF must match the manually reviewed oracle before parsing.
- Each expected value is pinned to a physical 1-based page, visually inspected table, exact row label, and period key. Table indices and period-column indices are **explicit operator-scoped declarations for each source and engine**, never inferred or silently repaired.
- A successful match requires **two atomic parser cells** on the same row: a separate unique source label and the expected period's numeric value. Recognizing a number anywhere in a page, embedding several values in one cell, or matching across rows does **not** pass.
- The numeric string preserves grouped thousands, parentheses, minus, decimals and trailing zero precision. Only whitespace and visual currency markers are removed. Wrong associated values are counted as wrong; unresolved/duplicate/flattened rows or missing column mappings abstain.
- The independent original-source checker that protects Research Drive's trusted CSV lane was **not** invoked for optional parser results. All 40 matches remain reviewed parser candidates, not verified published datasets.

## Measured result

| Publisher PDF | Target cells | Native exact | Native abstain | Optional exact | Optional abstain |
|---|---:|---:|---:|---:|---:|
| Apple FY25 Q1 | 8 | 8 | 0 | 8 | 0 |
| Apple FY25 Q4 | 8 | 8 | 0 | 8 | 0 |
| Alphabet 2025 Q2 | 8 | 0 | 8 | 8 | 0 |
| Alphabet 2025 Q3 | 8 | 0 | 8 | 8 | 0 |
| Amazon 2026 Q3 | 8 | 0 | 8 | 8 | 0 |
| **Total** | **40** | **16** | **24** | **40** | **0** |

Both engines completed all five selected-page executions. No wrong associated value was detected among these targets. The native engine frequently returns an entire Alphabet/Amazon financial row as **one concatenated cell**, with the label and multiple period numbers merged. Those 24 values are correctly classified as *not independently period-associated*, even if their numbers appear as readable text. The optional engine separated the label and period values correctly in this tightly scoped corpus.

Mean end-to-end per-document local execution: **native 0.233 seconds, optional 3.245 seconds**, on this single Optiplex host; execution timings are indicative and exclude manual inspection, network fetch and deployment overhead. This is a performance tradeoff, not statistical evidence of general throughput.

## Why this does not overturn the earlier HOLD

The first real-PDF stress pilot had **three img2table failures out of five document attempts** (two upstream PDF text/geometry `zip(..., strict=True)` errors and one rejected invalid bounding box). The present corpus deliberately selects structured public earnings reports with a single known target table/page for source-cell checks. Both results can be true: **excellent extraction on known financial statements and unreliable execution on a broader sample**.

The 40/40 figure does not measure unknown-table detection, page-header continuation, false-positive chart detection, scanned PDF recovery, all-cell recall, random corpus generalization, or blind reviewer agreement. It also does not authorize a model to assert provenance from a parser-generated cell; the existing Research Drive native independent checker must independently verify approved data sources before any trusted output. Under this corpus, the native checker cannot verify many optional cells without an independently reviewed alternative verification route. Do not bypass that checker.

## Reproducibility (local, authorized original PDFs only)

```bash
PYTHONPATH=src:. /path/to/isolated/bin/python scripts/financial_source_cell_acceptance.py \
  --oracle examples/discovery/operator_reviewed_financial_cells_20261103.json \
  --pdf-dir /path/to/original/pdfs \
  --research-drive-root /path/to/research-drive-private \
  --output /private/immutable/financial-cell-replay.json
```

The script fails on missing/mismatched original source hashes, refuses overwriting a receipt and calls the actual Research Drive helpers. A synthetic offline test suite verifies that a wrong row, a swapped period, a flattened value, a duplicate row and falsely numeric text cannot be promoted as an exact source cell. Output and the 40 individual outcomes are retained in [`financial_source_cell_acceptance_20261103.json`](../examples/discovery/financial_source_cell_acceptance_20261103.json).

**Next release gate:** a second person independently adjudicates the same cells and a holdout with 5–10 additional document/layout classes (including negative controls), followed by a custody-compatible independent recheck of optional cells against original PDF bytes and physical word/geometry evidence. Only then consider a restricted, operator-approved route. No merge, production activation, public dataset publication or private-source use is implied.

## Independent original-word/geometry verification bridge

A follow-up Research Drive source module, `optional_pdf_source_check.py`, now **reuses Research Drive's pre-existing `cell_evidence.pdf_words`** to independently reopen original source bytes and confirm selected label/value/header PDF words against the candidate's 200-DPI pixel geometry projected onto original PDF points. It rejects invalid/missing geometry, cropped or rotated pages, changed source hashes and misaligned original-word associations, but cannot certify the semantic meaning of multi-level period headers without an additional operator decision.

Atlas's executable wrapper [`scripts/interop_original_word_acceptance.py`](../scripts/interop_original_word_acceptance.py) replays the same five pinned company PDFs through **both** Research Drive functions and emits sanitized findings in [`original_pdf_word_witness_20261103.json`](../examples/discovery/original_pdf_word_witness_20261103.json). Result: **40 of 40 specifically selected cells obtained original-PDF label, number and selected header word witnesses; 0 abstentions on those selected cells**. All six comparison flags passed for each. These counts supplement, but do not upgrade, the earlier single-reviewer manually read cell checks. Original source bytes and fuller word excerpts remain in private local custody, not this Git repository.

This is still **review-only original-word evidence**, not the trusted Research Drive independent PDF-to-CSV checker. The checker's output never becomes a `PDFScope`, never calls `write_evidence_table`, and cannot authorize procurement, publication or dataset registration. The original BIS/arXiv extraction failures are retained. Further acceptance needs multilevel header/footnote interpretation, double adjudication, and an independently controlled trust transition before approval.

Replay (authorized local original PDFs and isolated `img2table==2.0.0` environment):

```bash
PYTHONPATH=src:. python scripts/interop_original_word_acceptance.py \
  --oracle examples/discovery/operator_reviewed_financial_cells_20261103.json \
  --pdf-dir /private/originals \
  --research-drive-root /local/research-drive-private \
  --out /private/new_word_witness.json
```

## Distinct reporting-period group and calendar-date evidence

The follow-up original-source checker `optional_pdf_period_check.verify_candidate_period_context` reuses the existing Research Drive `verify_candidate_words` verification and `pdf_words` source geometry. It additionally requires an **operator-declared, physically bounded reporting-period heading and date** from the original PDF, checks their literal text in original-source word coordinates, and checks group ownership of the selected numerical column and vertical ordering of heading/date/year/value. This matters when the same literal `2025` year appears in multiple columns belonging to **Three Months Ended** versus **Twelve Months Ended**, or when an Amazon quarter column and a nine-month column share `2026`.

Five real Apple/Alphabet/Amazon company PDFs were replayed against the independently sourced heading, source date, printed year, and selected values. **40/40 group/date/year/value witnesses matched**, with original, operator-scoped anchor rectangles and an explicit per-table group mapping. Individual check flags are committed in [`original_pdf_period_context_20261103.json`](../examples/discovery/original_pdf_period_context_20261103.json); the original source hashes and manually declared group/date rectangles are in the 40-cell oracle. [Reproduce the independent replay](../scripts/interop_period_context_acceptance.py) in an isolated environment containing Research Drive and the five unmodified public PDFs.

Adversarial offline unit tests prove that swapping to the neighboring nine-month group while keeping the **same year and same number** fails, even though the simpler independent word witness alone passes. Wrong group text, date, geometry and source digest also fail or abstain. Reporting-period claims remain conditional on operator-supplied source anchors; there is **no automatic discovery, no independent human second adjudicator, no authoritative accounting meaning inference, and no trusted Research Drive publication**. Heterogeneous PDF failures recorded earlier remain unsolved.

## Isolated no-network source-period acceptance

The Research Drive bridge now runs the full original-PDF period-group/date/year check within its **existing** bwrap/libseccomp isolated execution facility. Host-controlled verification modules and the installed original-word parser are copied into a temporary read-only runtime; source PDFs, parser candidates and operator-scoped declarations are staged separately as untrusted inputs. The worker cannot connect to a network and emits a bounded source-hash/count-only receipt. No trusted CSV or PDFScope is created.

The Atlas replay script accepts an optional --isolated switch. On all five publisher originals it independently rechecked 40/40 cells inside the separate worker, matching the 40/40 direct read-only verification count. Inspect the pinned, sanitized per-file and per-cell results in [isolated_period_context_acceptance_20261103.json](../examples/discovery/isolated_period_context_acceptance_20261103.json). A complete replay requires the original public files, Research Drive's installed sandbox and the optional img2table parser, and uses their original file SHA pins.

This still measures operator-defined cells and header regions. It is not a blind/general semantic assessment, not trusted write-path integration, and not a repair for the earlier BIS/arXiv parsing failures. Release status stays HOLD.

## New negative holdout: repeated real-PDF footnote labels

Four public, original-SHA-pinned financial PDF pages were probed using Research Drive's pre-existing original-PDF word path and a new **non-authoritative note-marker ambiguity audit**. This is a negative source-context acceptance check, not a means to infer footnote meaning.

- Apple FY25 Q1 and Q4: two separate sections printed as footnote (1) on each page (sales by segment versus category). Both require an explicit **ambiguous marker abstention**.
- Alphabet 2025 Q2 and Q3: only one candidate note definition detected after the selected reference row on the checked page; neither is automatically linked or semantically approved.
- **Zero automatic footnote links were verified** despite strong numeric/period source-word evidence. No note text is interpreted and no trusted source citation is generated.
- This is a bounded, left-margin-based word-position heuristic. A lone matching marker does not prove which data field or table section the note explains. Unsupported/multilevel, missing or cross-page notes remain a manual-review obligation.

The pinned [footnote negative acceptance receipt](../examples/discovery/real_pdf_footnote_ambiguity_20261103.json) and [replay script](../scripts/interop_footnote_ambiguity_acceptance.py) provide the original source SHA, selected physical page, reference-row lower boundary, definition count, and review status, without redistributing originals. These outcomes **do not reduce** the earlier 40/40 literal source-period witnesses: they define a separate unresolved layer of meaning. No promotion or publication is authorized.

## Operator-assisted multilevel-header and footnote choices

The next Research Drive review helper, `optional_pdf_operator_review.review_operator_annotations`, adds an explicit **operator assertion** layer without converting optional parser candidates into trusted `PDFScope` evidence. It verifies original-source statement title and units, previously scoped period-group/date/year evidence and row/value geometry, then treats note markers as an operator choice that may be unresolved or linked to a specifically located original printed definition. Even a source-witnessed note selection is labeled **second review pending**, never verified semantic meaning.

The replay on two official SHA-pinned Apple FY2025 Q1/Q4 financial PDFs produced **eight operator annotation examples**. Two note choices remain unresolved; the two competing `(1)` note definitions for each source page are each independently source-witnessed (**four alternative links, not four approvals**); two unfootnoted controls have correctly matched source title/unit/period/value. Thus six source-backed operator annotations are recorded, **zero independent human semantic adjudications** and **zero trusted promotions**. Importantly, both alternative interpretations of the same printed `(1)` source marker pass literal source checks, proving the checker cannot determine which accounting note applies without an actual independent reviewer.

The operator workflow includes a bounded two-record comparison to flag missing review and conflicting selections. Reviewer labels are not authenticated; even matching records do not grant approval or publish data. See the [replay script](../scripts/interop_operator_review_acceptance.py), [sanitized empirical receipt](../examples/discovery/operator_assisted_pdf_review_20261103.json) and Research Drive PR #91 for source code and operator documentation. The two Apple sources are **reused from the earlier five financial PDFs**—these eight annotations do not add eight new documents to the corpus. Existing mixed-layout extraction failures remain a separate HOLD gate.

## Blinded human-review invitations prepared, not adjudicated

The Research Drive optional PDF review layer can now issue **blank, separate source-scoped tasks** for a second reviewer without exposing the first operator's note-selection assertions, compare independently submitted claims, and replay the claims against the **original PDF** before reporting agreement or contradiction. **Session IDs are not authentication**: even two matching results do not prove two people or establish trusted financial semantics.

For the two Apple FY25 financial original-source cases with ambiguous reused `(1)` notes, four private invitation packets were generated (two per document) on the authorized local workstation, with the original source digests and source-cell IDs pinned. No private packet tokens, original PDF bytes or reviewer choices were committed. This is **readiness only, not an actual independent human evaluation**: submitted human review responses = 0, independently accepted note links = 0, trusted dataset promotions = 0. An actual second reviewer must inspect the publisher source and submit source-backed context and note decisions without seeing the first operator's answers.

See the [replayable blank invitation builder](../scripts/prepare_blind_pdf_review_invites.py), [sanitized readiness receipt](../examples/discovery/blind_review_invitations_20261103.json), and Research Drive's `OPTIONAL_PDF_PARTIAL_BLIND_REVIEW_20261103.md`. The source custody and native trusted-CSV acceptance boundaries remain unchanged. Release decision: **HOLD pending true independent reviewer and more unknown-layout validation**.
