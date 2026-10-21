# Cite–Refinery original-source verification: first broad standalone-map audit

**Observed:** 21 October 2026. **Scope:** independent *source identity / metadata* verification only, performed by the focused PR #99 GitHub Actions workflow, not validation of practical outcomes, academic conclusions or executable implementation quality.

## Frozen source universes

The baseline PR #98 maps stay unchanged: 9 reported Practical claims + 48 distinct notice metadata leads; 47 Academic abstract/index leads; 1,287 distinct GitHub Implementation metadata leads in 44 source search categories. Of 1,360 repository/category memberships, 220 had provisional model metadata judgments and 1,140 remained unreviewed.

Original audit inputs were the exact public manifests and balanced unreviewed-category backlog. No source was selected based on promise of commercialization or a preferred vertical. **None of this audit establishes a complete map of the world.**

## Independent Academic identity audit

Two public-source verification runs provide useful, *sometimes different*, bibliographic metadata.

| Measure | First CI run | Second CI run with OpenAlex fallback |
|---|---:|---:|
| Original scholarly leads | 47 | 47 |
| DOI identities confirmed by Crossref | 35 | 26 |
| Original work IDs or DOIs confirmed by OpenAlex in fallback | Not attempted | 21 |
| Total exact external identity confirmations | 35 | **47** |
| Previously missing publication-year fields recovered | 16 | **16** |
| Method, effect-size, full-text, or peer-review checks | **0** | **0** |

In the first run, nine DOI lookups were **HTTP 429 rate-limited** by Crossref; three original OpenAlex work-ID entries had no DOI in the source snapshot. **None of these twelve records was a demonstrated fake or invalid publication**. In the second run, fallback OpenAlex singleton lookups confirmed the previously unresolved identities, retaining separate API and date provenance.

### One real metadata disagreement — do not correct automatically

- Original source: **OA-0c2db6ec316fbc**, *Contamination of indoor dust and air by polychlorinated biphenyls and brominated flame retardants and relevance of non-dietary exposure in Vietnamese informal e-waste recycling sites*.
- The original source snapshot reports publication year **2012**.
- First-run **Crossref** bibliographic record reports **2013**, with a matching title.
- Second-run **OpenAlex** record reports **2012**.
- This may reflect a distinction between early online publication and another formal publication date, or changing publisher/index metadata. **The audit does not establish which year should be used as the canonical bibliographic year.** Retain both source-qualified values and verify the article's own publication dates in the publisher record before resolving.

This is exactly why the map should retain *provenance and disagreement*, not reduce two independent source reports to an arbitrary number or model vote.

## Independent Implementation source audit

From the 88-item deterministic unreviewed review backlog (two original repository/category pairs per each of the 44 GitHub search categories), the breadth-first pass selected **one pair per category**.

| Observation | Source-verified count |
|---|---:|
| Distinct original source categories inspected | **44 / 44** |
| Distinct public repositories reached by source identity | **44** |
| Exact default-branch source revisions pinned and repository root inspected | **44** |
| Root contains a test/spec directory (not tests executed) | **25** |
| Root contains a license/COPYING-named file (not rights clearance) | **37** |
| Root contains a README-like file (not independently read/verified) | **44** |
| Original functional test commands executed by this broad audit | **0** |
| Source reuse permission independently cleared | **0** |
| Independently proven adoption deficit or underconversion | **0** |

Root filename presence is a useful triage feature **only**. Repositories without a test directory may have tests elsewhere; those with one may not work. Metadata SPDX labels do not determine every transitive licensing obligation. The original source SHA is a reproducible inspection anchor, not a test pass.

The remaining 44 source-category pairs in the 88-pair backlog have **not** been audited by this run; the other 1,052 unreviewed category memberships are not covered by this original-source pass. The existence of 44 source revisions does not validate the underlying semantic category assignments.

## Persistent reproducibility and download

- First source-audit GitHub Actions run: https://github.com/Spectating101/cite-refinery/actions/runs/39614043554 (Crossref-only result and initial source checks).
- Second successful source-audit run: https://github.com/Spectating101/cite-refinery/actions/runs/39615130051 (Crossref plus OpenAlex fallback).
- Both were run on the PR #99 branch using a read-only GitHub Actions token for GitHub API data, against the original frozen corpus. They published JSON files for Academic and Implementation audits, baseline + enriched three-layer maps, a Markdown coverage report and the still-unreviewed implementation backlog.
- GitHub Actions artifacts have **temporary seven-day retention**, so the machine-readable source receipts should be downloaded and, if approved, persisted in long-lived versioned storage. This document preserves the empirical sample limits and findings even if those CI artifacts expire.

The source-audit implementation is intentionally restricted to API identity checks and explicit rejection of false scientific/technical promotion. The core three-layer atlas accepts the checked source facts as *additional metadata*, never as final evidence that a Practical claim, academic mechanism or technical capability works.

## Next map quality objectives

**Practical / Nocturnal** is currently the weakest source family: collect firsthand observation datasets, dated operator processes, independent program outcome series and differing institutional perspectives, not more guesses from scientific abstracts or procurement listings.

**Academic / Cite:** inspect original article full-text methods/results and publisher version/date history; separately evaluate contradictory studies, retractability, measurement quality and provenance, not just metadata identity.

**Implementation / Refinery:** extend original source inspection to the remaining review backlog, independently test diverse sample components at pinned commits, include non-GitHub forges, hardware/open design assets, public datasets and operational tools. Evaluate semantic category polysemy before claiming technical alignment.

**Do not resume optimizing between-layer monetization or arbitrage rankings until standalone within-layer coverage, truthfulness and navigational utility improve materially.**
