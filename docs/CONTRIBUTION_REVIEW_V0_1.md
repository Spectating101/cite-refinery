# Contribution Review and Canonical Attempt Projection V0.1

Status: **bounded operating seam; synthetic verification only**

This layer connects a submitted contributor workspace to the existing Problem Commons `Attempt` lifecycle without treating submission or review as a real-world outcome.

```text
retained Contributor Workspace
        +
exact submission snapshot
        +
independent review
        ↓
canonical Attempt + AttemptReview
```

It does **not** transition the Problem, create an Outcome, assert funding, authorize deployment, or establish causal impact.

## Preconditions

The contribution must already have passed the contributor-handoff boundary:

- exact Project Brief bound into a `ContributorWorkspace`;
- explicit participation basis;
- method/scope;
- at least one produced-output claim;
- at least one material artifact;
- immutable submitted workspace and matching submission snapshot.

The canonical Problem must still contain the referenced subproblem and be in a lifecycle state that permits Attempts.

## Independent review

Create a review against the retained workspace and exact submission:

```sh
problem-contribution-review create submission.json \
  --workspace workspace.json \
  --reviewer-ref REVIEWER_REF \
  --verdict accept \
  --summary "Bounded review summary" \
  --limitation "Important limitation" \
  --out review.json
```

Valid verdicts are:

- `accept` — the submitted contribution is accepted for its stated scope;
- `revise` — the contribution needs another work cycle and requires at least one explicit revision requirement;
- `reject` — the submitted attempt is preserved as rejected.

`reviewer_ref` must differ from `contributor_ref`, but this string comparison is **not identity verification**. A pilot or institution must establish reviewer identity/role through its trusted process.

The review is bound to the exact submission SHA-256. Canonical projection additionally records the exact review SHA-256 so a later review with the same verdict but different content is treated as a conflict, not an idempotent replay.

## Validate before projection

```sh
problem-contribution-review validate review.json \
  --submission submission.json \
  --workspace workspace.json
```

Validation rejects, among other things:

- a submission that differs from the retained submitted workspace;
- an empty or self-reviewing reviewer reference;
- a review bound to another submission;
- `revise` without actionable revision requirements;
- malformed or duplicate artifact records.

## Project into canonical Commons state

```sh
problem-contribution-review project review.json \
  --submission submission.json \
  --workspace workspace.json \
  --state problem-commons.json \
  --receipt-out projection-receipt.json
```

Projection creates deterministic IDs from the contributor workspace suffix:

- `pattempt:<workspace-suffix>`;
- `pareview:<workspace-suffix>`.

The canonical Attempt stores **opaque artifact IDs**, not submission artifact locators. The retained submission remains the source for private/local locator and digest information. This prevents local paths from leaking through a public Problem snapshot merely because an Attempt is projected.

Verdict mapping:

| Review verdict | Canonical Attempt status | Meaning |
| --- | --- | --- |
| `accept` | `accepted` | contribution accepted for stated scope only |
| `revise` | `active` | revision work is required |
| `reject` | `rejected` | rejected attempt remains part of the record |

An accepted Attempt is still **not** a Problem resolution or Outcome. Any later Problem transition, pilot/deployment decision, authority receipt, or outcome observation remains a separate operation under its existing gates.

## Replay and conflict safety

Replaying the exact same submission + review is idempotent and returns `changed=false`.

Projection fails if the deterministic canonical Attempt already represents different work or if a different review has already been projected. A pre-existing `--receipt-out` also fails **before** canonical state mutation so evidence is not silently overwritten.

## Evidence boundary

All tests in this V0.1 seam use synthetic contributors, reviewers, artifacts and Problems. Passing the workflow establishes software behavior only. It does not demonstrate external solver conversion, independent domain-review quality, adoption, funding, or outcome.

## Next seam

Do not expand this layer into outcomes or deployment.

The next useful operating increment after external/synthetic rehearsal is an explicit **revision-cycle handoff** for a `revise` verdict, or a user-facing reviewer surface if real reviewer friction demonstrates that the CLI/file workflow is insufficient.
