# v0.24 — Permissioned private GitHub observations

Cite-Refinery's Program layer now supports a SECOND, deliberately separate
GitHub source family: repository activity metadata readable only through an
authorized private GitHub account and only inside an authorized local private
research workspace. The v0.23 PUBLIC source collector is unaffected.

## Private source collection

The operator explicitly selects individual source-pinned repositories.
The command first validates their verified Git identity in the selected
project and confirms the editor/owner role in the local SQLite backend.
Only then will GitHub CLI use its existing account to query repository
metadata, recent published releases, tag refs and recent default-branch
commits. Repository must report private=true; a public repository is rejected.

The collector drops draft releases and keeps no issue bodies, issue titles,
release bodies, commit messages, actor profiles or private source-code blobs.
It retains repository counters, public-equivalent release/tag identifiers,
commit SHAs and dates in a restricted metadata format. These are provider
observations, not engineering-performance or adoption claims.

The snapshot file is written under the private DB directory's
private_github_snapshots subdirectory (mode 0700) as an exclusive new file
(mode 0600). No snapshot is written inside Git checkout, fixtures or the
public static Vercel demo. The private import command refuses other local
file paths, symlinks, wrong owners or permissive file modes.

The private CLI authenticates the local project **before** reading source
files or using the GitHub API. Collection requires an explicit --repository
option for each selected repository from a previously pinned manifest.
The GitHub CLI must already be authenticated with authorization to read
each selected private repository.

## Source interpretation

Each selected private repo gets its own Program topic cluster. The adapter
creates restricted provider snapshot nodes, sampled release/tag/commit
events and optional pinned dependency declaration events. Existing verified
repository identity nodes remain separate and are linked by qualified
provenance, not deployed capability claims.

Two observations of the same repo can produce a net provider-counter
difference, using explicit observation times. The comparison never estimates
user adoption, market traction, engineering quality or production readiness.

Pinned manifest changes are rederived from immutable Git base/head blobs;
the provider snapshot itself is unsigned and cannot independently prove the
original API response. Review evidence and provenance at every import.

## Real Optiplex validation — October 19, 2026

The existing private GitHub account could read the three expressly selected
private portfolio repositories: Nocturnal Oversight, Refinery and Policy Lab.
The collector wrote only sanitized metadata to an ephemeral private directory.
No raw private snapshot was committed or displayed.

An isolated private project first ingested the source-pinned five-repo
portfolio, then reviewed and queued the three private provider observations,
which added three source modules, eleven Program nodes and eleven source
relations. The final atlas had eight Program-only clusters; no unsupported
Practical/Academic nodes or three-layer completions were invented.
The v0.21 evolution comparison across two immutable checkpoints passed.
The temporary local private metadata was destroyed at test completion.

## Manual local operator workflow

Prerequisite: local editor/owner bearer credential in CITE_REFINERY_TOKEN.
Select an already-ingested v0.18 project and its pinned Git manifest.

Collect only the three named private repos:

    cite-refinery-github-private --db /private/research.sqlite3 --project "$PROJECT" --manifest examples/repository_portfolio_snapshot_v1.json --repo-root /path/to/project_portfolio collect --repository Spectating101/nocturnal-oversight --repository Spectating101/refinery --repository Spectating101/solarpunk-coin

The command returns the private file path, collection time and count, but
does not print actual metadata. After reviewing the file locally, preview:

    cite-refinery-github-private --db /private/research.sqlite3 --project "$PROJECT" --manifest examples/repository_portfolio_snapshot_v1.json --repo-root /path/to/project_portfolio preview --snapshot /private/private_github_snapshots/private-github-RECORD.json

Queue the exact same reviewed source:

    cite-refinery-github-private --db /private/research.sqlite3 --project "$PROJECT" --manifest examples/repository_portfolio_snapshot_v1.json --repo-root /path/to/project_portfolio enqueue --snapshot /private/private_github_snapshots/private-github-RECORD.json --expected-revision REVIEW_REVISION --expected-packet-digest REVIEW_DIGEST

Apply via the separate trusted local worker:

    cite-refinery-private --db /private/research.sqlite3 worker-once

The optional private evolution timeline can compare source-backed project
checkpoints as before; it never loads data without an authorized token.

## Limits and next step

This is a manually triggered private metadata import for an authorized
single-machine SQLite project. It is NOT hosted private SaaS, live
monitoring, an actual release-binary signer, a vulnerability scanner, or
an identity-independent proof of GitHub observations. GitHub CLI
permissions are broader than per-project permissions; exact local
project/manifest allowlisting is essential.

Production use needs an isolated least-privilege installation token,
server-side retention and deletion policies, redaction review for metadata
identifiers, a securely hosted managed datastore, authenticated background
workers, and independent signed evidence validation. No scheduler was set.
