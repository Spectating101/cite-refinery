# Repair versus replace: source-pinned three-layer functional evaluation

21 October 2026. Draft child of Cite–Refinery PR #81.

## Why this matters

Three-layer source discovery originally identified existing software with plausible relevance, then actual executable checks showed important deficiencies. This next pass distinguishes a defect that can be repaired under a bounded contract from a genuinely compatible alternative. Nothing here establishes sales demand, deployment readiness, a license right not already granted, or financial arbitrage.

All source snapshots were explicitly pinned to commit SHA, previously inspected and cloned into a separate research scratch directory on authorized Optiplex. Repair experiments use transient temporary copies. No upstream repository was modified, contacted or submitted to.

## 1. Battery recycling: runnable candidate repair, not replacement

The MIT-licensed LFP recycling model incorrectly omits positive battery feedstock fees from expense accounting. At a synthetic 10,000 tonnes/year and fee +$1/kg this overstates modeled annual profit by $10 million, holding all historical baseline parameters fixed. In a temporary local source copy, positive fees were added to the total cost and cost breakdown.

The corrected behavior passes Pyro, Hydro and Direct tests. Fee +1 versus fee 0 now reduces profit by exactly $10 million and increases total cost by $10 million; fee -2 still adds exactly $20 million of income, and zero-fee profit is unchanged. No actual local material recovery yield, buyer prices, Taiwan permits, safety CAPEX or independent earnings data were tested.

An alternative repository, Jamie-Hough/Batteryloop, has an empty source economics.py module in the checked commit and no detected root LICENSE file. It was not demonstrated to support the same paid-feedstock accounting invariant. It is not an equivalent validated replacement.

## 2. Flood warning: a real ranking failure and a local sorting repair

The first flood probe tested NaN inclusion. A stronger direct test proved a more consequential failure: with input stations [low=0.2, invalid=NaN, high=1.6], the original highest-risk selector returned low as its top-one result. Nonfinite float values defeat ordinary total ordering and an existing status check only filters None.

A temporary source patch normalizes nonfinite station values to None before sorting. All six permutations of low/NaN/high now select high for top-one; these are actual upstream module calls on synthetic levels. No deployed flood alert, forecasting errors, receiver behavior or public safety outcomes were measured. A function repair does not establish a complete warning system.

The bounded alternative search did not establish a license-reviewed executable replacement meeting the same requirements. That absence is a sample-level evidence gap, not proof that no alternative exists.

## 3. Classroom CO2: superficially valid replacement is not operational fit

The originally selected ajlongshanks ESPHome configuration fails YAML syntax. The RomainGehrig alternative is parseable with a safe loader that recognizes ESPHome's legitimate custom secret tag. Two configurations pass syntax parsing. However its documented module uses SCD40/SCD4x rather than SCD30, referenced font assets are absent from the inspected snapshot, a root LICENSE file was not detected, and no firmware schema compile or real hardware experiment occurred. It is NOT a drop-in replacement.

Another independently inspected repo, langchr86/homesensor, does have MIT-licensed SCD30 driver C++ source, but its architecture is different from ESPHome YAML. That is a potentially reusable part, not a compiled or tested replacement in this experiment.

## Model council outcomes and limitations

The independently executed engineering tests above are the reference. A fresh attempt to use Argon, Opus and Sonnet 5.5 on flood ranking and CO2 alternative compatibility produced TWO valid Argon medium responses. Argon correctly identified the NaN sorting hazard and the ESPHome secret-tag versus malformed indentation distinction. Opus and Sonnet 5.5 calls returned an early provider CLI exit (3) for these two cases. They did not produce valid results. No retry rotation, credential switching or silent fallback was used. Earlier PR #81 three-model agreement was only on the battery accounting case, not on flood or CO2.

Thus, the engineering conclusions derive from code/config execution, not from claiming multi-model consensus. This is not a comparative model benchmark or production model availability guarantee.

## Typed three-layer contribution

Practical layer: uncertain recycling margins; potential erroneous flood station prioritization; reliable CO2 monitoring requirements.

Academic layer: cost/throughput sensitivity; invalid-data sorting; sensor/BOM and observational-versus-intervention limitations. These are candidate technical explanations, not independently approved scientific outcomes.

Implementation layer: pinned existing projects, executable local modifications, explicit incompatible or incomplete alternatives and rights/asset boundaries.

Commercial conversion stays downstream: identify the real operator, a funded need or willing maintainer, rights to modify and redistribute, measured integration cost, maintenance exposure, and actual benefits. No contracts or production deployments validated. No frozen research holdout touched.

## Outputs

- Machine-readable: research_materials/opportunity_atlas/repair_replace_executable_results.json
- Readable: research_materials/opportunity_atlas/REPAIR_REPLACE_EVALUATION.md
- Runner: cite_refinery.repair_replace_trials, requiring trusted manually cloned, source-pinned repositories
- Updated original component trials and three-layer overlay expose the stronger low/NaN/high original failure.

For a local rerun, use the CLI with --scratch-root pointing to the inspected clones and --output /tmp/repair.json --markdown /tmp/repair.md. The runner never fetches GitHub or writes to original clones. Its temporary Python source execution is not a hardened OS sandbox; code should be inspected on an authorized machine before running.
