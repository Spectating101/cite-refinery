# Problem Commons Case Workspace V0.1

The Case Workspace is the first end-to-end orchestration view across the Problem Commons V0.1 planes.

It is intentionally **not another source of truth**.

The authoritative objects remain:

```text
Problem Commons    → Problem Packet / subproblems / attempts / outcomes
problem-stages     → what kind of work each contribution is
problem-governance → whether an intervention can cross Design → Test → Deploy
problem-pilot      → observed curation / solver / adoption / reuse measurements
```

The Case Workspace joins those objects by stable `problem_id` and `subproblem_id` and answers a different operational question:

> Where is this real problem in the full problem-solving loop, what is actually established, what is blocked, and what is the next bounded action?

## Why it exists

Before this layer, each registry could be internally correct while an operator still had to mentally reconstruct the complete case.

That creates several risks:

- a staged contribution points to a deleted/nonexistent subproblem;
- a Deploy stage exists with no governance envelope;
- governance and stage classifications contradict each other;
- an accepted attempt is mistaken for a tested intervention;
- a passed intervention test is mistaken for authority;
- deployment activity is mistaken for an observed outcome;
- successful work is never checked for reuse in a later problem.

The Case Workspace treats those as cross-plane consistency/readiness questions.

## Case milestone model

A case snapshot currently exposes:

1. problem formulated;
2. problem public;
3. work decomposed;
4. work staged;
5. attempt started;
6. attempt accepted;
7. intervention governed;
8. test recorded;
9. authority recorded;
10. deployed;
11. outcome observed;
12. reuse observed.

These are evidence states, not a mandatory linear waterfall. Research-only cases may legitimately never require an Intervention Envelope or deployment.

## Cross-plane validation

`ProblemCaseWorkspace.validate(problem_id)` checks:

- stage profiles reference real subproblems;
- governance envelopes reference real subproblems;
- stage↔governance alignment where both exist;
- attempts reference real subproblems;
- Deploy-stage work has a governance envelope;
- Test-stage work without governance is surfaced as a warning;
- deployed/monitoring/resolved Problem Packets retain an explicit authorized authority decision.

The workspace does not mutate any source registry to make validation pass.

## Next-action derivation

The snapshot derives bounded next actions from current state.

Examples:

```text
candidate + missing reviewed evidence
→ complete evidence-bounded curation

verified + decomposition
→ open only after steward review

open + unstaged work
→ classify remaining contribution paths

open + no attempts
→ match/recruit an independent solver

submitted attempt
→ independent review

accepted attempt
→ decide whether a bounded pilot is justified

governance test-ready
→ run a bounded test and record a receipt

deployed + no outcome
→ monitor the external condition

outcome + no reuse evidence
→ identify generalizable assets and test cross-problem reuse
```

This is advisory orchestration. It never grants authority and never automatically advances a Problem Packet.

## Case Bundle

`problem-case export` writes a `problem-case/v0.1` bundle containing:

- complete operator Problem Packet;
- relevant stage profiles;
- relevant governance envelopes;
- case-filtered pilot records;
- cross-plane validation;
- milestone snapshot;
- next actions / blockers / warnings.

The bundle is intended for operator/reviewer transfer, audits, pilot review, or reproducible case discussion.

It is **not a public export**. The Problem Packet may contain restricted evidence and governance material. Public sharing should continue to use the Problem Commons redacted public snapshot/catalog mechanism.

Schema: `schemas/problem-case.v0.1.schema.json`.

## CLI

```bash
problem-case snapshot problem:...
problem-case validate problem:...
problem-case next problem:...
problem-case export problem:... --out case.json
problem-case list
```

Custom registry locations can be supplied with:

```bash
problem-case \
  --commons state/problem-commons.json \
  --stages state/problem-stages.json \
  --governance state/problem-governance.json \
  --pilot state/problem-pilot.json \
  snapshot problem:...
```

## Architectural consequence

The full V0.1 stack now separates five concerns cleanly:

```text
Reality / sources
      ↓
Problem Packet      what is unresolved?
      ↓
Stage Profile       what kind of work is this?
      ↓
Governance Envelope can a concrete intervention cross into action?
      ↓
Pilot Ledger        what happened when humans actually used the system?
      ↓
Case Workspace      what is the whole case state and next legitimate move?
```

The Case Workspace is intentionally derived. If it ever starts inventing evidence, capability, authority, or outcome state instead of reading source registries, the architecture has regressed.
