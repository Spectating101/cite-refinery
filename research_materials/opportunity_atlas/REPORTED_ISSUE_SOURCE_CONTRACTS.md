# Two reported maintainer problems with source-fingerprinted arithmetic reproductions

Open public issue reports are paired with exact code blobs at independently checked repository commit SHAs. These tests execute **numeric analogs** of their underlying calculations, not the CoffeeScript or Ruby applications.

## Ofn Canada Map Bounds

[Source](https://github.com/openfoodfoundation/openfoodnetwork/blob/1167aa7b7585c1794199e032fc15c0e9c1c74104/app/assets/javascripts/darkswarm/services/map_centre_calculator.js.coffee) · [Issue](https://github.com/openfoodfoundation/openfoodnetwork/issues/14924)

**Reproduction:** three invented Canada-like latitudes 49/53/51 and a synthetic mis-geocoded latitude -15

**Engineering contract:** Outlier must not move first-view map outside normal region; use instance-defined override or robust geographic bounds.

**Execution status:** independent numeric analog of exact source min/max arithmetic, not original CoffeeScript execution

Latitude midpoint without synthetic outlier: 51.0; with one outlier: 19.0.

## Foodsoft Order Quantity Rounding

[Source](https://github.com/foodcoops/foodsoft/blob/f594be8e64f4d3748d0e418df05fbb554ccce71b/app/helpers/orders_helper.rb) · [Issue](https://github.com/foodcoops/foodsoft/issues/1368)

**Reproduction:** 1.7 kg ordered divided by 1.3 kg per unit

**Engineering contract:** Compared quantities must use consistent precision, including a fixture for units 1.7kg/1.3kg.

**Execution status:** independent Decimal analog of source helper, not original Ruby execution

Exact computed units: 1.3076923076923076923076923076923077; rounded units: 1.308; original asymmetric equality: False; symmetric precision equality: True.

## Required next proof

Run the original application-specific test suite, inspect geography/decimal edge cases and safe fixes with maintainer guidance. A reported bug does not imply a purchase commitment, and matching code tokens does not establish a production failure outside the reported case.
