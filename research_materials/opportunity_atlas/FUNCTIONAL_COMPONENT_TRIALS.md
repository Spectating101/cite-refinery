# Functional component verification: executable evidence vs operational promise

Probes use original pinned upstream files in a separate research scratch directory. A **pass** demonstrates only the specific synthetic requirement. A **fail** is a reproducible gap in that bounded trial; **blocked** means missing prerequisite/evidence and **not tested** means no field result. No external code is copied into Cite–Refinery.

## [lingrany/EverBatt-LFP-Recycling-Analysis](https://github.com/lingrany/EverBatt-LFP-Recycling-Analysis/tree/246c4d478f9ceb05c580856720ca56a66064e205)

**Three-layer problem:** mechanism:battery_recycling_economics; **execution:** actual_upstream_python_calculation_synthetic_input

| Requirement check | Result | Measured behavior / limitation |
|---|---|---|
| pyro_positive_fee_accounting | **FAIL** | {"actual_profit_reduction_usd": 0.0, "profit_usd_fee_positive_one": -13948123.1, "profit_usd_fee_zero": -13948123.1} |
| pyro_negative_gate_fee_income | **PASS** | {"profit_increase_usd": 20000000.0} |
| hydro_positive_fee_accounting | **FAIL** | {"actual_profit_reduction_usd": 0.0, "profit_usd_fee_positive_one": -10690391.29, "profit_usd_fee_zero": -10690391.29} |
| hydro_negative_gate_fee_income | **PASS** | {"profit_increase_usd": 20000000.0} |
| direct_positive_fee_accounting | **FAIL** | {"actual_profit_reduction_usd": 0.0, "profit_usd_fee_positive_one": 32197581.38, "profit_usd_fee_zero": 32197581.38} |
| direct_negative_gate_fee_income | **PASS** | {"profit_increase_usd": 20000000.0} |
| localized_hazard_control_and_pilot_yield | **NOT_TESTED** | "Original default parameters only; no field, regulator, or plant records provided." |

**Scope boundary:** Route/fee scenario computation; not recycler permit, plant profitability, safety or observed performance.

**Reuse boundary:** MIT file in checked repo; third-party workbook/data/embedded assets and derivative license compatibility not independently assessed.

### Interpretation

- **pyro_positive_fee_accounting** (fail): Upstream --battery-fee CLI says negative means recycler is paid. This result checks the reverse paid-fee direction using its own convention.
- **hydro_positive_fee_accounting** (fail): Upstream --battery-fee CLI says negative means recycler is paid. This result checks the reverse paid-fee direction using its own convention.
- **direct_positive_fee_accounting** (fail): Upstream --battery-fee CLI says negative means recycler is paid. This result checks the reverse paid-fee direction using its own convention.
- **localized_hazard_control_and_pilot_yield** (not_tested): The upstream model has parameters but no verified local inputs; a synthetic profit output cannot establish investment economics.

## [WeixuanZ/flood-warning-system](https://github.com/WeixuanZ/flood-warning-system/tree/c1c7facf2c5577a155edd93a0b7279ad7630518c)

**Three-layer problem:** mechanism:flood_warning_to_impact; **execution:** actual_upstream_python_code_synthetic_station_fixtures

| Requirement check | Result | Measured behavior / limitation |
|---|---|---|
| threshold_selection | **PASS** | ["high"] |
| missing_level_handling | **PASS** | null |
| invalid_typical_range_handling | **PASS** | null |
| nonfinite_sensor_level_is_excluded | **FAIL** | {"nan_in_ranked_stations": true, "nan_relative_value": "nan"} |
| nonfinite_station_corrupts_top_one_ordering | **FAIL** | {"input_order": ["low", "nan", "high2"], "top_one": ["low"]} |
| local_warning_distribution_and_health_outcomes | **NOT_TESTED** | "Synthetic UK-style MonitoringStation data only." |

**Scope boundary:** Station threshold/ranking utilities; not weather forecast skill, alert delivery, local calibration or reduced harm.

**Reuse boundary:** MIT license in checked repo; external data provider and operational regulatory requirements unresolved.

### Interpretation

- **nonfinite_sensor_level_is_excluded** (fail): Nonfinite measurements are invalid telemetry; passing them into risk sorting can mislead downstream processing.
- **nonfinite_station_corrupts_top_one_ordering** (fail): Upstream Python float NaN breaks total ordering and can suppress a truly higher station. Synthetic fixture is a direct module test; it does not establish actual public-warning failures.
- **local_warning_distribution_and_health_outcomes** (not_tested): No live station feed, dissemination authority or health endpoint was tested.

## [ajlongshanks/co2_esphome](https://github.com/ajlongshanks/co2_esphome/tree/d1b3c500ae475e3dcfef6e5dbb38279cdc267708)

**Three-layer problem:** mechanism:classroom_ventilation_outcomes; **execution:** static_yaml_syntax_and_reference_inspection_only_not_firmware_execution

| Requirement check | Result | Measured behavior / limitation |
|---|---|---|
| esphome_yaml_syntax | **FAIL** | {"parse_error": "while parsing a block mapping\n  in \"<unicode string>\", line 110, column 5:\n      - file: \"image.png\"\n        ^\nexpected <block end>, but found '-'\n  in \"<unicode string>\",  |
| display_image_identifiers | **FAIL** | {"undeclared_image_ids": ["face_good"]} |
| licensing_provenance | **BLOCKED** | {"license_file_detected": false} |
| firmware_compile_and_sensor_calibration | **NOT_TESTED** | "No ESPHome compiler, ESP32/T-Display hardware, or physical calibration instrument in this trial." |

**Scope boundary:** Configuration plausibility, not actual CO2 sensing, school ventilation or respiratory outcome.

**Reuse boundary:** No license file detected in pinned repository; clarify rights before reuse.

### Interpretation

- **esphome_yaml_syntax** (fail): PyYAML syntax parser, NOT ESPHome schema validator or firmware compiler.
- **display_image_identifiers** (fail): Static reference check; not an ESPHome C++ lambda compilation.
- **licensing_provenance** (blocked): No LICENSE/COPYING file in checked snapshot. This is a documentation gap, not a definitive legal ruling.
- **firmware_compile_and_sensor_calibration** (not_tested): Static syntax failure already blocks firmware testing; hardware/clinical effect cannot be inferred.

## Evidence gate

These trials do **not** establish a product fit for the complete operational need, an independently replicated research mechanism, a safe installation, or a viable commercial conversion. In particular, an apparent profit from a model with a failed fee-cost accounting invariant must not be presented as the project's economic value.
