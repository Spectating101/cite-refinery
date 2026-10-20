# Broad opportunity atlas — reconnaissance first, targeting later
2026-10-21. Independent branch stacked on draft Cite–Refinery PR #73. This is a **mapping** release, not an opportunity ranking or commercialization claim.

## What changed

We stepped away from selecting a single GitHub repository or use case. The purpose now is to build a reusable, cross-field source and capability landscape:

**Practical need and operating loss ↔ underlying scientific or engineering mechanism ↔ implementation inventory ↔ public requirements and conversion channels.**

Four evidence streams are kept separate. A documented problem does not imply a solution; software's existence does not imply field deployment; an institutional procurement notice does not imply eligibility or budget for our company; and no amount of GitHub attention proves an economically underconverted project.

## Breadth actually inspected

**Implementation supply:** two complementary GitHub topical search frames spanning 44 domain categories in six umbrellas (engineering; energy and environment; physical operations; public services; research/data; investigation/finance). The primary relevance-ordered frame retrieved 753 unique public repositories; a second recently active **5–300-star** frame retrieved 605. Deduplication produced **1,287 distinct repositories** across 88 bounded topic searches. This is a discoverability sample, not a full census, a market map or 1,287 economic opportunities.

**Semantic hygiene:** an authenticated Gemini 3.8 Flash Medium checked public descriptions/topics for the five most prominent results in each domain, 220 domain/repository pair assessments. It labeled 35 as **different meaning** and 6 as insufficient description. Examples: “flood” returned DDoS traffic tools, “repair” returned JSON/software repair utilities, “battery” returned laptop status and power-management utilities, and “supply chain” mixed package-security tools with physical supply chains. These labels are *model interpretations of repo metadata*, not an independent code audit. The remaining 1,140 repo-domain memberships are not semantically reviewed and are preserved as unknown.

**Demand context:** authenticated no-key EU TED public Search API returned **48 published notices**, sampled across 14 cross-sector queries. We intentionally used **ALL** historical published notices, not active-only eligibility. Their identity, buyer names, titles and publication dates may indicate institutional requirements but say nothing about whether the user can currently bid, whether funding remains, or whether software in this registry satisfies an RFP. No notice has been linked as a contracted buyer to a specific repo.

**Evidence-discovery channels:** 34 practical, scholarly, implementation, demand and market-context resources indexed. Only GitHub topical searches and EU TED notices were bulk-sampled in this branch; others are reusable access points, not ingested datasets. The catalogue includes 3ie, OpenAlex, Europe PMC, OpenAIRE, World Bank Projects, HDX, OECD OPSI, ecosyste.ms, Digital Public Goods, OSHWA, government procurement, GitHub issues, funding programs and paid-contributor marketplaces.

**Reasoning structure:** 21 cross-domain mechanisms and 12 distinct conversion pathways are recorded as structured, falsifiable *hypotheses*. Each mechanism has an explicit practical problem question, scientific requirement, implementation question and economic question. None is accepted as technical compatibility or profit evidence merely because both fields share a keyword.

## The significant discoveries are structural, not numerical

1. **Discovery platforms are not enough.** GitHub topic matching can be semantically wrong even at the most prominent results. A generic repo ranker is not an opportunity intelligence system. The new atlas records model-audited relevance separately and never automatically chooses the top search result as the right implementation.
2. **Supply and demand are different evidence universes.** Public GitHub repositories disclose technology availability; TED notices disclose some published institutional requirements; they cannot be paired credibly without checking a shared mechanism, program scope, procurement eligibility, and the actual scope of the source repository.
3. **Cross-field opportunities often concern conversion rather than invention.** Engineering simulation and physical diagnostics; offline field capture and statistical inference; scientific insight and verified production deployment; public audit requirements and provenance; software support and contributor contracts. These are possible *interfaces between abilities and needs*, not automatically identified customers.
4. **The absence of buyers is informative.** Across the wide GitHub inventory, company revenue, deployment success, maintained-service availability, buyer evidence and conversion rights remain unknown. Pretending to fill them with popularity metrics recreates the Cite-Agent failure mode in a new form.
5. **The same project can serve several conversion routes.** An asset might be reusable first-party infrastructure, suitable for a managed deployment, a licensed integration, or a maintainer service. Those rights, counterparty, failure economics and operator needs differ, and selection must wait until they are known.

## Sample cross-domain investigative lines, not chosen targets

- **Engineering ↔ environmental monitoring:** instrumented measurements can connect sensors, chemical/physical validity, source provenance and real field monitoring. The missing evidence is actual sensor performance, standards and who pays for longitudinal service.
- **Engineering ↔ circular economy:** a repairable component plus validated failure-mode knowledge could enable refurbishment, but only after estimating acquisition, parts, scrap, warranty, labor and resale outcomes.
- **Data science ↔ institutional decision making:** open evidence graphs and scientific methods could support audit and monitoring contracts where a decision maker needs explainable outcomes. Source citations are insufficient unless reasoning can survive independent validation.
- **Nonprofit logistics ↔ operations engineering:** time-sensitive supply allocation could reuse inventory/dispatch systems, but temporal, safety, geographic and beneficiary constraints determine whether they really fit.
- **Energy ↔ program finance:** existing electrical control tools may address a renewable/microgrid problem, but grid-code compliance, installation, counterfactual savings and contract eligibility are economic gates.
- **OSINT ↔ public accountability:** claim tracing and document graphing can assist investigations, but source duplication, attribution and legal restrictions make unverified entity graph edges dangerous.

These represent **where to deepen the map**, not what to buy, develop, bid on, or pitch tomorrow.

## Read the actual artifacts

- [Full generated atlas](../research_materials/opportunity_atlas/OPPORTUNITY_ATLAS.md) — field coverage, mechanism crosswalk, public procurement examples, conversion routes, source channels.
- [Machine-readable network](../research_materials/opportunity_atlas/atlas_network.json) — source-bound repo-domain memberships, semantic-review status, mechanism hypotheses, source channels and notice context.
- [Primary GitHub survey](../research_materials/opportunity_atlas/github_repository_survey.json) and [lower-visibility survey](../research_materials/opportunity_atlas/github_frontier_repository_survey.json).
- [Semantic review batches](../research_materials/opportunity_atlas/semantic_review_batch_1.json) (four files, numbered 1–4).
- [TED published-notice sample](../research_materials/opportunity_atlas/ted_published_notice_context.json).
- [Mechanism and conversion-route inventory](../research_materials/opportunity_atlas/mechanism_crosswalk.json).
- [Source channels](../research_materials/opportunity_atlas/source_channel_registry.json).

## Bounded reproduction

    PYTHONPATH=src python3 -m cite_refinery.opportunity_atlas_collect \
      research_materials/opportunity_atlas/survey_manifest.json \
      --output /tmp/github_primary.json

    PYTHONPATH=src python3 -m cite_refinery.opportunity_atlas_collect \
      research_materials/opportunity_atlas/frontier_survey_manifest.json \
      --output /tmp/github_frontier.json

    PYTHONPATH=src python3 -m cite_refinery.opportunity_atlas_ted \
      research_materials/opportunity_atlas/ted_survey_manifest.json \
      --output /tmp/ted_context.json

    PYTHONPATH=src python3 -m cite_refinery.opportunity_atlas \
      --survey research_materials/opportunity_atlas/github_repository_survey.json \
      --frontier research_materials/opportunity_atlas/github_frontier_repository_survey.json \
      --channels research_materials/opportunity_atlas/source_channel_registry.json \
      --mechanisms research_materials/opportunity_atlas/mechanism_crosswalk.json \
      --ted research_materials/opportunity_atlas/ted_published_notice_context.json \
      --review research_materials/opportunity_atlas/semantic_review_batch_1.json \
      --review research_materials/opportunity_atlas/semantic_review_batch_2.json \
      --review research_materials/opportunity_atlas/semantic_review_batch_3.json \
      --review research_materials/opportunity_atlas/semantic_review_batch_4.json \
      --output /tmp/opportunity_atlas_network.json --markdown /tmp/opportunity_atlas.md

Model metadata audits were run against a bounded public subset; source code and independent deployment histories have not been replayed. The model code to reproduce audit prompts and strictly validate complete batches is in opportunity_atlas_semantic.py.

## Where to spread the net next — still mapping, no targeting

- Harvest specific documented operational problems beyond the handful already curated for Cite–Refinery; record mechanisms, affected groups and source-supported losses with scientific confidence and dates.
- Extend software inventory to other source forges (ecosyste.ms), public-sector OSS registries, scientific-software inventories and open hardware build records. GitHub is a biased subset of possible assets.
- Expand institution/demand sources outside EU TED: Taiwan government procurement, World Bank notices, SAM.gov (API key needed), UNGM (API authentication), published maintainer paid-contribution processes and actual bounties. **Eligibility and active state must be verified**.
- Review the actual source code, design and documentation of selected *samples* within each area to calibrate metadata relevance, not to choose a commercialization target early.
- Only after both problem-source coverage and functional implementation coverage are meaningful should the engine propose provisional evidence-bounded matches. Compare those matches to human review before prioritization.

**Freeze retained:** No additions to the original PR #70 corpus or its sealed 66-source holdout. This atlas is a separate, public discovery inventory, not a replacement for source-grounded research.
