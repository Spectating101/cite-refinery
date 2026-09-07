# Problem Commons V0.1 case operations

This layer turns the existing V0.1 architecture into a repeatable pilot workflow.

It does **not** add a new source of problem, evidence, capability, governance, authority, or outcome truth. The existing stores remain authoritative:

- Problem Commons: living Problem Packet + attempts + authority/outcome relationships;
- Stage registry: experimental Observe → Generalize contribution semantics;
- Governance registry: Public-Good intervention gates, tests, and external-authority handoffs;
- Pilot ledger: measured curation/solver/adoption/reuse evidence;
- Operations ledger: append-only receipts proving which explicit operator action mutated the first two writable pilot stores.

The Case Workspace remains read-only.

## Operating loop

```text
source signal
  ↓
non-public candidate
  ↓
curation + production record
  ↓
owner review pack ──→ completed response ──┐
  ↓                                       │
domain review pack → completed response ──┤
  ↓                                       │
problem-ops assess ◀───────────────────────┘
  ↓
explicit curator promotion (if eligible)
  ↓
verified / open Problem Packet
  ↓
solver review pack
  ↓
solver comprehension + conversion measurement
  ↓
real attempt / test / governance / authority / outcome
  ↓
reuse measurement on a later problem
```

A score never changes lifecycle by itself. `problem-ops promote` is an explicit actor-attributed command and still uses the canonical Problem Packet transition rules.

## Commands

### 1. Record the cost of producing a candidate

```bash
problem-ops production-start problem:... \
  --actor curator-id \
  --curator-minutes 90 \
  --source-count 6 \
  --correction-count 2 \
  --reframing-count 1
```

This writes a `ProductionRecord` to the Pilot Ledger and an operation receipt containing hashes of resulting Problem/Pilot state.

### 2. Generate minimum-necessary review packs

Use the read-only Case CLI:

```bash
problem-case review-pack problem:... --audience owner --out /tmp/owner.json
problem-case review-pack problem:... --audience reviewer --out /tmp/reviewer.json
problem-case review-pack problem:... --audience solver --out /tmp/solver.json
```

The packs start from the redacted public projection; restricted evidence locators/provenance and internal governance evidence/reviewer identifiers are not exported.

### 3. Ingest completed reviews

The external participant/observer fills `response.item_scores` with `0` or `1` for every rubric item and records material disagreements/errors.

```bash
problem-ops review-ingest /tmp/owner.json --participant owner-001
problem-ops review-ingest /tmp/reviewer.json --participant reviewer-001
```

For solver observation, the response can additionally record:

- selected subproblem;
- minutes to a useful contribution edge;
- usefulness rating;
- serious-attempt conversion;
- abandonment and reason;
- observer notes;
- experimental arm.

### 4. Assess but do not auto-promote

```bash
problem-ops assess problem:...
problem-ops queue
```

`pilot/operations-policy.v0.1.json` currently uses 0.8 owner agreement, reviewer quality, and solver comprehension as **experimental pilot rules only**. They are not validated scales and are not canonical publication requirements.

### 5. Explicit curator promotion

```bash
problem-ops promote problem:... verified \
  --actor curator-id \
  --reason "Owner and independent domain review passed the pilot gates"

problem-ops promote problem:... open \
  --actor curator-id \
  --reason "Verified packet has a bounded contribution decomposition"
```

Promotion never creates professional or institutional authority. Consequential deployment still requires the governance and Problem Packet authority receipts already defined elsewhere.

### 6. Inspect operation receipts

```bash
problem-ops receipts problem:...
```

Receipts include action, actor, summary, inputs/outputs, timestamp, and SHA-256 hashes of the resulting Problem Packet and Pilot Ledger state. They are an audit trail rather than domain truth.

## Pilot policy vs canonical invariants

The following are canonical or architectural invariants:

- source signal != publishable problem;
- owner/reviewer feedback != automatic publication;
- research expertise != professional authority;
- successful build != successful test;
- successful test != external authority;
- deployment/activity != real-world outcome;
- reusable-looking asset != positive net reuse.

The following are experimental pilot policy and may change after evidence:

- 0.8 owner agreement threshold;
- 0.8 domain reviewer threshold;
- 0.8 mean solver comprehension threshold;
- whether external owner review is required for every type of verification.

Do not encode pilot thresholds into the canonical Problem Packet schema until external use justifies them.

## Current operational objective

The next evidence gate is to run 3–5 real cases through this loop and measure:

1. curator minutes and correction/reframing burden;
2. owner agreement with the formulated problem;
3. independent domain-review quality;
4. solver comprehension and time-to-useful-edge;
5. serious-attempt conversion and abandonment reasons;
6. attempt → test → authority → deployment → outcome survival;
7. positive or negative net reuse on later problems.

Engineering changes after this point should be driven primarily by failures observed in those real cases.
