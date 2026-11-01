# Atlas — Multi-source discovery intake v1

**Status:** experimental opt-in collection / original-source review queue, *not* a comprehensive technology, scientific or legal map. Built on the headless change inbox from Atlas PR #130. Separate from the external-tool adoption experiments frozen in PR #135.

## Why

An internal GitHub PR inventory tells us which projects and implementations we own. A practical cross-domain map must additionally discover open implementations, scientific mechanisms and findings, data, model assets, regulatory changes, public demand, security advisories, funding and procurement opportunities. It must also preserve source identity and independent verification boundaries.

## Source landscape

The source catalog at `examples/discovery/source_catalog.json` enumerates **93 candidate providers** (not 93 installed/working connectors). Each entry records category, source, possible access mechanism and readiness. Exactly **13 bounded source adapters** are implemented in this first pass:

- Software: GitHub Signals public CSV, GitHub repository search, npm package search, PyPI release RSS.
- Science: OpenAlex works, Crossref works, arXiv daily AI Atom feed.
- Models/datasets: Hugging Face model and dataset listings, DataCite DOI records, Zenodo published records.
- Community: Hacker News Algolia story index (community claims, not factual validation).
- Public policy: US Federal Register document search (US-only; not a substitute for authoritative applicability review).

These are representative starters, not an exhaustive or canonical census. The GitHub Signals CSV is a currently published download and might be narrower than the provider's total claimed historical archive. Provider selection, search ranking and sampling limits introduce major selection bias. The arXiv feed can be empty on days when there are no new entries.

Other catalog sources include: patent registries, standards bodies, security advisory feeds, EU TED procurement, USAspending, SBIR, grant providers, economy/market data, governmental data portals in Taiwan and Indonesia, CourtListener, EU legislation, media intelligence and financial disclosures.

**Readiness flags:** `implemented_live` means code exists for an opt-in evaluation, not deployment guarantee. `catalog_only` indicates no adapter exists; `needs_auth` and `needs_rights` require reviewed access or licensing. The SBIR API reported maintenance at the time of scouting.

## Live collection

Authentication is never embedded in files. The GitHub Search adapter uses the local authenticated GitHub CLI; the other implemented adapters read official public endpoints. All requests are bounded, with fixed endpoint constructors, fixed domains, no HTTP redirects, modest per-source records, 14-second HTTP timeout and response-size limits.

Local example (use an already authorized machine):

    PYTHONPATH=src python -m cite_refinery.multi_source_discovery \
      --manifest examples/discovery/sample_sources.json \
      --out ~/.local/share/atlas-discovery/first-run

A second small example exercises DataCite, Zenodo, Hacker News and the Federal Register:

    PYTHONPATH=src python -m cite_refinery.multi_source_discovery \
      --manifest examples/discovery/sample_sources_additional.json \
      --out ~/.local/share/atlas-discovery/second-run

Each source manifest must explicitly specify provider, bounded search term or feed type, review tags, project targets, and result cap. Source selection is opt-in: there is no unattended global crawl or scheduler. No user-supplied URLs are fetched and no third-party content is executed.

Outputs are owner-only files outside Git trees, never overwritten:

- `collection.json`: source statuses, records, stable provider identities and cross-source **same-identity candidates**.
- `headless_records.json`: candidate-only records compatible with the existing `cite_refinery.headless_intelligence` record-list feed.

The collector deliberately keeps observations separate if their titles resemble each other. It only proposes same-identity grouping for stable exact identities such as DOI or GitHub repository slug. A same-identity match does **not** mean independent scientific corroboration. Claims, product capabilities, demand, legal applicability or security findings are not verified by ingestion.

To wire this into the existing headless inbox, create a **private local** feeds config whose `record_list` path points to `headless_records.json`, and an explicit project registry whose `feeds` include that feed. Use `cite_refinery.headless_intelligence` to poll, and `cite_refinery.development_steering` to generate source-bound candidate briefs. The private portfolio paths and collected results must remain local, and the project owner retains final authority.

## Verified first two runs (2026-11-02, Optiplex)

The primary manifest queried 9 providers: 8 returned 8 records each; arXiv returned a valid empty feed, giving **64 candidates** and two proposed cross-provider entity matches. The additional manifest queried 4 more public providers and returned **32 candidates**. Total: 96 **metadata observations** across 13 source adapter trials (12 nonempty).

The primary run's 64 records were successfully ingested by the existing Atlas headless inbox (64 created / 0 errors) and its review-only project steering across five explicitly configured project targets. These routing results are **source-target/tag matches**, not independently validated semantic relevance. Some source-level tags are intentionally broad and produce noisy recommendations. This is a known limitation to fix before large-scale scheduling.

## Acceptance / next phase

1. Establish exact provider terms, rights, authentication, quotas, source freshness and the ability to disable each adapter independently; pin source API schemas where possible.
2. Validate against held-out high-quality examples: correct identification of an overlooked repo, paper, dataset, regulation and procurement opportunity, with false-positive and missed-discovery tracking.
3. Replace broad project-level tags with **capability-and-requirement matching** anchored to the verified portfolio registry. Route unsupported matches to an abstention pool.
4. Add source-specific diff/ETag/pagination strategies; do not confuse latest top-N sample with a comprehensive change history. Preserve deletions, corrections and negative findings.
5. Gradually enable more of the 93 cataloged sources based on demonstrated coverage gain, source rights, failure rate and running cost. Government/scientific original-source checks remain under native owners.
6. Compare Atlas discovery against GitHub Signals alone, a capable general agent, and a manually curated list on a pre-registered benchmark.

**Do not:** merge into public semantic graph, automatically adopt discovered packages, perform public allegations, schedule unbounded scraping, execute supplier contacts, trade, or treat source counts/stars/citations as validation.

## Tests

    PYTHONPATH=src python -m unittest discover -s tests -p 'test_multi_source_discovery.py' -v

Tests use offline provider fixtures and cover fixed-domain safety, 13 providers, exact DOI/repository identity, candidate status, absence of auto-upgrade, private immutable output and explicit partial/unavailable statuses.
