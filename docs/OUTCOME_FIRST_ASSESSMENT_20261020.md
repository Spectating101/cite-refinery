# Outcome-first assessment — Cite–Refinery (20 October 2026)

## Decision: usable evidence-navigation demo; not yet an independent discovery product

The practical output is a *problem dossier*: a defined issue, source-level academic and institutional evidence, candidate interventions, missing measurements, and specific questions an investigator should resolve next. The existing source-reviewed Taiwan roaming-dog acceptance case achieves that representation; it identifies that Taiwan's 2024 vs 2022 roaming-dog population point-estimate decrease was reported as statistically nonsignificant, and that Talea's lack of sighting photographs leaves a gap with photo-based individual-reconciliation workflows. **That case was manually source-reviewed and is not proof of autonomous discovery** (see `docs/PRODUCT_ACCEPTANCE_FREE_ROAMING_DOGS_02.md`).

The broader 63-source emergent atlas presents eight candidate areas and plausible follow-up questions, but the relationship accuracy, novelty, and real user benefit are unknown. It describes nearly every intervention domain using an unqualified *NO verified deployed intervention or measured outcome* form. This is a product-quality issue, not a benefit.

The richer 232-source corpus is a source collection, **not** a 232-source interpreted atlas: nine development inputs were mapped in the new shard, the remaining development material has not been fully mapped, and the 66 held-out records have no independent reviewer labels. GitTrend-style curation and our external adapters currently give navigation leads, not investigated conclusions.

## External falsification case — heat health warning programs

The automatically generated 63-source global atlas's heat domain states: *there is NO verified deployed intervention or measured outcome demonstrating empirical reductions in heatwave-attributable clinical morbidity or mortality resulting from these warning mechanisms.*

**Counterevidence outside that selected source manifest:** Hess et al. (2018), *Building Resilience to Climate Change: Pilot Evaluation of the Impact of India's First Heat Action Plan on All-Cause Mortality*, DOI 10.1155/2018/7973519, evaluated Ahmedabad's heat action plan with pre/post observational all-cause mortality data. It reported an **estimated 1,190 average annual avoided deaths** after implementation (95% CI: 162–2,218). But the ecological design cannot prove the plan caused that decline; authors note confounding and an analysis excluding 2010 that was no longer statistically significant.

- Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC6236972/
- Publication: https://doi.org/10.1155/2018/7973519
- The Ahmedabad article/DOI does not appear in the previous 63-source manifest.
- This is **not a sealed-holdout result**, and it does not establish the accuracy of all 8 domains.
- A defensible conclusion is: **the retrieved source set did not substantiate a causal mortality reduction; observational evidence of post-intervention reductions exists elsewhere; further appraisal is required**.
- Therefore the original global no-outcome wording is *overgeneralized*, not necessarily disproof of the underlying implementation.

## Root cause and narrow prevention

`open_corpus_atlas.synthesis_prompt` explicitly instructed models to say **NO verified** outcome. It did not adequately constrain negative claims to the retrieved source universe. Revised synthesis instructions now distinguish *not found in these sources* from *nonexistent in the world*, distinguish associations from causal impact, and retain source-specific endpoint boundaries. `validate_synthesis` rejects a targeted pattern of **unscoped 'no verified/no measured' assertions** in candidate intervention nodes. This is a limited lexical safeguard, not a semantic evidence reviewer. The original frozen atlas has **not** been rewritten, and no sealed evaluation material was exposed.

## Actual user-facing output we have earned

**Credible in a source-reviewed example:** organized, traceable problem evidence; visibility into implementation/method mismatches; explicitly open questions.

**Not earned by autonomous evaluation:** comprehensive problem discovery, globally justified statements of missing interventions, validated causal assessments, reliable identification of novel cross-domain solutions, time savings over an equivalent assistant, or adoption.

**Product direction:** a useful first screen should provide a few substantiated *discrepancy / solution-fit / missing-measurement* findings and suggested actions, not graph totals. A graph is the supporting evidence structure, never a claim of product value on its own.

**Next outcome trial:** choose one already-developed, non-holdout problem (e.g., Taiwan dog monitoring), freeze a short source set and real decision, have Cite–Refinery independently produce a one-page problem dossier, then compare its genuinely supported findings and decision changes to an equally equipped assistant. External reviewer checks factual scope and missed counterevidence. Advance only if meaningful, independently judged gains emerge. Do **not** touch the 66 sealed holdout while developing this workflow.
