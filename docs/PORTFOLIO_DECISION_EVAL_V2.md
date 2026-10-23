# Portfolio evaluation phase 2: auditable candidate decision gate

This branch builds on PR #119's **executed source navigation**, not on an imagined autonomous portfolio reviewer.

## What is implemented

`python -m cite_refinery.portfolio_decision_eval --tasks sealed.json --answers candidate.json --out receipt.json`

The input task list holds independent evaluator verdicts (`supported`, `refuted`, `insufficient`) for a specific claim, scope-limited evidence IDs, a case family, and allowed original public source URLs. Candidate output has exactly one verdict, cited evidence IDs and a rationale per task. Scores include claim accuracy, false approvals, unsupported approvals, evidence-scope violations and abstention on evidence-insufficient questions. Missing answers fail rather than being silently counted as abstentions. A false positive on an unanswerable physical validation claim is a failure even if the candidate cites a relevant README.

This is **evaluation infrastructure**, not automatic truth adjudication. The evaluator must independently label the source task and audit whether the admissible citation actually entails the claim. Matching an ID is not proof that an explanation is correct. `release_gate_pass` is intentionally named for the frozen task suite *only*; it cannot authorize an actual product release. The included unit tests use synthetic fixtures rather than live autonomous candidate outputs.

## Next executed experiment

1. Freeze a private answer key for 30–50 tasks across public projects. Include answerable positive and negative claims, deliberately insufficient claims, collisions between software CI and field testing, candidate cross-project integrations, and claims about commercial adoption. Hold the key separately from the candidate, with at least two independent reviewers resolving disagreements.
2. Feed identical **source-scoped evidence** to (a) the Cite–Refinery pipeline, (b) ordinary GitHub browsing with a strong general model and (c) a minimal BM25/semantic retrieval plus answer agent. Record model version, cost, wall-clock effort and citations.
3. Supply all candidate decisions as JSON to this evaluator. Independently inspect citations for entailment rather than granting credit merely because a source was retrieved. Publish only the public-safe aggregate and source receipts.
4. Add the authorized private portfolio only inside a local, access-controlled run; do not upload private source, labels or output to public GitHub Actions.

**Promotion criteria:** the Atlas must show reliable abstention and source-boundary fidelity *and* provide verified, nontrivial project weaknesses or reuse opportunities that the baseline did not find at comparable effort. Otherwise keep the product designated a provenance-aware navigation and research-workbench prototype.

## Nonclaims

This change does not implement a reasoning model, autonomously create dossiers, run competitors, access Optiplex or repair repository-wide CI. The first public eight-project pilot and its draft PR remain separately reviewable.
