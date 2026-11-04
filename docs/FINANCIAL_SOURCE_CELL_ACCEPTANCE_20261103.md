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

## Heterogeneous source-cell quality and issuer provenance

The heterogeneous BIS/arXiv recovered-page pilot has now been independently source-word checked beyond raw parser-execution counts. Seven proposed table regions contained 33 candidate rows: 25 failed conservative single-line label/atomic-number screening and eight were eligible for manual source-word checks. Of those eight, six were physically corroborated on a source PDF page, and two abstained due to parser-joined words. The six source-located values are in a *secondary academic reproduction* of a Manulife 1Q24 fact sheet, so **none has verified issuer-original custody or trusted publication authority**. The original 40/40 Apple/Alphabet/Amazon selected financial source-period acceptance is a different, well-structured corpus and was not diluted or broadened by these results. The three heterogeneous failed pages remain identified, not silently recovered.

See `heterogeneous_original_source_cell_oracle_20261103.json`, `heterogeneous_source_cell_quality_20261103.json`, and the replay script for explicit source locations, operator-expected printed strings, strict matching flags and provenance holds. We retain a hard separation between **candidate cell count**, **layout eligibility**, **original-PDF literal match**, **direct issuer source**, **second human semantic review**, and **trusted dataset write authority**.

## Original Manulife issuer SEC EDGAR source row reconciliation

The prior arXiv Figure 5 Manulife 1Q24 fact-sheet reproduction was not an original issuer filing. To correct its provenance, two **issuer-authored SEC EDGAR Exhibit 99.1 original HTML documents** were acquired under pinned exact-byte SHA-256 local custody. These are the 2024 first-quarter shareholder report and earnings release; Manulife's own website rejected direct PDF downloads (HTTP 403), so **the original issuer PDF binary is not verified**. Research Drive's new `optional_issuer_edgar_reconcile` checks the SEC HTTPS URL, CIK, original local byte size/SHA, literal issuer and period heading, and operator-declared exact HTML table/row/label/value/quarter/unit locations. It is a narrow, offline, source-backed original HTML row verifier, not another table extractor.

The issuer shareholder report **8/8** manually mapped figures and their original 1Q24 header/units verified. The same issuer's separate earnings release corroborated **7/7 overlapping** figures. A source-cell for **C$1,102 million general expenses**, the qualifier accompanying total expenses of C$1,679 million, also verified **1/1**. The issuer's **APE sales C$1,883 million** is explicitly converted to **C$1.9 billion** in the reproduction (one decimal, HALF_UP), never falsely counted as the identical printed numeric token. Other issuer items include net income 866, core earnings 1,754, new business CSM 658, NBV 669, Global WAM net flows 6.7 billion, and average AUMA 880 billion.

This **strengthens original issuer evidence**, but two issuer-authored reports from the same company are not two independent human reviewers, and the issuer EDGAR HTML is not the original Manulife PDF. The academic reproduction's `Newbusiness` fused-label errors remain **2/8 secondary-parser abstentions**, notwithstanding the eight issuer-row matches. No independent human accounting adjudication, trusted PDFScope promotion, dataset registration, or auto-publishing occurred.

The reproducible evidence is [issuer reconciliation script](../scripts/manulife_sec_issuer_reconciliation.py), [pinned original issuer SHA and manual row oracle](../examples/discovery/manulife_sec_issuer_reconciliation_oracle_20261103.json), and [sanitized 8+7+1 acceptance receipt](../examples/discovery/manulife_sec_issuer_reconciliation_20261103.json). Original SEC filing HTML bytes and academic PDF remain private. Release: **HOLD**.


## Heterogeneous page failure isolation and exact original-source native crop

BIS 138 p6 is now explicitly held as a plotted-graph source, not misclassified as a successful table. Two truly tabular but previously failing physical pages received manual original-PDF point-coordinate crops. Research Drive's **existing pdfplumber** native detector and separate original-PDF word witness matched **8/8 selected rows** (arXiv 2506 p6 Table 2: 4/4; arXiv 2604 p9 Table 12: 4/4). The underlying img2table crashes remain reproducible and no full-table completeness, multi-level-header semantics, original issuer provenance or independently adjudicated accounting meaning has been established. The detector and word verifier both use pdfplumber, so this is not independent-engine validation. Exactly **zero** rows were granted a trusted PDFScope, dataset promotion or auto-publishing authority. The source SHA-pinned [oracle](../examples/discovery/operator_cropped_failed_pdf_pages_20261103.json), [replay script](../scripts/failed_page_native_crop_acceptance.py) and [receipt](../examples/discovery/failed_page_native_crop_acceptance_20261103.json) preserve those distinctions. Release remains **HOLD**.

## Native-crop boundary sensitivity acceptance on prior failed pages

A five-way PDF-point crop perturbation replay (`-5, -2, 0, +2, +5`) was run on the **same two original heterogeneous pages** that native pdfplumber had recovered via exact manual source-crop instructions. This separates source-word matching at a single preferred crop from geometry robustness on nearby legal crop scopes. arxiv2506 p.6 (cost-comparison table) had **4/4 literal source matches at the baseline crop, but only 1/5 nearby crop trials preserved all four**; enlarged crops merged multiline observations, while shrunken crops lost selected data/header cells. arxiv2604 p.9 (LLM accuracy table) had **4/4 matches in all 5/5 crop trials**. Combined: 6/10 trial successes, 4/10 recorded abstentions; 1/2 pages fragile. The BIS chart-only failed page remains a chart-only no-table HOLD.

This is an original-PDF source-word/geometry *robustness negative gate*, not proof of table-row completeness, reporting meaning, independent human review, or trusted extraction. Existing 8/8 baseline words still match; their release interpretation is now qualified by the crop sensitivity finding. See the reproducible [crop-robustness replay](../scripts/failed_page_native_crop_stability_acceptance.py) and [source-pinned per-trial receipt](../examples/discovery/failed_page_native_crop_stability_20261103.json). No original PDFs, parser candidate source text or private operator data were committed. Source authority remains HOLD.

## Row-completeness witness for the crop-fragile cost table

The arxiv2506 original PDF's physical page 6 has a **vector-ruled** Table 2 cost comparison. Source-word matches from its native table parser had already passed **4/4 selected numeric rows**, but the fixed ±2/±5 PDF-point crop perturbations passed only **1/5** geometries; the crop is fragile and no table completeness could be inferred. A new original-source grid test independently reads exact original PDF vector ruling lines and all visible original words inside their physical table bounds, without relying on native crop row segmentation. With the manually pinned original source SHA and table/column geometry, it observes **six distinct horizontal boundaries, five printed rows, three columns and 15 source words**, all assignable to exactly one source cell. The manually transcribed 5×3 matrix agrees with the original word inventory and, separately, the native baseline parser's five candidate rows. These are **original-source completeness results limited to the explicitly ruled table**, not entire-document coverage, parser robustness, market-current pricing, independent human verification or trusted publication.

The original crop remains **1/5** under the tested perturbations despite full bounded original-source word coverage. The evidence is intentionally separate: [operator ruled source oracle](../examples/discovery/original_ruled_cost_table_oracle_20261103.json), [original-file replay](../scripts/original_ruled_cost_table_acceptance.py), and [sanitized source grid receipt](../examples/discovery/original_ruled_cost_table_acceptance_20261103.json). Adversarial synthetic *real vector PDF* tests reject omitted last rows, absent source ruling lines, extra original words and forged labels/numbers, with no trusted `PDFScope` or dataset publication authority. The same original source file, not a newly sampled document, was replayed. **Release HOLD.**

## Portable original-PDF row-region proposal — external nonblind fixture check (2026-11-04)

The Research Drive **source-only**, explicitly bounded ruling-line fallback now supports two PDF vector representations: original stroked lines (the original arXiv cost source) and thin filled rectangles (a previously unused Camelot software-test fixture style). The bounded table region and column edges remain operator-specified. The output contains original-PDF point rectangles per row/cell, source word counts and multi-line/empty-cell flags; it **does not** certify an operator-independent transcription, document-level table recall or financial semantics.

On the nonblind, intentionally selected original-source public `health.pdf` fixture, the page-one scoped data segment contains **24 original thin-rectangle horizontal boundaries, 23 row regions and 8 columns**. Of **190 source PDF words**, 190 are assigned to one row/column and none are ambiguous; **five separately transcribed literal row controls** (indices 0, 6, 12, 18, 22) also match. This remains a **23-row page slice**, not authenticated original Indian government budget data or a complete multi-page dataset. The second previously unused public fixture, `foo.pdf`, demonstrates the negative path: **51/52** source words assigned and a multi-tier/complex header; it is held and **not** counted as complete. The original arXiv p.6 cost source remains **5×3 with 15/15 words** and its **native parser crop remains fragile (1/5)**. No old benchmark denominators were rewritten.

Pinned source URLs, download SHA-256s, source bbox/column contracts and five selected literal control rows are in the [public fixture operator oracle](../examples/discovery/ruled_row_region_external_oracle_20261104.json). The [replay](../scripts/ruled_row_region_external_acceptance.py) executes Research Drive's actual source row proposer and the [sanitized receipt](../examples/discovery/ruled_row_region_external_acceptance_20261104.json) exposes only per-case counts, flags and source digests. Full original PDF word proposals and source PDFs stay in local private custody. This exercise used external fixtures but was **not blind** and no independent reviewer participated.

**Release remains HOLD:** 0 trusted PDFScope promotions, 0 auto-publishing, 0 dataset registration. Multilevel headers, complete original issuer provenance, independent human source/semantic review, and unfamiliar documents beyond intentionally selected engineering fixtures remain mandatory next gates.

## Prospective no-hint external PDF holdout — not production ready (Nov 4)

After the earlier operator-bounded successes, a **separately locked no-hint scanner** was tested on 16 original Camelot fixture first pages selected and committed before download. It produced **68 unreviewed source row bands across 6 pages**, abstained on 9 pages, and errored on one complex rotated/cropped header page. Six of these pages had published third-party expected-row tables: **10 strict text matches, 0 unmatched proposals within those six pages, and 97 missed expected rows**, yielding **100% conditional precision on 10 reference-scored proposed rows but only 9.35% recall**. The remaining 58 proposed row bands on ten other pages lacked comparable independent reference rows; do not extrapolate 100% precision to them. This is not a blind independent human study. See `docs/LOCKED_EXTERNAL_PDF_HOLDOUT_20261104.md` and the frozen manifest, execution/score scripts and receipts. **Release remains HOLD**; no change to native custody or trusted PDFScope.

## Reusing existing Camelot for unsupported layouts (Nov 4, 2026)

A pinned optional Camelot 1.0.9 adapter now calls upstream hybrid/network/lattice engines while independently checking the original PDF SHA and exact literal word/cell geometry. Its separately preregistered Tabula-Java external cohort was frozen before original PDFs were downloaded: 12/12 first pages attempted, 325 unverified hybrid candidate rows across 6 pages, 171 with full original-word cell witnesses, 5 engine errors/timeouts. On six single-page documents with published Tabula CSV references, primary hybrid had 185 exact row matches, 67 unmatched candidate rows and 53 missed expected rows (73.4% conditional precision, 77.7% recall). Only 135 rows passed BOTH original PDF cell words and reference CSV matching (135/150 candidate source-witnessed rows and 135/238 expected rows). The old frozen ruled-only scanner on the same new Tabula cohort recalled 115/238 rows (48.3%). The earlier 9.35% result from a different corpus is separate. No independent human or trusted dataset approval. Full details: docs/TABULA_EXTERNAL_ENGINE_HOLDOUT_20261104.md. HOLD.
