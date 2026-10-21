# Original upstream function replay — bounded v1

**Purpose:** advance the independent Implementation map from original Git metadata and source-code fingerprints to a genuinely executed upstream function test, without claiming generalized software quality, operator outcomes, safe network sandboxing or underconverted value.

## Pilot selected from existing independent source sample

The prior 44-repository original-code inspection returned 39 code-blob identity checks. Its **preselected** `github:blisspixel/recon` row includes:

- Original commit: `aad9746c29b5427263d7f7788373fcc85e7d4261`
- Source: `src/recon_tool/lexical.py`
- Git blob SHA-1: `c1a3dcaa8ea552ed508f89c05a9533f4aa7c4f54`
- File SHA-256: `d95915d73bde20b99d8e3d3cde93c45cf8809fbaf70a3fbd20093e50e64e5155`

The module contains a narrow standard-library lexical classifier for **observed subdomain naming patterns**; it is not a network reconnaissance test. The tested module's own design acknowledges that lexical environment/tenant/region-like names are not evidence of actual cloud infrastructure or tenancy boundaries.

## Execution contract

`implementation_original_function_trial.py` runs two explicit, separate phases.

1. **fetch** verifies the exact original repository source-tree audit identity, commit, path and blob fingerprint. Downloads **only that one reviewed GitHub API blob**, checks Git blob SHA-1 and full-file SHA-256 and refuses other original sources. Source is not embedded in version control or artifact uploads.
2. **replay** validates the source again, validates a separately declared 16-case fixture hash, and runs the original Python module in a short-lived `python -I -S` subprocess with a stripped environment. The module imports only `re` and `dataclasses` plus future annotations; risky import/name shapes trigger a preflight rejection.

**Limit:** Python interpreter flags, a stripped environment, AST checks and exact source hashes are *not* a security sandbox or network isolation. This is viable **only** for a previously manually reviewed, immutable source module. Do not point this at arbitrary repositories, install upstream packages, or create generalized arbitrary code execution in a CI runner. The full repository, its DNS or certificate-transparency collectors, network operations and deployment behavior are never invoked.

The fixtures check 16 predefined behaviors: environment prefix boundaries, numeric delimiters, embedded patterns, false positives, repeated region tokens, tenant patterns, wildcard exclusion, deduplication, multi-category classification, threshold suppression and minimum-match summaries. Their expected answers are independently specified in code before invoking the original function. Each case produces original actual value, expected value, pass/fail/error and the precise original source+fixture digest. The report includes failures: there is no pass-by-omission.

## Canonical commands

The existing implementation source-tree audit must already have run and be present.

```bash
python -m cite_refinery.implementation_original_function_trial fetch \
  --original-code-audit /tmp/implementation_original_code_structure_audit.json \
  --out-dir /tmp/original-reviewed-lexical

# No GITHUB_TOKEN is needed for replay.
python -m cite_refinery.implementation_original_function_trial replay \
  --source-dir /tmp/original-reviewed-lexical \
  --out /tmp/implementation_original_function_replay.json

cite-refinery investigate map-foundations \
  --academic-original-audit /tmp/academic_publisher_identity_audit.json \
  --implementation-original-audit /tmp/implementation_pinned_source_audit.json \
  --implementation-original-code-audit /tmp/implementation_original_code_structure_audit.json \
  --implementation-original-function-replay /tmp/implementation_original_function_replay.json \
  --implementation-atlas-out /tmp/implementation_with_executed_source.json \
  --json-out /tmp/layers_with_execution.json \
  --markdown-out /tmp/layers_with_execution.md
```

The Implementation map now has an additional **original pinned module with executable synthetic fixture receipt** stage. This is neither an independent audit of the broader repository, nor the earlier historical functional trial set (which remains 3 different assets outside the 1,287 survey). It does not promote `live_operational_implementations_verified`, reuse rights, market underconversion or cross-layer applicability.

## Verification / next tranche

CI runs the fixed, source-backed fetch and 16 replay checks on the original source; it will fail if source fingerprint or fixtures drift, and emits a reproducible results receipt. The original GitHub fetch step alone receives the GitHub token. The replay step gets no token injected by the workflow.

This one selected source gives **actual functional evidence for narrowly defined label classification**, not population-level functional verification across the 1,287 leads. Scale by adding separately reviewed, preregistered contracts across more original source categories, reusing safe specialized runtimes; never automatically execute arbitrary discovered repositories.
