# Mechanism-discrimination research plan

Cite-Refinery · 20 October 2026 · experimental. These are proposed study designs, not observations or validated causal effects.

## Purpose

The two-round Gemini investigation found credible reasons why CNVR street-dog counts may differ from underlying population abundance. It could not measure the relative contributions of immigration/abandonment, changes in detectability, or local births. This PR builds a mechanism-discrimination workflow: the LLM proposes falsifiable observational contrasts, a strict validator checks evidence receipts and scope, and a separate model critique can require revisions. More graph links are not substituted for missing measurements.

## Actual complete source ledger

The second round used evidence both newly retrieved and carried forward from Round 1. The new evidence input validates against 11 distinct persisted source IDs across the entire two-round investigation, not simply the eight last-round records. One WHO-hosted article had two different source excerpts under the same ID and URL; both passage digests are recorded and the excerpts remain one source identity, not independent studies. An ID reused with different URLs fails closed.

## Live Gemini results

An authenticated Gemini 3.8 Flash Medium invocation initially produced an answer rejected by the strict measurement-code validator; the attempted output was not imported. The ontology identifiers were then enumerated in the prompt and a second live model invocation succeeded.

| Proposed test | Alternative mechanisms | Necessary evidence |
|---|---|---|
| T1: mark–resight and detection calibration | Immigration/abandonment vs variable detectability | Individual dog photo IDs, repeat sightings, survey paths, observer/time/weather covariates |
| T2: demographic cohorts and arrival histories | Immigration/abandonment vs local births | Individual movement/age class, female reproductive and puppy histories, privacy-minimized ownership/relinquishment indicators |
| T3: calibrated detection and pup surveys | Variable detectability vs local births | Transect observation and detection probabilities, repeated effort, mother–pup observations |

Every alternative pair is represented. Every test contains contrasting predicted patterns, a non-identifying pattern, possible confounders, falsification conditions, and exact verified quoted source receipts. The model explicitly returned not_identifiable_from_available_sources; no percentage contribution or empirical impact estimate was invented.

## Actual skeptical review: a necessary correction

Gemini 3.8 Flash High separately critiqued the proposed protocols, but is the same model family as the planner. It classified:
- T1 — conditionally_useful: photo ID and spatial/open-population assumptions need stronger calibration and misidentification checks.
- T2 — not_discriminating: movement/cohort/household observations as originally proposed could still fail to distinguish mechanisms; also needs privacy minimization and less invasive methods.
- T3 — uncertain: distance-sampling g(0) and transect independence assumptions are not established, requiring improved double-observer detection calibration and field protocol checks.

The coded readiness gate returns revision_required. It never authorizes a field deployment, proves a causal mechanism or records independent expert acceptance. See critic_review.json and readiness_decision.json.

## Synthetic arithmetic illustration (not field data)

Under the elementary observation identity expected sightings = latent dog abundance times detection probability, all three scenarios below produce identical observations 80 to 100:

| Synthetic setting | True abundance | Detection probability | Expected sightings |
|---|---|---|---|
| Population growth | 100 → 125 | 0.80 → 0.80 | 80 → 100 |
| Changing visibility | 100 → 100 | 0.80 → 1.00 | 80 → 100 |
| Larger stable population | 120 → 120 | 2/3 → 5/6 | 80 → 100 |

This is not a capture-recapture fit, empirical demographic estimate, or proof that a named study has such detection rates. It proves only that aggregate expected counts cannot uniquely determine the two unknown quantities in this simplified model. Births versus immigration remain unidentifiable even after abundance is established without tracking individuals and reproductive observations.

## Engineering and graph

The installed entry point cite-refinery-discriminate validates a completed two-round investigation, builds a bounded model prompt, applies strict source-quote and measurement-schema gates, and optionally stages a neutral review packet. Copilot remains default; Gemini 3.8 Flash through Antigravity is an explicit provider. The optional raw-response path can capture invalid LLM JSON locally for debugging; invalid content is not promoted.

The real plan was staged in a copied research workspace, receipt sgpacket:1ca03cd1f4129fe8: 7 neutral nodes and 9 unresolved edges representing a gap, three hypotheses and three tests. Replaying the packet yielded the identical receipt; the old investigation remains done. The copied project graph contains 50 nodes and 71 relationships total (58 candidate, 13 unresolved). No accepted scientific or human-health effect records were created.

The outputs under research_materials/runtime_trials/discrimination_20261020 are protocol_candidate.json, critic_review.json, readiness_decision.json and synthetic_counterexample.json. All original sources remain attached to the local persisted investigation and are not indiscriminately reproduced in this repo.

To generate a new plan from a locally completed investigation, run:

    cite-refinery-discriminate --workspace /tmp/my-investigator --investigation-id EXISTING_ID --provider antigravity --model gemini-3.8-flash-medium --out /tmp/discrimination_plan.json --stage

For externally generated candidate JSON, use --model-output FILE instead of --provider. Any qualitative critic review is an aid, never an independent scientific authority.

## Next evidence gates

Revision of T2 and T3 under qualified research methods expertise, field feasibility/ethics review, privacy-safe individual identification procedures, prospective detection-calibrated repeated measurements and independent raw data are needed before an effect can be claimed. Anuradhapura source operational records and matched human rabies outcomes remain unavailable from the reviewed material. No external researchers were contacted, no production merge/deployment and no automatic authority promotion occurred.
