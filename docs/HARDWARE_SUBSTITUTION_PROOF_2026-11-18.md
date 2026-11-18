# Supply-driven PCB and enclosure substitution: executed proof

## Result

A shortage fixture now drives real engineering artifacts through Cite-Refinery's existing subprocess capability registry:

**KiCad 9.0.2 → DSN → Freerouting 2.5.0 → SES → native KiCad DRC → Gerber/drill files → board-derived connector geometry → CadQuery 2.7.0 → STEP re-import checks → BOM and material-volume planning.**

The illustrative job contains 40 passive adapters: 24 standard enclosures and 16 reinforced enclosures. J1 changes from a 2.54 mm pitch TE footprint to a 5.08 mm pitch Phoenix footprint; J2 stays unchanged. Pin function equivalence is explicitly a fixture assumption. This is a new reproducible experiment; the previous chat's shortage/replanning implementation was not recovered and is not represented as reused code.

| Executed check | Result |
| --- | --- |
| Original and replacement PCBs | Both: zero native DRC errors, warnings and unconnected items |
| Actual routing interchange | DSN exported, real Freerouting executed, SES imported into saved PCB |
| Fabrication output | Eight Gerber/job/drill outputs per revision, bound to their source PCB hash |
| Four enclosure combinations | A/B × standard/reinforced: valid reimported solids, zero collisions, 0.5 mm connector clearance |
| Old enclosure with replacement J1 | Rejected: 162.504 mm³ interference in standard case; 243.756 mm³ in reinforced case |
| Removed SENSE traces | Two actual copper segments removed; native DRC reports one unconnected error, exit 5 |
| Same-name changed PCB | Rejected by the saved artifact hash |
| Earlier content review | Invalidated by the new package fingerprint; this is a simulated review identity, not human approval |
| Contract regressions | 21 focused unittest cases passed; synthetic receipt tests, distinct from the actual engineering executions |

The tools executed through project-scoped Refinery capabilities and implementations. The saved registry contains the real subprocess run records, including the deliberately failing old-case run. The existing Optiplex graph was not modified.

## What the generated files change downstream

The BOM is extracted from the saved board. Revision A requires 80 original connectors. Revision B requires 40 original J2 connectors and 40 replacement J1 connectors. The fixture has 40 free original connectors and 10 free replacements; five other replacements are reserved. Free stock is already net of reservations.

Therefore B needs **30 purchased replacements, in three packs of ten**, at **90 synthetic currency units**. The reserved five are never consumed. This is a conditional purchase requirement, not a supplier quote or confirmed order. Replacement purchase fulfillment is assumed; supplier stock, a cash ceiling and arrival scheduling are not modeled.

Reimported case solids produce the following planning inputs:

| Input or result | Original A | Replacement B |
| --- | ---: | ---: |
| Total solid material volume for 40 cases | 695,320.69344 mm³ | 685,020.66144 mm³ |
| Printing estimate at the declared rate and overhead | 28.971696 h | 28.542528 h |
| Available printing capacity in fixture | 24 h | 24 h |
| Additional capacity needed in fixture | 4.971696 h | 4.542528 h |

The substitution clears the material shortage **conditional on buying the replacements**, but the modeled job still exceeds printing capacity. The runner preserves that infeasible result. These hours come from solid volume divided by an assumed 8 mm³/s, multiplied by 1.2 overhead. They are not slicer estimates or measured printer times.

## Implementation

- `examples/hardware_substitution/job.json`: explicit revision, interface, geometry, inventory and capacity fixture.
- `scripts/hardware_substitution_pcb.py`: genuine footprint-based board generation, DSN/SES routing, native DRC, fabrication exports, and the disconnected-copper negative control.
- `scripts/hardware_substitution_cad.py`: source-board-driven base/lid generation, STEP/STL exports, reimported-solid checks, and old-case interference measurement.
- `src/cite_refinery/hardware_substitution.py`: portable manifest, byte-hash joins, specification/board/rule/DRC/CAD consistency, review invalidation and derived material inputs.
- `scripts/run_hardware_substitution_proof.py`: registers and invokes these steps through the existing Cite-Refinery kernel; writes run, experiment and artifact records.
- `tests/test_hardware_substitution_contract.py`: focused malformed/stale/mixed-artifact and accounting regressions.

The verifier reads native DRC result arrays instead of trusting a `pass` flag. It binds the checked board, native project and rules, DSN/SES, geometry source, manufacturing outputs and case files. Nonfinite dimensions, fake part counts, stale reports, mixed revisions, missing fabrication formats and path escapes fail. Hashes protect package consistency; they are not cryptographic proof that a hostile party could not fabricate an entirely new receipt set.

## Reproduce

Requirements: KiCad CLI and its `pcbnew` Python environment, a Python environment with CadQuery, and the official Freerouting 2.5.0 Linux Java application bundle. The core module itself has no third-party Python dependency.

```bash
python scripts/run_hardware_substitution_proof.py \
  --output /absolute/new-output-directory \
  --pcb-python /usr/bin/python3 \
  --cad-python /path/to/cadquery/python \
  --freerouting /path/to/freerouting-2.5.0-linux-x64/bin/freerouting
```

Use an empty output directory; previous execution evidence is retained. The runner copies the fixture into the bundle and creates a new local Refinery project. It does not need an API key or contact a supplier.

Verify a relocated output bundle without rerunning CAD tools:

```bash
PYTHONPATH=src python -m cite_refinery.hardware_substitution \
  --root /path/to/unpacked-bundle \
  --manifest /path/to/unpacked-bundle/manifest_B.json
```

Run the contract regressions:

```bash
PYTHONPATH=src python -m unittest discover -s tests \
  -p test_hardware_substitution_contract.py -v
```

Bundle paths in manifests and artifact descriptors are relative. Historical subprocess command lines and registry invocation paths are absolute execution records; recreate those with the portable runner on another machine. Pinned footprint files and `fp-lib-table` accompany the output for native DRC reproduction.

## Engine behavior observed

The official Freerouting native CLI started its routing job but did not produce an SES file within a bounded 150-second local attempt. The official Java application bundle routed the same input successfully. Both release archives matched the upstream published digest. The failed attempt and successful engine provenance are retained; this does not establish a general native-CLI defect.

Sources: [Freerouting v2.5.0 release](https://github.com/freerouting/freerouting/releases/tag/v2.5.0), [pinned CLI documentation](https://github.com/freerouting/freerouting/blob/v2.5.0/docs/command_line_arguments.md), [KiCad 9 CLI documentation](https://docs.kicad.org/9.0/en/cli/cli.html), [CadQuery import/export documentation](https://cadquery.readthedocs.io/en/latest/importexport.html). The precise versions and hashes used are recorded in the output receipts. KiCad footprint source and license notices are included with the bundle.

## Scope and next constraint

This proves a bounded digital artifact handoff for a simple passive board and enclosure. It does not validate arbitrary electronics, electrical ratings, schematic/ERC correctness, real supplier equivalence, connector height, solder clearance, cable access, strain relief, fastening, retention, manufacturing tolerances or a physical assembly. The connector's XY envelope comes from footprint F.Fab geometry; its 12 mm height is a declared assumption. STEP creation and checking use the same CadQuery/OpenCascade kernel.

KiKit, Hardware Splicer's own runtime, ERPNext and FilaOps were not executed or connected in this proof. No production inventory was changed and no physical job was released. No comparison with a competent manual engineer, commercial advantage or fulfilled customer job is claimed.

The next measurable execution boundary is **a specific printer profile and genuine slicer output feeding resource scheduling**, together with component/dimensional qualification before any physical build. This run has made that capacity constraint concrete while preserving the successful engineering artifacts.
