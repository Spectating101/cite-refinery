# v0.22 — Private semantic module evolution interface

Cite-Refinery's center remains a semantic, clustered Practical / Academic /
Program map, not a generic progress scoreboard. The v0.21 private backend
captured immutable project revisions; this version makes those comparisons
inspectable **at the individual topic/module and node level**.

## Access, privacy and deployment boundary

The interface is intentionally available **only through the private API**
running on the authorized computer:

    cite-refinery-private --db /private/research.sqlite3 serve --host 127.0.0.1 --port 8780

Navigate locally to:

    http://127.0.0.1:8780/private/evolution

Supply an operator or viewer bearer token in the password input. Tokens exist
only in page memory and are not placed in the URL, browser local/session storage,
HTML, telemetry, downloaded files or server-access logs. Disconnect clears the
page's credential and research state. Reloading the page requires reconnection.

The HTML/CSS/JS shell itself contains **no private project content** and can
load without a token. All research records, project enumeration, snapshots and
comparisons come through the authenticated project-scoped API. Tenant isolation
and owner/editor capture permissions remain enforced server-side.

The private shell uses restrictive Content Security Policy, same-origin scripts,
styles and fetches, no third-party scripts, no CORS wildcard, cache-control
no-store, X-Frame-Options DENY, and escaped source-provided text. External
evidence links require valid HTTPS URLs and open with noopener/noreferrer.

**Never deploy this private service or database as the static public Vercel
atlas.** Vercel remains an isolated, SSO-protected demonstration of public
semantic data. External access to private workspaces needs a separate
production security/deployment review.

## What the UI does

1. Lists private projects visible to the authenticated account.
2. Lists their saved immutable checkpoints. Select an earlier and later revision.
3. Computes server-side, read-only evidence comparisons with module-local
   changes, not merely global graph totals.
4. Filters modules by text, changed Practical / Academic / Program nodes,
   candidate links, or newly represented limitations.
5. Displays side-by-side change cards per layer. New nodes are kept separate
   from **revisions to existing source receipts**.
6. Inspects each changed source statement, its origin, version-pinned source
   links and source-declared evidentiary limitations.
7. Distinguishes candidate/unresolved links from qualified/asserted relations
   and indicates cross-module links.
8. Allows an owner/editor to create a checkpoint at the exact current revision.
   A capture never changes the live graph and is not allowed for viewers.

The module comparison returns bounded detail arrays for large research
projects; it explicitly notes truncation and does not disguise unlisted
material as zero. Nodes belonging to multiple clusters can appear under
multiple module changes; totals must not be treated as unique item counts.

## Meaning of evidence evolution

More literature, more source-code excerpts or more Git commits are not proof
of product maturity. A recorded passing finite test may coexist with
significant failed limitation probes. A newly qualified semantic edge only
records a change in **graph status**. The view does not assert that a user,
auditor or independent experiment verified it.

All comparisons explicitly preserve the v0.21 null performance-improvement,
market-adoption and production-readiness estimates. Different test scope and
sample populations must not be made into a common time-series score.

## Verification, October 19, 2026

Against an isolated private tenant and real source packages:
- Captured four revisions: empty baseline; v0.18 five-repository portfolio;
  v0.19 pinned CloakPipe bounded experiment; v0.20 earlier broad review and
  two-episode scope comparison.
- Real headless Chrome on Optiplex loaded the private page, entered an
  authorized token, selected the default last two checkpoints, compared
  changes, filtered Program evidence, opened the prior broad-review module,
  inspected individual source URLs and disconnected without JS exceptions.
- Security tests check empty shell/CSP, unauthenticated API rejection, tenant
  isolation, source-level module changes, candidate/qualified distinction,
  and source citation preservation.
- Full Python suite: 119 tests pass. Distribution wheel includes the static
  private UI assets.

## Still ahead

Normalizing arbitrary Refinery run/experiment envelopes, broader repository
and ecosystem trend observation, reviewed retractions, and production
OIDC/PostgreSQL remain separate milestones. This is a local private
research interface, not a continuously monitoring autonomous service.
