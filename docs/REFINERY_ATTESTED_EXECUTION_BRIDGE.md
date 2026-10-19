# Refinery pinned execution evidence to Program semantic map — v0.19

This is the first **actual bounded implementation/run** integration. It adds
source-pinned Refinery capability records, implementation, preregistered
experiment, observed test results, documented limitations, and reuse decision
to Cite-Refinery's Program layer, alongside a source-reported practical problem.

This is NOT a general execution-attestation protocol, production service,
CloakPipe deployment, autonomous provider runner, or broad privacy guarantee.

## Pinned source and evidence

Source: Spectating101/refinery, pinned Git commit
2b03ad20f8ab3d55462adb38852855b940194c94.
Source case: evidence/cloakpipe-core-20261016/ in that commit.

The source case evaluates rohansx/cloakpipe at
5186e543056cc59c1f680afe3de2e68514ea89c7, specifically the
cloakpipe-core library with default features disabled, using a recorded Rust
harness and local loopback wrapper.

The predeclared bounded contract required 27 tests; its recorded run passes
27/27. Four broader probes involving names, split keys, encoded email and
internationalized email leaked 4/4. Its Refinery assessment is exactly
REUSE_CANDIDATE, execution_ready=false, scratch-only, and production
admission unchanged. Source-license observation is NOT full rights clearance.

The Practical side preserves a source-attributed public forum report about
sensitive-data leakage. The accepted review supports faithful extraction of
what a user reported, not independent truth of the underlying anecdote.

## Validation and provenance constraints

- Reads Git object bytes from the exact pinned commit, never the working tree.
- Verifies source origin and SHA256SUMS hashes against the pinned Git manifest.
- Checks preregistered input hashes, Rust harness/Cargo hashes, matching binary
  hashes and revision identity across contract, build and test receipts.
- Checks individual required cases, malformed-input cases and known failed
  limitation probes against the aggregate result. Contradictory results fail.
- Checks Commons capability, exact implementation, evaluation/limitation claims,
  and Refinery decision for matching identities and unchanged authority scope.
- Keeps a warning when the Refinery packet contains a Practical external
  source statement outside Refinery's primary Program authority. Review this.
- Never accepts a decision revision that claims broad readiness or production
  authorization instead of the recorded bounded REUSE_CANDIDATE.

This is a receipt-integrity audit, NOT a new execution replay. The adapter
cannot verify external authorship, source signatures, operational deployment,
general effectiveness or whether the public user's anecdote happened.

## Graph model

One observed privacy/problem semantic cluster:
- 1 source-attributed Practical observation.
- 6 Program nodes: capability, implementation, predeclared contract,
  recorded run, known limitations, and bounded reuse decision.
- 7 typed edges: verified receipt relationships are qualified; a proposed
  PARTIALLY_ADDRESSES relation to the observed problem remains candidate.

If the same private project already contains v0.18 source-pinned Refinery
repository evidence at the exact matching Git commit, one extra qualified
DERIVED_FROM relation ties the recorded assessment to that repository node.
It is a provenance link only, NOT proof of deployed functionality.

## Private operator workflow

Use an authenticated local private database and a short-lived token stored
in CITE_REFINERY_TOKEN.

Preview without state mutation:

    cite-refinery-refinery --db /private/research.sqlite3 --project "$PROJECT" --refinery-repo /path/to/refinery --ref 2b03ad20f8ab3d55462adb38852855b940194c94 preview

Inspect original links, limitation failures, source-authority warning,
assessment boundaries, project revision and packet digest before approval.
Then enqueue the same reviewed packet:

    cite-refinery-refinery --db /private/research.sqlite3 --project "$PROJECT" --refinery-repo /path/to/refinery --ref 2b03ad20f8ab3d55462adb38852855b940194c94 enqueue --expected-revision REVIEW_REVISION --expected-packet-digest REVIEW_DIGEST

Apply via the separate local transaction worker:

    cite-refinery-private --db /private/research.sqlite3 worker-once

## Actual Optiplex verification

The real frozen Refinery case was previewed and imported into a private project
which already contained the v0.18 five-repository source history snapshot.
The resulting map has 6 clusters, 27 nodes and 28 edges. CloakPipe case:
Practical 1, Academic 0, Program 6. The exact Refinery revision lineage is
qualified, and the possible problem solution is only candidate. Chrome passed
inspection of the limitations and citations with no JavaScript errors.

This does not create a three-layer-complete cluster, and the public Vercel
read-only demo is unaffected. No private case data or binary was copied to
the public repo.

Next: extend source contracts beyond this one bounded CloakPipe case, add
trusted service identity, richer actual Refinery run histories, and reviewed
problem-capability linking without falsely upgrading evidence.
