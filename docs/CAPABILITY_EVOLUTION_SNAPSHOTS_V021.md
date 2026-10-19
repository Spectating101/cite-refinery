# v0.21 — Evidence-aware capability and project evolution

Cite-Refinery remains a three-layer clustered semantic map (Practical,
Academic and Program). This version adds immutable snapshots and a reusable
comparison engine across any set of valid Nocturnal, Cite, repository and
Refinery source packets. It is independent of AI model access.

## Immutable private snapshots

The local SQLite private backend creates project_snapshots without altering
existing projects. Owner/editor captures require an exact current revision
and meaningful label. Checkpoints cannot be overwritten at the same revision,
do not mutate the live graph, and retain original provenance and source links.

Snapshot access is tenant/project scoped; viewers may read reports but cannot
create checkpoints. A stored SHA256 digest is checked on every comparison.
At most 32 checkpoints and 8 MiB per private project checkpoint are allowed.
Snapshots stay in the mode-0600 local SQLite file; no private data enters Git,
public static preview or remote Vercel.

## Deterministic comparison

Two captured states must belong to the same project and have ascending
revisions. The report distinguishes:
- new or revised nodes, clusters, typed relations and packet receipts;
- new Practical/Academic/Program coverage by semantic kind;
- new source-qualified/asserted relationships versus candidate/unresolved;
- status changes for existing edges, **not** independent truth verification;
- newly recorded capability, implementation, outcome, limitation, event and
  comparison nodes with original source receipts and readiness flags;
- shared explicit source identities (repo slug, capability key, implementation
  key or exact pinned source revision), as navigation hints rather than claims
  of experimental equivalence.

Every report labels test comparability as NOT ESTABLISHED. It intentionally
returns null performance improvement, market adoption and production-readiness
estimates. More source records do not prove better software. Different test
contracts cannot yield a common pass-rate denominator. Missing limitations
must not be called resolved. A future retraction facility will require signed
tombstones; silently removed historical graph objects are currently rejected.

## Local operator commands

A valid authorized token must be stored in CITE_REFINERY_TOKEN.

Capture a manually selected project revision:

    cite-refinery-evolution --db /private/research.sqlite3 --project "$PROJECT" capture --label "Before new tests" --expected-revision 2

After a reviewed ingestion and transaction worker, capture the next revision:

    cite-refinery-evolution --db /private/research.sqlite3 --project "$PROJECT" capture --label "After recorded tests" --expected-revision 3

List IDs (not private graph bodies):

    cite-refinery-evolution --db /private/research.sqlite3 --project "$PROJECT" list

Read-only compare:

    cite-refinery-evolution --db /private/research.sqlite3 --project "$PROJECT" compare --from-snapshot SNAPSHOT_OLD --to-snapshot SNAPSHOT_NEW

Equivalent authenticated local-only API endpoints:

- GET /api/projects/{id}/evolution/snapshots
- POST /api/projects/{id}/evolution/snapshots, label and expected_revision
- GET /api/projects/{id}/evolution/compare?from_snapshot=...&to_snapshot=...

The API rejects unauthorized readers, cross-tenant snapshot identifiers,
stale revision captures, invalid snapshot hashes and reversed comparison order.

## Source-backed Optiplex validation

Four checkpoint states were captured in one isolated private project:

1. Empty baseline, revision 0.
2. Five pinned portfolio repos (v0.18): 20 new Program nodes, 15 qualified
   source/history links and five candidate topic relations.
3. Actual CloakPipe bounded test (v0.19): one Practical source observation,
   six Program records and eight relations; 27 required passes and four
   broader leakage failures remained source-limited.
4. Earlier broad privacy-gate review plus cross-scope episode comparison
   (v0.20): eight additional Program records and nine new relations.

All three comparisons correctly returned NO market, performance or production
readiness estimate. Synthetic/HTTP tests cover cross-tenant access, source
tampering, same-source identity, status transitions, retraction requirements
and revision races.

## What remains

v0.21 provides CLI and private API comparisons, not a hosted authenticated
timeline visualization. We also still need generic Refinery run contracts,
normalized release/adoption time-series from GitHub and other evidence
providers, signed retractions, reviewed cross-layer links, and production
Postgres/OIDC. The Vercel demo remains separate and read-only.
