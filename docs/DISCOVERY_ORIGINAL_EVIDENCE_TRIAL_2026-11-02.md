# Atlas Discovery Challenge 002 — Source Evidence and Retrieval Strategy

**Date:** 2026-11-02 (Asia/Taipei)
**Status:** Experimental. Documentation-supported review only; no functional, scientific, or security certification.
**Dependency:** PR #138 (capability screening) → #137 (13-source intake) → #130 (headless change inbox).
**Scope:** Atlas discovery only; no Nocturnal, Policy Lab, Cite-Agent or Research Drive code changed. The unrelated non-HS integration freeze #135 remains in place.

## What was tested

The earlier eleven-source experiment screened 70 metadata records against four explicit project requirements: PV plant/time-series anomaly diagnosis, evidence-grade web archiving, original-cell PDF table correctness, and research claim-to-citation verification.

The first issue observed was **search ordering**. The GitHub repository-search adapter had been using `sort=updated`, which produced many generic and incidental repositories. This change makes the **GitHub API's default relevance ordering** the discovery default. `ranking: "recent"` is supported explicitly for monitoring recent activity, not used silently for technology search.

To preserve reproducibility, `examples/discovery/focused_live_sources.json` explicitly sets `ranking: "recent"` for the GitHub queries used in Challenge 001; the new `focused_relevance_sources.json` instead requests relevance. This is a *search strategy comparison*, not evidence that global search precision is universally improved.

**First live A/B probe on identical searches:**

- `web archiving`, relevance: IIPC awesome-web-archiving index, pywb, Heritrix, ArchiveBox, and a few unrelated web applications.
- `web archiving`, recently updated: largely unrelated websites, packages and unrelated tool repos.
- `pdf table extraction`, relevance: Camelot, img2table and specialized table extraction systems.
- `pdf table extraction`, recently updated: mostly small new repositories, including the useful PDF Table Traps fixture but multiple unverified implementations.

These differences establish **a meaningful qualitative improvement in candidate retrieval for this specific probe**, not a statistical assessment of recall.

## Added evidence gate

`source_evidence_gate.py` ingests an explicit subset of collected candidate IDs and independently retrieves **original-source metadata** without executing any third-party software:

- GitHub: canonical owner/repository README through authenticated `gh api`. Validates returned original-repository URL and Git blob SHA-1 from decoded contents, records SHA-256, and only scans a bounded text prefix. An oversized legitimate README (ArchiveBox) can be examined up to a fixed larger document cap; any truncation is explicit.
- Zenodo: official numeric record metadata with exact ID check, content hash and HTML-stripped abstract/description. A temporarily rate-limited record results in `ABSTAIN_ORIGINAL_UNAVAILABLE`, never false negative.
- arXiv: official Atom paper metadata, only with an operator-selected canonical original paper link and exact paper-ID check. Abstract text is author-supplied and not equivalent to peer-reviewed or independently replicated performance.

Source configuration specifies **mandatory original-source concept groups** for each project. A title-only search hit will not satisfy these groups. An obvious curated `awesome-...` repository is marked `SOURCE_REFERENCE_LIST_ONLY` instead of being treated as an implementation, even if it describes many working tools. Missing docs become **abstentions**. All successful gate outcomes say `DOC_CLAIMS_MATCH`, *not* verified implementation.

Data safety: 1–32 selected candidates per run, no arbitrary website targets, fixed official metadata endpoints, no HTTP redirects, read-only GitHub REST, limited response sizes/timeouts, no cloning/packages/code execution, no raw third-party text in the checked-in fixtures. Outputs remain private locally. No original documents are written into the public repo.

## Live evidence

**Historical original-source spot-check of nine manually reviewed candidates** (preexisting, deliberately nonrandom):

- 4 known on-scope benchmark leads, 4 known off-scope, 1 unresolved.
- Original-source gate retains **3/4 known relevant cases**, rejects or abstains on **4/4 known irrelevant cases**, and leaves the unresolved case without approval.
- Among **three gate-promoted cases**, observed precision against this tiny known set is **3/3**. One relevant PV dataset's original metadata fetch was temporarily unavailable on the first execution. Treat this as **lost coverage**, not empirical 100% precision/recall.
- The most actionable on-scope sources remained the PVDAQ leakage-aware benchmark, PDF Table Traps fixture, and RefVerifier scientific citation paper. None was executed as an integration.

**New relevance-ranked replay**, using 11 matched source queries: 70 metadata candidates again. An additional **ten original-source checks** returned:
- **3** README/record descriptions that matched all mandatory documentary requirements: [ArchiveBox](https://github.com/ArchiveBox/ArchiveBox), [img2table](https://github.com/xavctn/img2table), and [PV fault/leakage benchmark](https://zenodo.org/records/23646443).
- **6** did not establish the required full modality from the available original README (includes pywb, Heritrix and Camelot; these may be valid adjacent components and should not be labeled 'bad software').
- **1** `awesome-web-archiving` entry designated as **discovery reference**, not an archiver implementation.

This is not a population precision estimate: source choices were deliberate, the previously inspected cases influenced the design of the documentary gates, and no held-out independent corpus was scored.

## Work remaining before independent adoption or scheduling

1. Independently label a stratified held-out set across sources, domains and deceptive negative cases; evaluate **precision at a fixed review budget, recall, false positives, abstention, and source coverage** against keyword, relevance, and strong-agent baselines.
2. Differentiate *capture*, *replay*, *curated index*, *forensic metadata*, *scientific dataset*, *cell-image anomaly detection* and *plant time-series anomaly detection* as typed capabilities with explicit interoperability constraints—not just term intersections.
3. Investigate rate-limiting, cached immutable source receipts, ETag/pagination, stale/renamed source identities and provider terms before adding unattended polling.
4. Add an operator-reviewed dependency/capability edge to the existing Atlas mapping architecture only after evidence passes project-specific checks. No automatic source-to-capability claim promotion.
5. Expand the 93-source catalog only for measurable recall/diversity gains. Source count is not success; discovery-to-decision usefulness is.

## Reproduction

Use the inherited public-source collector:

    PYTHONPATH=src python -m cite_refinery.multi_source_discovery \
      --manifest examples/discovery/focused_relevance_sources.json \
      --out ~/.local/share/atlas-discovery/relevance-run

The candidate screening uses the preexisting requirement manifest:

    PYTHONPATH=src python -m cite_refinery.discovery_capability_review \
      --collection ~/.local/share/atlas-discovery/relevance-run/collection.json \
      --requirements examples/discovery/capability_requirements_v1.json \
      --out ~/.local/share/atlas-discovery/screened-run

Run the new original-source gate:

    PYTHONPATH=src python -m cite_refinery.source_evidence_gate \
      --collection ~/.local/share/atlas-discovery/relevance-run/collection.json \
      --config examples/discovery/original_source_gate_config.json \
      --cases examples/discovery/relevance_trial_cases.json \
      --out ~/.local/share/atlas-discovery/original-run

Only the comparison against the original nine manually reviewed cases may pass `--labels examples/discovery/first_trial_spot_check.json`; no labels are used by retrieval or matching. That comparison is a retrospective diagnostic, not a held-out test.

**Authority:** no merges, deployments, publishing investigative allegations, source/tool adoption, scientific claim upgrades, dependency installs, automatic source crawling or external contact.
