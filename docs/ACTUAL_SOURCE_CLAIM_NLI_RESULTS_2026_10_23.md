# Executed source-claim intelligence audit: authentic published XML + two real NLI models

**2026-10-23 · Source-anchored development evaluation. NOT an independently adjudicated source-claim quality score.**

## Original publication identity was independently confirmed

- Europe PMC fixed public JATS XML: `https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13500148/fullTextXML`
- Verified primary article DOI: `10.14202/vetworld.2026.2816-2849`; PMCID: `PMC13500148`.
- **Independently downloaded original XML SHA-256: `4210e7ebc871f3db31dee6cb761f09d82e4f29f49aceed6a860c268e74176b7e` — exactly matches the previously frozen 21-case casebook's `source_sha256`.**
- Original XML contains the numerical text anchors `1,368`, `484`, `0.55488235`, `0.835`, `0.038`, `0.0003`. All six were observed by the primary-source audit, but their individual positions, table header semantic relationship and original excerpt offset claims remain unverified in the NLI run.
- Independent original-source CI: https://github.com/Spectating101/cite-refinery/actions/runs/39955451187 — five safety/source tests passed and actual Europe PMC fetch succeeded.
- NLI CI now refuses to run if the newly downloaded article SHA or DOI differs from the historical source casebook; it preserves separate original-source and per-model review artifacts, without rehosting article full text.

This establishes **article identity and matching original publisher snapshot provenance**, not independent correctness of author-curated source interpretations or figure/table extraction.

## Authentic pretrained NLI run and fixed gate

Primary dual-model workflow: https://github.com/Spectating101/cite-refinery/actions/runs/39954767783 — **SUCCESS**. Models executed on CPU with `sentence-transformers==5.1.2`, exact HF source revisions, and the same frozen inputs:

- MiniLM `cross-encoder/nli-MiniLM2-L6-H768` @ `f3b1e8aac2451320dfe2ce56673b3f2ec63e6f03`.
- DeBERTa `cross-encoder/nli-deberta-v3-small` @ `e9890682d9e4279b7ae6d0fcfb435a43206280ec`.

Twenty-one investigator-selected cases: eight entailed, eight contradicted, three overreach, two unresolved. Four precommitted *cross-swapped original-evidence* pairs deliberately mismatch a claim and a different excerpt. Neither model received the reference label. **Four-way scientific adjudication is more demanding than these pretrained three-label NLI classifiers.**

Precommitted policy for both models: softmax top class at least **0.90**, margin to next probability at least **0.20**, *neutral always abstains*, and all results **review candidates only** (never accepted scientific facts).

| Outcome | MiniLM NLI | DeBERTa-v3-small NLI |
|---|---:|---:|
| Original case + source-swap comparisons | 25 | 25 |
| Abstained | **24** | **21** |
| Candidate supported | **0** | **2** |
| Correctly identified supported claims (of 8) | **0** | **2** |
| Candidate contradicted | 1 | 2 |
| Correctly identified contradicted claims (of 8) | 1 | 1 |
| False candidate contradictions vs curated reference | 0 | **1** |
| False candidate supports vs curated reference | 0 | 0 |
| Unresolved cases abstained (of 2) | 2 | 2 |
| Overreach cases abstained (of 3) | 3 | 2 |
| Mismatched original evidence controls abstained (of 4) | 4 | 4 |

**Neither is a viable standalone scientific claim-interpretation engine.** Both conservatively abstain on most true-source cases, failing to recognize nearly all the supported and contradicted claims. Zero false support candidates is not a demonstrated precision win when models almost always abstain.

## Exact observed errors and source-scope insights

The *unthresholded* MiniLM label maxima for eight curated entailed cases: three entailment, five neutral; eight contradicted: two contradiction, six neutral. DeBERTa unthresholded: five entailment and three neutral for entailed cases; one contradiction, six neutral and one entailment for contradicted cases. All four unrelated-source swaps were classed neutral by both; this is encouraging but source-swapped negatives are synthetic and not independent external validation.

- **B01** (specific count of dogs requiring sterilization): DeBERTa candidate support probability **0.919**; MiniLM top entailment **0.797**, abstains.
- **B03** (false statistically significant decline, Table 3 p=0.55488235): both models class **neutral** rather than clearly rejecting the numerical assertion.
- **B06** (source p=0.038): both models did not pass threshold for candidate support; numerical table interpretation is weak.
- **B13** (false precise quantification of local human rabies impact): both produced correctly grounded candidate contradiction, their clearest consistent signal.
- **B15** (Bonferroni illustrative p=0.0003 test): DeBERTa candidate support probability **0.990**.
- **B16** (falsely equates pre/post and buffer interaction estimands): DeBERTa high-confidence **contradiction 0.995**, but the investigator's four-way label is **overreach**; precise logical/type distinctions remain imperfect.
- **B20/B21** (cannot know inaccessible re-estimation or future independent replication): both abstain.
- **SWAP-01...04**: both abstain; no incorrect confident source-support recommendation.

These illustrate why a source-claim judge must understand **method, population, numbers, estimands, provenance and missing evidence**, not merely natural-language similarity.

## Engineering decision: an important negative benchmark, not a product upgrade

Retain the original verified publication source, casebook, per-model real score artifacts and fail-closed review gate as development evidence, but **DO NOT** set either NLI model as the universal Atlas claim verifier or automatically accept their outputs. These models may help prioritize an analyst's review queue, but current utility is weak and uncalibrated.

The next strong end-to-end test should **reuse our existing authorized, source-grounded generative reasoning path** and compare it with a baseline on original source passages **independently verified at exact character offsets**, table parsing and scoped numerical checks. Add separate human-adjudicated, out-of-development cases—including legally approved Nocturnal investigations and actual pinned Implementation code execution—before measuring cross-layer opportunity accuracy. Do not build another model-serving engine on the basis of these examples.

The former archived 18/21 source-scope model result used a different LLM and four-label rubric and is not directly comparable to this three-class NLI triage replay. No Academic sealed holdout identities, private Nocturnal matter, graph promotion, field validation, commercial benefit or independently adjudicated scientific gold were produced. The full repository-wide test workflow remains red on separate optional runtime/environment failures; this focused NLI/source gate passed.
