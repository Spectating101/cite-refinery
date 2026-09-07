# Problem Commons ↔ Public-Good governance bridge

Problem Commons is the broader work substrate; Public-Good remains the bounded diagnosis/intervention/authority control plane.

The shared relationship is:

```text
reality / signal
  ↓
Problem Commons living Problem Packet
  ↓
Observe / Measure / Explain
  ↓
Design contribution
  ↓
reviewed Public-Good projection
  ↓
Intervention Envelope
  ↓
Test gates + receipts
  ↓
competent external authority
  ↓
real-world handoff
  ↓
outcome / monitoring
  ↓
Nocturnal + Cite + Refinery + Problem Commons
```

The envelope is deliberately an **extension**, not a replacement for the Public-Good repository. It stores only the minimum reviewed projection needed for a living problem to know whether a proposed intervention is ready for review, test, or external deployment handoff.

## Why this exists

Problem Commons can scale problem supply and contribution volume, but volume without governance would recreate the failure mode of challenge boards: a problem quickly becomes a preferred solution, a successful prototype is treated as impact, and nobody records who may actually act.

The intervention envelope prevents those collapses.

## Intervention Envelope

An envelope attaches to `problem_id + subproblem_id` and records:

- target failing transition;
- diagnosis hypothesis;
- intervention class;
- smallest feasible change;
- expected mechanism;
- reversibility and rollback plan;
- preconditions and constraints;
- rights, safety and integrity risks;
- evidence/capability references;
- outcome metrics;
- monitoring plan;
- source Public-Good case/reference;
- explicit governance gates;
- test receipts;
- external authority handoff receipts.

It never grants authority itself.

## Gates

V0.1 defines:

- evidence;
- safety;
- integrity;
- rights;
- data access;
- reversibility;
- professional review when applicable;
- external authority.

A test is blocked when required non-authority gates are unresolved. Deployment readiness additionally requires:

1. no failed/pending required gate;
2. at least one passed test receipt without guardrail breach;
3. a named external authority actor and bounded scope;
4. an explicit authority receipt.

A `conditional` or `denied` authority decision does not become authorization.

## Important invariants

```text
problem evidence != diagnosis certainty

diagnosis hypothesis != intervention effectiveness

successful build != successful test

successful test != authority

authority != outcome

activity != public-good outcome

service/capability existence != access/live capacity

recommendation != permission to act
```

## Relationship to the staged model

The stage extension tells us **what kind of work this contribution is**:

`Observe → Measure → Explain → Design → Build → Test → Deploy → Monitor → Generalize`.

The governance extension tells us **whether a proposed real-world intervention can responsibly cross Design → Test → Deploy**.

Typical division:

- Observe / Measure / Explain: evidence generation; normally no intervention envelope yet.
- Design: create an envelope when a concrete intervention class appears.
- Build: produce a capability referenced by the envelope, but do not inherit authority.
- Test: execute only after test-readiness gates pass and record an evaluation receipt.
- Deploy: requires explicit external authority and a passed guardrail-safe test.
- Monitor: Nocturnal/outcome evidence updates the living Problem.
- Generalize: validated methods/capabilities can be promoted through Refinery.

`problem_stage_governance.py` checks that the two experimental extensions do not contradict one another. Examples:

- a qualified stage cannot pass alignment without a satisfied professional gate;
- a Test-stage contribution cannot align while test-readiness gates are unresolved;
- a Deploy-stage contribution requires both institutional stage authority and a deploy-ready envelope;
- a Build-stage capability can exist without deployment authority, but a non-review-ready envelope is flagged so the prototype is not mistaken for intervention validity.

This preserves three separate questions:

```text
Problem Packet:       what is unresolved?
Stage Profile:        what kind of work is this?
Governance Envelope:  can this intervention cross into real-world action?
```

## Public-Good repository remains authoritative for its own reasoning

The existing Public-Good Control Plane already defines the maintained shared loop:

`condition → failing transition → bottleneck → usable capability → safety/integrity/rights/authority gates → smallest intervention → authority → outcome → recurrence`.

Problem Commons should not reproduce every domain constitution, welfare rule, entitlement rule, disaster doctrine, procurement rule, or professional decision. Those stay in Public-Good/domain systems and competent institutions.

The envelope therefore includes `public_good_ref` and evidence/receipt references instead of copying the whole source case.

## Educational consequence

This bridge also makes the research/practice relationship concrete.

A student or researcher may establish a mechanism or measurement. An engineer may build the intervention capability. A professional may validate a domain-specific constraint. An institution may hold deployment authority. These are different contributions to the same problem, not a hierarchy of credentials.

The Commons can therefore connect academic inquiry to professional/trade execution while preserving the distinction between:

- producing trustworthy new knowledge under uncertainty;
- competent execution of established knowledge;
- professional/legal authority to act.

## Promotion criterion

Keep `problem-governance/v0.1` experimental until real pilot use demonstrates that it improves handoffs and prevents premature intervention without creating prohibitive curation burden.

Only then consider merging these fields into a future canonical Problem Packet version.
