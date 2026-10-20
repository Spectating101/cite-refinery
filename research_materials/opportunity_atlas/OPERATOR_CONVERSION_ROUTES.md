# From functional fixes to real maintainer/operator signals

Source-state checked at 2026-10-20T19:57:12.948359+00:00. **This is an external problem-evidence matrix, not a revenue pipeline.**

| Repository / problem | Independent practical signal | Technical proof | Present route |
|---|---|---|---|
| [lingrany/EverBatt-LFP-Recycling-Analysis](https://github.com/lingrany/EverBatt-LFP-Recycling-Analysis) | no specific current issue validated in this case record | scratch only synthetic repair verified | propose opt in upstream contribution |
| [WeixuanZ/flood-warning-system](https://github.com/WeixuanZ/flood-warning-system) | no specific current issue validated in this case record | scratch only synthetic repair verified | propose opt in upstream contribution |
| [ajlongshanks/co2_esphome](https://github.com/ajlongshanks/co2_esphome) | pending license PR; rights unclear | invalid config reproduced deployment blocked | license and deployment blocked |
| [openfoodfoundation/openfoodnetwork](https://github.com/openfoodfoundation/openfoodnetwork) | open public issue | original upstream component executed candidate needs integration | complete viewport solution then integration test |
| [foodcoops/foodsoft](https://github.com/foodcoops/foodsoft) | open public issue | original upstream component executed candidate needs integration | run original app integration before contribution |

## Conversion evidence still required

### Lfp Positive Gate Fee

**Three layers** — Practical: Unreliable process economics when feedstock is purchased for a positive gate fee. Academic: Cash-flow sensitivity to feedstock purchase fees and process assumptions. Implementation: Three-route LFP model with scratch-only accounting repair.

**Next decisive step:** Propose a minimal maintainer-approved fee-cost regression; obtain actual operating inputs before economic claims.

**Evidence links:** No relevant issue requested in this bounded source sample.

### Flood Nan Priority

**Three layers** — Practical: Nonfinite telemetry can corrupt highest-risk station ordering. Academic: NaN violates ordinary numeric ordering and should not enter valid normalized water-level comparisons. Implementation: MonitoringStation ratio and sorting with scratch-only finite-value repair.

**Next decisive step:** Validate with repo maintainer, obtain operational station schemas, expand fault injection and downstream alert contract.

**Evidence links:** No relevant issue requested in this bounded source sample.

### Co2 Yaml And License

**Three layers** — Practical: A CO2 device configuration cannot be deployed from an invalid YAML file and unresolved assets. Academic: Sensor hardware IDs, configuration syntax and calibration are separate prerequisites to any exposure outcome. Implementation: ESPHome SCD30 configuration fails YAML syntax; license creation PR is still pending.

**Next decisive step:** Clarify license, repair YAML and missing references on a permitted fork or with consent, compile and test actual hardware.

**Evidence links:** https://github.com/ajlongshanks/co2_esphome/pull/1

### Ofn Canada Map Bounds

**Three layers** — Practical: Canadian platform shoppers were shown an incorrect starting map location. Academic: Coordinate outliers can distort extreme-value midpoint centers; map bounds/zoom need robust geographic selection. Implementation: Open Food Network MapCentreCalculator and instance-map configuration require an independently reproduced fix.

**Next decisive step:** Read production MapCentreCalculator and tests; add geographic outlier and nationwide bounds fixtures, then offer maintainer PR if appropriate.

**Evidence links:** https://github.com/openfoodfoundation/openfoodnetwork/issues/14924

### Foodsoft Order Quantity Rounding

**Three layers** — Practical: Group order balancing shows an erroneous discrepancy marker for apparently equal quantities. Academic: Comparisons at different decimal precision can misclassify equivalent converted quantities. Implementation: OrdersHelper quantity comparison rounds only one of the two operands at three decimals.

**Next decisive step:** Run the original Ruby helper test at pinned revision; reproduce converted 1.7kg / 1.3kg/unit and add a symmetric precision regression.

**Evidence links:** https://github.com/foodcoops/foodsoft/issues/1368

## Hard authority and commercial gates

All five cases have **zero independently verified buyer commitments, paid work orders, full rights/compliance clearance, measured value capture, or external deployments**. A public issue is not a funded request. The license PR is a pull request, **not** independent external customer demand. Never rank by star count or promote a candidate merely because a repair passes tests.
