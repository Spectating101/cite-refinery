# Breadth-first semantic landscape — exploratory seed v1

**Goal:** map a wide field of potential problems *before* selecting any single topic for intensive research. This is a first deliberately diverse source-backed map, **not** a representative census of global problems, exhaustive taxonomy, ranking, report or solved-problem inventory.

## What exists

- Input: `examples/landscape_breadth_seed_v1.json`.
- Rebuild: `python3 scripts/build_landscape_breadth_seed.py`.
- Nine broad fields with two topical modules each; 41 nodes (18 neutral anchors, 10 Practical, 6 Academic, 7 Program) and 24 deliberately **candidate** relations. There are no asserted or qualified source-to-solution relationships.
- Separate sandbox project: import with `SemanticGraph.ingest_packet` or existing `graph-ingest`, keeping the two acceptance cases and frozen v0.24 graph untouched.

## Initial field coverage (unranked)

| Field | Initial problem modules | Starting primary/source anchors |
| --- | --- | --- |
| Animal welfare | Population observability; management feedback | Taiwan MOA, Belo review, ICAM Talea |
| LLM privacy | Sensitive prompt exposure; sanitization limitations | Pinned CloakPipe evidence, ALSA |
| Renewable electricity | Curtailment and grid constraints; power-system flexibility | IEA Renewables 2025 |
| Food systems | Household food waste; measurement coverage | UNEP 2024, systematic review, Food Waste Index |
| Antimicrobial resistance | Surveillance completeness; response capacity | WHO GLASS 2025, AMR scoping review |
| Education | Out-of-school children; digital learning access | UNESCO GEM 2026, UIS Data Browser, systematic review |
| Digital inclusion | Broadband cost/access; skills and use | ITU Facts and Figures 2025, academic review, ITU DataHub |
| Water | Hydrological monitoring; flood/drought preparedness | WMO 2024 water status, HydroSOS |
| Housing | Adequacy; measurement comparability | UN-Habitat SDG 11.1 |

The field count reflects **purposeful heterogeneous sampling**, not evidence of societal problem severity. Many modules intentionally contain only their neutral anchor and no supporting evidence. A Program record may be a *measurement platform* or a *documented research implementation* rather than a field intervention; it must never be counted as a working solution without separate evidence.

## Three-layer interpretation

Practical = published real-world observation or reported concern; Academic = scholarly claim/method or finding; Program = documented software, dataset, program, policy or implementable capability. Neutral modules provide research questions, not verified facts. A candidate `RELATED_TO` or `CONTEXT_FOR` relation shows *where to examine evidence*, not support, causal attribution, adoption, completeness or effectiveness.

This map keeps the original dog and prompt-privacy case-specific source boundaries: official non-significance, provider functionality limits, bounded privacy test failures. **Do not merge it with case 01/02 acceptance state and claim its nodes are independently accepted.**

## Why breadth first, and what happens next

1. **Expand the map horizontally:** acquire a wider set of actual problem statements, scholarly explanations, policies, datasets, tools and working implementations across different domains. Use Nocturnal, Cite and Refinery where their source contracts genuinely supply evidence, plus external primary sources.
2. **Resolve topical identity:** split broad terms into exact semantic problem nodes, map parent/neighbor modules, preserve geography, dates, publication types, measurement definitions, provenance and contradiction. Do not collapse “has a dataset” into “has a solution.”
3. **Expose the landscape:** browse field modules, partial three-layer neighborhoods, unanswered questions and candidate inter-module relations. Absence of evidence is only absence *in this current search*, not proof of real-world absence.
4. **Only then pick depth targets:** choose a module because the graph reveals an interesting question, repeated mechanism, substantive contradiction or evidence gap worth investigating—not simply because it was the first example collected.

## Verification and limitations

An isolated project can ingest the exact packet without mutating existing accepted cases. Run:
```
PYTHONPATH=src:. python3 -m unittest discover -s tests -p 'test_landscape_breadth.py' -v
PYTHONPATH=src:. python3 -m unittest discover -s tests -q
```

No statistical comparability across countries, time periods, or outcome measures is established. Papers were represented through inspected abstracts/reviews, not independent empirical replication. The 9-field seed does not have selection probability weights, market sizing, impact estimates or a composite “coverage score.” No approved intervention or executable Program-side solution was established.
