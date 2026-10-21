# Cite–Refinery: emergent conversion discovery with funding enablers

October 21, 2026. Corrective architecture increment after specialist branches #92–93.

## Core intent

Identify genuinely capable but underconverted projects, techniques, datasets, systems and research. Explain why their potential is unrealized; find overlooked practical needs, relevant academic mechanisms or independent technical capabilities; propose unexpected, falsifiable ways to reuse, integrate, introduce, repurpose or improve them, including for our own portfolio. The realized benefit may be technological, informational, institutional, scientific, social, operational or financial. Cash and paying customers are NOT mandatory.

Crucially **high quality and underconversion are conclusions to prove, NOT attributes inferred from GitHub stars, developer descriptions or few known adopters**. Sometimes an ignored project is ignored for an excellent reason.

Practical/Nocturnal, Academic/Cite, Implementation/Refinery remain the only THREE foundational conceptual layers. Funding is an optional enabling resource catalog, NOT a fourth layer.

## Actual implementation

The canonical Cite–Refinery investigate command now supports discover-conversions. It reuses the **existing Open Corpus emergent atlas**, its original 63-record bibliographic/official source manifest and the existing 605-repository, 44-strata GitHub survey. It neither depends on an introduced niche nor creates a separate commercial product, crawler, graph or installed CLI script.

The prompt receives **no predefined connection pairs**, ROI ranking, chosen sector, customer, financial requirement or suggested match. A stable-hash sampler covers original implementation strata across six macro areas (energy/environment, engineering, public services, finance/investigation, knowledge/data, physical operations). It can be rotated without modifying the domain logic. Each proposal must preserve original repo and research source IDs, state a concrete mechanism, explain why the relationship may be surprising, hypothesize a conversion barrier, propose the way to unlock capability, and specify a first falsifying test.

Supported discovery directions:
- Existing implementation -> practical problem.
- Academic mechanism/method -> existing implementation.
- 2–3 distinct existing implementations -> a candidate new combination, WITHOUT requiring a practical domain first.
- Domain -> domain analogy or shared constraint WITHOUT requiring an implementation first.
- Many-to-many partial links with multiple contributing assets for one need.

The discovery validator rejects nonexistent IDs, invented evidence, wrong source/domain scope, duplicate claims, fake approval of code quality, underconversion, funding or graph authority. Zero novel links is allowed. Model proposed links are ALWAYS unverified hypotheses.

## Real first experiment — NOT a benchmark of verified discoveries

The existing heterogeneous atlas comprises 63 primary source records and eight model-derived topical areas; the original implementation survey comprises 605 repos across 44 search strata. These are non-exhaustive, topic-seeded public research and GitHub samples, not the whole internet.

Two separate stable-hash repository slices: 35 and 36 source listings, covering all six macro categories. Two real Anthropic Sonnet 5.5 medium invocations proposed **6 plus 7 = 13** candidate relationships; second run originally failed our schema because it suggested two technical assets together for one practical problem. The schema was corrected to support that valid recombination and the original unchanged model response was replayed.

Examples not specified as desired pairs by the operator:

1. [Nongor offline crisis/SOS](https://github.com/AuvroIslam/Nongor) -> flood-warning last-mile delivery and outcome measurement. Unknown mesh range, authentication in field, consent, reliability and integration. NOT approved for emergency use.
2. [Argos OSINT audit-trail pattern](https://github.com/SOsintOps/Argos) -> possible evidence chain-of-custody for food redistribution evaluations. Actual nutritional outcomes remain unknown.
3. [GridShadow defensive cyber-physical research](https://github.com/Krishita17/GridShadow) + [Jackery solar state integration](https://github.com/Bigdaddy1990/jackery_solarvault) -> a possible OFFLINE simulation of aggregated behind-the-meter storage dependencies, not a tested grid device or exploitation pathway.
4. [carbon-fr](https://github.com/Kovelt/carbon-fr) -> a potential grid-intensity timing input to battery regeneration research, subject to French-region applicability and actual process economics.
5. Rabies vaccination effective coverage versus heat-warning exposure/response coverage -> a methodological analogy in the academic layer; transfer of biological herd thresholds is NOT implied.
6. [FreddyFridge](https://github.com/nadar71/FreddyFridge) + [factorysemantics-mes](https://github.com/factorysemantics/factorysemantics-mes) -> possible two-asset food redistribution and traceability combination, still entirely unexecuted.
7. [Transitland Atlas](https://github.com/transitland/transitland-atlas) -> possible context for courier work exposure analysis; not a substitute for actual platform dispatch telemetry; source GitHub license label CC-BY-4.0, so reuse permissions need review.

These are hypotheses worth falsifying, NOT thirteen verified opportunities. Source descriptions can omit important prerequisites.

### Preliminary source-quality audit

The six repositories selected in the first slice were checked against their CURRENT original public GitHub repository metadata and directory listings. Some have a tests folder or GitHub configuration; none was executed and no actual adoption or conversion deficiency was established. Published license API labels are NOT automatically full reuse authorization.

**Independent high-quality projects qualified: 0. Independently confirmed underconversion barriers: 0. Relationships promoted: 0. Realized capability value: 0.**

Read:
- [35-source slice, six hypotheses](../research_materials/opportunity_atlas/EMERGENT_CONVERSION_SLICE_0_V1.md)
- [36-source slice, seven hypotheses](../research_materials/opportunity_atlas/EMERGENT_CONVERSION_SLICE_1_V1.md)
- [original-repository metadata audit](../research_materials/opportunity_atlas/candidate_original_repo_metadata_v1.json)

The JSON artifacts retain source IDs, original URLs, original source digest references, uncertainty, and falsification tests. Raw source corpus and model receipts remain in authorized Optiplex research scratch.

## Small funding-enabler catalog

Funding is a POSSIBLE means of converting an independently viable capability or bringing people/resources together, never proof an asset is good or a buyer exists. No automatic proposal-to-funder match or fourth graph layer.

| Channel | Official reference and current caution |
|---|---|
| NLnet | [Official apply page](https://nlnet.nl/propose/) lists next general deadline **November 3, 2026 at 12:00 CET**, but specific program eligibility and AI-generated application policies matter. No verified user or project eligibility. |
| GitHub Sponsors | [Contributor sponsorship docs](https://docs.github.com/en/sponsors/receiving-sponsorships-through-github-sponsors/about-github-sponsors-for-open-source-contributors): regional and account eligibility apply; not a guaranteed sponsor. |
| Open Collective | [Open Source Collective fiscal host](https://opencollective.com/opensource/apply/intro): funds administration with advertised 10% host fee, NOT itself a grant. |
| Grants.gov | [Federal applicant eligibility information](https://grants.gov/learn-grants/grant-eligibility.html): individual NOFO jurisdiction, organizational type and program rules require verification. |
| Taiwan FINDIT | [Government-backed early-investment information and matchmaking](https://findit.sme.gov.tw/en/AboutUs), not a committed investor or open call. |
| CSG | User-specified funding acronym; meaning and official URL not verified. Keep an unresolved record, do not invent a scheme. |

All six are **resource channels**, not current eligibility confirmations, award decisions or matched investment offers. The original catalog is in funding_enablers_small_catalog_20261021.json.

## Canonical usage

~~~sh
cite-refinery investigate discover-conversions \
  --atlas research_materials/runtime_trials/open_corpus_20261020/global_atlas.json \
  --manifest research_materials/runtime_trials/open_corpus_20261020/source_manifest.json \
  --repository-survey research_materials/opportunity_atlas/github_frontier_repository_survey.json \
  --funding-catalog research_materials/opportunity_atlas/funding_enablers_small_catalog_20261021.json \
  --offset 0 --provider antigravity --model claude-sonnet-5-5-medium \
  --json-out /tmp/candidate_links.json --markdown-out /tmp/candidate_links.md
~~~

Alternatively use --model-output with previously saved raw model JSON for deterministic revalidation; --repository-audit may attach separate original GitHub metadata without claiming quality, actual adoption or realized value. Does not create an investigation workspace or external connection by itself beyond explicitly selected model calls.

## What remains genuinely necessary

1. Inspect actual original code and execute source-scoped functionality and independent tests for promising candidates. Only then begin a quality claim.
2. Investigate ACTUAL adoption/usage, maintenance constraints, license rights, integration costs and alternatives before calling a good project underconverted. A missing adoption record in our corpus is not absence of users.
3. Test a source-grounded cross-domain recombination as a reversible isolated experiment; measure whether it improves the target workflow, not whether a model found it interesting.
4. Expand source diversity beyond eight original research domains and the partial GitHub strata. Feed failure and new questions back into independent source retrieval.
5. Have independent human judges score novel matches versus a basic AI baseline on blind unfamiliar source sets: evidence-groundedness, actual quality, novelty, falsification, practical transfer and outcome utility.
6. Explore funding ONLY after actual project scope/rights/applicant eligibility becomes relevant.

Previous verified component tests, economic self-arbitrage and operator delivery remain optional downstream uses. No new standalone CLI, funding application, grant match, investment request, source permission or commercial claim was made.

**Core test remains:** discover a relationship no one thought to search for, establish that the underlying asset is genuinely capable yet underconverted, and demonstrate a concrete new use for it. This phase demonstrated the FIRST step only.
