# Contribution Revision Cycle V0.1

Status: **bounded operating seam; synthetic verification only**

This layer continues the contribution-review seam after an explicit `revise` verdict without mutating the original submitted workspace or creating a second canonical Attempt.

```text
retained submission N
        +
exact REVISE review N
        ↓
revision workspace N+1
        ↓
materially changed revision submission N+1
        ↓
independent review N+1
        ↓
same canonical Attempt + appended AttemptReview
```

It does **not** transition the Problem, create an Outcome, establish funding, authorize deployment, or establish causal impact.

## Why a separate revision workspace exists

A submitted `ContributorWorkspace` is immutable. `REVISE` therefore cannot mean “re-open and edit the old file.” The revision cycle creates a new workspace that inherits the prior work for editing but binds itself to:

- the original root workspace ID;
- the exact parent submission SHA-256;
- the exact triggering review ID and SHA-256;
- the next monotonic revision number;
- the triggering review's revision requirements;
- a base work hash used to reject unchanged resubmission.

The parent submission and review remain separate retained evidence. The revision workspace does not overwrite or supersede them.

## Create a revision workspace

The parent review must have verdict `revise`, must be independently authored (`reviewer_ref != contributor_ref`), and must be bound to the exact parent submission.

```sh
problem-contribution-revision init submission-v0.json \
  --trigger-review review-v0.json \
  --out revision-r1.json
```

A revision workspace starts `active` and carries the established participation basis plus the prior work payload. Edit only the new workspace:

```sh
problem-contribution-revision set-work revision-r1.json \
  --method-scope "Updated bounded method" \
  --notes "How the review requirement was addressed"
```

Artifacts may be added or removed from the revision workspace. Private/local locators remain local revision evidence and are never copied into canonical Commons state.

## No-op revisions are rejected

Before resubmission, the revision workspace computes a canonical work hash over the contributor-controlled work payload: participation details, method/scope, produced outputs, artifacts, blockers, and notes.

If that work hash is unchanged from the exact parent submission, validation fails. A `REVISE` decision therefore cannot be satisfied by simply wrapping the same contribution in a new revision ID.

```sh
problem-contribution-revision validate revision-r1.json \
  --parent-submission submission-v0.json \
  --trigger-review review-v0.json \
  --submittable
```

## Submit the revision

```sh
problem-contribution-revision submit revision-r1.json \
  --parent-submission submission-v0.json \
  --trigger-review review-v0.json \
  --submission-out submission-r1.json
```

The revision submission records both lineage hashes, the base work hash, the changed work hash, and a hash of the exact submitted revision workspace.

The submitted revision workspace then becomes immutable just like the original workspace.

## Review the revision independently

```sh
problem-contribution-review create-revision submission-r1.json \
  --workspace revision-r1.json \
  --parent-submission submission-v0.json \
  --trigger-review review-v0.json \
  --reviewer-ref REVIEWER_REF \
  --verdict accept \
  --summary "Bounded revision review" \
  --limitation "Important limitation" \
  --out review-r1.json
```

The same contribution-review schema is used for initial and revision submissions. Each review is bound to the exact submission it evaluates.

`accept`, `revise`, and `reject` retain their narrow meanings. A second `revise` starts another explicit revision workspace from `submission-r1.json` plus `review-r1.json`; the sequence can continue as `r2`, `r3`, and so on.

## Project the revision into Commons

```sh
problem-contribution-review project-revision review-r1.json \
  --submission submission-r1.json \
  --workspace revision-r1.json \
  --parent-submission submission-v0.json \
  --trigger-review review-v0.json \
  --state problem-commons.json \
  --receipt-out projection-r1.json
```

Revision projection requires the original canonical Attempt to exist and to be `active` because the immediately preceding canonical review was `revise`.

It reuses the root Attempt ID:

- `pattempt:<root-workspace-suffix>`

and appends ordered canonical reviews:

- initial review: `pareview:<root-workspace-suffix>`
- first revision: `pareview:<root-workspace-suffix>:r1`
- second revision: `pareview:<root-workspace-suffix>:r2`

The Attempt's current `artifact_refs` are updated to the revised submission's **opaque artifact IDs only**. Prior submissions and reviews remain preserved by exact hash and review history; private artifact locators are not promoted into the Commons object.

## Replay and sequence safety

Exact replay of the latest revision submission + review is idempotent and returns `changed=false`.

Projection fails closed when:

- the parent submission or triggering review differs from the workspace lineage;
- the immediately preceding canonical review is missing or is not `revise`;
- the canonical Attempt is not `active` before resubmission;
- a conflicting review already occupies the deterministic revision review ID;
- unexpected review history breaks the monotonic revision sequence;
- an older revision is replayed after a later revision has already been projected;
- a requested receipt path already exists.

Receipt collision is checked before Commons state is loaded and mutated.

## Claims boundary

```text
accepted revised Attempt
!= globally correct answer
!= Problem resolved
!= Outcome
!= funded
!= authorized
!= deployed
!= causal impact established
```

This V0.1 seam establishes software behavior and audit lineage only. Reviewer identity, reviewer competence, external validity, adoption, funding, authority, and real-world outcome remain outside the claim.

## Stop condition

Do not expand this revision seam into Problem transitions, Outcomes, funding, Public-Good behavior, deployment, or broad UI merely because the revision lifecycle now exists.

The next increment should be driven by external rehearsal: either reviewer/contributor friction demonstrates a missing operating surface, or a separate verified conversion route requires another bounded seam.
