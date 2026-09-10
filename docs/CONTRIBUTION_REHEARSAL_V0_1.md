# Contribution Review/Revision Rehearsal V0.1

Status: **synthetic operating rehearsal; architecture frozen upstream**

This pass does not add another contribution lifecycle concept. It takes the frozen review/revision seam and operates it end to end against a realistic synthetic case.

Upstream architecture boundary:

```text
prototype/contribution-review-v0
        ↓
prototype/contribution-revision-v0 @ 92227c6a577afd77ce9c7315c9c8af2624f5dd92
        ↓
prototype/contribution-rehearsal-v0
```

The rehearsal branch must not modify the upstream revision semantics merely to make the case pass. Any awkwardness observed here is evidence for a later decision.

## Rehearsal case

The synthetic case models a community food-redistribution intake register with eight listed records.

The first contribution correctly reports six completed pickups over eight listed records (`6/8 = 75.0%`) but intentionally does not define which records belong in the program-eligibility denominator.

Independent review therefore returns `REVISE` with one requirement:

> Define the eligibility rule and report raw listed-record coverage separately from eligible-program pickup coverage.

The revision preserves the raw ratio, defines eligibility as `eligible_window=true`, and reports five completed pickups among six eligible records (`5/6 = 83.3%`). The revised submission is then independently accepted for that descriptive scope only.

No external food-redistribution program, beneficiary effect, operational effectiveness, funding condition, or causal outcome is represented by this fixture.

## Run it

From an editable install:

```sh
python scripts/run_contribution_rehearsal.py \
  --out /tmp/contribution-rehearsal
```

The output directory must be empty. The runner refuses to overwrite an existing evidence pack.

The runner uses the actual contributor, revision, and review CLI handlers. It records each invocation and emitted JSON in `transcript.json`.

## Evidence pack

A successful run preserves:

- frozen source fixtures;
- initial Contributor Workspace;
- initial submission;
- initial `REVISE` review;
- initial projection receipt;
- explicit revision workspace;
- changed revision submission;
- independent revision `ACCEPT` review;
- revision projection receipt;
- final Problem Commons state;
- command transcript;
- friction audit;
- SHA-256 manifest.

The manifest asserts the final canonical state:

```text
Problem status: open
canonical Attempts: 1
review history: revise -> accept
Attempt status: accepted
Outcomes: 0
authority decisions: 0
private artifact locator leak: none
```

It also proves that the untouched inherited revision workspace is rejected as a no-op before resubmission.

## What this rehearsal is testing

This is primarily an **operability and evidence-continuity** test:

1. Can an operator move from a submitted contribution to a genuine `REVISE` decision without losing the original work?
2. Can the contributor create a materially changed revision without mutating the parent submission?
3. Can an independent reviewer accept that exact revision?
4. Does the entire sequence remain one canonical Attempt with ordered review history?
5. Can a third party inspect the retained files and reconstruct what happened?
6. Do private/local artifact locators stay outside the canonical public Problem snapshot?

Passing those checks does not validate the substantive domain conclusion beyond the synthetic fixture.

## Friction observed

The rehearsal intentionally records friction rather than automatically designing around it.

| ID | Severity | Observation | Current disposition |
| --- | --- | --- | --- |
| F1 | medium | Revision commands repeat parent-submission and triggering-review paths. | Safe but verbose. Consider only a thin session/pack wrapper if external operators repeat this burden. |
| F2 | low | Clearing inherited blockers currently uses an explicit empty `--blocker` value. | CLI ergonomics debt; possible explicit clear/replace flag later. |
| F3 | medium | One revision round already produces several evidence files that must remain associated. | Use the evidence-pack layout as the reference organization before considering a frontend. |
| F4 | expected boundary | `reviewer_ref != contributor_ref` is not reviewer authentication or competence verification. | Preserve as an external governance responsibility. |

F1-F3 are not evidence that a large UI is required. They are evidence that the next useful surface, if external rehearsal confirms the problem, would likely be a **thin orchestration/session wrapper** rather than another lifecycle subsystem.

## Claims boundary

```text
successful rehearsal
!= external adoption
!= independently validated domain result
!= authenticated reviewer competence
!= Problem resolved
!= Outcome
!= funded
!= authorized
!= deployed
```

## Decision after this pass

If the automated evidence pack and repository regression suite remain green, stop architecture work again.

The next branch should be selected from observed use:

- **external/manual rehearsal** if a real operator or evaluator is available;
- **thin CLI/session ergonomics** only if F1-F3 materially slow that operator;
- **packaging/external evaluator guide** if the system works but is hard to understand;
- **no change** if the current file/CLI workflow is adequate for the next conversion route.

Do not proceed automatically into Outcome, funding, deployment, Public-Good, or broad frontend work.
