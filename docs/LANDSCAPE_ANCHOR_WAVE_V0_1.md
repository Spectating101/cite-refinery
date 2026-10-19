# Anchor wave v0.1: breadth-first three-layer evidence map

**Status:** review-only / candidate evidence. Built 2026-10-20 from the user's completed *Cite-Refinery Anchor Ingestion* Deep Research report; stacked on PR #47's reconstructed 54-module registry (itself stacked on PR #46). Not merged, deployed, or accepted.

## What is actually in the packet

- **Nine fields / 54 module clusters** remain visible; **42 second-ring modules have no source claims**. Absence from the represented corpus is never evidence of absence from the world.
- **12 first-wave anchors** each have a Practical, Academic, and Program **source lead** (36 total). This is source-family representation, *not* equally strong evidence and *not* three effective interventions.
- **55 source-attributed claim/definition/capability nodes**: 23 Practical, 15 Academic, 17 Program. All are provisional and bounded; some are framework definitions or regulatory notices rather than observations of local conditions.
- **36 precisely worded, unresolved research-question nodes**, three per anchor, distinct from both the neutral module container and source assertions.
- **16 source-referenced candidate bridges** between modules, nine crossing field boundaries. No CAUSES, IMPLEMENTS, ADDRESSES, PRODUCES or effectiveness claim is asserted.
- **145 semantic nodes, 107 candidate graph edges, 64 clusters** in the isolated `cite_refinery.semantic_graph.v1` packet.
- A deterministic CSV coverage matrix and automatically derived **bridge investigation queue** for second-ring nodes neighboring a source-led anchor.

## Artifact contract

| Path | Description |
| --- | --- |
| `research_materials/landscape_20261020/anchor_wave_v0_1/anchor_sources_v0_1.json` | 36 canonical citations with publisher, date, scope, limitation, source type and automated address-check status |
| `research_materials/landscape_20261020/anchor_wave_v0_1/anchor_questions_and_bridges_v0_1.json` | 36 unresolved questions and 16 bounded cross-/within-field candidate relations |
| `research_materials/landscape_20261020/anchor_wave_v0_1/atomized_extra_claims_v0_1.json` | 19 additional narrowly worded, source-attributed claims and distinctions beyond the first claim per source |
| `research_materials/landscape_20261020/anchor_wave_v0_1/anchor_evidence_matrix_v0_1.csv` | 54 modules, exact represented source counts by P/A/P family |
| `research_materials/landscape_20261020/anchor_wave_v0_1/coverage_and_topology_v0_1.json` | Source types, source-access caveats, missingness, graph expansion queue, packet digest |
| `examples/landscape_anchor_wave_v0_1.json` | Reproducible **whole-map snapshot** to import into a **new isolated** Cite-Refinery project |
| `scripts/build_landscape_anchor_wave_v0_1.py` | Validated transformation and computed audit |
| `tests/test_landscape_anchor_wave_v0_1.py` | Eight epistemic/structural checks including idempotent graph ingestion |

The export is a **new snapshot**, not an incremental patch to `landscape_reconnaissance_wave1.json`; importing both into one project would artificially duplicate map representations.

## What the resulting graph actually says

**1. “We measure it” is structurally different from “we improved it.”** Five of twelve Program records are statistical data platforms (ITU, WHO UHC, FAOSTAT, OECD housing, JMP WASH); one is a multi-tier measurement framework and one a hydrological observing/outlook initiative. Other Program records cover financing, government support, agency adaptation plans, documented survey software, and exactly one bounded implementation assessment. **This sample does not independently verify any population-level intervention outcome.** Program lane presence must not be treated as solved-status or effectiveness.

**2. Access problems have multiple non-interchangeable properties.** Connectivity has availability, quality, affordability, device, skills and safety/security; electricity has connection, capacity, reliability and affordability; water has on-premises service, availability and contamination; healthcare has service access and financial protection; education has enrollment and demonstrated proficiency. The new problem questions preserve those distinctions so a downstream investigation cannot silently swap a convenient availability metric for a real outcome.

**3. Some graph neighborhoods deserve source acquisition without becoming chosen fields.** Candidate bridges connect electricity/connectivity/education, hydrological observations/agriculture, housing/health, food affordability/health, animal monitoring/One Health, and foundation-model privacy/PETs. These are **inspection leads, not independently discovered causal mechanisms.**

**4. The bridge queue is computed, not an importance ranking.** `ED-05` (connectivity for learning) and `PH-02` (equitable primary-care access) each have two currently source-led neighboring bridges. `AW-03`, `DP-05`, `FS-06`, `HO-03`, `HO-05`, `HO-06`, `PH-06`, `WA-05` each have one. This simple graph topology identifies next *places to look*, not higher social severity or confidence. Other unresearched modules—including those without any candidate bridge—must be sampled separately to prevent a self-reinforcing coverage bias.

## Source-access and review limitations

The 36 candidate URLs were address-checked from the authorized Linux workstation on 2026-10-20: **24 HTTP 200**, **11 HTTP 403**, and **one public 404**. HTTP 200 is *only route reachability*: some servers provide partial or dynamic shells; no full-text, method-by-method audit or primary data replication is claimed. The public 404 is the **pinned CloakPipe GitHub evidence URL**, which *was* successfully read using the authenticated GitHub connector at the same pinned SHA. The evidence states the core passed its bounded checks, four broader limitation probes leaked, and the result was `REUSE_CANDIDATE`; it does not certify the full privacy protection path.

The US FTC alert is a **regulatory-warning Practical source**, not an observed prevalence of foundation-model leaks. Other cases likewise preserve definition/observed-outcome distinctions. All evidence statements are **candidate source interpretations**, not locally validated factual findings. We have deliberately not reconstructed the original missing Deep Research CSV or created fabricated full-source coverage of the other 42 modules.

## Reproduce and QA

```bash
PYTHONPATH=src:. python3 scripts/build_landscape_anchor_wave_v0_1.py
PYTHONPATH=src:. python3 -m unittest discover -s tests -p 'test_landscape_anchor_wave_v0_1.py' -v
PYTHONPATH=src:. python3 -m unittest discover -s tests -q
```

The verification covers source-link identities, provenance fields, honest empty lanes, kinds within Program, strength-bounded relationships, regional scope caveats, deterministic regeneration, packet hash, idempotent duplicate import and isolated use of the graph store.

**Next:** review the most consequential source statements against primary datasets/actual full texts; obtain local deployment/outcome evidence where accessible; resolve whether the original research CSV differs from our reconstructed registry; expand to adjacent modules *and* disconnected fields while maintaining horizontal coverage. Only then ask Cite-Refinery to propose deeper investigations from the map itself.
