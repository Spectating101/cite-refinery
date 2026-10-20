# Anuradhapura Table T2 — partial statistical reanalysis

**20 October 2026 · Cite-Refinery research validation; no access to the study's unpublished data**

## Attribution and scope

Primary source: Nanayakkara et al. (2026), Veterinary World, DOI 10.14202/vetworld.2026.2816-2849, PMC13500148. The deposited JATS full text gives **Creative Commons Attribution 4.0** permissions: https://creativecommons.org/licenses/by/4.0/. This package transcribes and transforms the *published Table T2* to a CSV for validation, with a pinned XML checksum. It does not contain the author's separately held supplemental records.

## Reconstructed table

| Verification | Finding |
|---|---:|
| Program rows excluding subtotals | **80** |
| Positive catching-day rows | **68** |
| Zero-day/zero-count rows omitted from log-offset refit | **12** |
| Printed year/zone subtotals reconciled to columnwise contributing rows | **20** |
| Program rows where male + female differs from Total | **2** |
| Unlabelled publisher subtotal (2023, Zone 1) | **1** |

The sex-count inconsistencies are **2023 Zone 3 Program 2** (Total 62, 11 male + 47 female = 58) and **2024 Zone 3 Program 1** (Total 120, 49 male + 87 female = 136). They are present in the deposited publication itself. No numbers were changed or corrected, and the reason for the discrepancies remains unknown. The 2023 Zone 1 printed subtotal has a blank Program no. cell; the parser handles only this specific known case and preserves its provenance. All 20 printed year/zone subtotals agree with source columnwise program sums.

Files: table2_programs_from_publication.csv and published_program_table_quality.json under research_materials/runtime_trials/fulltext_dog_20261020.

## Refit specification

The authors describe a negative-binomial Year trend with log(catching days) offset. The exact model-ready dataset and R scripts are unavailable. We tested **12 specified sensitivity fits** using R MASS::glm.nb, crossing:

- Inner zones only versus including the buffer.
- Five annual aggregate observations versus positive-day individual program rows.
- Total versus male versus female counts.

All use Year indexed to 2021 and an explicit log(Days) offset. No invented, repaired or imputed counts.

| Total-count variant | Refit IRR | Refit p-value |
|---|---:|---:|
| Inner zones, annual totals | 0.9759 | 0.0540 |
| Inner zones plus buffer, annual totals | 1.0185 | 0.0708 |
| Inner zones, program-level observations | 1.0021 | 0.9401 |
| Inner plus buffer, program observations | 1.0378 | 0.2297 |
| **Published Table T3 (author result)** | **1.03** | **0.5549** |

None of our 12 candidate fits reproduces **both** the author-reported IRR and p-value within the explicit tolerances of 0.005. Some estimates are numerically close in IRR alone. At least one annual fit has an extremely large estimated dispersion, suggesting practical non-identifiability near a Poisson limit with n=5.

**This is not evidence that the original author analysis is wrong.** The paper may have used a differently cleaned/subsetted dataset, coding definitions, timing, true program records or alternative fitting choices that Table T2 does not expose. Without exact scripts and model inputs, there is no identified causal or numerical error to attribute.

The Table T6C Zone × Period × Buffer Total model remains **unreproduced**: the published table does not supply the aligned program-level contemporaneous buffer exposures and controls needed to recreate its design matrix.

Files: table2_nb_sensitivity.json (all model coefficients, p-values, estimates of theta and warnings) and replication_assessment.json (guardrailed interpretation and exact model comparison).

## Reproduce

First retrieve the official article JATS XML through the Europe PMC API, and save to a disposable local path, for example /tmp/anuradhapura.xml. The full XML is not committed. Use the published_table_reanalysis module to parse Table T2 and write the CSV/quality audit.

Then execute:

    Rscript --vanilla scripts/refit_published_table2_nb.R research_materials/runtime_trials/fulltext_dog_20261020/table2_programs_from_publication.csv research_materials/runtime_trials/fulltext_dog_20261020/table2_nb_sensitivity.json

    python scripts/summarize_published_table_replication.py --table-quality research_materials/runtime_trials/fulltext_dog_20261020/published_program_table_quality.json --models research_materials/runtime_trials/fulltext_dog_20261020/table2_nb_sensitivity.json --out research_materials/runtime_trials/fulltext_dog_20261020/replication_assessment.json

The committed Python tests validate original-row arithmetic and the frozen diagnostic report without requiring R; direct model reruns require installed MASS and jsonlite.

## Next scientific step

The precise **unsent** source-data request is prepared in docs/ANURADHAPURA_REPLICATION_DATA_REQUEST_V1.md. It asks for author-approved exact Table T3 and Table T6 analysis frames, model scripts, data definitions and the interpretation of the two within-row sex-total inconsistencies. No author was contacted.

The proper status of this branch is **public-source numerical sensitivity and specific unresolved discrepancies**, not replication of the original operational dataset and not validated evidence of improved rabies outcomes.
