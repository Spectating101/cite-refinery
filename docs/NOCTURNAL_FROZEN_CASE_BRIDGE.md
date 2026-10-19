# Nocturnal TRACE-5 to Cite-Refinery Practical bridge (v0.15)

Operational milestone: one frozen Nocturnal empirical case enters an authenticated
Cite-Refinery project through preview, reviewed queue, and separate worker.
This is a manual import adapter, not live sync, not a public dataset release.

## Canonical pinned source

Source: Spectating101/nocturnal-oversight, branch
feature/trace-accountability-provenance-v0 at
7663d19aa56c4558e32ea57a60ae672dce138c0c.

China's frozen empirical commit: b7fd1283c343154aeeed84a1f9d25530e80ef77d.
First case at that commit:
examples/research/countries/china/cases/china-kangmei-2020.json
Frozen case SHA256:
fc0bfc335a273c9b2468cd7ebd485b03ce53e889fe72196eed1b8230faf9ec5b.

The importer checks the exact source Git origin, ensures the working programme
freeze matches its committed HEAD, then reads the case with Git directly
from the frozen empirical commit. Working-tree edits are not imported.

Nocturnal's China scope is a frozen validated mechanism-study candidate,
NOT a national prevalence study. Its 25 development cases and separate
five-case validation holdouts must never become a pooled national denominator.
Cross-country comparison is not approved.

## Authority-conserving mapping

- One neutral case-context anchor and one source-derived semantic cluster.
- Each accepted, source-backed event is a Practical observation node carrying
  original event IDs, date, stage, review state, source URLs, actor roles,
  entity IDs, and optional media provenance.
- CONTEXT_FOR edges mean belonging to a case, NOT proof of support or cause.
- Accepted TRACE relationships are namespaced NOCTURNAL_CORRECTED_BY,
  NOCTURNAL_RESTITUTED_BY, etc., with original source/target event IDs,
  epistemic state, review state, rationale and citations.
- Even source-accepted edges are marked qualified in Cite-Refinery, never
  independently established causal claims. Missing/unreviewed claims are
  omitted. Invalid accepted link references stop the import.
- All node and cluster keys include the Nocturnal case ID, avoiding accidental
  cross-case entity merges from coincidentally matching text or event ordinals.
- No Academic or Program node is fabricated. The other two evidence layers
  must be populated through separately reviewed Cite and Refinery outputs.

## Local trusted operator instructions

Use an existing private project and local database from v0.14. Install optional
server dependencies before running. Set an authorized short-lived bearer token
as the environment variable CITE_REFINERY_TOKEN. Point NOCTURNAL_REPO to the
checked-out source branch that contains the China programme freeze.

Preview (no database mutation):

    cite-refinery-nocturnal --db /private/workspaces.sqlite3 --nocturnal-repo "$NOCTURNAL_REPO" --candidate-id china-kangmei-2020 --project "$PROJECT_ID" preview

Review the preview's source details, project revision, packet digest, new records
and epistemic/authority warnings. Explicitly enqueue only the unchanged packet:

    cite-refinery-nocturnal --db /private/workspaces.sqlite3 --nocturnal-repo "$NOCTURNAL_REPO" --candidate-id china-kangmei-2020 --project "$PROJECT_ID" enqueue --expected-revision REVIEW_PROJECT_REVISION --expected-packet-digest REVIEW_PACKET_DIGEST

Apply using the existing separate trusted worker:

    cite-refinery-private --db /private/workspaces.sqlite3 worker-once

Use the authenticated project API to inspect its atlas, provenance and audit.
Repeating the same imported frozen case is idempotent, while stale revisions
and changed packet digests are rejected.

## Optiplex validation (19 October 2026)

The actual Kangmei case, not an invented fixture, passed:
- Frozen bytes match empirical Git commit b7fd1283... exactly.
- 1 semantic cluster, 5 nodes (4 Practical, 1 neutral), 7 typed edges.
- Authenticated preview, queue submission and a separate worker commit.
- Private API returned Practical=4, Academic=0, Program=0, with source URLs,
  TRACE review semantics, and audit history.
- Exact replay introduced no new records.

All 25 development cases converted through the adapter. A separate mechanical
import into an isolated temporary project yielded 25 independent clusters,
116 nodes and 158 relations. Two Kunshan claims without editorial review states
were excluded. This is a software correctness test, not new empirical inference.

## Deployment and data boundary

No real Nocturnal source cases or enriched evidence are copied into the
public Cite-Refinery repository or public Vercel demonstration.
Source data are read on the authorized local machine and stored only in
the private local SQLite project. There is NO authenticated live engine
subscription, production identity system, published private database, or
public write endpoint.

Next: independently populate Academic/Cite nodes around specific shared
semantic problems, then Program/Refinery nodes, explicitly review cross-layer
links, and replace transitional identity/storage with PostgreSQL, OIDC,
trusted service credentials, and production worker controls.
