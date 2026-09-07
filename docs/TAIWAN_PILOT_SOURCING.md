# Taiwan pilot sourcing — Problem Commons V0.1

Checked during V0.1 pilot preparation in September 2026.

This document identifies **candidate-supply channels and test cases**, not verified Problem Packets. Nothing here should be published as a claim that a specific intervention is needed until the normal evidence, owner, prior-art, authority, and success-measure gates are satisfied.

## Why Taiwan is a useful first environment

Taiwan already has active infrastructure for public problem solving, open-data collaboration, challenge programs, and civic technology. That is useful because V0.1 does not need to prove that challenge participation exists; it needs to test whether a **living Problem Packet** improves formulation, entry, adoption, and reuse compared with ordinary challenge/project briefs.

The first pilot should therefore borrow problem signals and controls from existing ecosystems rather than manufacture ten synthetic challenges.

## Source A — Civic Tech Taiwan wish pool

Source: https://civictech.tw/

The current Civic Tech Taiwan site includes a `公民科技專案許願池` (civic-tech project wish pool). Its intake asks for a project name, a one-line formulation of using a technology to solve a person's/group's pain point, shortcomings of existing tools, needed capabilities/people, and current progress.

### Why this is useful

This is close to the **raw supply side** of Problem Commons: people already have issues and ideas they want collaborators to work on.

It is also a useful stress test because the intake is partly solution-oriented (`use [technology] to solve [pain point]`). Problem Commons should not simply copy that formulation. The curation experiment is:

```text
wish / project idea
      ↓
remove premature solution assumptions
      ↓
verify observed condition
      ↓
identify affected actors + owner
      ↓
Cite prior-art / knowledge frontier
      ↓
Refinery capability frontier
      ↓
constraints + authority + measurable success
      ↓
living Problem Packet
```

### Pilot use

Select a small sample of public wishes only when source rights/terms permit. Preserve the original URL/reference. Compare the original wish/brief with the curated packet in blind solver-comprehension sessions.

Do **not** imply that Civic Tech Taiwan endorsed the reformulation.

## Source B — Taiwan Presidential Hackathon

Main site: https://presidential-hackathon.taiwan.gov.tw/

FAQ: https://presidential-hackathon.taiwan.gov.tw/faq

Data partners: https://presidential-hackathon.taiwan.gov.tw/DataPartner

International track: https://presidential-hackathon.taiwan.gov.tw/en/international-track/index.html

The official program explicitly connects public/private participants, government open data, cross-domain teams, mentoring, implementation support, and policy follow-through. The 2026 FAQ states that selected proposals can receive data/technical/talent support; winning proposals are tracked for implementation. The international track also gives final-stage weight to implementation and verification.

### Why this is useful

It gives V0.1 two things:

1. **Control briefs** — existing challenge/proposal formats against which to compare a full Problem Packet.
2. **Adoption precedent** — a real program that does not treat selection as the end of the problem-solving process.

### Pilot use

Use publicly available challenge/proposal materials as comparison objects where rights permit. Measure whether solvers using the full Problem Packet identify uncertainty, contribution edges, constraints, and implementation needs with less coaching than solvers using a conventional brief.

Do not treat competition winners or proposals as validated causal solutions merely because they were selected.

## Source C — application-gated agricultural imagery

Source: https://presidential-hackathon.taiwan.gov.tw/farming

The 2026 Presidential Hackathon agricultural-vehicle imagery area makes geospatial agricultural imagery available to participating teams **by application/review**, with stated uses including image recognition, agricultural-facility inventory, rural-road/environment analysis, land-use observation, disaster assessment, and rural environmental governance.

### Why this is useful

This is a concrete precedent for the V0.1 access model:

```text
public problem formulation
        +
restricted / application-gated data
        +
verified team access
```

A Problem Packet should be able to expose enough information for outsiders to understand and choose a contribution without leaking the restricted dataset itself.

### Pilot use

Use this primarily as an **interoperability/access-control test case**, not as evidence that any particular agricultural problem exists. A candidate packet can describe a hypothetical or partner-approved analysis need while keeping the data locator/access process restricted.

## Source D — Taoyuan traffic-safety / pedestrian-infrastructure data

Traffic accident geodata:
https://data.gov.tw/dataset/46364

Traffic accident hotspot data:
https://data.gov.tw/dataset/173672

Taoyuan sidewalk-management data:
https://data.gov.tw/dataset/26069

Taoyuan real-time roadway data:
https://opendata.tycg.gov.tw/datalist/7b879012-ec7f-4ea6-8af4-9e5ea1bcb39c

The official accident dataset provides A1/A2 accident records by time, area, road/intersection, and longitude/latitude for 2017–2025 (ROC 106–114). The sidewalk-management dataset includes district, road length/width, and sidewalk length/width. The city also publishes hotspot aggregates and minute-level roadway travel-speed/congestion data.

### Candidate — not a verified problem

A defensible candidate question is:

> Can public data identify Taoyuan corridors where recurrent severe-accident concentration and pedestrian-infrastructure conditions justify **further investigation**, and can subsequent observation distinguish geometry, exposure, signal timing, visibility, behavior, or another mechanism before any intervention is proposed?

This formulation intentionally does **not** claim that sidewalk width causes accidents or that a specific intersection needs redesign.

### Candidate workflow

```text
accident/hotspot data
        +
sidewalk / road context
        +
traffic/exposure proxies where usable
        ↓
identify candidate corridors
        ↓
manual / domain review
        ↓
representative observation
        ↓
competing mechanism tests
        ↓
only then: verified Problem Packet or retirement
```

This is useful for testing whether Problem Commons rejects false causal shortcuts while still turning open data into a tractable research/contribution opportunity.

## Initial sourcing mix

For the first 10–15 candidate situations, aim for:

- 3–4 public/open-data-derived signals;
- 2–3 civic-tech/challenge/wish signals;
- 2–3 externally supplied partner problems with a real owner;
- 1–2 research replication/reproducibility problems;
- at least one restricted-data problem to exercise access/redaction;
- at least one candidate that is deliberately retired or invalidated after curation.

The point is **not** to force every candidate into publication. A high-quality curation system should kill weak, duplicate, already-solved, unsafe, unmeasurable, or ownerless candidates.

## First three seeded signals

Machine-readable candidate signals are stored in `pilot/candidate_signals.tw.v0.1.json`.

They are all marked `do_not_publish: true` and should enter the registry only as `candidate`/`researching` state.

## Outreach sequence after internal curation

1. Curate 3–5 public-source candidates without contacting an owner yet.
2. Run domain review and measure corrections/reframings.
3. Approach 2–3 plausible problem owners with the packet and ask whether it represents the actual condition/constraints.
4. Recruit independent solvers only after owner/evidence boundaries are clear.
5. Use the full-packet vs ordinary-brief control defined in `PILOT_PLAYBOOK.md`.
6. Do not optimize public traffic until at least one real attempt reaches a shadow pilot.

## Rights and attribution

- A public URL is evidence provenance, not permission to republish all underlying content.
- Preserve source-specific licenses/terms.
- Government open-data licensing applies to the relevant datasets, not automatically to every linked image/document/page.
- Application-gated data remain gated.
- Reformulating a public wish/challenge does not imply endorsement by the originating platform or organization.
