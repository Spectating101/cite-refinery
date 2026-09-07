# Problem Commons V0.1 — falsifiable pilot playbook

## Objective

The first pilot is not a growth launch. It tests whether a living Problem Packet improves the path from messy reality to useful external work and whether later problems gain net benefit from earlier work.

The pilot must be able to produce a negative result.

## Questions

1. Can a curator turn messy source material into a reviewable packet at a sustainable labor cost?
2. Does a problem owner agree that the packet represents the real condition, uncertainty, constraints and implementation boundary?
3. Can an independent solver identify a useful contribution without a private briefing from the curator?
4. Do serious attempts survive review and reach a real owner/shadow pilot?
5. Can a reviewed attempt cross the authority boundary into a bounded deployment without confusing prototype success with impact?
6. Does prior Commons work save net time on a later problem after search, adaptation and maintenance cost?

## Pilot population

Start small and heterogeneous rather than broad:

- 10–15 candidate situations across at least four domains;
- 5–10 packets that survive curation;
- at least two externally supplied/owned candidates;
- 10–20 independent solver sessions if practical;
- 2–3 real problem owners/partners;
- at least one attempt selected for a non-consequential shadow pilot;
- at least five explicit cross-problem reuse opportunities before claiming compounding.

These are practical pilot sizes, not statistical power claims.

## Stage 1 — problem production

For each candidate:

1. freeze the raw source bundle;
2. record start time and source count;
3. create the first Problem Packet without prescribing a solution;
4. run prior-art/evidence review;
5. run capability/reuse review;
6. ask a domain reviewer for corrections;
7. ask the problem owner, where available, whether the packet represents the actual problem;
8. record every material correction/reframing;
9. mark publishable, blocked, retired or invalidated.

Record with `problem-pilot production-add`:

- curator minutes;
- source count;
- correction count;
- reframing count;
- owner agreement on a 0–1 rubric;
- independent reviewer score on a 0–1 rubric;
- publishable status;
- blocker codes.

Suggested blocker vocabulary: `evidence_missing`, `owner_missing`, `authority_missing`, `already_solved`, `unsafe_to_publish`, `data_unavailable`, `scope_unbounded`, `success_unmeasurable`, `duplicate`, `other`.

## Stage 2 — solver comprehension test

The solver must not receive a verbal explanation of the problem before the timed task.

Ask the solver to:

1. explain the observed condition in their own words;
2. distinguish what is known from what remains uncertain;
3. identify one useful contribution they could make;
4. state what output they would produce;
5. identify one important constraint or guardrail;
6. decide whether they would start a serious attempt.

Use a simple 0–1 comprehension rubric decided before scoring. Record coaching minutes separately: a packet that only works after a curator explains it has not solved the coordination problem.

### Control comparison

When possible, compare the full Problem Packet against an ordinary short challenge brief containing title, background, goal and deadline/scope but no structured frontier/history/capability context.

For small samples, use two matched problems and counterbalance order across participants. Do not show the same problem first as a full packet and later as a brief because knowledge carries over.

Record:

- arm (`problem_packet` or `brief_control`);
- comprehension score;
- minutes to identify a useful edge;
- coaching minutes;
- selected contribution;
- serious-attempt decision;
- abandonment reason;
- usefulness rating.

## Stage 3 — attempt and review conversion

A click or repository fork does not count as a serious attempt.

A serious attempt must have:

- an explicit Problem ID and subproblem ID;
- contributor/team identity within the private workspace;
- a proposed method/scope;
- an expected output;
- at least one material artifact, analysis, experiment or field observation before submission.

Track:

`draft → active → submitted → accepted/revise/rejected → completed`

Record why attempts stop. Common reasons should be coded rather than hidden: insufficient data, unclear owner, excessive integration work, missing expertise, no implementation authority, duplicate solution, unsafe design, time/interest loss, or other.

## Stage 4 — adoption pathway

For every accepted attempt, explicitly test the post-prototype gap:

1. Is there a real problem owner?
2. Is an implementation/maintenance owner named?
3. Can the attempt be evaluated non-consequentially first?
4. Is the relevant competent authority identified?
5. Has an authority decision been recorded?
6. Can the pilot be reversed/stopped?
7. Are outcome measures and guardrails frozen before deployment?
8. Did the deployment actually happen?
9. Was a real-world outcome observed?

Use `problem-pilot adoption-add` to preserve these transitions.

A technically successful prototype that never receives owner/authority support is evidence about the problem-solving pipeline, not a hidden success.

## Stage 5 — compounding test

Do not measure reuse as “asset referenced.” Measure the counterfactual cost of doing the work again.

For every plausible reuse event record:

- source Problem ID;
- target Problem ID;
- asset type and stable reference;
- search/discovery time;
- adaptation/integration time;
- estimated rebuild-from-scratch time, recorded before or justified immediately after adaptation;
- whether reuse actually succeeded.

The ledger computes:

`net_minutes_saved = rebuild_estimate - search_minutes - adaptation_minutes`

Failed reuse counts search + adaptation as a negative cost.

The compounding hypothesis is supported only if net benefit remains positive across repeated problems; a growing registry with negative search/adaptation economics is not compounding.

## Provisional decision rules

These are **pilot management rules, not research findings or validated thresholds**. Revise them before observing results if the domain requires different economics.

### Curation

After at least 10 candidate records, narrow/pivot the formulation model if high-quality packets regularly require more than roughly one working day of expert curation **and** owner/reviewer agreement remains weak. High curation cost may still be justified for high-value institutional problems; measure value rather than assuming a universal threshold.

### Solver comprehension

After at least 10 solver sessions, redesign the packet/decomposition if fewer than roughly one-third can identify a defensible contribution with little/no curator coaching. The key comparison is also relative: a full packet should outperform the ordinary-brief control on comprehension, useful-edge discovery, coaching burden or serious-attempt conversion.

### Problem supply

Treat problem supply as a critical risk if repeated outreach to at least five plausible owners produces fewer than two willing to share enough public/restricted context to create a realistic packet. Diagnose whether confidentiality, reputation, data rights, procurement, or lack of implementation authority is blocking supply.

### Adoption

If several accepted attempts exist but none can enter even a non-consequential shadow pilot with a named owner, stop optimizing solver acquisition and work on ownership/authority/implementation integration instead.

### Safety

A material guardrail violation is a stop-and-review event. Do not compensate for it with higher participation or impact metrics.

### Compounding

After at least five genuine reuse opportunities, treat cumulative net reuse time <= 0 as evidence against the current Commons/promotion/search design. Do not call a growing asset count a network effect without net benefit.

## Reporting

Run:

```bash
problem-pilot report
```

The report deliberately warns when samples are too small or adoption/reuse have not been exercised.

Keep raw pilot data private when it contains partner/contributor information. Publish aggregate methods/results and minimum-necessary evidence where rights and consent permit.

## What would justify V0.2

V0.2 should be earned by evidence such as:

- multiple problem owners accept the representation of their problem;
- independent solvers can enter useful work with materially less coaching than a plain brief;
- at least one serious attempt reaches a real shadow pilot;
- lifecycle/authority gates survive use without being bypassed;
- at least one later problem receives measurable net benefit from earlier evidence/capabilities;
- no unacceptable privacy/safety/rights failure emerges.

If those do not occur, the correct response is to narrow or redesign the system—not add marketplace, social, payment, credential or gamification features.
