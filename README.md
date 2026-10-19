# Cite-Refinery

**Map the problem across reality, research, and what can actually be built or deployed.**

Cite-Refinery is a provenance-preserving research system whose conceptual center is a **clustered three-layer semantic map**.

Each exact semantic module is mapped across three independent authority families:

- **Practical** — empirical reality, observations, cases, events, institutions and sources; primarily supplied by Nocturnal.
- **Academic** — scholarly claims, mechanisms, methods, findings, limitations and research questions; primarily supplied by Cite.
- **Program** — programs, repositories, capabilities, implementations and other solution supply; primarily supplied by Refinery.

Cite-Refinery joins those records around the same semantic modules without pretending they are the same kind of evidence.

The product is **one workspace, not one monolithic codebase**. Nocturnal, Cite and Refinery remain independently testable engines. Cite-Agent can remain a standalone research/writing workbench; Cite-Refinery only consumes the research capabilities and records needed for the map.

## Core product model

```text
                          Cite-Refinery
                               |
                     semantic clusters/modules
                               |
          +--------------------+--------------------+
          |                    |                    |
      Practical             Academic              Program
       reality              knowledge              supply
      Nocturnal               Cite                Refinery
          |                    |                    |
          +--------------------+--------------------+
                               |
                    typed semantic relations
                               |
             gaps / contradictions / missing paths
```

A module can be as specific as:

```text
Population observability
Population replenishment
Intervention feedback
Citation reliability
Hidden-population estimation
```

The map is structural, not a composite score. `Practical + Academic + no Program`, for example, means that the current graph represents empirical and academic material around that module but does not currently represent program-side material. It does **not** prove that no program exists in the world.

## What hangs off the map

Lifecycle records remain useful, but they support the semantic map rather than define the interface:

```text
semantic module
  ├─ Practical records
  │    observations / events / sources / institutions
  ├─ Academic records
  │    papers / questions / methods / findings / limitations
  ├─ Program records
  │    requirements / programs / repos / capabilities / implementations
  └─ attached execution + evaluation
       runs / artifacts / experiments / feedback
```

This preserves several important boundaries:

1. empirical observation is not automatically academic evidence;
2. paper discovery is not automatically support;
3. a supply candidate is not automatically a solution;
4. adoption is not effectiveness;
5. a successful run is not real-world intervention success;
6. post-intervention observation is not automatic causal attribution.

## AI role

Cite-Refinery is a research system **with AI integrated**, not a chat product that stops working without AI.

AI can assist discovery, classification, semantic suggestions, clustering, retrieval, explanation, and gap investigation. But the durable project state remains directly inspectable and navigable without a model call:

- clusters;
- nodes;
- typed edges;
- provenance receipts;
- source references;
- requirements;
- capabilities;
- runs;
- experiments;
- feedback.

The web shell therefore does not require a chat box to operate the system.

## Semantic problem graph

The unit of analysis is a **specific semantic node/module**, not a whole domain and not a numeric coverage score.

Node kinds include observations, claims, mechanisms, methods, datasets, metrics, programs, capabilities, implementations, outcomes, limitations, requirements, institutions, sources, events, policies and concepts.

Typed relations include:

```text
SUPPORTS
CONTRADICTS
QUALIFIES
OBSERVES
CONTEXT_FOR
EXPLAINS
CAUSES
MEASURED_BY
REQUIRES
PROVIDES_DATA_FOR
ADDRESSES
PARTIALLY_ADDRESSES
IMPLEMENTS
IMPLEMENTED_BY
LIMITED_BY
PRODUCES
EVALUATED_BY
DERIVED_FROM
DEPENDS_ON
ENABLES
MISSING_LINK
SAME_AS
RELATED_TO
```

Every graph edge can preserve provenance, evidence references, authority, review state and uncertainty.

An absent edge means the relationship is **not represented in the current graph**. It is not proof that the relationship does not exist in the world.

See [`docs/SEMANTIC_PROBLEM_GRAPH.md`](docs/SEMANTIC_PROBLEM_GRAPH.md).

## Web product shell

v0.11 introduced a dependency-free read-only web surface over the real Cite-Refinery workspace.

```bash
python -m pip install -e .
cite-refinery-web --workspace .cite-refinery --host 127.0.0.1 --port 8765
```

Then open `http://127.0.0.1:8765`.

The default surface is **Map**:

1. choose a project;
2. choose a semantic cluster/module;
3. inspect **Practical / Academic / Program** nodes side by side;
4. inspect neutral anchors, typed relations, cross-module edges, contradictions, qualifications and unresolved links;
5. select any node to inspect its local three-layer neighborhood.

Supporting **Records** and **Project** views expose source-side records, execution/evaluation state and authority boundaries without replacing the map as the conceptual center.

### Product-facing API

```text
GET /api/health
GET /api/projects
GET /api/projects/{project_id}?graph=1
GET /api/projects/{project_id}/atlas
GET /api/projects/{project_id}/clusters/{cluster_id}
GET /api/projects/{project_id}/graph
GET /api/projects/{project_id}/nodes/{node_id}/coverage?depth=1
```

Current product schemas:

```text
cite_refinery.product_workspace.v2
cite_refinery.clustered_three_layer_map.v1
cite_refinery.cluster_view.v1
cite_refinery.product_node_view.v1
```

See [`docs/UNIFIED_PRODUCT_SHELL.md`](docs/UNIFIED_PRODUCT_SHELL.md).

## Core CLI

```bash
python -m pip install -e .

cite-refinery init "Pilot project" --problem "A real unresolved problem"
# -> rproject:...

# empirical input
cite-refinery nocturnal-ingest rproject:... case.json
cite-refinery research-agenda rproject:...

# research
cite-refinery research-discover rproject:... rbrief:...
cite-refinery research-ground rproject:... rbrief:...

# requirements and supply
cite-refinery requirement-add rproject:... "Continuously estimate the hidden population"
cite-refinery solution-map rproject:...

# project-local capability and execution
cite-refinery cap-add rproject:... "Population estimator" \
  --description "Estimate hidden population from reconciled repeat sightings"

cite-refinery impl-add rproject:... rcap:... subprocess \
  --invocation-json '{"argv":["python","estimator.py"]}'

cite-refinery invoke rproject:... rimpl:... \
  --input-json '{"dataset":"observations.json"}'

# validation
cite-refinery experiment-add rproject:... "holdout validation" \
  --method "frozen holdout" --result "passed acceptance threshold" \
  --verdict passed --run-id rrun:...

# semantic graph
cite-refinery graph-project rproject:...
cite-refinery graph-coverage rproject:... sgnode:...
cite-refinery graph-query rproject:... \
  --present practical --present academic --absent program
cite-refinery graph-trace rproject:... sgnode:... \
  --steps-json '[{"relation":"MEASURED_BY","target_kind":"method"},{"relation":"IMPLEMENTED_BY","target_kind":"repository"}]'
```

State lives in `.cite-refinery/state.json` by default. Writes are atomic.

## Promotion invariant

A project-local reusable capability may be promoted only after validation:

1. a linked experiment must be **passed** or **supported**;
2. executable capabilities require at least one linked **successful run**;
3. implementations proven by those runs can be marked validated;
4. promotion provenance records the originating project, capability, experiment, metrics and successful runs.

## Product-facing Python API

```python
from cite_refinery import CiteRefinery, ProductWorkspace, SemanticGraph

app = CiteRefinery(".cite-refinery")
workspace = ProductWorkspace(app.store)

projects = workspace.list_projects()
view = workspace.project_view("rproject:...")
atlas = workspace.cluster_atlas("rproject:...")
cluster = workspace.cluster_view("rproject:...", "sgcluster:...")
node = workspace.node_view("rproject:...", "sgnode:...")
```

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

The suite covers the evidence-to-build lifecycle, Nocturnal/Cite/Refinery authority boundaries, semantic graph ingestion and path discovery, clustered three-layer product projection, node-local coverage, feedback, subprocess execution, validation-gated promotion, and the HTTP product shell.

## Public product boundary

```text
Cite-Agent        -> standalone research/writing workbench
Cite-Refinery     -> clustered research / problem-intelligence product
  Nocturnal       -> Practical / empirical engine
  Cite            -> Academic / research engine
  Refinery        -> Program / implementation-supply engine
  Semantic Graph  -> connective map
```

Nocturnal and Refinery retain independent repositories, schemas and APIs. The user should not need separate public websites merely to move around the same semantic problem map.

## v0.12 — audit-ready three-layer tracing

- Selecting any Practical, Academic, Program or neutral node reveals the
  shortest currently represented typed paths to the three layers, with explicit
  edge direction, qualification and provenance. Candidate, unresolved,
  not-established and missing links are never promoted to verified connectivity.
- Source references are inspectable as links, provenance receipts expandable,
  and semantic modules export an independently reviewable JSON evidence packet.
- Search and structural filters operate without AI. Missing map connectivity
  is not evidence that a solution or finding does not exist in the world.
- A protected Vercel public-data demo builds from the checked-in pilot.
  It does not offer live ingestion or private multi-user workspaces.
  See docs/PUBLIC_ATLAS_PREVIEW.md for security and deployment boundaries.


## v0.13 — controlled local three-layer ingestion

Graph imports now validate whole typed cluster/node/edge packets in memory before
one atomic JSON-state replacement. Use graph-review --input to preview proposed
changes, layer authority/status warnings and hash constraints; apply only with
both reviewed packet and workspace digests. Receipts are per-project.
This is NOT a hosted write API or a concurrent multi-user database. See
docs/SEMANTIC_PROBLEM_GRAPH.md for the review workflow and its limits.


## v0.14 — first transactional private workspace backend

A separate local SQLite API now supports tenant-scoped bearer credentials,
read/editor/owner roles, revisioned project graph state, reviewed import queues,
single-transaction worker commits and audit records. The three-layer map stays
the conceptual core and remains operable without AI. The protected Vercel
demonstration is unchanged and receives no private data. For setup, security
boundaries and migration gates, read docs/PRIVATE_WORKSPACE_BACKEND.md.


## v0.15 — pinned frozen Nocturnal bridge

The authenticated local private backend now accepts version-pinned TRACE-5
Nocturnal empirical cases into the Practical layer. It preserves source
citations, original editorial and epistemic states, roles, and reviewed
accountability links without inventing Academic or Program coverage. Import
requires preview and an explicit trusted queue submission. Private Nocturnal
case content is not committed to the public repository. The Vercel read-only
public demo is unchanged. See docs/NOCTURNAL_FROZEN_CASE_BRIDGE.md.

## v0.16 — Cite-Agent literature in the same semantic module

The local private backend can now retrieve DOI-indexed Cite-Agent scholarship
and attach Academic SOURCE records to an **existing** frozen Nocturnal matter.
Topical literature links remain candidate, not grounded. The Practical,
Academic, and Program cluster model remains the product's center, and the
public Vercel demonstration is unchanged. See docs/CITE_ACADEMIC_BRIDGE.md
for its scope, trust boundaries, and explicit reviewed queue workflow.

## v0.17 — quote-checked Academic evidence receipts

Optional Cite-Agent grounding receipts can populate Academic claim nodes after
the quotes are checked against previously imported DOI-indexed abstracts.
Claim-to-paper relations are qualified; claim-to-Nocturnal context links remain
candidate. The three-layer map remains fully browsable without AI.
See docs/CITE_ABSTRACT_GROUNDING_BRIDGE.md for the exact workflow and limits.

## v0.18 — source-pinned repository and project trend mapping

The Program layer now includes a standalone, AI-optional bridge for pinned
Git repository identity, exact source-backed capability excerpts and bounded
commit-range history across multiple projects. Curated topic clusters and
explicit candidate links to existing Practical/Academic nodes let repository
supply participate in the same research map without pretending documentation
is working code or commit activity is market adoption. Use the local private
reviewed queue; see docs/REPOSITORY_TREND_SEMANTIC_MAP.md and the pinned
examples/repository_portfolio_snapshot_v1.json example. Public Vercel
remains a separate read-only demo.

## v0.19 — Refinery actual execution records

The Program layer now accepts a source-pinned, internally consistent
Refinery bounded evaluation: capability, implementation, preregistered
contract, recorded run, failed broader probes and reuse decision. It keeps
source integrity separate from independently reproduced execution, does not
turn a passing finite test into general effectiveness, and joins the existing
v0.18 repository trend map only at an exact matching source revision. The
observed public problem is attributed with an authority warning. See
docs/REFINERY_ATTESTED_EXECUTION_BRIDGE.md.

## v0.20 — Refinery evidence-history and change-of-scope mapping

The Program layer can now preserve two source-pinned Refinery evidence
campaigns as different episodes, including the earlier broad privacy review
(three implementations, 12 unresolved gaps, mixed detector fixture) and the
later bounded CloakPipe core test (27 required passes, four failed broader
probes). It explicitly compares their *evidence scope* rather than claiming
like-for-like improvement, and links episodes only at an exact shared
upstream commit. An authenticated local review/queue command is available.
See `docs/REFINERY_EVIDENCE_HISTORY_V020.md`; the protected public demo
remains separate and read-only.
