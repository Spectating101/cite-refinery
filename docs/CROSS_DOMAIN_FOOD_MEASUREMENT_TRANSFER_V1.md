# Cite–Refinery: first bounded positive capability transfer

Date: October 21, 2026. Core cross-domain capability-discovery follow-up to draft PR #96.

## The discovery and what was actually reused

The four-slice source-first atlas proposed using industrial measurement-quality methods for food redistribution, associated with candidate slice-2:CV-01 (DaSPi + PantryRaider). This experiment reuses ONLY [DaSPi](https://github.com/j4ggr/DaSPi) Gage Study / Gage R&R ANOVA. PantryRaider was neither executed nor integrated. The tested workflow is synthetic food-donation intake weighing, NOT actual food-rescue logistics.

Original DaSPi revision: 5b6234be9ac78cdea1318944ac854fcfd09c3fbd. No original source modified. Python 3.13 isolated virtual environment with declared-compatible dependencies: pandas 3.0.6, NumPy 2.5.4, SciPy 1.18.1 and statsmodels 0.14.6.

An initial attempt against statsmodels 0.15.0 failed one targeted upstream model test after seven passes (missing PandasData.design_info). With statsmodels 0.14.6, all **12 targeted original Gage Study / Gage R&R tests passed**. This is a dependency compatibility observation, not evidence that the whole upstream package is flawless.

Original license discrepancy worth reviewing: GitHub API reports BSD-3-Clause and the repository LICENSE is BSD-3-Clause, while pyproject.toml declares MIT. No license clearance for redistribution has been assumed. The trial imports original code for local testing only.

## Reproducible synthetic counterfactual

Eight fictional food batches weigh 8.4, 9.0, 9.6, 10.3, 10.8, 11.2, 11.9 and 12.4 kg. Three fictional intake workers each weigh every batch three times. The dataset has 72 readings plus 25 synthetic reference readings. A hypothetical 10 kg classification threshold is used only to test information loss, NOT as a food-safety or regulatory standard.

Two fixtures use the same deterministic measurement noise.

| Condition | Injected worker offsets | DaSPi operator ANOVA p | Individual worker/parcel classification mistakes | Pooled-parcel mean mistakes |
|---|---|---:|---:|---:|
| Worker bias injected | -0.55, 0, +0.55 kg | 1.216 × 10^-38 | **2 of 24** | **0 of 8** |
| No-bias control | 0, 0, 0 kg | 0.8653 | **0 of 24** | **0 of 8** |

The naive pooled means conceal two worker-specific threshold disagreements because positive and negative operator offsets cancel. The original DaSPi Gage R&R model detects the injected operator effect. The negative control correctly does not signal an operator effect at the chosen 0.01 cutoff.

**Positive result:** A preexisting statistical implementation detects a deliberately injected source of measurement disagreement in a new hypothetical food-intake use. This is a scoped analytical advantage over the specific naive pooled-average baseline, not a new statistical method or a claim of a real operational improvement.

## What remains entirely unproved

No real charity, person, donor, data, operator error, food outcome, user need, project adoption, confirmed underconversion, or realized institutional value was measured. DaSPi's statistical technique is established industrial methodology; whether food organizations already use it is unknown. The original two-asset pairing with PantryRaider remains **unvalidated**. Passing limited upstream tests is not whole-product quality certification.

## Executable research and atlas integration

- [Reproducible synthetic trial script](../research_materials/opportunity_atlas/trials/daspi_food_weight_reuse_trial.py) imports the pinned original DaSPi implementation and records loaded numerical versions and source license digest.
- [Result receipt](../research_materials/opportunity_atlas/daspi_food_weight_conversion_trial_v1.json) contains both counterfactual fixtures, original test regime, ANOVA results, baseline comparisons, source revision and explicit no-deployment/no-adoption flags.
- [Combined 21-candidate atlas](../research_materials/opportunity_atlas/CONVERSION_QUALIFICATION_WITH_POSITIVE_AND_NEGATIVE_TRIALS_V1.md) includes both this limited positive result for slice-2:CV-01 and the independent negative GridShadow/Jackery interface mismatch for slice-0:CV-03.

The core investigator accepts an optional functional-trial evidence receipt alongside bridge-trial on the existing qualify-conversions command. The validator requires exact existing asset identity, pinned original commit, a positive manipulated fixture and null control, and false real-world claims. No new console entrypoint, native graph approval, customer, fourth layer or funding requirement.

## Decisive next test

Use independently sourced, permissioned repeated intake measurements from an actual organization, not synthetic examples. Compare actual operator-bias detection, decision error, cost and process improvement to their existing procedures, and examine whether the method is already used. The ability to demonstrate synthetic transfer does not establish either an unconverted asset or a real-world reason it has not been converted.

This is a positive technical *method-transfer demonstration*, NOT yet evidence of successful conversion arbitrage.
