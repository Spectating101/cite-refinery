# Source-connected opportunity atlas v2

21 October 2026. Stacked on PR #74. Mapping, not target selection.

## What is actually connected

This pass joins *published institutional requirement descriptions* to *public repository capability descriptions* across six broad fields, with an optional research-source reading only when the mechanism warrants it.

The evidence stages are separate:
- Practical: published government or institutional procurement requirements, not independently measured operating loss, and not necessarily open tenders.
- Academic: development-only source-reading summaries, still unverified model paraphrases; no original scholarly text claim is promoted.
- Implementation: repository metadata and three further original README inspections; not code execution, actual deployments, or code rights.
- Economic: possible reuse vs delivery duties vs counterparties. No proven customer, monetization gap, or project-to-contract eligibility.

## Observations, not validation scores

From the 48 previously sampled TED publications, the source-level pass retrieved 18 notice descriptions via the official TED v3 Search API, including notice type. Of those selected: sixteen competition notices, one prior-information notice and one voluntary-ex-ante notice. Competitions are *published procurement context*; they are not assumed active or bidder-eligible. The voluntarily published Maltese negotiated procedure is explicitly not an open opportunity.

Cross-sector model reasoning was applied to these descriptions and 13–18 repository descriptions per sector. It returned 17 source-anchored proposals: three possible component fits, three broad functional-category links and eleven technically poor-fit illustrations. All are hypotheses; the prompt intentionally asks for useful wrong-fits, so these numbers are NOT a population error rate.

The source boundary enforces literal anchors from both the published work description and repository description, with exact source IDs. This ensures text-grounding, NOT correctness of the proposed relation. The renderer flags alleged missing repository features requiring further code review.

**No academic reading was credibly attached to these 17 links.** This reflects mechanism mismatch between the bounded 63-source development corpus and these particular procurement descriptions. It is neither a reason to invent citations nor proof that relevant science doesn't exist.

## The most plausible component-level connections

1. [Italian health-system energy-management services](https://ted.europa.eu/en/notice/-/detail/725724-2026) ↔ [u9n/dlms-cosem](https://github.com/u9n/dlms-cosem). The repository README at blob f699f429 documents DLMS/COSEM protocol functionality including APDU operations, HDLC and TCP client transport. This may help with energy-meter telemetry but does not deliver utility management, personnel, security, billing or a turnkey service. No Italian meter compatibility, licensing or institutional operational requirements have been verified.
2. [Swedavia airport asset-data platform](https://ted.europa.eu/en/notice/-/detail/718613-2026) ↔ [OpenDataLoader PDF](https://github.com/opendataloader-project/opendataloader-pdf). The official description calls for on-prem property-portal replacement and drawing/document access across ten airports. README blob e4907dc describes PDF-to-Markdown/JSON/HTML extraction. It might be a document-ingestion component, not an airport asset-management or CAD document workflow.
3. [Malta crop-identification system, negotiated-procedure notice](https://ted.europa.eu/en/notice/-/detail/606356-2026) ↔ [FarmVibes.AI](https://github.com/microsoft/farmvibes-ai). README blob 83ee475 documents multispectral remote sensing, geospatial fusion and crop classification examples. Potential reusable model/data preparation pieces, but no verified Malta-specific workflow, agricultural regulatory compliance or procurement access.

The three README checks are documentation-only. No software was cloned or run, and no product was integrated. None is selected as a target.

## Rejections and exclusions are equally useful

- WorldMonitor's public geopolitical situation monitoring is not evidence that it fulfills a Luxembourg internal operational risk-management system with RCSA, incidents, controls and policy tracking.
- OpenBB market analytics is not an off-the-shelf university enterprise governance/ERM platform.
- Apache Airflow DAG scheduling is not a human-staffed facilities-management service or turnkey board-governance solution.
- USGS EGRET river-water statistics is not physical harbor maintenance or soil supervision during highway construction.
- Biopython sequence analysis is not a national health enterprise integration platform.
- A household pantry inventory application is not a municipal food wholesale contractor.

These negative comparisons are model-originated interpretations of available source descriptions. They are not exhaustive evidence that a repository cannot be extended. Source-level negative claims have a specific warning flag.

## Inspect the artifacts

- [Readable connected atlas](../research_materials/opportunity_atlas/CONNECTED_ATLAS.md): the interpretation, underlying source excerpts, next tests, sector gaps and wrong-fit cases.
- [Typed source-connected graph](../research_materials/opportunity_atlas/connected_source_graph.json): notice/asset/research nodes, candidate relations and explicit no-authority markers.
- [TED work descriptions](../research_materials/opportunity_atlas/ted_notice_source_details.json): selected public descriptions and lifecycle classifications.
- [Original README scope checks](../research_materials/opportunity_atlas/repository_documentation_checks.json): three candidate components, commit SHA and technical limitations.
- [Per-sector inputs](../research_materials/opportunity_atlas/source_connection_inputs/) and [validated model proposals](../research_materials/opportunity_atlas/source_connection_results/): source-bounded assessments, model raw transcripts excluded from Git.

## Reproduce the documented connections

The CLI modules are cite_refinery.opportunity_atlas_source_input (assemble source-bound sector inputs), cite_refinery.opportunity_atlas_bridge (prepare/validate model predictions), cite_refinery.opportunity_atlas_notice_details (inspect published TED notice descriptions) and cite_refinery.opportunity_atlas_connected (assemble graph and Markdown).

The source corpora in PR #70 remain frozen, including the sealed 66-record holdout. No buyer or maintainer contacted, no bid submitted, no claimed rights, and no new standalone product launched.

## Next mapping work

The supply and institutional-requirements graphs now have explicit, auditable candidate links, but the **practical problem and mechanism layers remain thin**. Next spread the net over documented operational problems and measured failure/cost mechanisms beyond procurement; then trace real original research to the *same* mechanism and inspect smaller sets of implementation code. Continue mapping before prioritization or outreach. A true arbitrage conclusion requires operational fit, rights, identifiable buyer need and captured economic value.
