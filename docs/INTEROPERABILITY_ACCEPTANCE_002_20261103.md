# Atlas interoperability acceptance 002 — strict multi-page PDF and custody repair

**Executed:** 2026-11-03, Optiplex
**Authority:** Comparative evidence only; no verified technology promotion, deployment or production changes

## Why this second gate

The first acceptance round in Atlas PR #141 found that **img2table 2.0.0 with borderless extraction** passed all 9 upstream source-checked assertions across three small one-page PDFs. That was useful but insufficient to justify adding a generic financial/academic PDF ingestion lane to Research Drive. PR #140's typed maps also identified the separate requirement of trustworthy cell and header integrity.

This round adds **two three-page continuation PDFs** and **one two-page positional-text PDF**, all from the independently published [PDF Table Traps](https://github.com/LydiaTools/pdf-table-traps) fixture commit `c63aab8884671aa4c789f08d0891f1a3f0ee5f5d`. The fixtures and oracles remain upstream. No user/private PDFs were used or included in Git.

## Multi-page continuation (24 source rows each)

Three engines were **actually executed**, with the same two PDFs:

| Engine | Single header, naive per-page extraction | Repeated header, naive extraction | Single header + explicitly reviewed header |
|---|---:|---:|---:|
| pdfplumber 0.11.9 | 22/24 | 24/24 | 24/24 |
| PyMuPDF 1.28.2 | 22/24 | 24/24 | 24/24 |
| img2table 2.0.0, borderless | 22/24 | 24/24 | 24/24 |

All engines returned `Plant-09` and `Plant-17` as the first physical rows of continuation pages **without a repeated column header**. A naive downstream rule that always treats the first row of each page as the header would silently drop those two data rows. A source-supervised correction can preserve all 24, but the known `Item / Zone / Count / Price` schema must be **supplied by the operator** and confirmed before reuse.

A passed 24/24 count verifies only the fixture's declared row keys and `Count` values. It does not certify every price, total or table interpretation.

## Positional two-page table (same column coordinates, different title lengths)

The upstream PDF positions cells at the same coordinates on two pages but varies title/header width. An independent two-cell oracle checks `Cedar` under `Unit price` on both pages:

| Engine | Known price cells |
|---|---:|
| pdfplumber default table detector | 0 pass, 2 unknown |
| PyMuPDF default table detector | 0 pass, 2 unknown |
| img2table borderless | 0 pass, 2 unknown |
| **Upstream positioned extractor, operator-defined region + edges** | **2 pass, 0 unknown** |

The positioned extractor is **reused from PDF Table Traps** (`scripts.positional_table.extract`). It is not another Atlas-written geometry solver. The operator explicitly supplied the source region `0,60,612,500`, column boundaries `0,200,350,612`, and column names. No automatic discovery or generalization is claimed.

## Nocturnal source-side custody defect

During the more stringent checks, a native Nocturnal capture with **raw HTML different from extracted readable text** produced a WARC whose `X-Watchdog-SHA256` described the readable text, **not its archived HTML response body**. In a second negative control, a failed remote fetch could be replaced by an apparent successful HTTP response WARC.

This was a **real source-side integrity-contract issue**, independent of pywb. The isolated Nocturnal [draft PR #114](https://github.com/Spectating101/nocturnal-oversight/pull/114) retains the original text digest for compatibility, adds `warc_payload_sha256`, passes that digest to the native WARC writer, and skips WARC creation after failed fetch/no body. Local **12 focused Nocturnal tests passed**. The Nocturnal PR subsequently declared NumPy and provided Poppler test tools; all focused and full GitHub checks now pass. The PR remains unmerged. No historical WARC was modified.

## Deployment decision

- **Research Drive:** `LIMITED_OPERATOR_ASSISTED_CANDIDATE`. img2table borderless remains promising for small digitally readable tables, but incomplete multi-page headers and untabulated positional layouts **fail closed**. Do not enable unattended PDF-to-data promotion, auto-fill missing cells, or replace a verified source-cell check with numeric-token presence. The `local_file` query backend remains intentionally metadata-only, but a separate native Research Drive PDF table helper already exists; it must be retained rather than duplicated.
- **Nocturnal:** `SOURCE_INTEGRITY_FIX_REVIEW_REQUIRED`. Review and merge draft PR #114 only after affected consumers and a clean focused GitHub workflow check. The existing WARC/pywb replay stack still works for the earlier synthetic single-page test; it does not certify advanced capture.
- **Atlas:** Preserve this second acceptance receipt on the original typed edges. A source can be viable for capture but not replay, or extraction but not trustworthy row/header continuity.

**Caveat:** This was an expanded *independently maintained synthetic source corpus*. An attempt to fetch a real published annual financial PDF on Optiplex met HTTP 403/404; no real financial document was benchmarked, and no real-world performance number is asserted. There was no OCR, scanned-page, long-form academic, confidential or adversarial PDF evaluation. All source-specific inputs, artifacts and full logs remain private on Optiplex.

## Native Research Drive baseline correction (November 3 follow-up)

The earlier Atlas report inspected only the `local_file` query backend and incorrectly implied there was no existing Research Drive PDF table parser. The latest procurement-branch code (commit `42d5cdac4f0ef48269b14d38d93a7377cffde86a`) has an existing `recorded_fetch.HELPER.pdf_tables` backed by pdfplumber and a separate `PDFScope`/`SourceCell` evidence model.

**Actual native helper replay against the independent source fixtures:**

| Fixture | Native Research Drive parser | Optional img2table |
|---|---|---|
| Ruled table | 4/4 | 4/4 |
| Borderless table | 0 pass, 1 fail, 3 unknown | 4/4 |
| Prose negative control | 1/1 | 1/1 |
| Positional two-page | 0 pass, 2 unknown | 0 pass, 2 unknown |

The native system preserves PDF hash, physical page/table/row identity and source-cell references, with semantics marked unassessed. The new **optional candidate** in Research Drive draft PR #91 reuses those primitives, requires manual source-cell review and has no auto-publication capability. Neither approach is approved for unattended production ingestion.

## Reproduce

With the earlier Atlas PR #141 Python environment (pinned PDF Table Traps fixture checkout, versions and optional packages):

    python scripts/interop_multipage_benchmark.py --fixtures /path/to/pdf-table-traps --out /tmp/atlas-acceptance/multipage
    python scripts/interop_positional_benchmark.py --fixtures /path/to/pdf-table-traps --out /tmp/atlas-acceptance/positioned

These scripts enforce the upstream commit, use original fixture oracles, write immutable run results, and do not modify Research Drive or Nocturnal repositories. Synthetic offline CI tests verify loss-of-row and abstention behavior, but do not execute third-party engines during GitHub CI.

## Next genuine acceptance gate

Use 5–10 **permitted original financial/academic PDFs with separately reviewed source-cell ground truth**, cover repeated/missing headers, spanning rows, footnotes, tables with parentheses and units, and scanned documents separately. Require exact preservation of row/header/value and source-page provenance, track abstention separately from errors, then consider an *opt-in* Research Drive adapter. A correct result from one benchmark is not sufficient to recommend a default library.
