# Cite–Refinery: source-verified bridge falsification

October 21, 2026. This is a **negative but informative** follow-up to broad discovery PR #95. It does not make Cite–Refinery a grid-engineering product. The three-layer atlas remains domain-general; this is one bounded experiment of a model-proposed unexpected capability pairing.

## Candidate and underlying source

Candidate [slice-0:CV-03](../research_materials/opportunity_atlas/emergent_conversion_slice_0_v1.json) proposed combining:
- [GridShadow](https://github.com/Krishita17/GridShadow), pinned original Git commit **bbeaa5d1d1b617025c2e7c3acd4c1f4c629bd4a4**. The original source contains a typed CouplingMap with accepted physical element kinds line, trafo and gen.
- [Jackery SolarVault for Home Assistant](https://github.com/Bigdaddy1990/jackery_solarvault), pinned original Git commit **36a89d127663f02b68c68a1c3b1c8dbaa1965773**. Its published const.py defines FIELD_SOC=soc, FIELD_GRID_IN_PW=gridInPw, FIELD_GRID_OUT_PW=gridOutPw; the declared package environment requires Python >=3.14.2 and <3.15.

The observation **does not establish** that either project is unused, excellent throughout, deployable to a new sector or able to run with the other.

## What was actually executed

The existing isolated Python environment (used to run **15 passing unchanged GridShadow original tests**) invoked the **original** GridShadow CouplingMap, and a read-only AST parser extracted actual Jackery telemetry declarations from its original pinned source.

All THREE attempts to supply Jackery telemetry strings as a physical grid actuation element were **rejected by the original GridShadow type guard**. A correctly formed synthetic GridShadow line actuation was accepted, controlling for the possibility that our test indiscriminately rejected everything.

This establishes that an unmediated telemetry-field-to-physical-actuation mapping is invalid. **It does not prove that an independently validated adapter is impossible.** A scientifically meaningful simulation would require a topology/meter mapping, explicit control semantics and permissions, common physical boundaries and units, and target-domain evidence explaining why that simulation would improve a real decision.

We did not import or run Jackery integration code, connect to a Home Assistant instance, obtain credentials, control physical hardware, or access a grid. Only a local source parsing / original GridShadow type guard was invoked.

[Reproducible read-only original-source contract trial](../research_materials/opportunity_atlas/trials/jackery_gridshadow_contract_audit.py) · [machine-readable result with two original Git commits and Jackery const.py SHA-256](../research_materials/opportunity_atlas/gridshadow_jackery_interface_trial_v1.json).

## Why this matters for conversion arbitrage

The atlas originally proposed the link because two genuine implementation capabilities may be complementary. The attempt to use them revealed a concrete, testable **integration prerequisite**. Before our evidence review, a model could easily have called it a promising energy-system integration. After the review, the proposition is more accurate:

- **Present capability:** GridShadow original coupling primitives and upstream toy/simulation suite; Jackery publisher source exposes separate household battery/AC telemetry keys.
- **Confirmed obstacle:** The raw telemetry fields do not satisfy GridShadow's grid-element-actuation input type.
- **Unconfirmed causes of underconversion:** Adoption difficulty, genuine operator demand, licensing burden, institutional issues or insufficient functionality have **not** been established.
- **Potential next conversion:** An offline, permissioned and validated topology-aware testbed if real needs and independent physical interpretation justify it. No automatic approval to deploy.
- **Alternative:** Reject this particular recombination if the required intermediate model costs more than the advantage it could provide.

This is not a conventional defect report or a profit estimate. It shows Cite–Refinery **disqualifying its own attractive cross-domain hypothesis** when original technical evidence shows the shortcut does not work.

## Engineering integration

The existing cite-refinery investigate qualify-conversions command accepts an optional --bridge-trial source receipt. The trial is checked against the *exact already-discovered asset identities*, both 40-character original Git revisions and any previously reported original test source revision. It refuses changed identities, mismatched revisions or claims of real-world deployment, quality or underconversion.

The refreshed [21-candidate qualification atlas](../research_materials/opportunity_atlas/CONVERSION_QUALIFICATION_WITH_BRIDGE_TRIALS_V1.md) marks only slice-0:CV-03 as **direct_mapping_blocked_requires_external_verified_interface**. The other 20 hypotheses are untouched.

No native graph relationship, new conceptual layer, standalone CLI, funding opportunity or monetization requirement was created.

**Current evidence status:** one reproduced *direct interface mismatch*; zero completed new cross-project integration; zero proven genuinely good-and-underconverted assets; zero measured added value.

## Next priority

Explore **different** candidate relationships as well, with low-cost source test and independent adoption/use check. Prefer genuine capability reuse and externally verifiable operational value to generating repeated same-domain simulations. The current source-diagnostic method should serve the broader three-layer intelligence and conversion map, not become the goal itself.
