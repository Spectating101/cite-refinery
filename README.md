# Cite-Refinery

**Reality → research → semantic structure → solution supply → implementation → feedback.**

Cite-Refinery is the unified problem-intelligence product layer across three specialist engines:

- **Nocturnal** supplies empirical reality: cases, observations, timelines, institutions, sources and post-intervention follow-up.
- **Cite** supplies academic knowledge: research questions, literature discovery, grounding, mechanisms, methods and evidence.
- **Refinery** supplies implementation space: requirements, capabilities, repositories, programs, implementations and reusable solution components.
- **Cite-Refinery** preserves the authority boundaries between those systems, joins them through a provenance-preserving semantic graph, and carries a project through build, validation and feedback.

The product is intentionally **one workspace, not one monolithic codebase**. Nocturnal, Cite and Refinery remain separately testable engines. Cite-Refinery is the control plane and user-facing project model that composes them.

## Unified product model

```text
                           Cite-Refinery
                        problem workspace
                               |
       +-----------------------+-----------------------+
       |                       |                       |
   Nocturnal                  Cite                 Refinery
    Reality                 Research                Supply
       |                       |                       |
       +-----------------------+-----------------------+
                               |
                        Semantic Graph
                               |
                   requirements / implementation
                               |
                       runs / experiments
                               |
                       outcome feedback
                               |
                           Nocturnal
```

The browser workspace is organized by user task rather than repository name:

```text
Overview
Reality      -> Nocturnal empirical observations
Research     -> Cite research briefs, discovery and grounding
Graph        -> semantic nodes, clusters, typed relations and missing paths
Solutions    -> Refinery requirements, candidates, capabilities and implementations
Build        -> implementations, runs and artifacts
Validate     -> experiments and Nocturnal feedback
```

Cite-Agent can still stand alone as a full research workbench. Cite-Refinery consumes the research capabilities it needs; it does not attempt to replace the Cite-Agent product experience.

## Semantic problem graph

The unit of analysis is a **specific semantic problem/module**, not a whole domain and not a composite score.

A node can connect to practical, academic and program-side material using typed relations such as:

```text
SUPPORTS
CONTRADICTS
QUALIFIES
OBSERVES
EXPLAINS
MEASURED_BY
REQUIRES
ADDRESSES
PARTIALLY_ADDRESSES
IMPLEMENTED_BY
DEPLOYED_BY
LIMITED_BY
PRODUCES
EVALUATED_BY
```

That makes it possible to ask structural questions such as:

```text
practical evidence + academic method + no implementation
program supply + no demonstrated practical problem
intervention exists + outcome-evaluation path missing
problem -> method -> [missing implementation] -> deployment -> outcome
```

An absent edge means the relationship is **not represented in the current graph**. It is never treated as proof that the thing does not exist in the world.

See [`docs/SEMANTIC_PROBLEM_GRAPH.md`](docs/SEMANTIC_PROBLEM_GRAPH.md).

## Web product shell

v0.11 includes a dependency-free first web surface over the real Cite-Refinery workspace.

```bash
python -m pip install -e .
cite-refinery-web --workspace .cite-refinery --host 127.0.0.1 --port 8765
```

Then open `http://127.0.0.1:8765`.

The first milestone is intentionally read-only. It exists to validate the product boundary before committing to a larger frontend stack. It exposes:

- project selection and project overview;
- Nocturnal Reality observations, sources and stages;
- Cite Research briefs, questions, discovery and grounding state;
- Semantic Graph search and node-local practical/academic/program inspection;
- Refinery Solutions requirements, supply authorities, capabilities and implementations;
- Build runs and artifacts;
- Validate experiments and outcome-feedback state.

The same projection is available programmatically through `ProductWorkspace` and a small HTTP API:

```text
GET /api/health
GET /api/projects
GET /api/projects/{project_id}?graph=1
GET /api/projects/{project_id}/graph
GET /api/projects/{project_id}/nodes/{node_id}/coverage?depth=1
```

See [`docs/UNIFIED_PRODUCT_SHELL.md`](docs/UNIFIED_PRODUCT_SHELL.md).

## Core CLI

```bash
python -m pip install -e .

cite-refinery init "Pilot project" --problem "A real unresolved problem"
# -> rproject:...

# empirical problem map
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

cite-refinery invoke rproject:... rimpl:... --input-json '{"dataset":"observations.json"}'

# validation
cite-refinery experiment-add rproject:... "holdout validation" \
  --method "frozen holdout" --result "passed acceptance threshold" \
  --verdict passed --run-id rrun:...

# semantic graph
cite-refinery graph-project rproject:...
cite-refinery graph-coverage rproject:... sgnode:...
cite-refinery graph-query rproject:... --present practical --present academic --absent program
cite-refinery graph-trace rproject:... sgnode:... \
  --steps-json '[{"relation":"MEASURED_BY","target_kind":"method"},{"relation":"IMPLEMENTED_BY","target_kind":"repository"}]'
```

State lives in `.cite-refinery/state.json` by default. Writes are atomic.

## Authority boundaries

The integration is deliberately conservative:

1. **Empirical observation is not academic evidence.** Nocturnal material enters as practical context.
2. **Paper discovery is not support.** Cite discovery receipts can become academic source nodes without silently becoming `SUPPORTS` edges.
3. **A supply candidate is not a solution.** Refinery search results remain `CANDIDATE_FOR` until explicitly adopted/reviewed.
4. **Adoption is not effectiveness.** A project-local capability can be selected without being treated as validated.
5. **Execution is not intervention success.** A successful run and a supported real-world outcome remain distinct records.
6. **Post-intervention observation is not causal proof.** The Nocturnal feedback protocol records later evidence without automatic attribution.

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
node = workspace.node_view("rproject:...", "sgnode:...")
```

The product projection schema is `cite_refinery.product_workspace.v1`.

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

The suite covers the evidence-to-build lifecycle, Nocturnal/Cite/Refinery authority boundaries, semantic graph ingestion and path discovery, project projection, feedback, subprocess execution, validation-gated promotion, and the unified HTTP product shell.

## Current product boundary

The intended public architecture is:

```text
Cite-Agent        -> standalone research workbench
Cite-Refinery     -> integrated problem-intelligence product
  Nocturnal       -> internal/specialist Reality engine
  Refinery        -> internal/specialist Solutions engine
  Semantic Graph  -> connective reasoning layer
```

Nocturnal and Refinery retain independent repositories, schemas and APIs. The user should not need separate public websites merely to move through one problem lifecycle.
