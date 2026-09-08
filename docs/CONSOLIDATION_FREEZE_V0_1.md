# Problem Commons × Public-Good Consolidation Freeze V0.1

Status: **experimental interface freeze**

This document freezes the current division of responsibility between Problem Commons and the Public-Good Control Plane while empirical validation proceeds. It is intentionally a boundary contract, not a repository merger.

## Why freeze now

Both systems have reached enough internal depth that further ontology growth risks duplicating working machinery rather than increasing external value. The next evidence should come from real cases, solvers, problem owners, resource matching, pilots, and adoption.

The freeze therefore establishes:

1. what each system owns;
2. what may cross the boundary;
3. what may never be silently escalated across the boundary;
4. which apparent overlaps are deliberately kept as orthogonal concepts;
5. what evidence would justify changing this contract.

## Ownership

### Problem Commons owns

- living Problem identity and public/restricted lifecycle;
- problem formulation, uncertainty, evidence references, success/falsification criteria;
- subproblem decomposition;
- contribution work stages: Observe → Measure → Explain → Design → Build → Test → Deploy → Monitor → Generalize;
- solver/project matching, Project Briefs, attempts, submissions, review, contribution credit;
- project-level effort, compensation, volunteer compatibility, funding need/readiness, implementation/maintenance budget ownership;
- cross-problem work graph and reuse relationships;
- derived Case Workspace joining these states without becoming a new source of truth.

### Public-Good owns

- domain-constituted diagnosis of public-good delivery/control failures;
- scarcity vs access vs capacity vs dependency reasoning;
- safety, integrity, rights, professional and authority constraints;
- domain constitutions/adapters (animal welfare, public nutrition, disaster response, etc.);
- external resource-program qualification across grants/CSR/technical assistance/partnership/in-kind support;
- freshness, deadline, eligibility, geography, actor-type and amount checks for resource matches;
- smallest-feasible-intervention reasoning;
- consequential real-world handoff reasoning and domain-specific governance;
- outcome interpretation where activity/output must not be confused with improved conditions.

## Frozen orthogonal axes

Do **not** merge these concepts:

### Commons work stage

`Observe → Measure → Explain → Design → Build → Test → Deploy → Monitor → Generalize`

Question: **What kind of work is being performed?**

### Public-Good control stage / problem class

Examples: `safety`, `stabilize`, `prevent`, `route`, `integrity`, `capacity`, `access`, `outcome`, `evidence`.

Question: **What type of system condition/failure/control transition is being diagnosed?**

A Commons `Measure` contribution may measure a Public-Good `access` problem. A later Commons `Design` contribution may design against that same `access` bottleneck. Therefore there is no automatic stage-to-stage mapping.

## Frozen bridge directions

### 1. Commons FundingNeed → Public-Good CoordinationNeed

Purpose: expose an evidenced project resource demand to Public-Good's external-resource matching plane.

Allowed projection:

- problem/subproblem identity;
- funding/resource kind;
- requested amount when actually known;
- currency;
- compensation/resource context;
- restrictions;
- source references.

Forbidden escalation:

- eligibility;
- current program availability;
- application readiness;
- submission;
- award;
- funding commitment;
- procurement;
- authority.

### 2. Public-Good CoordinationMatch → Commons funding-opportunity projection

Allowed states:

- `qualified_candidate`;
- `requires_verification`;
- `blocked`.

A `qualified_candidate` is still only a candidate. It must never mutate Commons `committed_amount`, set `funded`, or imply a submitted application.

### 3. Public-Good NormalizedFinding → candidate Commons work

A Public-Good finding may propose work that a Commons curator can turn into a Subproblem.

The projection preserves:

- Public-Good control stage;
- problem class;
- priority;
- recommended action;
- evidence refs;
- authority requirement;
- structural-candidate flag;
- domain detail.

The bridge must **not**:

- create a Commons Subproblem automatically;
- invent a Commons work stage;
- start or accept an Attempt;
- grant authority.

### 4. Public-Good intervention reasoning → Commons Governance Envelope

Existing rule retained: the Commons Intervention Envelope is a reviewed projection of Public-Good intervention reasoning. Commons may track the gates/test/handoff state needed for the work graph, but Public-Good/domain experts and competent external authority remain authoritative for consequential action.

## Non-escalation invariants

- Problem status != diagnosis certainty.
- Commons work stage != Public-Good control stage.
- Capability existence != accessibility != current capacity.
- Funding need != eligibility.
- Resource match != funding commitment.
- Application != award.
- Build != successful test.
- Successful test != authority.
- Authority != outcome.
- Activity/output != improved public-good condition.
- Public-Good finding != Commons Subproblem until curator review.
- Shared architecture != transfer of domain-specific professional/legal/welfare rules.

## What is frozen out of scope

Do not add before external evidence demands it:

- payment custody;
- autonomous grant applications;
- generic grant marketplace duplication;
- generic sponsorship marketplace;
- reputation/leaderboards/gamification;
- automatic intervention authorization;
- automatic Public-Good-stage → Commons-stage mapping;
- copying Public-Good domain constitutions into Commons;
- merging repositories for architectural neatness.

## Evidence required to reopen the architecture

Change this freeze only if one or more of the following repeatedly occurs in real use:

1. the same information must be manually re-entered across the bridge in multiple independent cases;
2. a required real workflow cannot be represented without semantic loss;
3. users consistently misunderstand the ownership boundary;
4. duplicated code produces divergent decisions or safety behavior;
5. at least three heterogeneous real cases demonstrate a stable new shared primitive;
6. an external partner requires a durable interoperability contract not expressible by this projection layer.

## Immediate empirical program

Use the frozen seam on at least:

- Taoyuan mobility;
- one animal-welfare/public-good case;
- one disaster/resource-coordination case.

Measure:

- curator minutes to create projections;
- number of semantic corrections required;
- false escalations prevented;
- whether candidate work becomes a real contribution;
- whether resource matches lead to verified applications/commitments;
- whether a later Problem reuses resulting capability.

The architecture is considered frozen while these empirical questions are more important than additional internal sophistication.
