# Browser Jasmine and Ruby RSpec: real scoped framework verification

Real pinned original source and two experimental local patches were executed.
The full Angular frontend and Rails/database suites were NOT executed.

| Scoped suite | Original source | Experimental local patch |
|---|---|---|
| OFN Karma/Jasmine browser (9 original + 5 new) | 10/14 pass; 4 fail | 14/14 pass |
| Foodsoft RSpec against original Ruby helper (9 new cases) | 6/9 pass; 3 fail | 9/9 pass |

The OFN candidate uses newly proposed region-bounds configuration, filters
nonfinite coordinates and uses circular longitude calculation. It handles
synthetic multiple bad geocodes and a two-point antimeridian fixture.
It DOES NOT wire those new config keys into real OFN instances or test
zoom, nationwide viewport, true geocoding errors or all global geometry.

The Foodsoft candidate rounds both sides of a price conversion comparison
to three decimal places. It passes real-helper RSpec assertions for
ordered, received, billed, priority, nil and genuine discrepancy behavior.
It DOES NOT use actual Rails OrderArticle models or a database; policy
around precision and the complete project suite remain unverified.

## Hard gate

No upstream edit, submit, maintainer consent, full deployment, scientific
outcome or paid customer is established. See the source-pinned patch
diffs and executable test harnesses for the bounded next step.
