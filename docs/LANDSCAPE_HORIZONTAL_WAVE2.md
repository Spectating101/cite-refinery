# Cite-Refinery: horizontal landscape wave 2 (2026-10-20)

**Status:** research-only candidate graph, not merged, accepted, deployed or causal field analysis. This branch is stacked on draft PR #48 (itself stacked on draft PR #47 and draft PR #46).

## Purpose and actual output

Avoid converging prematurely around the original nine fields or around high-degree modules. Preserve broad but incomplete problem modules while adding **both** evidence on the neighboring unsourced nodes identified in anchor wave v0.1 **and** four independently selected new fields.

- Existing: **nine fields, 54 candidate modules**, 12 initial evidence anchors.
- New depth-adjacent breadth: **12 of the previous 42** unsourced modules supplied with 24 additional source leads; remaining **30 original second-ring modules still have no sourced claims**.
- New independent fields: **labor/occupational work, transport/road safety, ambient air quality, disaster risk and preparedness**, each with two intentionally different problem modules (**eight new modules**, 16 source leads).
- Entire graph snapshot: **13 fields, 62 candidate modules; 76 clusters; 213 nodes; 206 candidate edges**.
- New provenance material: **40 institutional/academic/technical source leads** linked to 20 module areas; **20 hand-authored, narrow, unanswered questions** that remain separate from the source claims.
- New bridge leads: **19 additional candidate relationships** between field-specific modules. They are deliberately **not** evidence of causal relationships. The previous graph snapshot's 16 candidate bridges are retained.

The independently chosen new fields are a deliberate defense against the map becoming a self-confirming, internally connected cluster. They should not be interpreted as four maximally important world problem areas, and they are not claimed to have come from the original missing Deep Research CSV.

## What is empirically visible *in the represented corpus*

1. **Measurement versus improvement remains a repeated distinction.** ILOSTAT, WHO's air quality database and road-safety country profiles, and the UNDRR Sendai Monitor publish measures; they are not policies demonstrated to improve measured outcomes.
2. **A reported system's existence differs from its reach.** WMO/UNDRR describe multi-hazard early-warning-system adoption, yet country-reported existence does not establish effective local dissemination, accessibility, response or reductions in disaster mortality.
3. **The meaning of access varies across sectors.** Youth *unemployment* and *NEET* are different indicators; road deaths by mode differ from total deaths; settlement-level air-quality readings differ from individual exposure; cold-chain infrastructure availability differs from realised smallholder sales.
4. **Academic evidence remains thin in this expansion.** Of the 40 new source leads, most are Practical/Program and only a small minority Academic. This is *not* a complete P/A/P neighborhood; do not synthesize academic consensus or intervention success.
5. **New graph-degree results are mostly bookkeeping, not discovery.** The newest bridge set was hand-specified from source overlap. After covering the original adjacency queue, the next unsourced modules with candidate incident bridges are `HO-03` (homelessness/prevention) and `WA-03` (urban water scarcity). Neither is ranked by human significance, evidentiary maturity or causal centrality. No novel causal discovery has been demonstrated.

## Representative grounded source constraints

| Field | Source | Claim scope; not proven |
| --- | --- | --- |
| Labor | ILO 2025 World Employment and Social Outlook / ILOSTAT | Headline unemployment vs youth NEET/underemployment; database is not a jobs program |
| Road safety | WHO Global Status Report on Road Safety 2023 | ~1.19m annual global road deaths in 2021 source estimates, not a 2026 measured count or a city causal diagnosis |
| Air quality | WHO 2024 air-quality database | Annual means from 7,182 settlements spanning observational years 2010–2022; does not establish equitable exposure monitoring in all neighborhoods |
| Disaster warnings | WMO/UNDRR 2025 early-warning status report | 119 countries reported multi-hazard warning systems; existence is not local alert delivery or impact |
| Groundwater | UN-Water WWDR 2022 and WMO hydrological assessment | Global resource context, not a local aquifer extraction-minus-recharge estimate |
| Food cold chains | UNEP/FAO 2022 | System overview and loss mechanisms, not an independently evaluated smallholder intervention |
| PETs | OECD 2025 and NIST SP 800-226 | Threat-matched trade-offs; no blanket or empirically verified end-to-end privacy guarantee |
| Rabies/DPM | WHO rabies fact sheet and WOAH Terrestrial Code Chapter 7.7 | Separate vaccination and population dynamics; neither guidance alone demonstrates a locally effective program |

The 40 source URLs are normalized in `research_materials/landscape_20261020/horizontal_wave2/source_leads.json`; the 20 questions are authored in `specific_questions.json`. Eleven sources blocked generic HTTP requests (403), 28 returned HTTP 200 and the canonical WOAH chapter was verified through a public web result instead of independently recorded as an HTTP 200. Route availability is not full-document review or independent data replication.

## Artifacts and regeneration

| Path | What it contains |
| --- | --- |
| `research_materials/landscape_20261020/horizontal_wave2/source_leads.json` | Forty source leads with publisher, kind, geographic scope, bounded claim, provider/access check and honest review limitations |
| `research_materials/landscape_20261020/horizontal_wave2/fields_and_bridges.json` | Four new field definitions, eight modules and nineteen proposed semantic bridges |
| `research_materials/landscape_20261020/horizontal_wave2/specific_questions.json` | Twenty specific, independently answerable investigation questions |
| `research_materials/landscape_20261020/horizontal_wave2/graph_discovery_audit.json` | Computed per-module evidence presence, degree, next unsourced neighbors, source-access status and packet digest |
| `research_materials/landscape_20261020/horizontal_wave2/coverage_matrix.csv` | Sixty-two source-lane/degree rows, including explicit zeros |
| `examples/landscape_horizontal_wave2.json` | Rebuildable `cite_refinery.semantic_graph.v1` *entire snapshot* for import to a new isolated project |
| `scripts/build_landscape_horizontal_wave2.py` | Graph builder and machine-computed audit |
| `tests/test_landscape_horizontal_wave2.py` | Evidence honesty, topology, reconstructability and isolated import/idempotency gates |

```bash
PYTHONPATH=src:. python3 scripts/build_landscape_horizontal_wave2.py
PYTHONPATH=src:. python3 -m unittest discover -s tests -p 'test_landscape_horizontal_wave2.py' -v
PYTHONPATH=src:. python3 -m unittest discover -s tests -q
```

Do not ingest the prior snapshot together with this one: it repeats existing nodes under a different research source system and would artificially inflate represented evidence. Ingest **one** complete snapshot per isolated landscape project until cross-packet identity/upsert semantics can guarantee equivalence.

## Limits and follow-on experiment

The corpus is heavily biased toward global international institutions, their monitoring programs, English language publications, and evidence that is easy to identify on public pages. It is not a systematic census of problems; none of the proposed causal/action edges is promoted; no field has validated intervention effects at scale. Do not use node count as an estimate of real-world coverage or knowledge completeness.

A meaningful **next analytical experiment** should not merely add volume. Sample some unsourced nodes from disconnected fields and from connected modules, source their competing explanations, then run *blind* semantic bridge generation with evidence thresholds against the existing hand-specified candidate edges. Evaluate which proposed edges are genuinely new, which are false merges, whether sources actually support the direction/type, and whether alternative explanations remain visible. The first genuinely independent graph-discovered relationships will only be those arising from that prospective test, **not** relationships pre-seeded in the manifests.
