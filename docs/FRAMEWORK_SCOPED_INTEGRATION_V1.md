# Reproducing the original maintainer-reported issues inside test frameworks

2026-10-21. This is a draft child of Cite-Refinery PR #84.

## What was really run

Open Food Network: compiled the exact pinned CoffeeScript MapCentreCalculator service AND the original nine upstream Jasmine assertions with project-pinned CoffeeScript 1.12.7. The tests ran inside real headless Chrome using Angular 1.8, angular-mocks, Jasmine 5.12 and Karma 6.4. Four of five additional geographic checks failed on the original source: a single bad coordinate, multiple bad coordinates, nonfinite numbers, and crossing the international date line. The fifth verified empty-enterprise default configuration. Total original result: TEN OF FOURTEEN passing.

An experimental local diff adds invalid-coordinate filtering, optional region bounds settings, and circular longitude midpoint geometry. It passes the original nine plus all five additional Jasmine cases: FOURTEEN OF FOURTEEN passing in headless Chrome. The bounds keys are NEW PROPOSALS, not settings already wired into the real OFN backend. No interactive map rendering, real geocoding, configurable zoom, layer bounds, global geographic datasets or full frontend application lifecycle were tested. The simple earlier median prototype was discarded because it fails multi-outlier cases.

Foodsoft: the original pinned OrdersHelper was loaded under RSpec 3.13 in an isolated official Ruby 3.3 container, with actual BigDecimal division of 1.7 kg by 1.3 kg per unit performed by a realistic price conversion fake. Nine authored RSpec assertions cover ordered, received, billed, genuine differences, absent data, custom discrepancy marker, and branch priority. Original source: SIX OF NINE passing, including three false quantity-discrepancy regressions. A temporary local diff makes the three-decimal comparison symmetric, preserving correct warnings, and passes NINE OF NINE.

These are ACTUAL test-framework executions of original source, not independent mathematical analogs. The exact published experimental unified diff files were reapplied to clean temporary copies and passed 14/14 browser Jasmine and 9/9 Ruby RSpec checks; source checkout Git statuses remained clean. They remain scoped: the original OFN full application Karma assets and Foodsoft complete Rails/database dependency suite were NOT run. In particular, Foodsoft bundle dependency verification could not resolve a Git-sourced gem inside its isolated environment. Do not claim a production-ready patch or user effect from these numbers.

## Pinned evidence and no-upstream-write controls

Source trees on the authorized Optiplex were checked at OFN commit 1167aa7b7585c1794199e032fc15c0e9c1c74104 and Foodsoft commit 337489007f863d64abf2fae7b20f440f1651ab00. The source blob hashes are recorded in the machine-readable report and matched the same source files from PR #84. The two experimental repairs are stored as small unified diff files, not copies of the third-party projects, and were tested on private scratch copies. No original upstream checkout was changed or contribution submitted.

Published executable test code:
- scripts/original_app_verification/browser_test_setup.cjs compiles pinned source and its original upstream Jasmine spec.
- scripts/original_app_verification/browser_karma.config.cjs configures a bounded browser test environment.
- scripts/original_app_verification/map_browser_regressions.js contains five additional Jasmine cases, including the dateline test.
- scripts/original_app_verification/foodsoft_helper_rspec.rb tests the real original Ruby helper with a conversion stub using BigDecimal.
- scripts/original_app_verification/candidates contains proposed source diffs only.
- cite-refinery-framework-suite-evidence validates original-vs-experimental test logs against pinned source revisions.

To rerun Karma, set CITE_VERIFY_NODE_MODULES to an isolated installation of Angular 1.8, angular-mocks, the upstream CoffeeScript 1.12.7 compiler, Jasmine, Karma and Chrome launcher. Generate service.js and original_spec.js in a temporary browser scratch directory using browser_test_setup.cjs with arguments for the original checked service path, checked Jasmine spec path, local node_modules path and output scratch path. Set CITE_VERIFY_BROWSER_SCRATCH to that directory and CHROME_BIN to the authorized Chrome executable, then run Karma against browser_karma.config.cjs. Rerun after applying the experimental patch to a COPY of the pinned source.

To rerun Foodsoft, install RSpec 3.13 in a temporary gem directory, then run foodsoft_helper_rspec.rb under Ruby 3.3 with TARGET_HELPER pointing at the SHA-checked original helper, then a scratch patched COPY, preferably inside a network-disabled, read-only container with a capped memory/process budget. Preserve JSON RSpec reports.

The suite evidence collector accepts --checkouts, --karma-original, --karma-candidate, --rspec-original, --rspec-candidate, --output and --markdown, with strict source pin and expected regression-count checks.

## Next hard gate

OFN must wire region bounds into actual admin/instance configuration, establish a policy for geographically distant legitimate customers, validate zoom and viewport policy, and test in the real map/frontend stack with synthetic and representative country data. Foodsoft must run RSpec with actual ActiveRecord order models and the full Rails application dependencies, including unit/precision boundary coverage and maintainer approval.

These issues are real public problem reports; neither constitutes a contract, a buyer commitment or documented commercial value. The research holdout was not accessed. The source graph has NO qualified commercial or scientific status promotion.

See research_materials/opportunity_atlas/FRAMEWORK_SCOPED_INTEGRATION.md and the updated OPERATOR_CONVERSION_ROUTES.md for exact results and next steps.
