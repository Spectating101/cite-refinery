# Independent Implementation Atlas — capabilities, not repository popularity

**22 October 2026. Source-qualified implementation map, stacked on Academic PR #101 and Nocturnal Practical PR #100.**

## The critical discovery

The earlier wide GitHub search identified **1,287 distinct source-repository leads** and **1,360 repository/category memberships** (220 metadata-semantic reviews, 1,140 unreviewed memberships). Those are *research leads*, not 1,287 technologies proven useful. The existing original GitHub source audit was limited to a balanced **44 category-pair** sample, with pinned revisions and root directory identities; this was not a code run.

The existing functional component trials concerned **three entirely different repositories, absent from the 1,287-lead survey**:

- `lingrany/EverBatt-LFP-Recycling-Analysis`, pinned `246c4d4…`: synthetic fee-accounting probes (three critical paid-gate-fee handling failures), not validated plant economics.
- `WeixuanZ/flood-warning-system`, pinned `c1c7fac…`: synthetic flood-station threshold/ranking probes (nonfinite NaN telemetry failure), not operational forecasting or public warning effectiveness.
- `ajlongshanks/co2_esphome`, pinned `d1b3c50…`: static YAML/configuration trial, not deployed firmware or calibration.

The original frozen trial JSON contains **6 pass, 7 fail, 1 blocked, 3 not-tested** requirement cases. The atlas keeps **17 individual testable requirement receipts**, including **11 recorded failures, blocked checks or untested gaps**; it supports exact within-Implementation queries such as `--implementation-requirement-terms NaN --implementation-requirement-status fail`. A positive case proves only that the original investigator reported the tested bounded synthetic behavior; this new map does **not** independently rerun those untrusted upstream programs or verify external signed authorship. We do **not** claim 3/1,287 sampled implementations work, since overlap is exactly zero.

## What this branch adds

The Implementation evidence atlas (`src/cite_refinery/implementation_evidence_atlas.py`) preserves three distinct evidence populations without conflation:

1. **Original survey layer**: all 1,287 GitHub leads, survey category memberships, metadata semantic review labels, source citation, license *label* and popularity fields (neither proves capability/adoption nor rights).
2. **Pinned original-source layer**: original GitHub API commit/root receipts and optional new tree/blob SHA-verification receipts. A code sample may confirm the exact existence of a parsed function or test source at a revision, not whether that code works or is safe.
3. **Previous bounded functional trials**: 3 separate upstream assets, 17 explicit probe requirements with original recorded statuses, expected/actual snapshots, failure names, limitations, scopes and pinned upstream revisions. This is a historical evidence trail, not newly executed tests or certified results.

The original-code auditor (`src/cite_refinery/implementation_original_code_audit.py`) samples up to 60 independently pinned public GitHub revisions. It follows the GitHub commit → tree → git blob SHA-1 identity chain; samples an eligible original source file plus an eligible test file when present, validates Git blob hashes, and optionally parses Python AST to identify structural public functions. It **never imports code, installs dependencies, executes tests, downloads entire repositories, runs arbitrary script instructions, or republishes original source contents**. Inconclusive, truncated and unavailable upstream data remain explicit failures. GitHub API records are not cryptographic signatures from an independent authority.

### Canonical commands

Export the Implementation map including the original three historical probes, independently of Academic or Practical:

```bash
cite-refinery investigate map-foundations \
  --implementation-component-trials research_materials/opportunity_atlas/functional_component_trials.json \
  --implementation-stage historical_trial \
  --implementation-atlas-out /tmp/implementation.json \
  --json-out /tmp/maps.json --markdown-out /tmp/coverage.md
```

Given the two read-only original-source metadata audits already produced by the existing `original_layer_source_audit` step, inspect up to 44 previously pinned code repositories using **public GitHub API only**:

```bash
python -m cite_refinery.implementation_original_code_audit \
  --original-implementation-audit /tmp/implementation_pinned_source_audit.json \
  --max-repositories 44 \
  --out /tmp/implementation_original_code_structure_audit.json
```

Attach original source checks and historical functional trials to the **same standalone map**:

```bash
cite-refinery investigate map-foundations \
  --academic-original-audit /tmp/academic_publisher_identity_audit.json \
  --implementation-original-audit /tmp/implementation_pinned_source_audit.json \
  --implementation-original-code-audit /tmp/implementation_original_code_structure_audit.json \
  --implementation-component-trials research_materials/opportunity_atlas/functional_component_trials.json \
  --implementation-atlas-out /tmp/implementation_enriched.json \
  --json-out /tmp/maps_enriched.json \
  --markdown-out /tmp/implementation_coverage.md
```

Original-source and component evidence can be navigated by `--implementation-category`, `--implementation-terms`, and `--implementation-stage` (survey / original_commit / source_sample / historical_trial). Browsing is literal, **not semantic truth discovery**, with no cross-layer edges or quality ranking. Scoped requirement search returns recorded case status and pinned original upstream revision; it cannot extrapolate successful tests to untested safety requirements or a different code revision.

## Executable/operational test maturity ladder

| Evidence tier | What is supported | What is *not* supported |
|---|---|---|
| Source index | Original claimed project/topic exists in metadata | Useful function, uptake, licensing |
| Pinned Git revision/root | GitHub API reported exact source revision/root listing | Tests pass, actual function, complete dependency closure |
| SHA-validated code blob | Source file is directly linked to the pinned Git tree; Python AST can parse | Function correctness, safety, deployment |
| Prior synthetic probe | Historical receipt records a scoped pass/fail/blocked/untested requirement | Reproduced independent evaluation, field benefit |
| Independently executed sandbox benchmark | **Not yet delivered by this branch** | Cannot claim it happened |
| Operator outcome and license permission | **Not established** | No successful field deployment or underconversion claims |

## Coverage and remaining gaps

There is no dishonest global `percent functional` metric: the denominator for functional tests is a targeted nonrandom set of three prior projects, **not** the 1,287 leads. No project has been promoted into evidence of a complete operational solution; no original commercial reuse grant or realized conversion has been reviewed.

To increase actual capability coverage next, sample domains from the *original repository universe*, execute narrow representative original code on genuinely isolated machines under preregistered failure cases and input fixtures, attach immutable per-case receipts, and separately investigate licensing, safety and operational context. Hardware, non-GitHub forges, deployed services and dataset tools are outside this first indexed GitHub survey and should be brought in as distinct source families—without pretending they are already covered.

## Verification

Focused tests use the **actual 1,287-repository manifest and three historical trial records**, plus synthetic GitHub API tree/blob identities, and reject contradictory pinned commits, digest substitutions, fake functional promotion, malformed cases and corrupted aggregate counts. GitHub Actions additionally attempts real original-source sample inspection and emits source/historical-trial artifacts, which should be read for success/failure counts rather than assumed positive.

All inputs are read-only, no source-repo branches are changed, and the new checks do not alter Academic's sealed 66-source holdout, Nocturnal's public release approval, or Refinery Commons promotion policy.
