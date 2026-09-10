# Contributor handoff V0.1

Status: **backend handoff contract / no independent review yet**

This increment closes one narrow seam:

`Project Brief -> contributor workspace -> material submission package`

It deliberately does **not** mutate the canonical Problem Commons attempt lifecycle yet. A submitted workspace is only contributor-supplied work waiting for independent review.

## Core boundaries

- A workspace is cryptographically bound to the exact Project Brief it was issued from.
- Active work requires an explicit participation basis.
- Volunteer work is rejected when the Project Brief says `volunteer_compatible=false`.
- Compensated work is rejected unless the Project Brief reports `funding_readiness=ready`.
- Academic-credit, in-kind, and mixed arrangements require an explicit note describing the established arrangement.
- A submission requires a method/scope statement, at least one claimed produced output, and at least one material artifact reference.
- Artifact references may carry SHA-256 digests; the CLI computes one automatically for local files supplied with `--file`.
- Submission freezes the workspace. Later revision must occur through the independent-review/revision workflow rather than silently editing submitted work.
- `submitted != accepted != correct != outcome != authorized != funded`.

## CLI

Initialize from a Project Brief JSON:

```sh
problem-contribution init project-brief.json \
  --contributor-ref private:solver-123 \
  --out contribution.json
```

Activate only after the participation basis is explicit:

```sh
problem-contribution activate contribution.json \
  --basis compensated
```

Record work:

```sh
problem-contribution set-work contribution.json \
  --method-scope "Run the frozen pipeline and document validation results" \
  --produced-output "Validated transformation script"
```

Attach a material artifact and compute its digest:

```sh
problem-contribution artifact-add contribution.json \
  --title transform.py \
  --kind code \
  --file ./transform.py
```

Validate and submit:

```sh
problem-contribution validate contribution.json --submittable
problem-contribution submit contribution.json --submission-out submission.json
```

The resulting submission is the input to the **next** increment: independent reviewer assignment, verdict, revision/acceptance, and only then projection into the canonical Commons `Attempt` lifecycle.

## Evidence boundary

This increment contains synthetic test briefs and synthetic submissions only. It establishes software behavior, not solver adoption, payment, problem resolution, or institutional use.
