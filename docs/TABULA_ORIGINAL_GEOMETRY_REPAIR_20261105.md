# Original-PDF calibrated geometry recovery — post-holdout research

**2026-11-05. Actual engineering output, no trusted source promotion.**

The 12-PDF Tabula-Java first-pass holdout from the preceding phase is unchanged and remains the baseline: 325 unverified Camelot hybrid candidate rows, 68 strict operator-review-ready rows from three normal-coordinate documents, and five engine errors. This phase is **post-holdout** development on four already inspected geometry-blocked original PDFs, and therefore **does not count as a new blind test or revise any first-pass accuracy estimate**.

Research Drive PR #91 now has a reusable source-coordinate calibration layer, not a duplicate PDF table extractor. It creates a private PyMuPDF-normalized copy of the selected rotated/CropBox PDF page, calls the already integrated **Camelot 1.0.9 hybrid** engine, and independently fits a uniform scale/translation mapping using unique literal PDF words. It demands full original text preservation and word bounding-box matches against the **original bytes**, then inversely maps proposed candidate boxes into original page points. The strict operator packet builder reruns source SHA and word/cell evidence and rejects empty/merged, multiline or overlapping claims. Derivatives, original PDFs and all full source-row proposals remain outside public Git.

## Fixed original-source case results

| Original first page | Geometry | New candidate rows | All-cell literal source matches | Strict operator-review rows | Blocked |
|---|---|---:|---:|---:|---:|
| `rotated_page.pdf` | 90° rotation | 40 | 36 | **30** | 10 |
| `schools.pdf` | 90° rotation | 76 | 28 | 0 | 76 |
| Transport award notice | 90° rotation | 49 | 21 | 0 | 49 |
| `should_detect_rulings.pdf` | Offset CropBox | 90 | 89 | 0 | 90 |
| `argentina_diputados_voting_record.pdf` | Parser row/cell geometry inconsistency | No recovery | — | 0 | HOLD |
| **Totals across four calibrated pages** | | **255** | **174** | **30** | **225** |

The original source-word alignment uses 373, 282, 165 and 72 unique original PDF word boxes respectively. All selected original source words were preserved in the private normalized derivatives, and the fitted word-box residual was zero to four decimal places on these samples. This is a source-location verification, **not** an independent complete table, publisher provenance, current financial value or human adjudication.

The newly eligible `rotated_page.pdf` source has a **real 30-card self-contained HTML reviewer**, rendered and checked in local Chrome. Private location on the authorized workstation:

`~/chatgpt-work/review-20261103/sources/tabula-locked-20261104/private-calibrated-reviews-20261105/rotated-second.SOURCE-REVIEW.html`

The remaining three normalized source PDFs produce **no** review-ready rows under the nonempty and nonoverlap gate; they are not claimed as completed usable datasets. The fifth original row/cell-geometry error has not been circumvented or normalized away.

## Reproducible proof and decisions

- `scripts/tabula_original_geometry_recovery_acceptance_20261105.py` reopens exact originally pinned source PDFs, recomputes affine anchors against the private derivatives, replays source-cell packet validation, checks row denominator and original SHAs and emits a sanitized receipt.
- `examples/discovery/tabula_original_geometry_recovery_20261105.json` retains four source SHA pins, normalized derivative SHA pins, original rotation/crop markers, anchor box counts, candidate/review/block counts, and the fifth unresolved original failure.
- `tests/test_tabula_original_geometry_recovery_20261105.py` checks this result cannot silently rewrite original first-pass denominators or introduce trust promotions.
- Research Drive #91 supplies synthetic original-PDF adversarial unit tests and the usable private calibrated review CLI.

**HOLD:** zero actual operator submissions, zero independent reviewers, zero trusted `PDFScope` promotions, zero dataset publication. Both PRs remain open drafts, unmerged and undeployed. Further unknown-layout accuracy needs a **new** preregistered untouched rotated/cropped PDF sample and true original semantic adjudication.
