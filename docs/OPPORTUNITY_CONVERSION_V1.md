# Opportunity conversion — real repository trials (2026-10-21)

## Goal
Turn a source-bounded Practical / Academic / Program problem into an investable or serviceable **conversion hypothesis**: documented operational need → working mechanism → existing implementation → capability fit/mismatch → rights → buyer or maintainer demand → execution test.

GitHub popularity and README text never establish underconversion, buyer willingness-to-pay, deployment effectiveness, contract acceptance or legal permission. The 232-source frozen evidence corpus and its 66-source holdout were NOT modified.

## Implemented
- **Semantic matching** (opportunity_matcher.py): an authenticated model compares bounded, attributed problem needs against published repository capabilities. It proposes direct documented matches, adaptation hypotheses or not-fit candidates. Unverified capability absence is flagged for further code inspection. No matching on star counts.
- **Conversion assessment** (opportunity_conversion.py): rights-aware decisions distinguish self-execution, service to maintainer, and component reuse. Published paid-contributor invitations are explicitly different from ordinary community contribution calls. Unlicensed copying/deployment is blocked.
- **Economics and demand gating**: funded requests require reviewed procurement evidence; signed deals require documented contracts. Any supplied price-minus-delivery-cost is clearly a conditional gross-contribution scenario, not actual income. No demonstrated buyers or prices in initial cases.
- **Operation**: opportunity_cli.py and opportunity_match_cli.py produce human-readable or JSON outcomes; all calls are read-only, no contact or licensing commitments.

## Real outputs and what we should do

### Highest-potential near-term service channel: Open Food Network
- [OFN issue #14924](https://github.com/openfoodfoundation/openfoodnetwork/issues/14924) records a real Canadian map-centering failure when one mis-geocoded enterprise shifts the geographic midpoint; fixed zoom is also inappropriate. Issue text reports operator/user dissatisfaction, **not measured churn**.
- [Open Food Foundation's contributor page](https://openfoodfoundation.org/become-a-contributor/) publicly references paid developer/system-administrator applications. It is **not a job offer to us or a confirmed paid assignment**.
- Proposed first test: reproduce with in-country points plus one international outlier; add a failing regression fixture; investigate bounds / preferred instance viewport before offering a narrowly scoped fix. No upstream patch has been executed here.
- Decision: verify that the advertised application pathway remains open and whether the issue can be assigned. Propose a small deliverable, not a broad "takeover."

### Technical contribution proof: Foodsoft
- [Foodsoft issue #1368](https://github.com/foodcoops/foodsoft/issues/1368) documents false order quantity mismatch warnings when a displayed quantity is rounded to three decimals but summed group quantity is not.
- [Foodsoft](https://github.com/foodcoops/foodsoft) is actively maintained, with AGPL licensing. A fix could serve as a test-backed contribution, but there is **no evidence of a budget to pay for it**.
- Next: reproduce the numeric fixture, test rounding precision at the actual financial/quantity boundary, discuss a fix with maintainers. Do not assume software bug count equals conversion demand.

### First-party deployment hypothesis: field dog surveys
- Cite–Refinery's reviewed Taiwan dog case identifies identity reconciliation and survey timing as investigation needs. [KoboToolbox](https://github.com/kobotoolbox/kpi) already handles form data, offline field collection and API integration. That is **potentially reusable collection infrastructure**; it is NOT proven to provide dog re-identification or population estimation.
- Next: minimal offline photo-and-location form, replay synchronized attachments, inspect data fidelity and separately test identification. No municipal buyer is confirmed.

### Possible partner asset — legal hold
- [Food Rescue MVP](https://github.com/still-trying/food-rescue) claims food listings, geographic search, atomic claiming and pickup workflows. Its README references an MIT license, but no root LICENSE file was observed in the GitHub contents and the repository API returned no recognized license.
- Next: confirm permission/licensing with maintainer before using code. Do not represent its popularity or feature claims as operational deployment outcomes.

### An important exclusion
Foodsoft may be suitable for recurring food-coop orders but is not demonstrated as a time-sensitive food-rescue dispatch engine. The semantic matcher classified Foodsoft for urgent donor pickup as **not-fit hypothesis**; this is a reason to inspect before investing, not proof that the code can never support notifications.

## Live semantic comparison

The Gemini 3.8 Flash Medium call returned candidate pairs:

1. Foodsoft's balance bug ↔ Foodsoft accounting module (directly relevant).
2. OFN's broken Canadian map ↔ OFN geographic display (directly relevant).
3. Urgent food pickup ↔ Food Rescue MVP (possible adaptation; rights unresolved).
4. Dog photo-sighting intake ↔ KoboToolbox collection system (component fit; individual identity algorithm separate).
5. Urgent food pickup ↔ Foodsoft batch co-op ordering (likely poor fit).

Each pair includes an explanation, limitation and falsifying technical test. The model has **not** tested these repositories. Claims that code "does not have" a function are flagged as unverified.

## Conversion priorities, without made-up scores

1. **OFN:** investigate its publicly described paid-contributor route and offer a bounded, test-backed fix only if the route is genuinely open.
2. **Foodsoft:** a well-scoped engineering contribution to establish credibility, not assumed income.
3. **Kobo dog survey:** first-party integration experiment with a real field-data workflow, then operator interviews.
4. **Food Rescue:** legal/maintainer clarification and buyer discovery *before* any code reuse.

These choices distinguish short-term services from potential reusable product infrastructure. All remain unconfirmed commercial opportunities. Neither repo stars, complaint counts nor unfilled issues can establish financial arbitrage on their own.

## Verification and artifacts

- Source-backed case inputs: research_materials/opportunity_conversion/*.json
- Semantic matching input and redacted review: semantic_match_input.json, semantic_match_review.json
- Human-readable conversion decisions: conversion_dossiers.md
- Existing source-reviewed cross-layer evidence: docs/CROSS_LAYER_INTERPRETATION_V1.md

No third-party repositories were modified, no maintainer or buyer was contacted, and no payment or revenue was represented as earned. No new corpus collection was performed. Next meaningful progress must be a **reproduced fix, an operator-verified need, explicit permission, or a real paid engagement**.
