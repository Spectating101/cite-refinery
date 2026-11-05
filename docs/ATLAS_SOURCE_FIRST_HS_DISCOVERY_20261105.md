# Atlas source-first engineering discovery: Hardware Splicer

**2026-11-05 | Engineering research pilot | Unmerged draft, no integration claims**

## What now runs

The existing Cite–Refinery multi-source GitHub collector and capability review are combined into an objective-profile-driven command-line workflow. The user supplies an engineering objective and capability questions, not a named list of competing repositories. Atlas generates bounded GitHub searches, screens candidate descriptions with existing mandatory-concept matching, then retrieves original public Git repository metadata, a pinned commit, a bounded source tree and up to two original code blobs per candidate. It checks the exact Git SHA-1 blob digest against fetched bytes. It does not execute third-party code, run a local printer, test an API, or promote a repo to a trusted capability.

Five configured engineering questions cover URDF, parametric CAD, KiCad DRC, multi-device printer controls and KiCad BOM generation. These **question categories and lexical/code tokens are operator configured**. This is **NOT unrestricted autonomous natural-language planning**, objective decomposition by an LLM, or a claim that file existence demonstrates a working device function.

The same source inspection is used on the existing Hardware Splicer default branch, pinned to commit 38dbad2b759a9313b81a5b10bfde7f20d64f308c. A matching code token in HS is **possible existing functionality**, not functional equivalence; it triggers a comparison before suggesting installation of another library. **Open HS PRs and non-default branches are not included.**

## Live evidence (November 5, 2026)

| Evidence | Result |
|---|---:|
| Capability questions | 5 |
| GitHub repository search candidates observed | 43 |
| External repositories inspected at original Git SHA | 13 |
| Capability areas with source code literal indicators | 5/5 |
| Plain GitHub first results also meeting source code indicator | 5/5 |
| Atlas top review results meeting source code indicator | 5/5 |
| Tied original-source evidence priority areas | 4/5 |
| Capability areas with possible existing HS code | 5/5 |
| Runtime integrations, authenticated operator reviews and license clearances | 0 |
| Auto-merges, trusted registrations, physical device actions | 0 |

**Comparison conclusion: no demonstrated ranking advantage over ordinary GitHub search.** The better-supported value is explicit provenance, original source file verification, conservative evidence-state separation, and detection of possible duplicate work within HS. The same evidence scoring across alternatives often produces ties; these are displayed instead of inventing a winner. Code-source hints are not independent engineering proof.

The actual report contains pinned original-source links to Unity URDF, CadQuery, KiCad inspector/DRC, Klipper/OctoPrint printer adapter, and BOM generator files. It also links existing HS code in CAD, PCB DRC, simulation, printer and BOM-related areas. The source evidence should be treated as review leads. Some matched code may be generic or merely related to the topic.

## Artifacts

- Objective profile: examples/discovery/hardware_splicer_capability_goal_20261105.json
- Actual live source-evidence receipt: examples/discovery/hs_atlas_source_investigation_20261105.json
- Human-readable source and comparison report: reports/hs_atlas_source_investigation_20261105.md
- Reusable read-only CLI and source-inventory validation: src/cite_refinery/atlas_capability_investigator.py
- Offline synthetic adversarial provider/source/score tests plus pinned snapshot assertions: tests/test_atlas_capability_investigator.py

Example invocation from Cite–Refinery root:

    PYTHONPATH=src:. python3 -m cite_refinery.atlas_capability_investigator --goal examples/discovery/hardware_splicer_capability_goal_20261105.json --out-dir /private/atlas-runs --stem hs_probe --probes 2

Requires an authenticated GitHub CLI for read-only network retrieval. The CLI refuses to overwrite an existing output. The GitHub API SPDX label is unreviewed metadata; legal approval remains pending. All external code is read as untrusted data only, never executed. No Research Drive imports, PDF work, new frontend, or separate app.

## Recommended next real integration test

**PCB design-rule checking:** take one known-good KiCad board and one board with a deliberately seeded violation, and compare the existing HS DRC path against an external candidate such as salitronic/eda-agent using KiCad's actual DRC output as the reference. Run in an isolated environment and record false positives, missed violations, dependency/licensing friction, and setup effort. Integrate only if an independently demonstrated new ability or measurable improvement justifies it.

**Printer interfaces must first use mocked OctoPrint/Moonraker services. Do not connect physical hardware or issue real print commands from a discovery result.**

This product pilot is **source-discovery acceptance only**, not a verified end-to-end autonomous investigation or a better recommender. A human must choose technical acceptance tests and independently assess results before a build/integrate decision. Both original PRs remain draft HOLD. No code published as trusted capability or production deployment.
