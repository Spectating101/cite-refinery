# Original-runtime component execution: OFN and Foodsoft

**Both original source functions were actually executed using appropriate language runtimes and SHA-checked source revisions.** This is materially stronger than an arithmetic analog, but not yet full framework integration.

## Open Food Network — original CoffeeScript factory

Source: https://github.com/openfoodfoundation/openfoodnetwork/issues/14924. The actual MapCentreCalculator service was compiled with coffee-script 1.12.7 and exercised using a minimal Angular factory capture with synthetic geocoded-enterprise data.

| Test | Original | Local median candidate |
|---|---|---|
| Prior ordinary/default-center fixtures | pass | pass |
| One wrong geographic outlier | FAIL | pass |
| Three coordinated wrong outliers | FAIL | FAIL |

**Not ready as a full fix:** the median prototype fails the multi-outlier regression and does not implement zoom/viewport policy. No browser, real address or nationwide bounds integration was exercised.

## Foodsoft — original Ruby OrdersHelper

Source: https://github.com/foodcoops/foodsoft/issues/1368. The actual module was loaded and invoked inside a digest-pinned Ruby container with network disabled, read-only mounts and BigDecimal conversion fakes.

| Test | Original | Local symmetric-rounding candidate |
|---|---|---|
| Equal quantities, ordered/received branches | FAIL | pass |
| Genuine differences still flagged | pass | pass |

**Not a merged application fix:** Rails models, DB integration and project test suite were not run; maintainers must adjudicate acceptable unit and decimal precision semantics.

## External conversion gate

Both are independently reported public problems, not paid work orders. Source and runtime checks support a credible contribution proposal, but do not validate rights, financing, deployment or user outcomes. Upstream repositories remain untouched.
