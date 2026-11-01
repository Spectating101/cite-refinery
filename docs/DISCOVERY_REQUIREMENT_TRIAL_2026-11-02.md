# Atlas Discovery Challenge 001 — First live capability-matching and history evaluation

**Date:** November 2, 2026 (Asia/Taipei). **Status:** Experimental, source-review only.
**Upstream base:** Atlas multi-source intake PR #137, itself stacked on headless inbox PR #130.
**Owner:** Atlas coordinates candidate discovery; Nocturnal, Policy Lab, Research Drive and Cite-Agent retain separate acceptance authority.

## Predeclared task

Ask whether the existing discovery sources can surface specific *candidate capabilities or evaluation artifacts* relevant to four real portfolio gaps:

1. Policy Lab: PV plant time-series fault/anomaly diagnosis, scientific-quality controls and independent holdouts.
2. Nocturnal: capture and preservation of volatile online evidence with traceable custody.
3. Research Drive: original-cell, row and header correctness across PDF-to-table extraction.
4. Cite-Agent: citation-bounded research claim verification.

The new code in `src/cite_refinery/discovery_capability_review.py` accepts an explicit requirement manifest with mandatory concept groups and optional review-order terms. It **abstains** when these groups are not found in title/short provider description. Results are labeled `SOURCE_REVIEW_NEEDED`, not ready, adopted, verified or authoritative. The score is simply an explainable review-order heuristic, NOT a truth score.

### Reproduce locally

Run the existing PR #137 collector with the 11 explicitly configured searches in `examples/discovery/focused_live_sources.json`. This will make **read-only requests to public providers** and create private local snapshots.

    PYTHONPATH=src python -m cite_refinery.multi_source_discovery \
      --manifest examples/discovery/focused_live_sources.json \
      --out ~/.local/share/atlas-discovery/my-run

Then screen using the predeclared concept groups:

    PYTHONPATH=src python -m cite_refinery.discovery_capability_review \
      --collection ~/.local/share/atlas-discovery/my-run/collection.json \
      --requirements examples/discovery/capability_requirements_v1.json \
      --out ~/.local/share/atlas-discovery/my-review

For a repeat run, supply a different output directory to collector and pass `--previous` with the prior `collection.json` to the review CLI. It outputs a `observation_changes.json` comparison. A vanished search result is never described as deleted source content.

Do not commit the collected source snapshots, upstream external text, credentials, or private portfolio details to public GitHub.

## Actual observations

**Live run A:** 11 configured source searches: GitHub Signals (2 queries), GitHub Search (4), OpenAlex (2), Crossref, DataCite, Zenodo. All 11 returned usable results. 70 raw candidate records across them. Per-requirement lexical matches: Policy Lab 26; Nocturnal 8; Research Drive 8; Cite-Agent 15. **13 distinct records matched none**. Matches can overlap; the 57 sum of per-requirement matches is not a claim of 57 independent suitable capabilities.

**Live run B:** repeated those same queries in a fresh bounded snapshot: 70 records. The history comparator found **1 newly observed, 1 revised observation, 1 not observed in the latest sample** (all GitHub Search); other record identities were stable. These search windows are sampled/latest lists rather than a full synchronized provider changefeed. Provider payload shifts can appear as revisions without material capability change.

**Source-specific baseline observation:** In this narrow benchmark GitHub Signals offered 4 records from the two archive/citation queries, none of which ranked in the top displayed requirement-level recommendations. This is evidence for **source complementarity within these query choices**, not a general estimate of its recall or value. OpenAlex/DataCite and GitHub Search yielded the most directly relevant items in this first sample.

## Independent original-source spot-check

The checked-in `examples/discovery/first_trial_spot_check.json` contains nine **nonrandom top-candidate cases** with exact discovered ID, original-source link, and an applicability verdict. Results:

- **4 on-scope benchmark leads**, not functional approvals.
- **4 off-scope** despite matching the two mandatory keyword groups.
- **1 insufficient evidence** because original README/implementation evidence was unavailable on inspection.

Notable on-scope leads:

- [PV fault-diagnosis leakage benchmark](https://zenodo.org/records/23646443): Zenodo metadata describes 3 public sources including NREL PVDAQ, leakage-aware protocols and 360 injected fault episodes. It is *derived data + code*, and original datasets must still be obtained under appropriate permissions.
- [FHC Twin-Plant PV time-series dataset](https://zenodo.org/records/18979876): Zenodo metadata records paired plants, 30-second DC string and environmental measurements. A plausible alternative/holdout for Policy Lab; no experiment executed against Policy Lab.
- [PDF Table Traps](https://github.com/LydiaTools/pdf-table-traps): original README and source files describe reproducible row/header/cell failure checks against real PDFs. An actionable Research Drive evaluation fixture, subject to independent source checks.
- [RefVerifier academic paper](https://arxiv.org/abs/2609.07652): literature claim verifier evaluated on manuscripts; authors report 71% verdict accuracy on eight manuscripts. Candidate benchmark architecture for Cite-Agent, not proof of reliability.

**Important negative case:** the top three "web archiving" GitHub repos included a Microsoft WebView2 runtime-binary mirror, an ordinary Next.js site, and an agency marketing site—**not evidence-grade web capture tools**. Another PV result was about PV **cell** imagery rather than plant-level time series. Source names and topic keywords were misleading, highlighting a serious need for original-source and modality verification.

The nine observations were selected for diagnostic evaluation; they are not a representative precision estimate. No code from external projects was installed, executed or silently incorporated. No existing project behavior changed.

## Safety and interpretation

- Require exact original-source assessment before promotion to an accepted capability. A good paper/data record alone does not demonstrate accessible code, valid methodology, licensing or scientific transferability.
- Source metadata, author-supplied abstracts and repository READMEs are claims or documentation, not independent correctness evidence.
- Nocturnal still retains editorial hold and human reviewed case attribution; neither an archive nor metadata validates allegations.
- Policy Lab still retains instrument/source verification and domain acceptance, independent of the Atlas screen.
- No economic value or funded opportunities were established by this test.
- Do not infer deletions from re-ranking, incomplete windows, API timeouts or errors.

## Decision / next rigorous gate

**Accept as a useful first scouting prototype, not as a production recommendation engine.** Trial demonstrated source diversity, exact-identity extraction, ability to screen against portfolio requirements, and conservative historical comparisons. But it also showed excessive false positives.

Before advancing: improve capability/modality matching with independently grounded original-source excerpts, pre-register held-out positives/negatives, score precision/recall/abstention against a manually reviewed representative sample, and compare with GitHub-only and frontier-agent baselines under equal budgets. Only then may specific owners authorize isolated adapter or dataset acceptance benchmarks.

**No merges, scheduler, dependencies, deployments, scientific claims, investigations, purchases or external contact authorized.**
