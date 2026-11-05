# New unseen external PDF geometry cohort — first-pass failure evidence

**2026-11-05 | Atlas PR #142 | release HOLD**

## Chronology and authority

This is a separately selected external PDF source corpus from the **pdfplumber repository**, not the older Tabula-Java or Camelot fixture corpora. The selection of **12 exact filenames** was frozen and pushed at Atlas commit `6f7427e`, based on *public source metadata only*, before any PDFs were downloaded. Seven filenames were predefined geometry/table stresses and five were selected by a SHA-256 filename hash from a pinned upstream directory. Original upstream revision: `4c64b92d5caccd71c645e98e0fabb0c4dba7ff45`.

The Research Drive engine implementing original PDF calibration, strict source-word cell checks and a **separate blocked-row structural-review tier** was frozen at `4e3dabe`; the fixed all-case Atlas runner was committed at `3e16c07` **before first PDF download**. The run always uses **Camelot 1.0.9 hybrid**, using a private PyMuPDF extraction-aid derivative and independently mapping candidate cells back into the original source physical coordinate system. There was no document-specific parser, crop/rotation, threshold or flavor selection after the files were opened. The engine requires 20+ unique original source words for affine calibration and full original word preservation, otherwise abstains. The original PDF bytes were never rewritten; every fetched source SHA-256 remains in the sanitized receipt.

This is a **prospectively held-out, self-administered engineering trial**, not an external human-blind or representative population sample. There are no independent publisher-transcribed row labels for this corpus. **Precision and recall are unknown and deliberately null**; original-word location agreement is not a substitute for external table truth.

## First-pass results (all 12 original first pages)

| Metric | Locked first-pass result |
|---|---:|
| Original first pages attempted; original source SHA-256 captured | **12 / 12** |
| Pages with original-word affine proof | **6** |
| Pages with hybrid table candidates | **2** |
| Raw candidate rows on those pages | **88** |
| Strict original source-word, nonempty/nonoverlapping review-ready rows | **3** |
| Blocked candidate rows, retained for structural review only | **85** |
| Errors / calibration abstentions, retained in denominator | **10** |
| Independent semantic approvals / trusted dataset registrations | **0 / 0** |

The ten failures comprise **six** early normalization/calibration errors (including three sparse rotated annotation pages, a simple page-box example and other low-word pages) and **four** `ValueError` failures during the fixed Camelot-hybrid stage after coordinate calibration. This runner records stage and exception type, but did not independently resolve the four parser-stage errors; do not reclassify them as successes. No candidate rows from those ten are included in the 88.

Two previously unseen, initially 90-degree-rotated PDFs supplied candidate rows:

| Source first page | Candidate table rows | Strict original-source reviewer rows | Explicitly blocked rows |
|---|---:|---:|---:|
| `issue-461-example.pdf` | 27 | **3** | 24 |
| `senate-expenditures.pdf` | 61 | **0** | 61 |
| **Total** | **88** | **3** | **85** |

Across these two, the *blocked structural observation* tier found **240** candidate source-empty or parser-empty slots that remain `UNRESOLVED_BLANK_VS_MERGED` and **2** multiline source-cell observations. These are *cell slots*, not 240 missing data values or independent adjudicated merged cells. The source-word geometry and the original physical page were independently re-read for every candidate. No source-empty cell was converted to an inferred zero or copied neighbor.

## Real private operator handoff, not reviewer approval

After the first-pass receipt was frozen, the unchanged Research Drive pipeline was rerun for `issue-461-example.pdf` to produce a usable private original-source operator sheet and an independent structural review sheet. It reproduced the first-pass counts: **27 candidates / 3 strict reviewer rows / 24 blocked structural rows**, with original source SHA `34f3fe05d1c8e242f0e2d2204399f46aebcbef630834d544deb4a0d625846d63`. Chrome rendered all three clean-row review cards and the first 15 structural review cards. This separate UI handoff was NOT a second benchmark attempt or a post-hoc change to the frozen 12-page result.

On the authorized Optiplex:

`~/chatgpt-work/review-20261103/sources/pdfplumber-untouched-20261105/private-review-followup-20261105/issue461-same-engine-post-holdout.SOURCE-REVIEW.html`

`~/chatgpt-work/review-20261103/sources/pdfplumber-untouched-20261105/private-review-followup-20261105/issue461-structural.complex-source-review.html`

The clean sheet requests independent second review, while the structural sheet supports **requires_manual_transcription**, reject or abstain; it does **not** offer an acceptance action. Reviewer labels and exported notes are not authenticated. No one has submitted decisions.

## Evidence files and next engineering gate

- Frozen source-name and selection rules: `examples/discovery/pdfplumber_geometry_holdout_preregistration_20261105.json`, `scripts/preregister_pdfplumber_geometry_holdout_20261105.py`.
- Fixed pre-download runner with per-document subprocess timeout, original SHA check and source-only review pipeline: `scripts/pdfplumber_geometry_holdout_runner_20261105.py`.
- Actual sanitized all-12 first-pass receipt: `examples/discovery/pdfplumber_geometry_first_pass_20261105.json`.
- Guard assertions, including old Tabula corpus denominator unchanged: `tests/test_pdfplumber_geometry_holdout_20261105.py`.
- Research Drive #91: `optional_pdf_complex_structure_review.py` and its tests; prior affine calibration path is unchanged from the separately documented 2026-11-05 source recovery.

This result shows the extraction+source gate can generalize to **some** unseen rotated PDFs but **does not** establish robust general-purpose PDF extraction. Next work should investigate the four Camelot-stage errors as an explicit **post-holdout** diagnostic, then benchmark any repairs on a *new* untouched corpus. Structural operator review is useful for locating ambiguities, but incomplete accounting, merged-cell semantics, trusted source provenance and actual independent human second review remain blocked.

**HOLD:** zero trusted PDFScope, zero automatically promoted source rows, no publisher dataset publication, no merges/deployments. Both PRs remain draft.
