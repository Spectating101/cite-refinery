# v0.23 — Public repository signals and pinned dependencies

Cite-Refinery maps Practical investigations, Academic evidence and Program
repositories/capabilities as source-backed semantic modules. This Program
adapter adds a separate temporal public-GitHub observation family. It does
not require AI, and does not assert working software or user adoption.

## Observation contract

The local operator uses GitHub CLI authenticated to access four bounded
PUBLIC provider endpoints: repository metadata, eight latest releases,
twelve latest tags and eight recent default-branch commits. The collector
retains only metadata: timestamp, repo name, public/archive status, branch,
stars, forks, open issue/PR counts, latest push time, release tags/dates/URLs,
tag refs and sampled commit SHAs/dates. Draft releases are filtered OUT,
even if the authorized collector account could see them.

The open-issues counter includes PRs, and the release/tag/commit listings
are truncated samples, never a complete census. Stars and forks cannot
establish active use, product quality or market adoption.

The importer requires each observed repo to exist in an explicitly pinned
v0.18 portfolio manifest and in the exact authorized private project as a
verified repository identity. It creates a separate Program source module
per repository. Release nodes remain distinct from mutable tag references;
GitHub recent commits are sampled activity, not engineering velocity.
Links establish source identity and provider attribution, never readiness.

A future manually collected observation creates a bounded comparison of
two actual counter readings with explicit timestamps, preserving both
source receipts. These are net provider counter differences, NOT an
adoption metric or like-for-like effectiveness test.

## Dependency declaration changes

For the same pinned repository base/head Git revisions, selected allowlisted
package.json, pyproject.toml and requirements.txt manifests are read using
immutable Git blobs, not mutable working files. Added, removed and modified
declaration strings are recorded with source revision and SHA256 hashes.
No claim is made about lockfile resolution, transitive dependencies, CVEs,
successful builds, license clearance or production deployment.
Absent or unsupported paths never become invented dependency findings.

## Private/public separation

Three existing portfolio source repositories are PRIVATE:
Spectating101/nocturnal-oversight, Spectating101/refinery, and
Spectating101/solarpunk-coin. The public collector refuses them instead
of silently publishing authenticated metadata. Private-repo analysis
continues under existing pinned local Git workflows, and requires a
separately authorized provider feed before any private GitHub metadata
capture can be supported. Public static Vercel remains separate.

The first live source-backed sample on October 19, 2026 covers only the
public repos Spectating101/yzu-cluster (Research Drive) and
Spectating101/hardware-splicer. The historical source document is
examples/github_public_signals_20261019.json. At collection time GitHub
reported respectively 1 and 3 published latest releases returned, 12
tags returned each, and 8 recent commits sampled each. Both displayed
0 stars and 0 forks. The open issue/PR counters were 33 and 102.
No changes were found in the selected root dependency declarations within
the exact previously pinned base/head windows.

The isolated real-source import, including five existing source-pinned
repository identities, yielded 7 semantic clusters, 52 Program nodes
and 52 relations. A separate Chrome test verified both public modules
inside the authorized private evolution page, source links and two
checkpoint comparisons with zero JavaScript errors.

## Local review workflow

Using an authenticated GitHub CLI session, capture exactly two PUBLIC
repositories from the existing pinned portfolio:

    cite-refinery-github-signals collect --manifest examples/repository_portfolio_snapshot_v1.json --repository Spectating101/yzu-cluster --repository Spectating101/hardware-splicer --out /private/github-observations.json

New output files use restricted 0600 permissions and are never overwritten.
Review the recorded public status, endpoints, release/tag distinction,
commit samples and the time of capture.

With an authorized private owner/editor credential in
CITE_REFINERY_TOKEN and an existing v0.18 portfolio import, preview:

    cite-refinery-github-signals preview --db /private/research.sqlite3 --project "$PROJECT" --snapshot /private/github-observations.json --manifest examples/repository_portfolio_snapshot_v1.json --repo-root /path/to/project_portfolio

Then enqueue the SAME reviewed source against the expected revision/digest:

    cite-refinery-github-signals enqueue --db /private/research.sqlite3 --project "$PROJECT" --snapshot /private/github-observations.json --manifest examples/repository_portfolio_snapshot_v1.json --repo-root /path/to/project_portfolio --expected-revision REVIEW_REVISION --expected-packet-digest REVIEW_DIGEST

Run the separate trusted local queue worker:

    cite-refinery-private --db /private/research.sqlite3 worker-once

Capture before/after private project checkpoints with the existing
cite-refinery-evolution CLI to browse changes at /private/evolution.

## Limits and future work

The JSON captured through GitHub CLI is not independently signed. An
operator could falsify a supplied JSON snapshot; source labels and local
packet hashes do not prove authentic original responses. The exact pinned
Git dependency evidence is re-evaluated directly during packet conversion.

Future steps: separately permissioned private-repository provider signals,
verified release artifacts and source-tree attestations, longer historical
sampling with rate-limit/error recovery, lockfile and vulnerability evidence,
and independently supported adoption/usage data. No automatic scheduler
or external hosted private tenant was created in this milestone.
