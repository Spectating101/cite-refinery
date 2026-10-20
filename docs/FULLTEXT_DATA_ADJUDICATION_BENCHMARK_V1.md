# Full-text, data provenance and blinded semantic benchmark — v1

**2026-10-20 — Cite-Refinery — experimental research validation**

This branch addresses the previous investigator's main gaps: reliance on abstracts, inability to distinguish original from comparator data, and absence of an inspectable diagnostic evaluation.

## 1. Full-text Anuradhapura intervention audit

The original study is Nanayakkara, Wijayawardana and Jayasekara (2026), Veterinary World 19(7), pp. 2816–2849, DOI https://doi.org/10.14202/vetworld.2026.2816-2849. The genuine deposited JATS XML is available at https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13500148/fullTextXML.

The new Cite-Refinery fulltext_audit module parses scholarly article metadata, titled methods sections, numbered tables, and data availability statements. The complete source XML is retained locally, not redistributed as a new source file. The report records the XML SHA-256 for auditability.

| Source | Verified published value | Interpretation |
|---|---|---|
| Abstract/results | Dogs *requiring sterilization*: 1,368 (2021) to 484 (2025) | An eligibility subset, not total dog abundance |
| Table T3 | Total effort-adjusted count IRR 1.03, p=0.55488235, CI 0.93–1.14 | No significant trend at 0.05 |
| Table T6B | Zone 1 male pre/post catch-rate p=0.835 | Not significant |
| Table T6C | Zone 1 male buffer-interaction IRR 0.9955 per buffer dog, p=0.038 | Distinct estimand, nominal association |
| Table T6C | Zone 3 female buffer-interaction IRR 0.9943, p=0.0003 | Distinct nominal association |

The pre/post and buffer-interaction estimands are not interchangeable. An illustrative six-comparison Bonferroni sensitivity would use 0.05/6 = 0.00833: p=0.038 fails that hypothetical threshold; p=0.0003 survives. **This is not proof that these six tests are the prespecified inferential family.**

The authors explicitly acknowledge lacking resources for systematic community-wide dog surveys, and they lacked sufficiently complete within-study-area dog bite, human post-exposure prophylaxis and confirmed rabies outcome series to quantify direct public-health effects. They also say catching days were decreased in response to apparently declining dog numbers, creating a material sensitivity around their effort offset.

The DATA AVAILABILITY section states that the supplementary data can be made available **from the corresponding author upon request**. Original individual-level captures, exact analysis scripts and causal claims are therefore **not independently reproduced**. The fulltext audit is an **internal published-source consistency check**, not independent raw-data replication.

Reports: research_materials/runtime_trials/fulltext_dog_20261020/fulltext_audit.json and method_excerpts_and_tables.json.

## 2. Real open research data and code — separate comparator

Smith et al. (2022), PLOS ONE, DOI https://doi.org/10.1371/journal.pone.0266636, lists this actual public repository:
https://github.com/lauren-smith-r/Smith-et-al-Population-dynamics-free-roaming-dogs

Its clone was pinned at commit 2cd2e6bf9e9298875766ca947cb6b44036484855.

- 235 individual identified dogs in Pescara, Italy, and Lviv, Ukraine (not Anuradhapura).
- 567 sighting events across 15 repeated survey variables, independently recounted with Python and R 4.5.0.
- 40 published population-size estimate rows, with 40 numerically ordered confidence intervals.
- Actual capture-resighting records, R scripts, a Stan model, model output and file SHA-256 fingerprints are present.
- The Stan posterior has **not been refitted**: the local R runtime lacks rstan. Python/R descriptive replay is *not* posterior replication.
- No standalone LICENSE was found in the research repository checkout. Avoid bundling its raw files pending proper reuse/licensing review.

Reports: reproducibility_manifest.json. The original Sri Lankan article's missing data must not be substituted with this comparator's observations.

## 3. Real blind diagnostic benchmark

A frozen, inspectable diagnostic suite contains **21 source-anchored reference cases**, built directly from cited tables and study limitation statements. Cases include direct numeric entailment, false statistical significance, confusion between two model estimands, claims about actual dog abundance, sampling/causality overreach, source availability and separate country datasets.

The benchmark prompt strips reference labels and gold explanations before calling GPT-6.1 through the authenticated Codex session.

**Actual 2026-10-20 GPT-6.1 trial:**

- 18 of 21 reference labels matched: 85.7% on this *small, curated test only*.
- 8/8 directly supported cases correctly classified.
- 8/8 directly contradicted cases correctly classified.
- 2/3 overreach cases and **0/2 insufficient-evidence cases** correctly classified.
- No false positive entailment, one false contradiction, and **zero abstentions**.
- The model disagreed on B16 (one disputed boundary between overreach and contradiction), and chose overreach rather than unresolved for B20/B21.

**Do not describe this as general scientific accuracy.** Reference labels were constructed in this implementation from the published article. B16's label boundary is itself a good candidate for independent expert adjudication. The test chiefly shows **an abstention/epistemic-calibration failure**, despite good performance on easy numerical cases. The original reference labels have not been retroactively adjusted to inflate the result.

Results: benchmark_cases.json, benchmark_results.json, benchmark_results.raw_response.json.

## 4. Independent human-review infrastructure — not fictitious human agreement

Cite-Refinery now exports a blind_reviewer_packet.json with claims and evidence **but without gold reference labels or explanations**, plus an independent_reviewer_template.json with empty answers. The blind_review module validates completed reviewer submissions, checks consistent dataset fingerprints and separate reviewer identifiers, calculates raw agreement/Cohen's kappa, and produces an explicit disagreement queue.

No independent human reviews have been obtained. No independent panel approval, new gold-standard data, or model independence is claimed. Reviewer identities and expertise require verification outside the repository, and unresolved disagreements require genuine adjudication before using such labels as external reference truth.

## Reproduce

1. Fetch the PMC13500148 JATS XML from the public Europe PMC endpoint using the fulltext_source function in Cite-Refinery and save it to a disposable local file.
2. Run scripts/build_fulltext_research_case.py with arguments --xml LOCAL_JATS_FILE and --out OUTPUT_DIRECTORY. This generates methods/table evidence, audit and diagnostic reference cases.
3. Shallow-clone the public PLOS comparator repo, pin its commit, and pass the local checkout to audit_published_dog_repo in Cite-Refinery's research_data_audit module.
4. Run scripts/run_adjudication_benchmark_v1.py using --cases benchmark_cases.json and --out RESULTS.json. For an authorized model supply --provider codex --model gpt-6.1-sol, or supply an externally authored JSON using --response-json.
5. Export the blind reviewer packet and seek two genuinely independent domain experts for future submissions. Do not manufacture expert identities or accept synthetic adjudications.

All code can be tested offline using the committed bounded source excerpts, tables and reference fixtures. Research source retrieval, model invocation and scientific data access are separate explicit steps. Nothing has been merged, deployed or automatically promoted to accepted knowledge.

## Next evidence requirements

For true Anuradhapura replication, the corresponding author would need to provide authorized access to program/day/zone/sex/ownership records, dog-level capture histories or counts, sterilization and vaccination denominators, buffer intervention timing, geographic coverage, exact R GLM scripts and convergence diagnostics, confounder/DAG data, multiple-comparison procedures, and suitably privacy-protected within-area health outcomes. The author request has not been sent.

A real scientifically independent benchmark requires external expert annotations on unseen cases and, where possible, a different permitted reasoning provider. A high score on this internally curated set must not be used for automatic authority promotion.

## Live integration into the persistent investigator

The original investigation CLI now offers the opt-in init flag **--fulltext-enrichment**. When enabled, each research collection round can add up to two bounded JATS full-text methods/results extracts to scholarly abstract leads carrying valid PMC accession identifiers. The source is downloaded from the archived public Europe PMC fullTextXML endpoint, parsed with the same structure-preserving JATS parser, and shortened to at most 7,500 characters; no whole manuscript is sent indiscriminately to the LLM. Failed JATS retrieval does not erase the abstract; it records a separately reviewable fulltext_enrichment_failure. The original DOI, PMCID, XML digest and explicit same-study parent link are preserved in LLM input and graph provenance so two excerpts from one paper are **never described as independent replication**.

Actual source integration was tested on the original Anuradhapura study: PMC13500148 produced a 7,286-character methods/limitations/results/table JATS research passage, source identifier JATS-2cb34d5325b7, tagged as belonging to DOI 10.14202/vetworld.2026.2816-2849. A controller fixture test confirms the opt-in stage automatically appends the enriched scholarly source without dropping the abstract or treating it as a separate study. The existing two-round investigation is intentionally left unchanged; this flag applies to new or resumed opt-in sessions.

Example: cite-refinery-investigate --workspace /tmp/my-investigations init --question 'Why are field counts poor proxies for free-roaming dog abundance?' --modules path/to/modules.json --max-rounds 2 --fulltext-enrichment
