# Existing Camelot PDF engines: locked external Tabula evaluation

Date: 2026-11-04. Release decision: HOLD. Private review candidates only.

## Implementation and chronology

Research Drive PR #91 now contains an optional read-only adapter to the existing upstream Camelot 1.0.9 hybrid, network and lattice engines. It does not duplicate a table parser. It checks the original source PDF byte SHA-256, uses the original PDF page, converts Camelot cell boxes into original top-left PDF points and independently rechecks cell text against the original pdfplumber words and geometry. All source text remains private; no trusted PDFScope, publication or dataset registration is possible through the adapter.

Atlas preregistered the source filenames and score policy at commit 7c64037 before downloading them. Research Drive's original adapter was frozen at commit 9b502d8 before the external PDFs were acquired. The corpus is 12 original Tabula-Java test PDFs (8 hash-selected CSV-backed examples plus 4 predeclared stress layouts) from upstream revision 2cdf3b4fd3f7e921dca8cc6814cdd9316be40f0f. The fixed primary engine is hybrid; network and lattice are diagnostics, never selected by per-case reference performance.

This is a self-administered, prospective engineering holdout, not a human-blind independent study or a representative random sample of all PDFs.

## Frozen first-pass original PDF outcomes

| Metric | Result |
|---|---:|
| Original PDF first pages attempted | 12/12 |
| Hybrid pages returning candidate rows | 6 |
| Hybrid proposed rows, not reference-approved | 325 |
| Hybrid rows with every proposed cell literally located in original PDF word geometry | 171 |
| Hybrid engine errors or timeouts | 5 |
| Pages with comparable prior-published Tabula reference CSVs | 6 |

Original publisher files, reference CSV contents and full private proposals remain on the authorized workstation and are not checked into Git.

## Third-party CSV reference results, six scorable first pages only

The published Tabula CSVs were acquired after the primary row proposals were frozen. They are independently authored reference fixtures, but NOT fresh human-transcribed ground truth.

| Engine | Exact whole-row matches | Unmatched proposals | Missed expected rows | Conditional precision | Conditional recall |
|---|---:|---:|---:|---:|---:|
| Camelot hybrid (locked primary) | 185 | 67 | 53 | 73.4% | 77.7% |
| Camelot network (diagnostic) | 185 | 67 | 53 | 73.4% | 77.7% |
| Camelot lattice (diagnostic) | 146 | 13 | 92 | 91.8% | 61.3% |

Six scoped CSV reference PDFs contain 238 expected rows. On these six PDFs, hybrid proposed 252 rows, of which 150 had exact original-source word witnesses for every cell. Only 135 of those 150 also matched the independent Tabula reference CSV. The combined literal source + external row intersection therefore has 90% conditional precision (135/150) and 56.7% recall (135/238). These results are still NOT authorized financial records or independently human-approved data. Across the remaining six documents there are 73 unscored hybrid candidate rows; do not apply 73.4% precision globally.

## Same-cohort old scanner diagnostic

The original ruled-only scanner frozen at 2f5bd7f was executed unchanged on the same 12 Tabula PDFs and the same 6 reference-supported first pages. The secondary comparison was done after the new holdout results, not preregistered as the main engine.

| Scanner | Exact matches | Unmatched | Missed | Conditional precision | Conditional recall |
|---|---:|---:|---:|---:|---:|
| Previous ruled-only source row scanner | 115 | 48 | 123 | 70.6% | 48.3% |
| Fixed-primary existing Camelot hybrid | 185 | 67 | 53 | 73.4% | 77.7% |

The previous 9.35% recall on the different Camelot fixture corpus is NOT a same-cohort comparator. On this same set, mature Camelot produced 70 more exact row matches. The source gate still filters many candidate rows and preserves errors on difficult pages.

## Inspectable files and limits

- Preregistration: scripts/preregister_tabula_engine_holdout_20261104.py and examples/discovery/tabula_engine_holdout_preregistration_20261104.json.
- Read-only engine runner: scripts/run_locked_tabula_multi_engine_20261104.py and sanitized tabula_engine_holdout_first_pass_20261104.json.
- Exact CSV scoring: scripts/score_tabula_multi_engine_20261104.py and sanitized tabula_engine_holdout_csv_scoring_20261104.json.
- Frozen ruled-only comparison: scripts/compare_frozen_ruled_tabula_holdout_20261104.py and tabula_ruled_baseline_same_cohort_20261104.json.

Remaining blockers include rotated/cropped source coordinate calibration, 5 engine errors/timeouts, merged headers, source-word mismatch, multi-page and missing-reference cases, unbiased new-publisher accuracy checks and second-human semantic review. Source-location matches are not accounting or publisher semantic approval. Both PRs remain open drafts, unmerged, undeployed and without automatic trusted publication authority.

## Follow-on private operator queue — 2026-11-04

The fixed first-pass `hybrid` output was run through Research Drive's stricter source-and-row review packet builder. Of the original **325 source candidates**, only **68** had all nonempty cells originally word-matched without reused word geometry or multiline ambiguity, and **257** are held with reason codes. Real offline HTML source-preview reviews are prepared privately for three PDFs (44 + 21 + 3 rows). No operator input or second human review was submitted. Original engine failures remain 3 rotated, 1 offset CropBox and 1 inconsistent Camelot row/cell output. The earlier **171 all-cells-match flag** and **135 source+CSV reference matches** remain separate historical quantities, not counts of rows approved for publication. See `docs/TABULA_OPERATOR_REVIEW_QUEUE_20261104.md` and the sanitized receipt; release HOLD.
