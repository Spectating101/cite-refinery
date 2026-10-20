# Rich public evidence dump and frozen blind evaluation (v1)

**20 October 2026. Cite-Refinery experimental source research.**

This branch extends the original 63-source semantic atlas (PR #69) into richer, heterogeneous documents and deliberately freezes evaluation material before any new model run.

## Actual public material collected

| Acquisition channel | New records | Actual contents |
|---|---:|---|
| Europe PMC public Open Access | 79 | Article XML, abstracts and multiple full-text sections |
| World Bank Documents & Reports | 50 | Downloaded report text, not mere search snippets |
| Zenodo public records | 48 | Dataset descriptions and file inventories, **not underlying dataset values** |
| **Total** | **177** | **386,207 extracted words** |

Twelve broad collection topics covered urban heat, e-waste, food redistribution, animal health, floods, batteries, schools, gig work, drinking water, housing, disability access and healthcare waste. One retrieval failed (HTTP error). Two World Bank search categories yielded no usable text report; no substitutes were invented.

The source access routes are documented at [Europe PMC](https://europepmc.org/RestfulWebService), [World Bank](https://documents.worldbank.org/en/publication/documents-reports/api) and [Zenodo](https://developers.zenodo.org/).

## Frozen development-versus-evaluation split

The 177 new records were checked against all 63 earlier references using canonical URLs, DOI aliases (when present) and normalized publication titles. Eight previous overlaps were discarded. This leaves **232 combined unique records**: the original 63 and 169 eligible new.

| Purpose | Records |
|---|---:|
| New development documents | 103 |
| **Held out from new mapping** | **66** |
| Held-out entire housing and transport-access strata | 29 |
| Held-out documents from remaining strata | 37 |

Holdout identity and text digests were cryptographically sealed in the immutable source manifest. Re-freezing the same destination fails instead of quietly reshuffling test membership. The development-only mapping input contains **zero held-out IDs** and omits all collection-quota IDs and the previous hand-defined semantic modules.

Two short development items failed the minimum mapping passage length, so **101 new documents** are mapper-ready. Full source records remain in the restricted archive. Model inputs are bounded to 9,000-character excerpts and have separate source fingerprints.

**Unseen means the records were never sent to the new Cite-Refinery mapper.** It does not imply no model ever saw the publications during pretraining or that all related topics were absent from the earlier atlas.

## Live compatibility trial

The authenticated Gemini 3.8 Flash Medium backend mapped nine new development-only excerpts, including full-text papers, an official report, and dataset descriptions. Quote and source-ID validators accepted **nine candidate readings, five local problem clusters, one candidate relation and four open questions**. These are not independent semantic accuracy scores.

The remaining 92 development mapping inputs have not yet been completely mapped in this branch. The held-out 66 were never used for generation or evaluation.

## Local source archive

The complete and legally sensitive publisher extracts stay in a permission-restricted directory on Optiplex:

    /home/phyrexian/ResearchDumps/cite-refinery/richer_corpus_20261020/

The local archived package:

    richer_corpus_and_frozen_holdout_20261020.tar.gz

contains the complete new source materials, private split, development-only records, frozen receipt and a **66-source blank blinded annotation packet**. Each blinded packet record contains original source passages and blank fields for an independent reviewer, with no model classifications or graph labels. **Zero human annotations have been completed.**

Only shareable titles, URLs, hashes, candidate paraphrases, aggregate acquisition statistics and the holdout seal are committed to GitHub. Neither full source text nor the held-out documents are published in the PR.

## Command-line workflow

    cite-refinery-rich-corpus --workspace /private/corpus collect

    cite-refinery-rich-corpus --workspace /private/corpus \
      --previous-corpus /private/old/private_corpus.json freeze

    cite-refinery-rich-corpus --workspace /private/corpus prepare

    cite-refinery-rich-corpus --workspace /private/corpus annotation-packet

The safe mapping input is the development-only export named development_mapper_input.json. Place it into a separate development mapping directory as private_corpus.json before invoking the existing cite-refinery-corpus-map command. Do not ever point the mapper to private_partition.json or to the sealed annotation packet.

## What is established and what is not

Established: sources from three genuine repositories; actual longer article/report extracts rather than abstract-only entries; traceable SHA-256 provenance; deterministic identity-aware deduplication; segregated 103/66 development/holdout; no overlap leakage into new model input; real nine-source mapping smoke; reusable code and regression coverage.

Not established: independent blind annotator accuracy; universal problem coverage; observed causal effects; independently confirmed implementation outcomes; full scientific validation of underlying studies; actual Zenodo data observations; production deployment or merged branch.

Next: independently annotate the sealed holdout before estimating role-specific precision, evidence-scope false promotion, false cross-domain relationships, and completeness.
