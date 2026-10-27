# Project-development steering v1 (candidate-only)

This extends the headless evidence inbox into an **opt-in portfolio advisor**.
It is not an autonomous code editor, GitHub issue bot, knowledge-authority
upgrade or replacement for Nocturnal/Cite/Refinery.

## The loop

1. First-party and external feed exporters produce pinned local JSON snapshots.
2. Headless poll records source revisions with SHA-256 and incremental events.
3. A registry defines **active** repositories, goals, current priorities,
   baseline constraints, subscribed feeds and specific technical watch tags.
4. The steering CLI routes new source revisions only when the record explicitly
   names the project or intersects its structured watch tags.
5. It records a durable project-specific **candidate next check**, with original
   source URL, changed record revision and reason for routing.
6. An authorized local agent asks MCP for development_brief(project_id) and
   decides whether to benchmark, create a ticket or propose a PR. No operation
   occurs automatically.

Strictly **no free-text semantic matching** or model-generated relevance
claims are involved in this first deterministic routing milestone. A vendor
source title alone cannot trigger an arbitrary project's roadmap.

## Synthetic fixture replay

Install from the Cite-Refinery checkout:

    python -m pip install -e '.[headless]'
    cite-refinery-headless --db /tmp/refinery-inbox.sqlite run --config examples/headless/feeds.json
    cite-refinery-steer --db /tmp/refinery-inbox.sqlite run --config examples/headless/feeds.json --registry examples/headless/projects.json
    cite-refinery-steer --db /tmp/refinery-inbox.sqlite brief --project refinery

Two illustrative projects are in the example registry. The supplied
fictional leads intentionally carry structured tags and source URLs.
The native semantic packet is parsed with source-bounded cross-layer review,
but does not automatically create a steering recommendation or accepted edge.

Repeating both commands should report **zero new proposals** when the
source snapshots remain unchanged. Editing a record while retaining its
stable ID generates a new revision candidate at the next poll/steer cycle.

## Opting in any active repository

Add a project to the **private** registry:

    {
      "id": "engineering-project",
      "repository": "OWNER/REPOSITORY",
      "state": "active",
      "feeds": ["cite", "nocturnal", "refinery", "git"],
      "watch_tags": ["robotics", "cad", "firmware"],
      "goals": ["Deliver a reproducible mechanical/electrical validation pipeline"],
      "current_priorities": ["Benchmark reusable upstream components"],
      "benchmark": "Reproduce with pinned fixture and independently checked behavior"
    }

Valid states: active, paused, archived. Paused and archived repos receive
no new candidate proposals. Updates must be rechecked when reactivated.
Each feed must be in the configured feed manifest and provide a valid local
snapshot. Existing official graph and publication controls are unchanged.

## Monitor local development commits too

An optional **read-only** local Git adapter produces a project_change
record whenever a registered project's latest commit SHA changes.

Create a private local checkout manifest (no file paths committed to Git):

    {
      "schema": "cite_refinery.local_checkouts.v1",
      "checkouts": [
        {"project_id": "engineering-project", "path": "/absolute/path/to/repository"}
      ]
    }

The local project must match the registered GitHub origin and point directly
to the worktree root. The adapter never pulls, fetches, writes to GitHub,
reads source blobs or executes repo hooks. It uses read-only Git metadata.

    cite-refinery-git-heads --registry /private/projects.json --checkouts /private/checkouts.json --out /private/git.json

In the private feeds.json add:

    {"id": "git", "system": "local_git", "kind": "record_list", "path": "git.json"}

Then poll and steer as above. Stable HEADs do not generate more events.
Commits on a different checkout without being in the checkout manifest are
not monitored; this is explicitly opt-in, not all-repository discovery.

This exporter currently observes the checked-out HEAD only, not remote
releases, GitHub Issues, PR activity, or repository-wide merge state.
Feed adapters for those require separate explicit data-access and identity
checks, and are tracked in issue #131.

## Run repeatedly and consume through MCP

Run the **export → poll → steer** sequence via a *trusted private* scheduler
(systemd/cron/Prefect). Each command is bounded and exits; the MCP server
is not the background scheduler. Schedule upstream academic/news/repository
exporters before headless polling, not after it.

The stdio MCP server exposes:

- feed_status(): feed health and last fingerprints
- recent_changes(limit): source change receipts
- registered_projects(): opt-in repository registry (requires
  CITE_REFINERY_DEVELOPMENT_REGISTRY)
- development_brief(project_id,limit): proposal provenance and next checks

Example environment:

    export CITE_REFINERY_HEADLESS_DB=/private/inbox.sqlite
    export CITE_REFINERY_DEVELOPMENT_REGISTRY=/private/projects.json
    cite-refinery-headless-mcp

All returned recommendations are **candidate_review**. They are next
checks, not instructions to auto-merge or automatically accept claims.
A source can suggest a match, but it cannot create a direct causal
relationship or evidence of verified technical superiority. A real agent
must inspect the source and current repo implementation first.

## Boundaries and limitations

- No live external models, TrendRadar, Graphiti, DeerFlow, The Lens or
  Project Emet are installed in this PR. Their integration is separately
  gated by licensing, privacy, source reliability and benchmark results.
- New recommendations require structured signal categories, HTTPS source
  references, stable IDs and either explicitly targeted project IDs or
  preselected watch tags; malformed/unrelated records are ignored.
- Superseded intermediate revisions are counted and skipped rather than
  incorrectly attributed to the latest source contents.
- Feed failure blocks cursor advancement, allowing recovery without losing
  an earlier reviewable revision.
- Each project processes at most 500 committed events per pass; if has_more
  is true, repeat the pass. Project-specific review is isolated by ID.
- Candidate records contain short source titles and URLs; never commit
  private source snapshots, Optiplex checkout paths or private SQLite.
- Security-advisory signals are routed for inspection, but a matching
  tag is not evidence that any project is vulnerable.
- No automatic PR/issue creation, issue assignment, remediation,
  source ingestion beyond the existing feed contracts, or notifications.
- System currently uses structured tags, not an accurate semantic
  relation/competition evaluator. Future model reasoning needs explicit
  source verification and independent benchmark gates.

## Acceptance gate before broader autonomy

1. Run local Git/head + academic + monitoring source replay on real active
   projects, without disclosing private sources.
2. Independently label relevance on a fixed sample of new external records.
   Measure precision, missed relevant changes and stale recommendations.
3. Compare recommended engineering experiments to actual project capabilities,
   pinned tests and licensing constraints before creating draft PRs.
4. Reject semantic upgrades that confuse topical overlap, theoretical
   plausibility, working code and demonstrated real-world performance.
5. Deploy a private scheduler only after audit and failure-recovery checks.
