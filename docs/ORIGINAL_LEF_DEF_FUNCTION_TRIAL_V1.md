# Second original-source execution trial: LEF/DEF compatibility parsing

**Purpose:** validate a separate engineering capability from the Implementation Atlas's original 44-repository category-balanced source audit, without passing off code presence as functionality or one bounded test as full production quality.

## Original upstream identity

Source repository: `Mr-Fang-VLSI/EDAgent`, pinned revision `18211ef80ae15c75e17100ed18890706f4245314`.

Original file: `skills/bspdn-physical-contract-auditor/references/scripts/scripts__debug__check_lef_layer_compatibility.py`. Git-blob SHA-1 `17d4689a87890c80c92a71aaae51cc9c856d9e6d`; full file SHA-256 `5f5b449584a86ceecf90330e412fab8f511771976238aad168a562dfcd332d78`.

Only this one checked source file is fetched with a GitHub token, after confirming the repository, commit, path and binary digest against the existing original-code inspection receipt. The second stage rechecks both hashes and executes the same Python source in a stripped `-I -S` subprocess. No real LEF/DEF PDK, foundry design, synthesis tool or proprietary EDA dataset is used. The original text is not rehosted in this repository or downloadable CI artifacts.

This is **not** an OS/network sandbox for arbitrary upstream code. The fixed module has been reviewed as a standard-library checker. CI does not run the upstream program's full CLI, shell commands or full EDAgent system. It calls only parsing and style-qualification functions against private temporary synthetic LEF/DEF fixture files.

## Independent 16-case protocol

The frozen fixtures cover technology LEF layer declarations, leading whitespace, case-sensitive parsing, ignored comments in technology LEF, design LEF references, DEF TRACKS parsing, absent/unknown DEF paths, metal/via nomenclature, missing cross-file layer references, duplicate references and an adversarial *commented design LEF* input.

The last case tests an important failure mode: a line `# This is a comment: LAYER PHANTOM` should not create a real design-layer reference. The original implementation uses an unanchored design-LEF regex, so the test may reveal a spurious phantom layer. The runner records the observed result as **fail** when it disagrees with the preregistered expectation; it does not patch upstream code or silently discard the input.

The audit records test ID, actual output, expected output, status, original commit and both original-source/fixture digests. Case failures are **bounded synthetic defects**, not demonstrated errors in a real production chip, nor a conclusion that the broader EDAgent product does not work.

## Commands

```bash
python -m cite_refinery.implementation_original_lef_def_trial fetch \
  --original-code-audit /tmp/implementation_original_code_structure_audit.json \
  --out-dir /tmp/original-reviewed-lef

python -m cite_refinery.implementation_original_lef_def_trial replay \
  --source-dir /tmp/original-reviewed-lef \
  --out /tmp/implementation_original_lef_def_replay.json

cite-refinery investigate map-foundations \
  --academic-original-audit /tmp/academic_publisher_identity_audit.json \
  --implementation-original-audit /tmp/implementation_pinned_source_audit.json \
  --implementation-original-code-audit /tmp/implementation_original_code_structure_audit.json \
  --implementation-original-function-replay /tmp/implementation_original_function_replay.json \
  --implementation-original-lef-def-replay /tmp/implementation_original_lef_def_replay.json \
  --implementation-atlas-out /tmp/implementation_with_two_executed_sources.json \
  --json-out /tmp/consolidated_maps.json \
  --markdown-out /tmp/implementation_coverage.md
```

The Implementation Atlas accepts the second receipt only if the originally pinned source exists in the surveyed 1,287-repository universe, is already linked to the 44-repository original code audit, and each fixture and actual result remains intact. Coverage will report **two originally executed source modules**, separate original case pass/fail counts, three prior historic external trial assets still *outside the 1,287 survey*, and **zero** live operator outcomes or established commercial underconversion.

No Practical or Academic assertion or cross-layer edge is generated. Real LEF/DEF grammar compliance, other input-file corner cases, secure arbitrary-file handling, source licensing and suitability for an actual electronics manufacturing workflow remain open.
