# Cite–Refinery | Internal arbitrage mapping, not just service monetization

**Established October 21, 2026.** Read-only source-derived reconnaissance on the existing three-layer graph. This is the next step after PR #91, which packaged operator decision briefs as one optional commercial wedge. The broader purpose is to **discover information, sourcing, operational, technological and geographic asymmetries that we might exploit directly**—including avoided mistakes, acquired hardware, repaired goods and components reused in our own projects—not to turn every insight into a paid service.

## What “arbitrage” means here

We need to distinguish four statuses:

1. **Research lead:** A practical need, academic mechanism and candidate implementation appear connected in source-bounded records. This is not a market inefficiency yet.
2. **Technical advantage:** We can reproduce a real error or execute a useful candidate mechanism with exact original-code evidence. It may create an advantage for our own engineering or bid decisions, but does not prove a tradable or monetizable spread.
3. **Economic spread hypothesis:** Contemporaneous, condition-matched acquisition and exit prices, after all relevant costs and failure probabilities, suggest a possible positive return. Listings and hypothetical prices are not completed sales.
4. **Realized arbitrage:** We obtained the actual item/right/capability legally, took the actual action, and verified net cash benefit or an independently measurable avoided cost. **There are currently zero documented realized cases.**

The first three are stages of screening, NOT authoritative status upgrades in the native graph. Value-capture is a derived economic overlay, **not a fourth foundational layer**. No automatic semantic or financial join based solely on similar words or repository names.

## The first wide map — existing evidence, not fabricated links

Existing non-exhaustive source survey: **21 practical problem views, seven with all three foundational layers represented, five separately tracked executable technical issue leads, and zero validated end-to-end commercial captures.** The original atlas still includes public procurement listings, which are only requirements or candidate procurement events; they do not prove that procurement is live or accessible to us.

- [Internal arbitrage map and evidence gap inventory](../research_materials/opportunity_atlas/INTERNAL_ARBITRAGE_MAP_V1.md)
- [Machine-readable 21-view / five-trial atlas](../research_materials/opportunity_atlas/internal_arbitrage_map_v1.json)
- [Our six explicit strategy hypotheses, separate from source graph](../research_materials/opportunity_atlas/owner_arbitrage_targets_v1.json)

The existing graph has documented candidates in battery-recycling economics, classroom ventilation, animal identity surveys, e-waste impact assessment, flood warnings, food redistribution and heat-warning systems. **Each still needs independent applicability and field observations.** One worker algorithm harm problem lacks a usable implementation reference. Public procurement cases lack independently confirmed academic mechanisms or successful deployable implementation proof. Broad mapping is retained rather than selecting one niche prematurely.

## Priorities for our own capture — order of falsification, NOT projected profitability

| Investigation track | Potential self-capture mechanism | What actually exists | Cheapest decisive next step |
|---|---|---|---|
| **Taiwan used devices, consoles and repairable components** | Acquire, diagnose, repair, part out or resell devices where condition-adjusted exit value exceeds purchase, full repairs and risk | Owner hypothesis only. No verified matched buy/sold quotes, inventory or prior trades in Cite–Refinery | Collect 10 date-stamped condition-matched acquisition / completed-sale examples; quote actual components, fees and shipping; test five low-risk devices only after rights and positive expected margins |
| **Battery recycling model/accounting errors** | Avoid a wrong gate-fee bid or identify whether process model inputs under/overstate costs | A reproduced upstream positive-fee sign defect on synthetic economics and a local patch test; not a profitable recycler | Use independently licensed actual gate-fee, throughput, yield, disposal liabilities and regulatory costs; compare counterfactual quotes |
| **Original-source integration gap (OFN, Foodsoft)** | Save engineering time, improve own authorized deployments or build technical reputation/reusable test assets | Actual original-function regressions and bounded successful local test candidates; no full app integration or paid customer | Run full Rails/Angular tests, seek authorization and measure the actual operator consequence; do not infer a buyer from a public issue |
| **Flood warning data-quality components** | Reuse resilient sensor rankings or gain fault-handling advantage in a permitted testbed | Original function-level synthetic NaN failure and temporary candidate; no deployment or effectiveness | Test real operator data and false-alarm/latency behavior, with permission, before claiming public-safety impact |
| **Energy/utility metering requirement gaps** | Reuse low-level telemetry parsing instead of building protocol handling from scratch, possibly avoiding development cost | Institutional requirement candidates and GitHub protocol components, **not complete procurement fit** | Verify notice lifecycle and eligibility, then meter-protocol interface and organizational access |
| **Classroom ventilation sensor components** | Reuse low-cost hardware/configuration in our own permitted environments | Candidate implementation includes a static configuration problem and unresolved code-use rights | Establish license and physical calibration first; do not ship undocumented rights or performance claims |

Other paths remain in the map; these priorities are driven by our own stated engineering interests, not an external ROI ranking.

## A deterministic real-world device arithmetic gate

The optional **scenario ledger** prices the actual trade decision in TWD or USD. It requires:

- Purchase/acquisition amount and **success-case sale price**, not a hypothetical listing interpreted as a completed sale.
- Probability of successful repair/re-sale, after-sale platform fees and delivery cost.
- Failure-case salvage recovery and disposal cost, including the case where repair fails.
- Initial shipping, materials, **labor hours × opportunity-cost rate**, storage, taxes/compliance and contingency.

The conditional expected profit is:

\[
E[\mathrm{net}]
= p(P_{\mathrm{sale}}-F_{\mathrm{sale}}-S_{\mathrm{outbound}})
+ (1-p)(V_{\mathrm{salvage}}-C_{\mathrm{disposal}})
- P_{\mathrm{buy}} - C_{\mathrm{common}}
\]

The break-even bid price is the preceding expression **without** the purchase price. A positive modeled value only instructs **RESEARCH_MORE_AND_VERIFY_QUOTES**, never “buy automatically.”

For a **fully fictional** console-like Taiwan example, NT$2,000 purchase, NT$6,000 successful sale, 75% success probability and explicit fees, labor and failure loss yield a *conditional* NT$730 net and NT$2,730 break-even bid. **None of those prices or probabilities is a verified Taiwanese market quote.** The same calculator returns a no-buy recommendation when failure rates or costs deteriorate. See [illustrative inputs](../research_materials/opportunity_atlas/tw_electronics_hypothetical_scenario.json) and [isolated hypothetical output](../research_materials/opportunity_atlas/INTERNAL_ARBITRAGE_HYPOTHETICAL_PREVIEW_V1.md).

For actual Taiwan trading, the observable public cost stack is more complicated than a single seller fee: [Ruten's official transaction-fee rules](https://pub.ruten.com.tw/service_center/000600040029.html) describe category transaction charges and separate payment costs, while its [seller agreement](https://pub.ruten.com.tw/service_center/agreements.html) also references logistics, returns and other platform fees. **Recheck the applicable category and checkout configuration before each real price calculation.** Marketplace asking prices and a platform's fee table do not establish completed-sale realizations.

## How to run in the canonical system

The existing application exposes one added subcommand, **not** a standalone executable:

~~~sh
cite-refinery investigate arbitrage-map \
  --atlas research_materials/opportunity_atlas/three_layer_unified_atlas.json \
  --operator-routes research_materials/opportunity_atlas/operator_conversion_routes.json \
  --owner-targets research_materials/opportunity_atlas/owner_arbitrage_targets_v1.json \
  --json-out /tmp/internal_arbitrage_map.json \
  --markdown-out /tmp/internal_arbitrage_map.md
~~~

To assess a *strictly hypothetical* device scenario, optionally provide:

~~~sh
  --scenarios research_materials/opportunity_atlas/tw_electronics_hypothetical_scenario.json
~~~

The command refuses to overwrite results, validates exact three-layer graph connections, restricts owner overlay references to actual node and case IDs, and fails on missing financial failure-path assumptions. Its output records input content SHA-256 hashes for audit.

## Collection plan for the next sweep

Use a **market evidence sheet** with item model/condition/serial state, acquisition listing time, whether stock was actually obtainable, repair-cost estimate, shipping and tax, competitor completed-sale proof versus asking price, platform fees, repair outcome frequency and after-return receipt. Split by Taiwan geography/platform and do not pool incomparable conditions or sales dates. A file of public links is a **reconnaissance set**, not arbitrage evidence.

In parallel, continue the broad Practical → Academic → Implementation discovery net: novel practical operator data, independent mechanism sources, version-pinned implementation and tested examples. Separate these source families; preserve abstentions; avoid forced topic selection. Once the map identifies a plausible, legally accessible self-capture case, run an intentionally small capital-controlled test and record realized outcomes.

## Stops and exclusions

Do not trade, bid, scrape private systems, contact maintainers or claim deployment automatically. No rights/license clearance, tender eligibility, price availability, capital source, actual buyer, verified arbitrage gain or realized resale margin is implied. The fee-based verification sprint remains one option—but **internal arbitrage discovery and decision support are now an equal first-class delivery surface.**
