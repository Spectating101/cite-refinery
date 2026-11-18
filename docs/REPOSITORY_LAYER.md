# Repository layer

The repository layer reconciles the known software inventory and its technical
evidence before any demand analysis. Its records describe repository identity,
mechanisms, inputs, outputs, requirements, limitations, source interpretations
and explicitly supported technical relationships. It creates no problem,
customer, market or opportunity records.

The current software discovery catalogue remains an input, with its original
source and mapping history preserved. The new layer is an independent technical
projection of that catalogue plus older known inventories and separately
reviewed evidence. It does not replace or rewrite the user's discovery queue,
workflow maps or uncommitted mapping modules.

## Evidence authority

These measures are separate and can overlap:

| Record | What it establishes | What it does not establish |
| --- | --- | --- |
| Discovery observation | A repository was present in an identified source snapshot | Actual functionality or a working interface |
| Captured original source | A retained README, document or source file, with its locator and available hash/pin | A correct interpretation of that source |
| Source interpretation | A model or analyst's technical reading, bound to source bytes and literal excerpts | Verified semantic support, a runtime pass or integration compatibility |
| Reviewed capability | A separately supplied, scoped capability review with mechanism and technical contracts | That every capability of the repository has been reviewed |
| Scoped execution evidence | The recorded operation ran in the stated trial and environment | General production readiness or success outside that trial |

Reviewed capability levels are `documented`, `code_inspected` and `executed`.
Execution needs an execution receipt and explicit scope. Source interpretations
instead retain `semantic_support_verified: false` and `runtime_tested: false`.
An interpretation from an LLM has authority
`source_bound_model_interpretation`; older source-bound analyst records retain
`source_bound_interpretation`. Neither contributes to reviewed-capability counts.

The older connected catalogue contains keyword-derived role assignments. Those
remain `proposed_capabilities`, with unreviewed or rejected status. They are
different from the later source-bound technical interpretations. A captured
README does not convert an old role assignment into a reviewed capability.

## Input and output contracts

The main APIs are in `src/cite_refinery/repository_layer.py`:

```python
build_repository_layer(survey_paths, *, supplemental_paths=(), evidence_path=None)
validate_repository_layer(catalog)
repository_layer_packet(catalog, project_id=None)
```

`build_repository_layer` accepts complete survey snapshots and normalized
supplemental inputs. There is no inventory sampling cap. Identities normalize
case-insensitively to `github:owner/repository`; aliases, domains and source
observations are retained. A source's Git blob SHA remains a blob identity, not
an invented commit revision. Domain-specific judgments remain annotations and
cannot remove a repository from the inventory.

The output has schema `cite_refinery.repository_layer.v1` and scope
`repository_only`. It contains:

- `repositories`: stable identity, aliases, descriptions, domains, observations,
  reviewed `capabilities`, `source_interpretations`, old
  `proposed_capabilities`, `rejected_assignments` and explicit `unknowns`.
- `sources`: original locators, available commit/blob/content hashes, capture
  paths, source kind and verification scope.
- `relationships`: separately supported declared dependencies, proposed
  technical handoffs or scoped tested handoffs.
- `proposed_relationships`: legacy rule-derived relationships, retained apart
  from active technical relationships.
- `input_sources`, `coverage`, `boundaries` and a content `catalog_digest`.

A reviewed capability has a stable `key`, `name`, `mechanism`, `evidence_level`
and source `evidence_ids`. Its `inputs` and `outputs` contain a name, format and
description. Requirements contain kind, name and constraint. Limitations contain
a scoped statement. Empty arrays mean these contracts are not recorded; they do
not mean that the component needs no configuration or has no limitations.

A source interpretation preserves `purpose`, input/output strings, `human_work`,
`custom_glue`, `limitations`, literal source evidence and model/analyst provenance.
Hypothetical workflow `contribution`, workflow family and workflow role fields
are omitted from this projection. Eleven older analyst records in the initial
current-catalog export have no separate purpose field; their technical arrays
and evidence remain available without inventing a summary.

Source references must exist, belong to the recorded repository where required,
and retain their authority. Repeated snapshots preserve distinct observations.
Unchanged source receipts and interpretations have stable identities; changed
captures or interpretations become additional history instead of overwriting
earlier records. The validator reconciles counts and the complete content digest.

## Existing source adapters

`src/cite_refinery/repository_layer_import.py` supplies four adapters:

| Adapter | Input | Retained authority |
| --- | --- | --- |
| `current_catalog_snapshot(path)` | Frozen technical export of the current software discovery SQLite catalogue | Repository metadata, audited original-source receipts and separately labelled technical interpretations |
| `connected_snapshot(profiles, audit)` | Earlier connected catalogue and its matching hash audit | Explicit repository identities, source receipts, old role proposals and legacy relation proposals |
| `source_lock_snapshot(path)` | Source lock file | File/version observations; a lock pin alone is metadata |
| `legacy_snapshot(root, portfolio_path=None)` | Prior documentation reviews, functional probes, domain judgments and repository portfolio history | Historical observations, including failed, blocked and untested cases |

Current exports use schema
`cite_refinery.current_repository_catalog_export.v1`. They identify the immutable
source database by SHA-256, retain the original per-row payload hashes and include
the source catalogue's metadata and complete `projects` list. The adapter checks
the exported row count against the original catalogue count. Only explicit
`github:` project identities are repositories. A repository URL mentioned inside
a product or paper description is not another repository record.

The current export's source checks bind each retained path and expected content
hash to the actual hash. Interpretation evidence must have a matching source
check and `quote_integrity: exact_quote_present`. Original excerpt offsets remain
labelled `retained_catalog_check`: the export rechecks literal presence and bytes,
not a new semantic or runtime assertion. Recoverable missing source/hash/quote
checks withhold interpretation authority while preserving repository identity
and exclusion provenance. Contradictory hashes, cross-repository source identity
or malformed snapshot identity fail the import for review.

## Technical relationships

Declared dependencies are directed from consumer to dependency. Their scope can
distinguish a required package from an optional backend. Repository lineage is
not a dependency. A shared JSON format, topic or language never creates an edge.

A `tested_handoff` requires source and target revisions, a named case, a passing
result and execution evidence. The recorded test scope remains attached to the
edge. A `proposed_handoff` stays a candidate. Legacy proposed edges remain outside
the active graph; rejecting an endpoint's old producer/consumer role also rejects
the associated legacy relationship proposal, without erasing its history.

## Building and reviewing

The command entry point is `cite-refinery-repository-layer`; the equivalent
module invocation is `python -m cite_refinery.repository_layer_cli`.

```bash
cite-refinery-repository-layer build \
  --survey research_materials/opportunity_atlas/github_repository_survey.json \
  --survey research_materials/opportunity_atlas/github_frontier_repository_survey.json \
  --current-catalog /private/current_repository_catalog.json \
  --connected-profiles /private/module_profiles.json \
  --mapping-audit /private/mapping_audit_compact.json \
  --source-lock /private/source_lock.json \
  --legacy-root research_materials/opportunity_atlas \
  --evidence /private/reviewed_repository_evidence.json \
  --output /private/repository-layer

cite-refinery-repository-layer validate /private/repository-layer/repository_catalog.json

cite-refinery-repository-layer view \
  /private/repository-layer/repository_catalog.json \
  --output /private/repository-layer/repository_layer.html
```

`--survey`, `--supplemental`, `--current-catalog` and `--source-lock` are
repeatable. Build output includes normalized inputs, the catalogue, HTML view,
Program-only graph packet, validation report and exact identity reconciliation.
Private source exports stay outside the tracked repository.

For the existing private service,
`repository_layer_index.build_repository_layer_index` builds an immutable SQLite
query index. `query_repository_layer` returns bounded technical-only pages;
`CITE_REFINERY_REPOSITORY_LAYER_DB` selects the index. This preserves ordinary
service authentication and project access checks. Its search projection uses
repository technical fields rather than the old workflow/customer search text.

## Native graph projection and scale

Every generated node has the Program layer. Repository source interpretations
are their own node kind, with candidate source-binding edges. Reviewed
capabilities, mechanisms, I/O, requirements, limits and source records remain
distinct. No problem root is bootstrapped, and legacy relationship guesses are
not active native edges.

The local `import` command previews the exact packet, refuses changes to existing
edge authority, checks the approved state digest and saves an immutable
catalogue artifact attached to the selected project:

```bash
cite-refinery-repository-layer import \
  --catalog /private/repository-layer/repository_catalog.json \
  --workspace /private/repository-workspace \
  --project-id PROJECT_ID \
  --receipt /private/repository-layer/import_receipt.json
```

Omitting `--project-id` creates a separate local project. This is useful for an
isolated full-inventory verification; it does not replace existing native graph
bindings in the user's private project.

The full packet exceeds the hosted request budget. Existing
`software_mapping_atlas.node_packets` / `edge_packets` provide the service's
two-phase transport pattern: bounded node packets first, then edges bound to the
actual admitted node IDs. Hosted imports must preserve the preview, revision,
status and receipt gates for each packet. Publishing a query index does not
require creating duplicate repository nodes in the existing graph.

Native in-memory packet staging takes one detached copy at each staging
boundary, rather than copying the growing graph at every node/edge. This keeps
full-inventory preview and import practical while retaining atomic validation:
an invalid late edge or stale review does not mutate persistent state.

## Initial reconciled snapshot, 2026-11-18

The identified snapshots reconcile to **15,196 repositories**: 13,462 current
repositories plus 2,031 older connected repositories, minus 312 shared
identities, plus 15 other known identities. The current catalogue's one
`product:readplace` record remains outside the repository layer. All repositories
from both major inventories are present, with zero missing IDs.

At this snapshot, 5,136 repositories have captured source evidence; 2,616 have
source-bound technical interpretations. Separately, 21 repositories have 40
reviewed capabilities: 27 documented, 6 code inspected and 7 scoped executed.
There are 7 declared dependency edges and 2 bounded tested handoffs. The 5,071
old role proposals and 7,187 legacy relationship proposals remain visible as
history, including 10 rejected roles and 25 invalidated relationship proposals.
The historical functional probes retain all 16 outcomes: 6 pass, 6 fail,
3 not tested and 1 blocked.

These are coverage counts, not a claim that every repository's functionality
has been reviewed. Inventory completeness is relative to the named snapshots;
capability review remains explicitly incomplete.

## Focused verification

```bash
PYTHONPATH=src:tests python -m unittest \
  test_repository_layer test_repository_layer_import \
  test_semantic_graph test_semantic_ingest_review
```

The tests cover identity completeness and deduplication, source-bound authority,
negative evidence, wrong-role correction, preserved snapshot history, false
source ownership, stale hashes and literal excerpts, no format-only connections,
Program-only projection, replay stability, isolated staging and atomic failed
imports. Synthetic adapter fixtures are contract tests, not third-party software
execution evidence.
