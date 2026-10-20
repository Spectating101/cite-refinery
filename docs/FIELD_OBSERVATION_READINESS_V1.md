# Field observation readiness — repairs to T2/T3

20 October 2026 · Cite-Refinery · experimental engineering validation.

**No animals were observed, no owner data accessed and no participants enrolled. All bundled observations are expressly synthetic.** This branch follows PR #66 and its separate Gemini High critical review (T1 conditionally useful; T2 not discriminating; T3 uncertain).

## Why

Unadjusted CNVR street-dog counts cannot establish relative contributions of immigration/abandonment, births and survey visibility. This minimum data-quality contract makes missing observational prerequisites inspectable, but **never turns a filled-in data form into a causal result or field approval**.

Independent double-observer surveys are one way to address the conventional distance-sampling assumption g(0)=1, but they require explicit matching and observer-independence assumptions. See University of St Andrews teaching materials: https://distancesampling.org/online-course/11-mrds/mrdslanding.html, and Burt et al. (2014), DOI 10.1111/2041-210X.12294: https://www.usgs.gov/publications/using-mark-recapture-distance-sampling-methods-line-transect-surveys. **This code does not fit an MRDS model or estimate g(0).**

## Exact observational interchange

Schema identifier: cite_refinery.noninvasive_dog_observation.v1

| Table | Required fields | Why |
|---|---|---|
| visits | visit_id, round_id, site_code, survey_day, planned_effort_km, actual_effort_km, fixed_route, observer_independent, observer_blinding_documented, weather_code | Comparable survey effort, time windows and protocol |
| detections | visit_id, event_code, observed_a, observed_b, match_status, matching_confidence, distance_m, animal_code, age_class, reproductive_sign | Independent paired observer detections, matching confidence, individual pseudonym and reproductive class |
| origin_evidence | event_code, origin_class, evidence_kind, corroborated, consent_confirmed | Putative cross-boundary/arrival or resident mother evidence, or deidentified reports |

Additional top-level keys are schema, synthetic, species. Only the approved fields are accepted. Precise GPS, names, addresses, contacts, household IDs, original photo/video or owner identity mappings are prohibited from this interchange. The pseudonymous animal code is NOT anonymous in an absolute sense: any sensitive photo-ID mapping, if necessary, requires separately governed controlled storage and consent/ethics review. Human voluntary reports require confirmed consent.

An origin-evidence value of corroborated=true is a **field declaration**, not independently established scientific truth. Dog births, immigration, abandonment and detection effects can co-occur.

## Repairs to the criticized tests

**T1 — Mark–resight:** Repeat individual pseudonyms and record matching quality, effort, spatial boundary coverage and independent observer procedures. Still requires specialist checks for false splitting/merging, open-population assumptions and model identification.

**T2 — Immigration vs local recruitment:** Compare repeated animal identities, age/pup cohorts and observed resident-mother indicators with cautiously classified cross-boundary observation and privacy-minimized voluntary owner reports. Collars, genetic tests, invasive animal tracking and identifiable household surveillance are **not mandatory**. The original critique remains: these measurements may still fail to separate true arrivals from local births or distinguish immigration from abandonment. Requires actual corroboration, uncertainty and external methods review.

**T3 — Detection vs local reproduction:** Collect independent/blinded paired observers, match confidence, repeated effort, sighting distance, age and maternal indicators, without assuming certain detection on a transect line. Proper MRDS modeling, den detectability, responsive movement and season effects remain untested.

## Real executable synthetic tests

The generator creates two reproducible datasets; neither contains an actual recorded dog.

| Synthetic condition | Visits | Events | T2 result | T3 result |
|---|---:|---:|---|---|
| Complete format | 4 | 24 | Data elements available; external design review still required | Conditional data-quality review only |
| Degraded quality | 4 | 24 | Unresolved data gap | Not ready for detection model |

The degraded case intentionally lacks observer independence, contains a low-confidence double match and lacks original-recruitment corroboration. Neither scenario estimates mechanism prevalence, g(0), dog abundance or a change in human rabies outcomes.

The pilot format flags require repeated survey rounds, at least four visits, at least four paired detections and at most ten percent uncertain pairs. **These thresholds are diagnostic heuristics, not scientifically calibrated power or fitness cutoffs.** Every report has explicit NOT-IDENTIFIED/NOT-APPROVED status even if format checks succeed.

## Run the tools

Generate synthetic examples:

    cite-refinery-field-audit --examples /tmp/field-demo

Validate an explicitly privacy-filtered field file:

    cite-refinery-field-audit --input /tmp/field-demo/synthetic_observations.json --out /tmp/field-summary.json

Bind the critical review and generate a candidate repaired-protocol report:

    cite-refinery-field-repair --original-plan research_materials/runtime_trials/discrimination_20261020/protocol_candidate.json --critic-review research_materials/runtime_trials/discrimination_20261020/critic_review.json --observations /tmp/field-demo/synthetic_observations.json --out /tmp/repair-status.json

The last command does not change the original critical review; it leaves approved_for_field_deployment false and causal_identification not_identified.

See source code under src/cite_refinery/field_observation_*, test_field_observation_* and research_materials/runtime_trials/field_observations_20261020. The output summaries preserve data digests but do not copy animal-level source records.

## Next evidence gate

A qualified ecologist/statistician must review the repeated-sampling and double-observer protocol, photo-ID matching, ethics, welfare, consent and privacy implications. A field pilot then needs to measure actual detection behavior, including whether individuals respond to surveyors, before committing to an inference model. Original Anuradhapura operational data and geographically matched human health outcomes remain unavailable in this project.

Nothing here constitutes a collected field study, authorization to approach households, empirical causal identification, a validated model, a merge or deployment.
