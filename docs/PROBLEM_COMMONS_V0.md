# Problem Commons V0.1 — system specification

## Purpose

Problem Commons treats the **real unresolved problem** as the primary public object.

It is not a course platform, generic challenge marketplace, research assistant, issue tracker, or autonomous decision system. It is infrastructure for converting messy real-world conditions into living, evidence-backed, attemptable problem objects; connecting those objects to people who can contribute; and preserving what was learned when attempts succeed, fail, deploy, or recur.

The intended loop is:

```text
reality
  ↓
problem signal / observation
  ↓
curation + diagnosis
  ↓
knowledge frontier + capability frontier
  ↓
verified living Problem Packet
  ↓
decomposed contribution paths
  ↓
private attempts / experiments
  ↓
review + bounded pilot + competent authority
  ↓
observed outcome
  ↓
revision / resolution / reopening
  ↓
reusable evidence + capabilities
```

## Engine ownership

Problem Commons is an umbrella coordination surface, not a replacement for domain engines.

| System | Authoritative ownership |
| --- | --- |
| Nocturnal | observations, matters, chronology, corrections, disputes, later outcomes |
| Public-Good Control Plane | bottleneck diagnosis, constraints, intervention framing, authority boundary |
| Cite-Agent | literature, empirical evidence, scholarly claims, research gaps, datasets |
| Refinery / Commons | capabilities, implementations, runs, experiments, reusable promotion |
| Citation Engine | provenance, basis edges, uncertainty, gates, authority transitions, receipts |
| Problem Commons | living problem identity, public formulation, decomposition, attempts, curation state, outcome references |

Cross-system state is referenced, not duplicated as a new universal database.

## Primary invariants

1. **Observation is not a publishable problem.**
2. **A problem is not a proposed solution.** Diagnosis remains revisable and competing mechanisms are preserved.
3. **Verification is a reviewed transition.** A model/provider cannot auto-publish by generating text.
4. **Opening for contribution requires decomposition.** Outsiders should know where useful work can attach.
5. **Attempt is not solution.** A project, paper, prototype, or model is only an attempt until reviewed/validated.
6. **Experiment success is not impact.** Real-world outcome is a separate object.
7. **Consequential action requires competent authority.** V0.1 blocks `deployed` without an explicit authority decision.
8. **Restricted evidence stays restricted.** Public snapshots redact private/restricted locators and data URIs.
9. **Resolution is reversible.** Later recurrence can reopen a problem without erasing previous history.
10. **Negative/inconclusive results remain useful.** The commons should accumulate failures and limitations, not only winners.
11. **Credentials are local gates, not global access rules.** A contribution path can require a specific credential when safety/domain authority requires it; otherwise matching is capability/interest based.
12. **Sponsor money cannot buy epistemic status.** Funding provenance is separate from verification, review, and outcome state.

## Lifecycle

```text
candidate
   ↓
researching
   ↓
verified
   ↓
open
   ↓
partially_resolved / piloting
   ↓
deployed
   ↓
monitoring
   ↓
resolved
```

Side transitions support `reframed`, `retired`, and `invalidated`. A resolved problem can return to `open` or `reframed` if later evidence changes the state.

### Public states

Anonymous/public surfaces may expose `verified`, `open`, `partially_resolved`, `piloting`, `deployed`, `monitoring`, and `resolved`. Candidate, researching, reframed, retired, and invalidated state stays curator-side by default.

## Publishability gate

`ProblemPacket.publishability()` returns explicit checks, blockers, warnings, and an unweighted completeness fraction.

Required for verification:

- title;
- observed condition;
- unresolved core;
- steward;
- authority boundary;
- evidence;
- at least one reviewed/corroborated/verified evidence record;
- at least one success criterion.

Required to become `open`:

- all verification requirements;
- at least one explicit contribution subproblem.

Warnings intentionally remain non-blocking for fields such as affected actors, constraints, knowledge frontier, capability frontier, problem owner, implementation pathway, or falsification detail. The point is to expose incompleteness rather than silently pretend certainty.

## Problem Packet

The packet carries five categories of state:

### Reality and scope
- title / summary / observed condition;
- geography and time scope;
- affected actors and beneficiaries;
- evidence references;
- disputes and uncertainty.

### Problem formulation
- unresolved core;
- working diagnosis / competing mechanisms;
- prior attempts;
- constraints;
- authority boundary;
- problem owner / steward / sponsor.

### Frontier
- knowledge frontier;
- capability frontier and structured capability needs;
- data resources and access;
- success criteria, falsification and guardrails;
- implementation pathway.

### Participation
- decomposed subproblems;
- skills, interests, effort and expected outputs;
- optional explicit credential gates;
- attempts, reviews and contribution credit.

### Consequence and learning
- authority decisions / receipts;
- outcomes and attribution status;
- revisions;
- external system references;
- rights, funding and contribution-license notes.

## Contribution matching

V0.1 provides a deterministic, inspectable matcher instead of opaque ranking. A match gains points from skill overlap, interest overlap, and an optional preferred contribution kind. Missing required credentials apply a visible negative gate. The returned object explains matched tags and any missing credential.

This is deliberately simple. Production semantic matching can be layered on later, but the deterministic baseline gives us an auditable control and avoids turning participation into an unexplained reputation score.

## Attempt lifecycle

```text
draft → active → submitted → accepted → completed
                  ↘ rejected
                  ↘ revise → active
```

Attempts must attach to at least one explicit subproblem. An accepted/completed attempt is required before a problem can enter `piloting`.

This protects the distinction:

```text
interesting idea ≠ reviewed attempt ≠ pilot ≠ deployment ≠ outcome
```

## Authority and deployment

`ProblemPacket.authorize()` records actor, scope, decision (`authorized`, `conditional`, `denied`), rationale, and an optional receipt reference. A packet cannot transition to `deployed` without at least one explicit `authorized` authority decision.

This is a minimum V0.1 invariant, not a complete institutional authorization model. Production should defer to domain/statutory authority and Citation Engine authority receipts.

## Outcome semantics

Outcomes record a summary, observed change, evidence references, disposition, and attribution status. Default attribution is `not_established`: a changed condition must not silently become a causal claim that an attempt produced the change.

Recommended attribution labels are `not_established`, `suggestive_not_causal`, `supported`, `contradicted`, and `mixed`.

## Public redaction

`ProblemPacket.public_snapshot()` exports a minimum-necessary public representation.

Restricted/private evidence keeps source label, summary, confidence, and rights metadata while removing locator and detailed provenance. Restricted/private data resources keep public descriptive metadata while removing URI. Restricted external-system references are excluded. Steward-review internals are excluded.

A public Problem Packet is therefore not equivalent to publishing every underlying source or dataset.

## External-engine integration

`problem_integrations.ContextUpdate` is a provider-neutral bridge for observation updates from Nocturnal, knowledge updates from Cite, capability updates from Refinery, diagnosis/constraint updates from Public-Good, outcome updates, and Citation Engine references.

External-engine output does **not** mutate a packet automatically. `apply_update()` requires an explicit `accepted_by` reviewer and preserves the source reference.

```text
provider proposes context
      ↓
human/curator accepts or rejects projection
      ↓
Problem Packet changes
```

## Persistence and exchange

`ProblemCommons` supports JSON save/load with schema marker `problem-commons/v0.1`. Writes use a temporary file followed by replace. The public catalog can be exported as redacted JSON. A JSON Schema under `schemas/` defines the stable exchange envelope for adapters and independent clients.

V0.1 JSON persistence is suitable for prototype/single-writer use only. Multi-user hosted deployment should move to a transactional database with concurrency control, role-scoped APIs, migrations, backups, and append-only audit records.

## Roles

### Anonymous public
Browse verified/public packets, inspect public evidence/context, inspect contribution paths and outcomes. No direct publication or consequential execution.

### Registered contributor
Create private attempts, attach artifacts/evidence/experiments, request review, and control sharing.

### Verified partner / problem owner
Provide restricted evidence/data, maintain implementation context, and participate in pilot review.

### Steward / reviewer
Curate candidate → verified transitions, reframe/split/merge/retire problems, review attempts, manage public redaction, and record disputes/corrections.

### Operator / competent authority
Authorize or deny bounded consequential action and remain outside model authority.

## V0.1 browser

The browser prototype demonstrates a searchable/filterable public catalog; problem-first detail; overview, contribute, evidence, attempts/outcomes and steward views; deterministic contribution matching; local private draft attempts; local candidate intake; evidence/data visibility cues; and lifecycle/outcome separation.

The bundled packets are illustrative and must not be interpreted as verified current public claims.

## What V0.1 deliberately does not build

- unrestricted open publication;
- arbitrary public code execution;
- autonomous intervention;
- universal person/organization reputation scoring;
- payment/crypto incentive system;
- credential marketplace;
- full LMS/course management;
- giant cross-domain ontology;
- automated causal conclusions;
- automated statutory/eligibility decisions;
- public release of restricted source data.

## Empirical program

The next phase should test the Problem Commons rather than add generic platform features.

### Problem-production test

Take 10–20 messy real situations and measure curator time to first packet, corrections after independent review, reframings, evidence/source completeness, problem-owner agreement, and independent solver comprehension.

### Solver test

For open packets measure serious-attempt rate, time to first useful contribution, whether contributors identify appropriate subproblems without curator handholding, abandonment reasons, and match quality against simple browse/control.

### Adoption test

For partner-owned problems measure attempts accepted for pilot, pilots actually authorized, prototypes reaching real operation, maintenance owner identified, observed outcomes, and guardrail violations.

### Compounding test

Compare later problems with and without prior Commons assets: evidence reused, capability reused, problem templates reused, engineering/research time, failed duplication avoided, and adaptation/maintenance cost.

The key hypothesis is not merely that reuse occurs; it is that **net reuse benefit exceeds search, adaptation, integration, and maintenance cost**.

## Kill / pivot signals

The concept should be challenged if, after a bounded real pilot:

1. high-quality Problem Packets remain too expensive to curate for the value they create;
2. independent contributors still require extensive private explanation to understand useful work;
3. problem owners consistently refuse to expose enough evidence/context for outsiders to help;
4. serious attempts rarely progress beyond prototype despite a real owner and authority pathway;
5. prior capabilities/evidence do not produce net savings on later problems;
6. public curation generates unacceptable privacy, safety, liability, or manipulation burden;
7. existing challenge/project tools plus light process changes deliver the same value substantially more cheaply.

## Current claim

V0.1 proves only that the proposed object model, governance gates, public/private boundary, contribution decomposition, attempt review, authority gating, outcome separation, and reuse references can coexist in one coherent prototype.

It does **not** prove demand, educational superiority, problem-curation economics, real-world causal impact, compounding, institutional adoption, or uniqueness. Those are empirical questions for the next pilots.
