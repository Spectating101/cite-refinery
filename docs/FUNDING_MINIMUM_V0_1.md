# Problem Funding V0.1 — minimum viable economics

This extension exists to remove one bad default assumption from Problem Commons: **useful work is not presumed to be free**.

It is intentionally much smaller than a grant marketplace, payment system, sponsorship platform, or procurement product.

## What V0.1 records

For one `problem_id + subproblem_id`, the funding extension can record:

- problem-solving stage;
- compensation mode;
- whether volunteer contribution is actually compatible with the work;
- currency;
- minimum and target budget when known;
- committed amount;
- eligible instrument classes such as research grant, stipend, paid project, prize, CSR sponsorship, or institutional budget;
- in-kind needs such as compute, equipment, data access, field access, or expert review;
- expense categories;
- restrictions/conflict boundaries;
- evidence/source references for actual funding when they exist;
- implementation budget owner;
- maintenance budget owner.

Unknown numbers remain `null`. V0.1 must not invent a budget merely to make a Project Brief look complete.

## What V0.1 does not do

It does **not**:

- move or hold money;
- verify a grant opportunity;
- infer funder eligibility;
- award funding;
- create sponsorship contracts;
- estimate project costs automatically;
- grant professional or institutional authority;
- treat sponsor preference as evidence;
- treat an unfunded project as volunteer-compatible by default.

Actual grants, CSR programs, donations, sponsorships, procurement routes, and other opportunities need evidence from their own authoritative sources before they become `funding_source_refs`.

## Funding readiness

The extension derives only a narrow resource-readiness state:

- `unknown` — insufficient funding information;
- `blocked` — non-volunteer work is known to be unfunded/seeking and has not met its minimum budget;
- `partial` — some resources are committed but the minimum is not met;
- `ready` — the stated minimum is met, or an explicitly volunteer-compatible zero-minimum task can proceed;
- `not-required` — the contribution genuinely does not require a financial plan.

`ready` means **financially able to start under the declared minimum**, not scientifically valid, safe, authorized, or deployment-ready.

Those remain separate Problem, Stage, and Governance questions.

## Project Brief behavior

`build_project_brief(...)` joins:

```text
Problem Packet
+ contribution/subproblem
+ Stage Profile (when available)
+ Funding Need (when available)
= Project Brief
```

The Project Brief exposes work scope and economic reality together. If a Funding Need is missing, it emits:

> funding plan missing; do not assume the contribution will be performed for free

That is the most important V0.1 behavior.

## Conservative Taoyuan example

`pilot/funding/taoyuan-mobility.funding.v0.1.json` attaches funding semantics to the existing researching Taoyuan candidate.

It deliberately leaves all budget amounts unknown because no defensible costing exercise has been completed. It records possible instrument *classes* only and explicitly states that no grant, sponsor, eligibility, or amount is being asserted.

This is preferable to fabricating an NTD range.

## Promotion criterion

Do not move these fields into canonical Problem Packet V0.2 until real pilot use shows that they materially improve one or more of:

1. solver willingness to start;
2. realistic staffing/costing;
3. identification of an execution blocker;
4. funder/problem matching;
5. implementation/maintenance handoff.

If external users mostly ignore the funding extension, keep it optional or remove it.
