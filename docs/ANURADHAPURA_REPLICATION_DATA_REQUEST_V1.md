# Anuradhapura CNVR study — replication material request (prepared, NOT sent)

**Purpose:** assess whether the published Table T3 annual negative-binomial results and Table T6 buffer-zone estimates can be reproduced from the same analysis inputs and program definitions. Request study data only from the authors under their permitted data-sharing and ethics terms.

**Paper:** *Long-term evaluation of a zoned catch-neuter-vaccinate-release program integrating owner engagement and buffer zone* (Veterinary World, 2026), DOI 10.14202/vetworld.2026.2816-2849, deposited JATS PMC13500148.

## Existing independent checks

The article's Table T2 publishes program-level counts and effort by year, zone and program. We transcribed **80 program rows**, of which **68 have positive catching days**, and checked the 20 printed zone/year subtotals. All printed subtotal column totals match their source program rows. One 2023/Zone 1 subtotal has an **unlabelled** program-number cell in the JATS source.

Two entries merit clarification, without assuming an error:
- **2023, Zone 3, Program 2:** reported total 62, male 11 and female 47 (sum 58).
- **2024, Zone 3, Program 1:** reported total 120, male 49 and female 87 (sum 136).

We fitted **12 separately specified R/MASS negative-binomial models** over Table T2 counts: inclusion/exclusion of the buffer zone, annual vs program grain, and total/male/female outcomes. The authors' reported Table T3 numbers are not exactly reproduced by any of these simplified specifications. An annual aggregate fit has only **five annual data points**, and some fitted dispersion values are extremely large, raising stability concerns. This discrepancy **does not establish a mistake in the article**: the published Table T2 may not contain the authors' exact T3 analysis inputs, cleaning conventions, or model implementation.

The article explicitly acknowledges that supplementary data can be requested from the corresponding author. It also acknowledges the absence of systematic community-wide dog surveys and incomplete program-boundary human rabies/PEP/bite data. We are not requesting unavailable data to be invented.

## Minimum viable data package — requested for legitimate research verification

- **Dataset definitions:** data dictionary, unit of observation, study boundaries, date/year coding, definition of "total", "male", "female", ownership category, "dogs requiring sterilization", "buffer" and "program"; handling of missing/unknown sex and duplicate individuals.
- **Table T2/T3 exact analysis source:** the anonymous program-day or annual count dataset actually used for each of the nine Table T3 demographic models, including catching effort, inclusion/exclusion of buffer programs, program identifiers and zeros; date of snapshot and any exclusions or recodes.
- **Tables T6A/B/C exact analysis source:** year, zone, period, sex, catching days, number of dogs in each zone and the **program-aligned buffer total** that entered Zone:Period:Buffer Total interactions, plus exact lag variable definitions and intervention timing.
- **Statistical implementation:** R version, packages and versions, runnable scripts for Tables T3/T6, model formulas and contrasts, method for confidence intervals/p-values, dispersion estimation and convergence warnings, model diagnostic outputs, any source-level validation checks, and decisions on multiple sex-by-zone comparisons.
- **Two specific printed rows:** clarification of the 2023 Zone 3 Program 2 and 2024 Zone 3 Program 1 sex sums; explanation of the unlabeled 2023 Zone 1 subtotal, if relevant.
- **Public-health data, only if held and lawful:** what geographically matched and de-identified dog bites/PEP/rabies outcomes, if any, were actually available; otherwise confirmation that analysis cannot establish those effects.

A minimal response consisting of **the exact aggregate model input frames and analysis scripts** would already allow a meaningful numerical audit; individual-level dog or person records are **not necessary** if aggregate study inputs reproduce the published model. Do not request personal contact details, names, precise household locations or confidential health records.

## Unsent draft request

**Subject:** Research reproducibility request — Anuradhapura CNVR study (Veterinary World, 2026)

Dear Corresponding Author,

I am examining the statistical methods and reported estimates in your 2026 Veterinary World article on the long-term Anuradhapura CNVR program (DOI: 10.14202/vetworld.2026.2816-2849). I saw the Data Availability statement indicating that supplementary material can be provided upon request.

Would it be possible to share the de-identified **analysis-ready data and R scripts** used to produce Tables 3 and 6A–6C, particularly the year/zone/program catching-effort definitions and the buffer-intervention interaction inputs? I am interested in understanding how the annual and program-level observations were aggregated, as reproducing the published estimates from the summarized Table 2 alone has not been exact.

I also noticed two possible Table 2 reporting discrepancies that I would appreciate clarification on: in 2023, Zone 3, Program 2, the male and female counts sum to 58 while the reported total is 62; in 2024, Zone 3, Program 1, they sum to 136 while the reported total is 120. I understand there may be coding or reporting conventions behind these differences.

I do not require any identifiable animal owners' or patients' records, and I would be glad to follow the study's data-access and ethics conditions. An anonymous model input frame or an analysis codebook would already be helpful.

Thank you for considering this request.

Best regards,
[Researcher name and institution]

## Status and boundaries

- **Not sent.** No data-access agreement has been entered and no author reply has been received.
- The research team has **not** reproduced the original Tables T3/T6 with the authors' unreleased analysis inputs.
- Public source tables and independent sensitivity results are audit leads, not a basis for allegations or automatic graph acceptance.
- Await author's data definitions/analysis scripts, then re-run preregistered models without retroactive parameter tuning.
