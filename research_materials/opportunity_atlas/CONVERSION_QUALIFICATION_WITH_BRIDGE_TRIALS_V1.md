# Conversion-discovery qualification sweep

**Coverage:** 4 source slices; 142 implementation observations; 21 proposed connections; 1 rejected fabricated/invalid candidates; 25 referenced repository identities.

**Original source:** 25 referenced repositories checked at the public GitHub API. **Original code execution:** 15 passing tests in 1 scoped suite(s). **Globally validated high-quality projects, verified underconversion and realized new capabilities: ZERO.**

## Candidate-by-candidate evidence and missing qualification tests

| Proposed connection | Repository source evidence | Technical source status | Bottleneck to investigate |
|---|---|---|---|
| slice-0:CV-01 — asset_to_problem | github:Kovelt/carbon-fr (source-checked) | unverified_original_functionality | no_demonstrated_need (UNVERIFIED) |
| slice-0:CV-02 — asset_to_problem | github:AuvroIslam/Nongor (source-checked) | unverified_original_functionality | missing_evidence (UNVERIFIED) |
| slice-0:CV-03 — asset_to_asset | github:Krishita17/GridShadow (source-checked); github:Bigdaddy1990/jackery_solarvault (source-checked) | scoped_upstream_simulation_tests_passed_not_real_world_qualification, unverified_original_functionality | integration (UNVERIFIED) |
| slice-0:CV-04 — research_to_asset | github:SOsintOps/Argos (source-checked) | unverified_original_functionality | no_demonstrated_need (UNVERIFIED) |
| slice-0:CV-05 — domain_to_domain | source-cited research only | academic analogy, no technical repo | missing_evidence (UNVERIFIED) |
| slice-0:CV-06 — asset_to_problem | github:transitland/transitland-atlas (source-checked) | unverified_original_functionality | no_demonstrated_need (UNVERIFIED) |
| slice-1:CV-01 — asset_to_problem | github:ALNezar/FishMaster (source-checked) | unverified_original_functionality | missing_evidence (UNVERIFIED) |
| slice-1:CV-02 — asset_to_asset | github:factorysemantics/factorysemantics-mes (source-checked); github:Alpha-Park/genpark-personal-agent-dynamic-home-energy-spot-tariff-arbitrage-skill (source-checked) | unverified_original_functionality, unverified_original_functionality | integration (UNVERIFIED) |
| slice-1:CV-03 — research_to_asset | github:soypat/lneto (source-checked) | unverified_original_functionality | no_demonstrated_need (UNVERIFIED) |
| slice-1:CV-04 — research_to_asset | github:judegomila/OnCo (source-checked) | unverified_original_functionality | coordination (UNVERIFIED) |
| slice-1:CV-05 — asset_to_problem | github:nadar71/FreddyFridge (source-checked); github:factorysemantics/factorysemantics-mes (source-checked) | unverified_original_functionality, unverified_original_functionality | missing_evidence (UNVERIFIED) |
| slice-1:CV-06 — asset_to_asset | github:tangency-labs/fieldcraft (source-checked); github:pasteurlabs/tesseract-core (source-checked) | unverified_original_functionality, unverified_original_functionality | integration (UNVERIFIED) |
| slice-1:CV-07 — domain_to_domain | source-cited research only | academic analogy, no technical repo | rights (UNVERIFIED) |
| slice-2:CV-01 — asset_to_problem | github:j4ggr/DaSPi (source-checked); github:Syracuse3DPrintingOrg/PantryRaider (source-checked) | unverified_original_functionality, unverified_original_functionality | no_demonstrated_need (UNVERIFIED) |
| slice-3:CV-01 — asset_to_problem | github:TheWillMiller/river-wise (source-checked); github:sdmlua/FIMserv (source-checked) | unverified_original_functionality, unverified_original_functionality | integration (UNVERIFIED) |
| slice-3:CV-02 — asset_to_problem | github:wilsto/pool-monitor-card (source-checked) | unverified_original_functionality | no_demonstrated_need (UNVERIFIED) |
| slice-3:CV-03 — asset_to_asset | github:alphaparkinc/genpark-agentic-commerce-vendor-lead-time-po-safety-stock-skill (source-checked); github:ncsa/eidolon (source-checked) | unverified_original_functionality, unverified_original_functionality | missing_evidence (UNVERIFIED) |
| slice-3:CV-04 — asset_to_problem | github:alphaparkinc/genpark-agentic-commerce-vendor-lead-time-po-safety-stock-skill (source-checked) | unverified_original_functionality | missing_evidence (UNVERIFIED) |
| slice-3:CV-05 — asset_to_problem | github:lindbrook/cholera (source-checked); github:openstreetmap-polska/openaedmap-backend (source-checked) | unverified_original_functionality, unverified_original_functionality | missing_evidence (UNVERIFIED) |
| slice-3:CV-06 — asset_to_asset | github:Sinity/polylogue (source-checked); github:ShipfoxHQ/shipfox (source-checked) | unverified_original_functionality, unverified_original_functionality | integration (UNVERIFIED) |
| slice-3:CV-07 — domain_to_domain | source-cited research only | academic analogy, no technical repo | missing_evidence (UNVERIFIED) |

## Reproduced source-interface restriction: slice-0:CV-03

**Specific unsupported direct mapping:** Jackery measures battery/AC telemetry. GridShadow requires source-specific line/transformer/generator topology indices and control semantics. The sources do not supply an approved physical mapping.

**Pinned source revisions:** Krishita17/GridShadow @ bbeaa5d1d1b6, Bigdaddy1990/jackery_solarvault @ 36a89d127663

**Original values rejected as grid-element actuation:** FIELD_SOC, FIELD_GRID_IN_PW, FIELD_GRID_OUT_PW.

**Next verification:** Obtain consented, topology-validated source schemas and real requirements before building a simulation adapter; do not infer such topology from names.

This disproves only the *raw field-to-grid-actuation shortcut*, not all future integration. There is NO live device test, confirmed underconversion barrier, whole-project quality certification, or demonstrated external value.


## What can be claimed now?

- Real source repository metadata was inspected, but README promises and release activity are not independent deployment evidence.
- Only separately pinned original-source test suites can establish narrow functional behavior; the user-generated new cross-project combination remains untested.
- No negative adoption survey or usage baseline exists yet, so **underconversion is still a hypothesis**.
- Missing or unclear license declarations block reuse assumptions, not all future study.
- Models may propose a novel mechanism, but source support, novelty and usefulness require external or experimental checks.

**Next path:** inspect licenses and code rights, independently run original components, investigate actual users/alternatives, then test a small integration or within-layer analogy against field data. A funding resource may help later but is never a prerequisite.
