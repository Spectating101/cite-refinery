# Practical ↔ Academic ↔ Implementation: execution results, not a commercial shortlist

The previously unified conceptual graph now has **read-only functional trial evidence** attached to three existing three-layer paths. The status of every edge remains **candidate** or lower; outcomes below are synthetic or static and cannot validate the full system.

## Battery Recycling Economics

- **Academic mechanism:** mechanism:battery_recycling_economics (review: partial_support)
- **Implementation:** github:lingrany/EverBatt-LFP-Recycling-Analysis at pinned revision 246c4d478f9c
- **Test execution:** actual_upstream_python_calculation_synthetic_input
- **Reproduced failures:** 3; missing prerequisites: 0.

### Exact failed or blocked requirements

- **pyro_positive_fee_accounting (fail)**: A positive gate fee ($1/kg paid to obtain feedstock) must reduce annual profit by mass in kg times $1. Evidence: {"profit_usd_fee_zero": -13948123.1, "profit_usd_fee_positive_one": -13948123.1, "actual_profit_reduction_usd": 0.0}
- **hydro_positive_fee_accounting (fail)**: A positive gate fee ($1/kg paid to obtain feedstock) must reduce annual profit by mass in kg times $1. Evidence: {"profit_usd_fee_zero": -10690391.29, "profit_usd_fee_positive_one": -10690391.29, "actual_profit_reduction_usd": 0.0}
- **direct_positive_fee_accounting (fail)**: A positive gate fee ($1/kg paid to obtain feedstock) must reduce annual profit by mass in kg times $1. Evidence: {"profit_usd_fee_zero": 32197581.38, "profit_usd_fee_positive_one": 32197581.38, "actual_profit_reduction_usd": 0.0}

**Conversion gate:** FAIL/UNVERIFIED. No full technical fit, license clearance, scientific efficacy, or buyer.

## Flood Warning To Impact

- **Academic mechanism:** mechanism:flood_warning_to_impact (review: partial_support)
- **Implementation:** github:WeixuanZ/flood-warning-system at pinned revision c1c7facf2c55
- **Test execution:** actual_upstream_python_code_synthetic_station_fixtures
- **Reproduced failures:** 2; missing prerequisites: 0.

### Exact failed or blocked requirements

- **nonfinite_sensor_level_is_excluded (fail)**: NaN water-level readings must not be returned as candidates for an operational highest-risk list. Evidence: {"nan_relative_value": "nan", "nan_in_ranked_stations": true}
- **nonfinite_station_corrupts_top_one_ordering (fail)**: At input [low=0.2, invalid=NaN, high=1.6], top-one must select the high station, irrespective of telemetry insertion order. Evidence: {"input_order": ["low", "nan", "high2"], "top_one": ["low"]}

**Conversion gate:** FAIL/UNVERIFIED. No full technical fit, license clearance, scientific efficacy, or buyer.

## Classroom Ventilation Outcomes

- **Academic mechanism:** mechanism:classroom_ventilation_outcomes (review: partial_support)
- **Implementation:** github:ajlongshanks/co2_esphome at pinned revision d1b3c500ae47
- **Test execution:** static_yaml_syntax_and_reference_inspection_only_not_firmware_execution
- **Reproduced failures:** 2; missing prerequisites: 1.

### Exact failed or blocked requirements

- **esphome_yaml_syntax (fail)**: Configuration must parse as valid YAML before considering firmware build. Evidence: {"yaml_valid": false, "parse_error": "while parsing a block mapping\n  in \"<unicode string>\", line 110, column 5:\n      - file: \"image.png\"\n        ^\nexpected <block end>, but found '-'\n  in \"<unicode string>\", line 114, colu
- **display_image_identifiers (fail)**: Every face image referenced by the display lambda must be declared as a configuration image. Evidence: {"undeclared_image_ids": ["face_good"]}
- **licensing_provenance (blocked)**: A verifiable distribution/reuse license must be established before commercial component reuse. Evidence: {"license_file_detected": false}

**Conversion gate:** FAIL/UNVERIFIED. No full technical fit, license clearance, scientific efficacy, or buyer.

## Next engineering work

For each failed check, ask whether the flaw can be repaired under proper license or whether another implementation is safer or cheaper. Only run actual hardware, field deployment, or economic simulations with measured inputs and independent controls; passing synthetic unit calculations does not clear the deployment gate.
