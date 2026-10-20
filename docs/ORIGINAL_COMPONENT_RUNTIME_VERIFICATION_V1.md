# Original upstream component execution: two maintainer-reported problems

October 21, 2026. Draft child of Cite-Refinery PR #83.

## Why this differs from the previous arithmetic analogs

Cite-Refinery executed the real, pinned original Open Food Network CoffeeScript factory and Foodsoft Ruby helper. Only synthetic inputs were used. No complete application, external customer system, Rails database, or browser was run. Both upstream Git checkouts and Git blob SHA-1 identities were confirmed unchanged before and after.

- Open Food Network: the MapCentreCalculator CoffeeScript at commit 1167aa7b7585c1794199e032fc15c0e9c1c74104, Git blob 74a669690f56c15f2c15ceffe34c8f02a96d0e27, compiled with CoffeeScript 1.12.7 as pinned in the project lockfile, and invoked through a minimal Angular factory capture in a separate Node VM.
- Foodsoft: the original OrdersHelper Ruby source at current sparse-checkout commit 337489007f863d64abf2fae7b20f440f1651ab00, Git blob 64567d22f2a02cd3d4b0a481ff1f8b581e90420d (identical to the issue's referenced older commit), was loaded into Ruby 3.3 and directly invoked with BigDecimal conversion stubs. Runtime used digest-pinned official ruby:3.3-alpine image, no network, read-only mounts, CPU/memory/process limits and dropped Linux capabilities.

No upstream source files were changed. Local repair experiments were carried out in temporary copies and discarded.

## Real component results

| Component | Executed original source | Temporary experimental patch | Missing proof |
|---|---|---|---|
| Open Food Network | Ordinary center fixtures pass, but one mis-geocoded latitude moves computed center from 51 degrees to 19 degrees | Median variant keeps the ordinary cases and handles the single outlier | Still FAILS a synthetic case with three bad geocodes. Country bounds and configurable zoom remain unsolved |
| Foodsoft | Actual helper incorrectly flags equal quantities in ordered and received branches; billed and genuinely different cases behave correctly | Consistent three-decimal comparison passes ordered/received and preserves billed and genuine differences | Complete Rails/RSpec integration, model quantity conversions and precision policy still untested |

The median candidate is not a complete or automatically safe map repair. Fixing a single outlier must not be confused with solving zoom, viewport policy, multi-outlier contamination or international geography.

## Operator gate integration

The same three-layer Practical/Academic/Implementation graph now attaches original-runtime evidence without changing any accepted claim status. The source-backed routes become:
- Open Food Network: complete_viewport_solution_then_integration_test
- Foodsoft: run_original_app_integration_before_contribution
- Battery and flood repairs and the CO2 rights blocker remain under their previous routes.

The original GitHub issues provide public operational problem evidence but **not** paying customers, funded work orders, deployment permission or maintained code acceptance.

## Reproduction

The optional runner is cite-refinery-original-component-trials. Give it --checkouts pointing to authorized local source checkouts, --output for JSON and --markdown for the human report. Checkouts and compiler/docker runtimes must be source-inspected and available. The project pytest suite verifies archived evidence and anti-promotion guards without downloading third-party projects or executing Node and Ruby.

See the original-component results in research_materials/opportunity_atlas/ORIGINAL_COMPONENT_EXECUTION.md and refreshed operator matrix in research_materials/opportunity_atlas/OPERATOR_CONVERSION_ROUTES.md.

**No Rails integration, browser workflow, actual user outcome, completed map solution, third-party pull request, revenue or research holdout use.**
