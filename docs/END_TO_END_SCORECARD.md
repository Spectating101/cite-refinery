# End-to-end project scorecard

`cite-refinery scorecard rproject:...` reports coverage at each authority boundary without collapsing the project into one composite number.

The stages are:

1. `empirical_problem_map` — Nocturnal matters/observations and source-presence coverage.
2. `research_agenda` — bounded research briefs and dependence on structural fallback questions.
3. `literature_discovery` — completed Cite deep-research acquisition receipts and paper counts.
4. `literature_grounding` — research briefs that completed grounding/synthesis audit.
5. `requirement_translation` — explicit capability requirements and research-lineage coverage.
6. `solution_mapping` — mapped requirements, candidate coverage, and candidate authority (`commons`, `operational`, `reviewed_market_graph`, etc.).
7. `execution_validation` — adopted capabilities, implementations, successful runs, passed/supported experiments, and promotions.
8. `nocturnal_feedback_loop` — whether post-intervention observations are explicitly linked back to the originating project/run/experiment.

## Why there is no composite score

A downstream success cannot compensate for a missing upstream evidence gate. For example, a successful subprocess run does not make an intervention literature-backed, and a large paper set does not make an empirical claim true. The scorecard therefore reports stage status and bottlenecks directly.

## Important boundaries

- Source presence is not source fidelity, accessibility, or truth validation.
- Literature discovery means papers were found, not that a mechanism or intervention is supported.
- Requirements are explicit decisions; literature output is not automatically converted into build instructions.
- `reviewed_market_graph` candidates are descriptive reviewed supply, not Commons admission or execution permission.
- Promotion requires the existing Cite-Refinery run/experiment gates.
- Cite-Refinery v0.7 still lacks a formal experiment/run → new Nocturnal observation contract, so the final feedback stage is expected to report `not_implemented` unless an external integration provides explicit provenance keys.

The intent is operational: a user should be able to see exactly whether the next bottleneck is empirical evidence, literature acquisition, synthesis, requirement translation, supply coverage, implementation validation, or real-world feedback.
