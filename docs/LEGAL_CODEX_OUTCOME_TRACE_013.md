# Global Legal Codex — Milestone 013: remediation outcome trace

**Research cutoff:** 15 November 2026. **Status:** machine-validated official administrative snapshots, not original-byte authentication, case-specific payout verification, independent legal review or proven causal effectiveness.

## Question

After legal and institutional failures in the UK Horizon and Dutch childcare-benefits cases were acknowledged, what administrative redress is documented, and what remains to be demonstrated?

**Critical distinction:** received case records, persons with convictions quashed, offers, accepted settlements, money actually paid, recognized affected parents, completed programme assessments and decided objections are **not interchangeable counts or units**.

## Official reporting sources and reference dates

- UK Ministry of Justice 2024 Act casework summary; **data 15 September 2026, published 24 September**:
  https://www.gov.uk/government/publications/post-office-horizon-system-offences-act-2024-quashed-convictions-management-information/summary-quashed-convictions-management-information-24-september-2026
- UK Horizon redress report; **data 30 October 2026, updated 13 November**:
  https://www.gov.uk/government/publications/post-office-horizon-financial-redress-and-legal-costs-data-for-2026/post-office-horizon-financial-redress-data-as-of-30-october-2026
- UK corrected September redress; **data 30 September, corrected 13 November**:
  https://www.gov.uk/government/publications/post-office-horizon-financial-redress-and-legal-costs-data-for-2026/post-office-horizon-financial-redress-data-as-of-30-september-2026
  Correction notice and details: https://www.gov.uk/government/publications/post-office-horizon-financial-redress-and-legal-costs-data-for-2026
- Dutch UHT programme dashboard; **dated 16 October 2026** (dynamic publication date not independently established):
  https://herstel.toeslagen.nl/dashboard-kinderopvangtoeslag/
- Dutch ministerial additional-damages update, **18 September 2026**:
  https://www.rijksoverheid.nl/actueel/nieuws/2026/09/18/steeds-meer-ouders-ronden-hun-aanvullende-schade-af

Source-page URLs are official, but the Milestone 013 evaluator does not capture byte-level archives, certify signatures, independently audit the statistics or establish individual case outcomes.

## United Kingdom: legal restoration versus scheme payments

The MoJ summary reports **1,011 traceable received and assessed case records**, **620 individuals** with at least one conviction quashed by the **2024 Act**, and **584 of those individuals notified**. These are not equivalent to the 42 individual appellants in the 2021 Hamilton judgment (39 appeals allowed, three dismissed).

Distinct scheme categories as at **30 October 2026**:

| Scheme | Full claims received | Settled/accepted | Offer not yet accepted | Under assessment |
| --- | ---: | ---: | ---: | ---: |
| HCRS (convictions) | 545 | 515 | 14 | 16 |
| HSS (shortfalls) | 14,901 | 13,541 | 582 | 778 |
| GLO (group litigation) | 492 | 463 | 26 | 3 |
| HSSA (shortfall appeals) | 173 | 28 | 86 | 59 |

HSS and HSSA claimant journeys may overlap. HCRS includes transfers from the closed OC scheme. Accepted settlements may still await payment. No stage fraction measures nationwide overall remedy effectiveness.

The headline **approximately GBP 1,756 million** cumulative paid across Horizon schemes includes interim payments. Approximate rounded categories: HSS 1,106m; HSSA 18m; GLO 237m; HCRS 326m; closed OC 68m. The rounded components sum to 1,755m, not 1,756m; this does not indicate a discrepancy in an audited individual ledger, as the amounts are rounded and their reporting rules differ.

**Correction gate:** on **13 November 2026**, the department corrected September total from **GBP 1,731m to GBP 1,727m**, and September HSSA payments from **GBP 22m to GBP 18m**. A revision of previously reported data must not be counted as new payments or negative recovered cash. This pilot pins the corrected amount and retains the superseded value as an explicit correction event.

## Netherlands: administrative classifications versus effective relief

The UHT dashboard's **16 October 2026** snapshot reports:
- **69,738 registrations**: **44,131 recognized as harmed** and **25,607 not recognized**.
- **69,517 comprehensive assessment processes marked completed**; preliminary notification or opt-out can be included, so this is not a count of fully compensated individuals.
- **18,886 objections**: **13,570 decisions issued**, **5,316 pending**. A decision does not imply the objection was successful.
- **12,377 admissible CWS additional-damages applications**: 1,964 advice issued; 669 awaiting treatment; 714 in review; 304 on hold; 8,726 no longer in review. The last category **does not mean fully paid**.
- Dutch government reported **approximately 4,500 parents** with completed additional-damages processes as of **18 September**. This is approximate and a separate date/cohort.
- Published cash categories: EUR 795.5m after first test, EUR 1.76bn after comprehensive assessment, and EUR 42.1m for actual damages. They are reported channel-specific figures, not an independently reconciled country-wide total and not directly comparable to UK pounds.

The national programme does not prove the individual claimant's post-remittal remedy in **ECLI:NL:RVS:2019:3535** (entitlement) or **3536** (recovery). The missing primary administrative re-decisions are still the decisive gap.

## Code and reproducibility

- src/cite_refinery/legal_codex_outcome_trace.py — validates five official-source locators, as-of dates, immutable source figures, cohort units, stage partitions, reported money types and correction history for both overall and HSSA September payments; no inter-country causal comparisons.
- examples/legal_codex_outcome_trace_013.json — eleven distinct cohorts, eleven monetary categories, two official September corrections, three **context-only** judgment references and four unverified individual-record requests.
- tests/test_legal_codex_outcome_trace_013.py — adversarial tests rejecting fake original archives, case/person/claims conflation, stale amount, invalid stage/denominator, currency mixing, individual-payment inference, foreign law transfer and forged judicial links.
- Candidate-only semantic graph; **no aggregate link to individual court holding establishes payment, culpability or causation.**

Commands:

    PYTHONPATH=src python -m unittest discover -s tests -p 'test_legal_codex_outcome_trace_013.py' -v
    PYTHONPATH=src python -m unittest discover -s tests -p 'test_legal_codex*.py' -v
    PYTHONPATH=src python -m cite_refinery.legal_codex_outcome_trace examples/legal_codex_outcome_trace_013.json --output /tmp/outcome-013.json --packet /tmp/outcome-013-graph.json

## Original-record and implementation handoff

1. **Capture and authenticate original public statistics** in Nocturnal with real TLS, SHA-256 of raw/source text, extraction checks, timestamp and source metadata; keep all failures visible. Retain durable controlled copies beyond GitHub Actions 30-day artifacts.
2. **Version and reconcile corrections** across reporting dates without overwriting previous source editions; 13 November UK correction is the first regression fixture.
3. **Find the 2021 Hamilton-to-2024 scheme legal/person crosswalk** and payment confirmations through lawful, privacy-protecting access. A national scheme total does not reveal which of the 42 appellate cases obtained redress.
4. **Obtain the Dutch administrative follow-up decisions** after 2019 ECLI:3535 and 3536, including original orders and appeal/cash outcomes with protected identities redacted. Aggregate 2026 figures are not evidence of these individual cases.
5. Only then design independent outcome-effectiveness estimates with defined eligible denominators, observation windows and disconfirming evidence. Legal/editorial sign-off required.

**Next target, Milestone 014:** an append-only source snapshot vault, original-data hash and page/section anchors, correction-aware time-series comparisons, and an identity-protected individual outcome registry. The Indonesia Chromebook original June 2020 PPK appointment and corresponding e-order are still unverified; no PPID request has been submitted.

**No publication, personal-liability finding or global policy effectiveness ranking is authorized.**
