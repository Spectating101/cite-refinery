# From three-layer evidence to externally grounded conversion routes

21 October 2026. Draft successor to Cite–Refinery PR #82.

## Objective

Determine whether a technically repairable repository defect is also work that an operator or maintainer actually requested, without mistaking either situation for funded procurement. Five cases across battery recycling, flood response, classroom air, food retail ordering and food distribution were inspected. These are complementary Practical, Academic and Implementation perspectives, with commercial conversion assessed separately.

## Read-only external source collection

An authenticated GitHub API snapshot on October 21 (Taipei) retrieved exact public repository/issue/PR identities, issue states, reported license metadata, issue-body digests and timestamps. It does not publish full issue bodies, post to GitHub or contact anyone. Snapshots older than 14 days must be refreshed before current availability is asserted.

- **Open Food Network:** [issue #14924](https://github.com/openfoodfoundation/openfoodnetwork/issues/14924), open and unassigned, describes Canadian map mis-centering after a bad enterprise geocode and a hard-coded zoom. It reports operational user frustration, but not verified lost revenue or a funded repair engagement.
- **Foodsoft:** [issue #1368](https://github.com/foodcoops/foodsoft/issues/1368), open and unassigned, documents inconsistent quantity rounding in the order balancing view. It is a public bug report, not a contract.
- **LFP recycling model:** independently reproduced positive gate-fee accounting omission and proved a temporary local patch across three routes; no matching maintainer issue attached to this case and no buyer verified.
- **Flood-warning system:** independently reproduced a NaN ordering failure and temporary fix across six station orderings. No matched issue or operational operator has been established; repo's last reported push was March 2023.
- **CO₂ ESPHome:** static configuration failure and missing sensor reference. An existing [license-creation PR #1](https://github.com/ajlongshanks/co2_esphome/pull/1) remains open in the snapshot, originally from 2021. It is a pull request for repository rights clarification, not an external user report.

## Two new pinned-source arithmetic reproductions

**Open Food Network:** [MapCentreCalculator CoffeeScript, pinned commit](https://github.com/openfoodfoundation/openfoodnetwork/blob/1167aa7b7585c1794199e032fc15c0e9c1c74104/app/assets/javascripts/darkswarm/services/map_centre_calculator.js.coffee). The actual upstream implementation calculates midpoint from the minimum and maximum coordinates. An independent synthetic arithmetic analog uses invented latitudes [49, 53, 51], midpoint 51, plus one mis-geocoded outlier at -15, shifting midpoint to 19. This explains the outlier sensitivity; actual application CoffeeScript tests, real enterprise locations, zoom behavior and a fix were not executed.

**Foodsoft:** [OrdersHelper Ruby source, pinned commit](https://github.com/foodcoops/foodsoft/blob/f594be8e64f4d3748d0e418df05fbb554ccce71b/app/helpers/orders_helper.rb#L50-L71). The helper rounds only the converted ordered/received side before comparison. A high-precision Decimal analog of the issue's 1.7kg divided by 1.3kg/unit yields 1.307692... units; the rounded result is 1.308. Asymmetric equality is false while equal three-decimal rounding on both operands produces true. This does not replace the actual Ruby helper integration test or settle all rounding branches.

These source contents were verified by GitHub blob SHA1 and bounded inspected code anchors. No third-party source contents were copied into our repo.

## Explicit delivery pathways

The source-backed conversion gate distinguishes:
- reproduce_public_maintainer_issue: documented open, operator-visible bug with pinned source mechanism, but still lacking native application proof;
- propose_opt_in_upstream_contribution: locally fixed synthetic failure, without a maintainer issue or commitment;
- license_and_deployment_blocked: copyright/rights and technical prerequisites unresolved;
- research_candidate_unready: neither a confirmed open request nor a verified external production solution;
- refresh_public_source_before_contact: GitHub observation older than 14 days, no longer actionable as current evidence.

The system rejects fabricated source IDs/commit blobs, stale issue claims, issue/PR conflation, unexpected technical revision changes, and any attempt to treat model reasoning as confirmed revenue. Every case has zero independently verified contracts, buyers, operator budgets, economic return or external deployment.

## What remains

First test OFN in its Angular/CoffeeScript suite and Foodsoft in its actual Ruby application tests; verify owner contribution process. For the two proven scratch repairs, obtain maintainer interest before proposing or delivering a patch; no money inferred. For CO₂, resolve license and hardware compatibility before reuse. Broaden horizontally with independently documented operator budgets and actual support costs before selecting a commercial offering.

**No source status promotions, sealed research holdout access, external issue posts, pull requests to third-party owners, contract applications or verified income.**

## Artifacts

- [Operator conversion route matrix](../research_materials/opportunity_atlas/OPERATOR_CONVERSION_ROUTES.md)
- [Exact-source problem mechanism reproductions](../research_materials/opportunity_atlas/REPORTED_ISSUE_SOURCE_CONTRACTS.md)
- Machine-readable API snapshot: research_materials/opportunity_atlas/operator_github_snapshot.json
- Machine-readable decision routes: research_materials/opportunity_atlas/operator_conversion_routes.json
- Reusable entrypoints: cite-refinery-operator-conversion-gate and cite-refinery-reported-issue-contracts

To refresh, run the operator-conversion gate with --collect and supply its required snapshot, functional, repair, issue-contracts, output and markdown paths. The command reads GitHub but never writes to external repositories.
