# Nocturnal feedback contract v1

Cite-Refinery now has a formal empirical return path after a validated intervention.

```text
Nocturnal baseline observations
  -> Cite literature discovery/grounding
  -> explicit requirements
  -> Refinery supply / implementation
  -> successful run + passed/supported experiment
  -> feedback-request
  -> Nocturnal follow-up collection
  -> feedback-ingest
  -> new post-intervention ProblemObservation rows
```

## Creating a request

A request can only be created from an experiment whose verdict is `passed` or `supported`. If the experiment references executable runs, at least one linked run must have succeeded.

```bash
cite-refinery feedback-request \
  --workspace .cite-refinery \
  rproject:... rexp:... \
  --window-start 2026-10-01T00:00:00Z \
  --window-end 2026-12-31T23:59:59Z
```

The packet records the project, experiment, run/capability/implementation IDs, originating empirical observations, matter/event scope, observation window, and requested signal families.

## Ingesting Nocturnal follow-up

```bash
cite-refinery feedback-ingest \
  --workspace .cite-refinery \
  rproject:... \
  --input /tmp/nocturnal-feedback-result.json
```

The result must exactly match the stored request's `request_id`, `project_id`, `experiment_id`, and `run_ids`. Every accepted observation is written back into the empirical map with:

- `source_system=nocturnal-feedback`;
- `frame=post_intervention`;
- exact request/result/experiment/run lineage;
- descriptive relation and outcome direction;
- `causal_status=not_established`.

Repeated ingestion of the same packet is observation-idempotent and produces the same deterministic result ID.

## Causal boundary

This contract closes provenance, not causal identification. A later event can be temporally and descriptively related to an intervention without being caused by it. V1 therefore rejects result packets that claim a causal status stronger than `not_established`.

The end-to-end scorecard now distinguishes:

- validated intervention with no follow-up request;
- request pending;
- result ingested;
- linked post-intervention observations present.

No composite score is used, so a successful intervention run cannot hide missing real-world follow-up.
