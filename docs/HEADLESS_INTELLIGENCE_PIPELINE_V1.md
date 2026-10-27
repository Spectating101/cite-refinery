# Headless intelligence pipeline v1

The independently owned engines remain Nocturnal (practical evidence), Cite-Agent (academic research) and Cite–Refinery (capabilities and cross-layer interpretation). This feature adds a **local, headless change inbox**, not another web application.

## Implemented

- Finite schedulable polling of explicitly configured local JSON exports with the cite-refinery-headless command.
- SHA-256 fingerprinting, stable record identities, idempotent change detection and atomic checkpoints in a private SQLite database.
- Import contracts for record_list (leads only) and existing semantic_graph.v1 packets. Semantic packet interpretation calls the existing source-bounded cross_layer_stack engine.
- Optional local stdio MCP server with read-only feed_status and recent_changes tools.
- Errors, missing exports and malformed packets cannot erase already captured records.
- No raw documents, extracted names, investigations, credentials or source text are stored in the event inbox.
- No remote fetch, graph mutation, publication, causal assertion, claim promotion or autonomous investigation is authorized by the polling layer.

## Reproduce

Install from a local checkout of Cite–Refinery:

    pip install -e '.[headless]'
    cite-refinery-headless --db .cite-refinery/private/headless.sqlite run --config examples/headless/feeds.json
    cite-refinery-headless --db .cite-refinery/private/headless.sqlite status

Repeating run against unchanged snapshots produces zero new change events.

Use MCP on a trusted local machine:

    export CITE_REFINERY_HEADLESS_DB="$PWD/.cite-refinery/private/headless.sqlite"
    cite-refinery-headless-mcp

The MCP transport is stdio only. Do not expose this local private database to an unauthenticated network. The MCP server is read-only; external scheduling is separate.

For unattended operation, use a user-level systemd timer, cron or Prefect. Example cron (replace all absolute paths):

    13 */6 * * * /abs/venv/bin/cite-refinery-headless --db /private/headless.sqlite run --config /private/feeds.json

The upstream exporters must generate their snapshots **before** each poll; polling does not run the source exporters automatically.

## JSON contracts

Config schema: cite_refinery.headless_feeds.v1

    {
      "schema": "cite_refinery.headless_feeds.v1",
      "feeds": [
        {"id": "nocturnal", "system": "nocturnal", "kind": "record_list", "path": "nocturnal.json"},
        {"id": "cite", "system": "cite-agent", "kind": "record_list", "path": "cite.json"},
        {"id": "atlas", "system": "cite-refinery", "kind": "semantic_packet", "path": "atlas.json"}
      ]
    }

Record list schema: cite_refinery.headless_records.v1

    {
      "schema": "cite_refinery.headless_records.v1",
      "records": [
        {"id": "source-stable-identifier", "title": "Lead requiring verification", "url": "https://example.org/item"}
      ]
    }

Inputs are explicitly selected **local files**, maximum 2 MiB per file and 2,000 entries per feed. Missing or duplicate IDs fail closed. Vendor IDs should remain stable over time; changes to other fields produce new revisions. Removed records do **not** create deletion instructions. Source records are treated as untrusted leads. A separate source-specific exporter must normalize vendor output; the generic schema is not a claim that vendor APIs are already supported.

Semantic packets must be scoped to a single project and use cite_refinery.semantic_graph.v1. Existing explicit reviewed/candidate relationships can yield bounded insight counts. Same-word or same-cluster overlap never creates new graph relationships.

## External reuse disposition

| Upstream system | Current reuse mechanism | Prerequisite for real live integration |
| --- | --- | --- |
| TrendRadar | Normalized local record export contract | Pin version, confirm output schema and replay diff tests |
| Graphiti | Optional downstream graph candidate, not installed | Verify temporal semantics and prevent authority escalation |
| Research Intelligence Agents | Academic source leads via normalized export | Verify paper IDs, quotes and contradiction assertions |
| Project Emet | **Not bundled** | Source-available restricted license; rights and privacy review |
| Research Niche Scout | Opportunity leads via normalized export | Independently validate novelty and reproducibility |
| Academic Commercialization Agent | Technology/commercialization leads | Verify IP, deployment, TRL and counterparty evidence |
| The Lens | Candidate source interface | Verify subscription/API rights and retention restrictions |
| Prefect | Optional external scheduler | Use only if local systemd/cron insufficient |
| OpenSanctions / FollowTheMoney | Already available in Nocturnal ecosystem | Reuse existing investigative custody and authority gates |
| DeerFlow | Optional agent-runner benchmark | Compare with existing investigation controllers before adoption |

This table does **not** assert vendor software or connectors are installed. In particular, do not copy, package or execute Project Emet merely because its code is public. The source-available license limits who may use it.

## Ownership and guardrails

1. Nocturnal owns investigative evidence, source custody, actor attribution and publication/correction gates.
2. Cite-Agent owns academic retrieval and grounded scholarly verification. Discovery alone does not prove claim support.
3. Cite–Refinery owns the candidate three-layer graph. Its existing graph-review digest/revision approval remains mandatory for persistence.
4. The inbox saves **change metadata only**. It never converts a lead, AI confidence value or candidate edge into an accepted fact.
5. Do not put private Nocturnal cases or credentials in public GitHub Actions.
6. Poll errors do not remove records or silently mark stale evidence as new.
7. A successful poll is not proof of end-to-end research, successful deployment or commercial value.

## Next integration checkpoints

- Benchmark source normalization with two live pinned external snapshots (suggest TrendRadar and one academic source), with independently adjudicated change diffs.
- Run daily on Optiplex using a private scheduler after remote execution is available; collect missed-poll and false-change diagnostics.
- Add source-specific adaptors only after schema, licensing, API quotas and privacy review.
- Pilot a project-scoped cross-map update using exact source-reviewed edges; test changes against independent human adjudication before allowing any candidate proposals into the graph-review queue.
