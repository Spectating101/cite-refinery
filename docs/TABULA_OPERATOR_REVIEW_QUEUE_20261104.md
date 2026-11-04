# Real offline PDF operator-review sheets — original-source evidence, not data approval

**November 4, 2026. Source review stage operational; no human review submitted.**

Research Drive PR #91 now implements a private offline reviewer UI over real Camelot original-PDF candidates. It reopens the original source PDF and independently recomputes original word/cell witnesses rather than trusting the candidate's own literal match flags. It rejects both sides of duplicate source-word overlaps, and holds missing/empty/merged cells, multiline cells, altered text or forged stored source witnesses. A reviewer receives a self-contained offline HTML page, original PDF preview crops, stable SHA-based row IDs and explicit **Accept for second review only / Reject / Abstain** options, with notes. The browser can download an operator action JSON file. An intake command validates the source packet digest and exact row IDs, but reviewer identity is not authenticated, and no positive operator action is treated as independent adjudication, trusted dataset registration or publication.

## Actual source-pinned results on the 12-file Tabula-Java cohort

| Measurement | Result |
|---|---:|
| Previously generated, untrusted Camelot hybrid source row proposals | 325 |
| Rows passing stricter original nonempty, literal, nonoverlapping source checks | **68** |
| Rows blocked, with explicit source-evidence reason codes | **257** |
| Review sheets with source PDF preview images (privately created) | **3** |
| Human decisions submitted | **0** |
| Trusted dataset rows published | **0** |

The three reviewable sources are `MultiColumn.pdf` **44 rows**, `spanning_cells.pdf` **21**, and `jpeg2000.pdf` **3**. Other source candidates are still listed as blocked, including 54/54 `twotables.pdf` rows disqualified by overlapping, empty/merged or source-word disagreement checks. No source table was silently dropped from the 325-row denominator. The original-word checker used the **same first-pass original PDF SHAs and fixed hybrid candidates** rather than reselecting a better parser.

The previously published 171/325 literal source-matched row flag is a less strict quantity: a row can have literal matches that are both empty or reference reused original words. The earlier CSV intersection 135/150 on six pages is yet another separate metric and does **not** imply 135 safe-to-review rows. The new 68/325 review-ready denominator is deliberately conservative and still represents unapproved candidate evidence.

The private sheets were created on the authorized Optiplex at:
`/home/phyrexian/chatgpt-work/review-20261103/sources/tabula-locked-20261104/private-operator-review-v2/`

The reviewer uses the `*.source-review.html` files directly in a browser. Raw source PDF files, source-row text and preview screenshots remain private. A browser-render check successfully created all **44 MultiColumn cards** and a source preview screenshot. No human decisions were fabricated to test the intake.

## Original geometry failure classification

Of the original five Camelot hybrid engine errors: **three** first pages have PDF rotation 90°, **one** has offset CropBox source geometry, and **one** has otherwise uncalibrated/inconsistent Camelot table row/cell output despite upright source coordinates. Original source checks still reject all five. Their original PDF SHA, source rotation, CropBox-offset flags and error categories are recorded in the sanitized triage JSON. No coordinate transform, source PDF rewrite, or OCR repair was used to bypass the original source evidence requirement.

Versioned evidence: `examples/discovery/tabula_operator_review_queue_20261104.json`, `examples/discovery/tabula_original_geometry_blockers_20261104.json`, `scripts/tabula_operator_review_pilot_20261104.py`, and `scripts/tabula_geometry_blockers_20261104.py`; synthetic regression controls and HTML rendering live in Research Drive #91.

**Release remains HOLD.** Source and row review are not full table completeness or financial semantics. A real human operator must submit decisions; a separate independently verified reviewer must resolve any positive claims before any publisher dataset consideration. No draft merges or production deployment.
