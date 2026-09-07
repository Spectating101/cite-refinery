# Problem-solving stages V0.1

Problem Commons treats the **real problem** as the primary object. This extension classifies contribution paths by the kind of uncertainty/work they address so that research, professional practice, engineering, public authority, and reusable capability can coexist without pretending they are the same activity or ranking one discipline above another.

This is deliberately a **versioned extension** (`problem-stages/v0.1`) rather than a frozen field in the canonical Problem Packet. We should first test whether it improves routing, comprehension, decomposition, and reuse.

## The nine stages

1. **Observe** — What is happening? Preserve events, recurrence, corrections, and live state without prematurely diagnosing the mechanism.
2. **Measure** — How large, frequent, severe, or distributed is it? Freeze definitions, samples, denominators, and baselines.
3. **Explain** — What mechanism best accounts for the condition? Compare competing explanations and preserve unresolved alternatives.
4. **Design** — What research design, intervention, workflow, or constraint set could change or test the situation?
5. **Build** — Can the design be implemented as a working method, dataset, tool, process, or software capability?
6. **Test** — Does the implementation or claim survive empirical, reproducibility, safety, usability, or shadow-pilot evaluation?
7. **Deploy** — Can a competent real-world authority authorize and execute a bounded consequential use?
8. **Monitor** — What happened after deployment? Did the condition improve, recur, shift, or create new harms?
9. **Generalize** — What evidence, method, dataset, protocol, or capability is portable enough to help later problems?

These stages are **not mandatory waterfall steps**. A problem can loop backward, skip irrelevant stages, split into parallel stages, or reopen after monitoring. `Explain → Measure` is common when an attempted explanation exposes bad measurement. `Monitor → Explain` is common when an intervention behaves differently than expected.

## Why this matters for academia versus trade/professional practice

The distinction is not “academics are smarter.” The relevant distinction is the kind of uncertainty being handled.

- **Known practice**: a known problem and established method can be executed competently. This is where professional/trade capability is often strongest.
- **Adaptive practice**: an established or adaptable method must be fitted to a new context under supervision or explicit constraints.
- **Empirical inquiry**: the condition, mechanism, effect, or validation state is uncertain enough that trustworthy new evidence must be produced.
- **Research frontier**: the method itself or the relevant knowledge is novel/frontier and cannot be treated as routine practice.

Professional authority is a **separate axis**. A licensed practitioner can be required for a low-uncertainty task; a PhD does not inherit that authority. Conversely, a high-uncertainty empirical question can require research skill without granting any right to deploy the resulting intervention.

The problem therefore decides what competence matters.

## Default routing across the existing stack

The extension provides default routing suggestions, not authority transfer:

| Stage | Default systems | Why |
|---|---|---|
| Observe | Nocturnal, Problem Commons | longitudinal reality, recurrence, corrections, candidate state |
| Measure | Cite, Refinery | empirical definitions/evidence plus data/method capability |
| Explain | Cite | competing explanations, prior art, causal/empirical support |
| Design | Public-Good, Cite, Refinery | bottleneck/constraint reasoning, evidence, existing capability |
| Build | Refinery | implementation, execution, artifact/capability preservation |
| Test | Cite, Refinery, Public-Good | empirical validation, reproducibility, safety/decision constraints |
| Deploy | Public-Good, external authority | bounded intervention reasoning plus explicit competent authorization |
| Monitor | Nocturnal, Cite | observed outcomes, recurrence, attribution/evidence updates |
| Generalize | Refinery, Cite | promote reusable capability and preserve validated evidence/limits |

Nocturnal, Cite, Refinery, and Public-Good remain authoritative only for their own domains. A routing suggestion never grants deployment authority or silently mutates a public Problem Packet.

## Stage profile

Each staged contribution records:

- `problem_id`
- `subproblem_id`
- `stage`
- `question`
- `epistemic_type`
- `uncertainty`: low / medium / high / frontier
- `method_maturity`: established / adaptable / experimental / novel
- `expected_outputs`
- `evaluation_method`
- `authority_level`: none / review / qualified / institutional
- `authority_requirement`
- `required_credentials`
- `system_routes`
- `reuse_target`
- notes

Derived fields include:

- **work mode**: known-practice / adaptive-practice / empirical-inquiry / research-frontier
- whether qualified/professional authority is required
- a human-readable route plan for the portfolio systems

## Hard validation rules

V0.1 rejects or warns on several category errors:

- **Deploy** requires explicit institutional authority and an external-authority route.
- Qualified/institutional work must state its authority requirement.
- Every staged contribution must state a question, epistemic type, output, and evaluation method.
- **Generalize** must route to Refinery; lack of a reuse target is warned because the compounding opportunity would be lost.
- **Monitor** without Nocturnal is warned.
- high/frontier **Explain** work without Cite is warned.
- **Build** without Refinery is warned.

These rules are intentionally conservative. They can be revised after pilot evidence.

## Worked example: shelter food access

The same real problem supports different kinds of contributors without pretending they have interchangeable roles:

1. **Measure** — researcher/student freezes interruption frequency and cause taxonomy.
2. **Observe** — data/operations contributor verifies which donor capacity is actually live rather than stale inventory.
3. **Design** — veterinarian/domain expert defines safe compatibility constraints.
4. **Build** — engineer implements constraint-aware routing/matching.
5. **Test** — operator/research team evaluates shadow recommendations against frozen cases.
6. **Deploy** — participating shelters explicitly authorize any bounded field use.
7. **Monitor** — Nocturnal/outcome process tracks recurrence and safety.
8. **Generalize** — validated measurement, compatibility, and routing assets become reusable Refinery capabilities with limitations preserved.

Academic research is especially valuable where the system needs to **measure, explain, or test something that is not already known**. Professional/trade expertise is especially valuable where the method is established but competent execution, safety knowledge, or legal authority matters. Engineering turns validated designs into working capability. None is globally superior; the stages expose the division of labor.

## Worked example: Taoyuan mobility candidate

The current real-source Taoyuan candidate is intentionally blocked from becoming a public infrastructure prescription.

- **Measure**: validate accident/infrastructure data semantics, representative exposure, and joinability.
- **Explain**: only after measurement survives review, compare geometry, signal timing, visibility, exposure, and behavior mechanisms.
- **Design/Test**: intervention candidates come later and require transport-domain review.
- **Deploy**: any real road/signal change requires competent transport authority; Problem Commons cannot confer this authority.

This is exactly the kind of situation where academic empirical reasoning matters: public data alone does not establish the mechanism.

## Worked example: replication problem

- **Design**: freeze estimand, sample, exclusions, and robustness family before outcome inspection.
- **Build**: create a provenance-preserving harmonized panel and executable pipeline.
- **Test**: independent clean-environment reproduction.
- **Generalize**: promote the validated replication runner, transformation patterns, and known limitations so later replications begin further ahead.

This demonstrates the Cite × Refinery multiplication effect: research questions produce methods and executable assets; validated assets become reusable capability; later research consumes those capabilities instead of starting from zero.

## What we should measure in the pilot

The stage model earns a place in the canonical Problem Packet only if it improves real behavior. Compare staged versus unstaged packets on:

1. solver comprehension of what work is actually needed;
2. ability to identify an appropriate contribution without curator explanation;
3. lower rate of category errors (prototype mistaken for evidence, research result mistaken for authorization, professional authority mistaken for academic rank);
4. better matching between contributor capability and task;
5. clearer handoffs between Cite, Refinery, Nocturnal, Public-Good, and external authority;
6. higher reuse capture at Generalize;
7. acceptable classification cost for curators.

### Kill/pivot condition

If independent curators cannot classify contribution paths consistently, solvers do not understand the stage semantics, or the model adds ceremony without improving matching/handoffs/reuse, keep stages as internal analytics or remove them rather than forcing them into every Problem Packet.

## CLI

The extension is managed independently:

```bash
problem-stages add problem:... psub:... \
  --stage explain \
  --question "Which mechanism drives the recurrence?" \
  --epistemic-type mechanism-discrimination \
  --uncertainty frontier \
  --method-maturity experimental \
  --output "mechanism comparison" \
  --evaluation "pre-specified competing-hypothesis tests"

problem-stages route problem:... psub:...
problem-stages coverage problem:...
problem-stages validate
```

Example profiles are in `examples/problem_stage_profiles.json`.
