# Functional verification of three problem–mechanism–implementation paths
21 October 2026. Draft successor to the semantic scope audit (#79).

## What was materially tested

The preceding source-entailment review explained which *scientific mechanism links* were supported only partially. This pass checks what the implementation layer can **actually do** against bounded, falsifiable functional requirements. We deliberately sampled three distinct domains rather than selecting a lucrative target.

Original upstream sources were shallow-cloned into the authorized Optiplex research scratch directory, **outside Cite–Refinery**, pinned to exact commit SHAs. No code from the other projects was copied to our repository, installed into a production service, modified or pushed to the owners. Two small, inspected Python upstream modules were executed on synthetic fixtures using a local interpreter; a separate ESPHome configuration received **static YAML validation only**. Executing an imported third-party Python module is not a hardened container sandbox. No real hardware, real sensor feed, patient data, private account, buyer, or paid system was involved.

## 1. Battery economics: a genuine accounting failure

- Repository: [lingrany/EverBatt-LFP-Recycling-Analysis](https://github.com/lingrany/EverBatt-LFP-Recycling-Analysis), pinned commit `246c4d478f9ceb05c580856720ca56a66064e205` (MIT license file present).
- Actual upstream callable: `lfp_analysis_verified.py:analyze_method`; three routes **Pyro, Hydro, Direct**; synthetic 10,000 tonnes/year; historical parameter set, not live market data.
- Per the upstream CLI documentation, **negative battery fees mean payment to recyclers**. At -$2/kg, all three routes show the expected **+$20 million** increase in profit relative to a $0/kg fee.
- But for a **positive +$1/kg gate fee** (recycler must pay to acquire feedstock), all three routes return **exactly the same profit** as for $0/kg. The input is accepted but the expense is not deducted. Under the upstream's sign convention, the expected reduction is **$10 million annually** at 10,000 tonnes. This is an invariant violation, not an estimate of any actual Taiwan recycler's earnings.
- The model's internally calculated `Direct` profit at zero fee is approximately **$32.20 million/year** using its hard-coded 2019 assumptions. At +$1/kg, it incorrectly returns that same number rather than reducing it by $10 million. These model numbers are *not* investment returns or validated local commercial margins.
- Site-specific hazardous-material permits, environmental/safety CAPEX/OPEX, pilot recovery yields, wages, throughput and sale prices were **not tested against actual Taiwan operating data**.

**Consequence:** This candidate is useful as a scenario-calculation starting point but is not yet a credible stand-alone profit/risk estimator. Any downstream arbitrage ranking would need to **block** or repair this fee-cost accounting before economic comparison.

## 2. Flood warning: part of the station-risk workflow works; invalid telemetry isn't excluded

- Repository: [WeixuanZ/flood-warning-system](https://github.com/WeixuanZ/flood-warning-system), pinned `c1c7facf2c5577a155edd93a0b7279ad7630518c` (MIT).
- Inspected and ran real `MonitoringStation.relative_water_level`, `stations_level_over_threshold`, and `stations_highest_rel_level` with synthetic levels. Normal station selection, missing measurements and invalid typical ranges are handled correctly in the bounded tests.
- **Failed safety-relevant behavior:** `float('nan')` is accepted as a relative water-level value and is included by the highest-risk-ranking function rather than being rejected as invalid telemetry. This can compromise downstream station selection; we have not tested whether the entire web application uses that list in its user-facing alerts.
- Upstream subset (station, flood, geo, analysis, utils) yielded **13 passing tests** in our environment. Attempting full upstream test collection was **blocked by missing Bokeh**. The original dependency pins date from 2019/2020 and do not demonstrate deployment with current toolchains.
- Forecast error, live station-data quality, geographic adaptation beyond source context, warning lead times, message reach, actual evacuation and morbidity/mortality outcomes remain **unverified**.

**Consequence:** A narrow water-level threshold component is reusable in principle, but production warning/risk applications must handle invalid values, instrument uncertainty and institutional governance. A passing flood module does not establish flood protection.

## 3. Classroom CO₂ sensing: configuration does not clear a basic syntax check

- Repository: [ajlongshanks/co2_esphome](https://github.com/ajlongshanks/co2_esphome), pinned `d1b3c500ae475e3dcfef6e5dbb38279cdc267708`.
- Static PyYAML parsing of `co2sensor.yaml` **fails** around the image list: an `- file: moderate.png` entry is indented under another entry instead of being a peer list item.
- The display lambda references `face_good`, which is **not declared** among image IDs. This is a separate unresolved reference after YAML correction.
- No `LICENSE` / `COPYING` file was present in this checked snapshot. Do not assume code or design reuse is permitted merely because it is publicly accessible.
- No ESPHome compiler, actual board or calibrated SCD30 instrument was available in this experiment; a true firmware build and accuracy/ventilation field test were **not performed**.

**Consequence:** This is an architecture reference and repair candidate at best, not ready-to-use sensor firmware, let alone an evaluated health intervention.

## The key three-layer inference

For each of these specific systems, we have:
1. **Practical** — an operating problem/requirement (uncertain recycling margin, warning reliability, classroom exposure).
2. **Academic** — partially supported explanation or research mechanism, still source-scoped and not independently human approved.
3. **Implementation** — a source-pinned component whose actual code/config was probed and whose limitations were identified.

The new **read-only Functional Three-Layer Overlay** attaches the trials to the exact Practical, Academic and Implementation IDs. It refuses invented technical identities and never promotes any relation to `qualified`. All three investigated paths have a reproducible failing component-level check or config flaw. This **does not imply** all repositories generally fail: our sample deliberately selected probeable leads, and a passing subset cannot settle full suitability.

## What we need to convert this into an arbitrage-grade finding

We now know particular *engineering deficits*, not merely alleged market gaps. Next expand horizontally: sample alternative implementations addressing the same mechanism, test them against the **same comparable functional contract**, investigate maintainership/license obligations, and obtain real measured field/operator/contract economics. These checks should allow a reasoned **reuse vs repair vs build vs service for maintainer** decision without selecting a product based solely on a citation, a benchmark score or speculative profitability.

## Artifacts

- [Full executable/static probe report](../research_materials/opportunity_atlas/FUNCTIONAL_COMPONENT_TRIALS.md)
- [Read-only joined three-layer functional evidence](../research_materials/opportunity_atlas/FUNCTIONAL_THREE_LAYER_OVERLAY.md)
- Machine-readable source-pinned results: `research_materials/opportunity_atlas/functional_component_trials.json`
- Source-linked three-layer overlay: `research_materials/opportunity_atlas/functional_three_layer_overlay.json`
- Runner: `cite_refinery.functional_component_probes`
- Overlay: `cite_refinery.functional_three_layer_overlay`

### Reproduce against authorized, separately cloned upstream Git repositories

Run only on an authorized trusted machine. The exact pinned SHAs are enforced; no fetching or cloning is performed by the probe.

```bash
PYTHONPATH=src python -m cite_refinery.functional_component_probes \
  --scratch-root /path/to/authorized/upstream_clones \
  --output /tmp/component_trials.json --markdown /tmp/component_trials.md

PYTHONPATH=src python -m cite_refinery.functional_three_layer_overlay \
  --graph research_materials/opportunity_atlas/three_layer_unified_atlas.json \
  --trials /tmp/component_trials.json \
  --semantic research_materials/opportunity_atlas/academic_semantic_review_queue.json \
  --output /tmp/functional_overlay.json --markdown /tmp/functional_overlay.md
```

Each required clone directory follows the exact `owner__repo` naming in the pinned runner. The selected upstream Python dependencies, plus PyYAML for config analysis, must be installed in an isolated environment. Tests are not OS-level sandboxed; inspect third-party source code before execution. Cite–Refinery's standard `pytest` tests inspect the frozen artifacts without importing third-party code.

**No status promotions, external commits, buyer contacts, live clinical/public-safety recommendations, or economic claims.** The 66-record sealed research holdout remains untouched.
