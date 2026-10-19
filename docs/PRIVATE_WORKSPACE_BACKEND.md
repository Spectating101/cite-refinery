# Private workspace backend v0.14 — transactional first slice

**Status:** built and verified locally, not deployed as a private public-facing service.
The existing Vercel site remains an authenticated static demonstration of public-source data.

## Product and access model

The central product remains the three-layer clustered map (Practical / Academic /
Program). This local backend adds transactional persistence, isolation, user roles,
an import queue, and audit history. AI is not needed to use or ingest the map.

SQLite provides the first working transactional implementation: tenants, users,
memberships, SHA-256-hashed bearer credentials, projects, jobs, and audit events
are relational tables; each project has a revisioned JSON graph state. Import
runs under one SQLite BEGIN IMMEDIATE transaction (including graph validation and
revision update). This is **not PostgreSQL or a multi-instance hosted database**.

Memberships grant access to *all* projects in their tenant:
- owner: manage membership via trusted local CLI, create/read, import, audit
- editor: create/read, preview/queue import, audit
- viewer: read the mapped research and job statuses; cannot queue writes

No unauthenticated private data; no cross-tenant reads/writes; no AI invocation.
The service has no public registration or unauthenticated write endpoints.

## Local operator setup

Install optional dependencies in a virtual environment:

    python3 -m pip install -e ".[server]"

Create a local tenant:

    cite-refinery-private --db /private/workspaces.sqlite3 bootstrap --tenant "Lab" --owner "operator"

Save the returned tenant and user IDs. Obtain a time-limited bearer credential:

    cite-refinery-private --db /private/workspaces.sqlite3 issue-token USER_ID --ttl-hours 24

The raw token is shown once to the trusted operator and only its hash is stored.
Keep the token out of logs, git and shared terminals. Start the private API:

    cite-refinery-private --db /private/workspaces.sqlite3 serve --host 127.0.0.1 --port 8780

Only loopback binding is supported. Authenticate by sending an Authorization:
Bearer TOKEN header. For an authenticated project API, use:

- GET /api/projects
- POST /api/projects (tenant_id, title, problem)
- GET /api/projects/PROJECT_ID (read-only project projection)
- GET /api/projects/PROJECT_ID/atlas
- GET /api/projects/PROJECT_ID/nodes/NODE_ID/coverage
- POST /api/projects/PROJECT_ID/ingest/preview (JSON body with packet)
- POST /api/projects/PROJECT_ID/ingest (packet, expected_revision, expected_packet_digest)
- GET /api/jobs/JOB_ID
- GET /api/projects/PROJECT_ID/audit (editor or owner)

Preview validates all semantic nodes/edges without mutation, reporting structural
and source-authority warnings. Enqueue requires a matching previewed packet hash
and project revision. Import is executed only by a separate worker process:

    cite-refinery-private --db /private/workspaces.sqlite3 worker-once

Or run worker-loop supervised on the private host. Failed/stale queued jobs never
change the graph. Unexpected worker crashes roll the entire transaction back,
leaving the job queued. Jobs execute no arbitrary programs, only typed graph
ingestion. Candidate and missing semantic links are not elevated to proven claims.

## Boundary to production

Do NOT expose this service directly to the Internet or copy its database to
Vercel. The public static Vercel demo is deliberately unaffected.

Before private multi-user hosting: migrate to PostgreSQL with transactional
migrations/backup recovery, implement OIDC identity + MFA/session lifecycle and
per-project permissions where required, add a distributed lease/retry queue,
trusted source identity and signed/verified connectors for Nocturnal/Cite/Refinery,
rate and cost limits, audit retention, security review, network TLS, privacy
controls and tested encrypted backups. A source_system label in an imported
packet does not authenticate its source, and structural validation does not
establish whether a research claim is true.

SQLite is suitable for this first local single-host correctness gate, not a
durable multi-instance hosted SaaS. Project state is still JSON within a DB row;
future relational graph indexes and PostgreSQL isolation are separate work.
