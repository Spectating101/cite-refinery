# Unified Product Shell

Cite-Refinery v0.11 introduces a thin web product layer over the existing control plane. It does **not** merge the Nocturnal, Cite, or Refinery engines into one codebase. It projects their outputs into one provenance-preserving semantic map.

## Product core

The product is not a linear wizard and not an AI chat surface. Its center is a **clustered three-layer map**.

Each semantic module/cluster is inspected across three independent families:

```text
                         semantic module
                               |
          +--------------------+--------------------+
          |                    |                    |
      Practical             Academic              Program
       reality              knowledge              supply
      Nocturnal               Cite                Refinery
```

Examples of modules include `Population observability`, `Population replenishment`, `Citation reliability`, or any other exact topic/problem neighborhood represented in the graph.

The map preserves neutral concepts/anchors separately from the three source families. Typed edges express what is actually represented between nodes. A layer being populated is not a score, and an empty layer is not proof of absence in the world.

## What hangs off the map

Lifecycle material remains useful, but it is supporting context attached to mapped nodes and modules:

```text
cluster/module
  ├─ Practical records: observations, events, sources, institutions
  ├─ Academic records: questions, papers, methods, findings, limitations
  ├─ Program records: requirements, programs, repositories, capabilities, implementations
  └─ attached execution/evaluation: runs, artifacts, experiments, feedback
```

This means the user does not have to operate Cite-Refinery as a sequence of `Reality -> Research -> Solutions -> Build -> Validate` screens. Those records can still exist and be inspected, but the primary question is always:

> What is represented around this semantic module across Practical, Academic, and Program, and how are those nodes connected?

## Authority boundaries

The engines retain their authority boundaries:

- a Nocturnal observation remains empirical context;
- a Cite paper discovery does not automatically support a claim;
- a Refinery candidate does not automatically solve a requirement;
- an adopted capability is not automatically effective;
- a successful run is not an intervention outcome;
- a post-intervention observation is not automatic causal attribution;
- a semantic missing layer or edge means the relationship is not represented in the current graph, not that it is absent from the world.

## AI role

Cite-Refinery remains directly operable without an AI conversation.

AI can assist discovery, classification, semantic suggestions, explanation, clustering, retrieval, and gap investigation, but the durable product objects remain inspectable without a model call:

- clusters;
- nodes;
- typed edges;
- source references;
- provenance receipts;
- requirements;
- capabilities;
- runs;
- experiments;
- feedback.

The web shell therefore does not require a chat box to navigate or understand a project.

## Run the prototype

```bash
pip install -e .
cite-refinery-web --workspace .cite-refinery --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`.

The server uses only the Python standard library and the existing Cite-Refinery state. No frontend framework is required for this prototype.

## Read-only first milestone

The v0.11 shell is intentionally read-only. It is designed to validate the product ontology before a larger frontend investment.

The default surface is **Map**:

1. select a project;
2. select a semantic cluster/module;
3. inspect Practical, Academic, and Program nodes side by side;
4. inspect neutral anchors, typed internal relations, cross-module edges, contradictions, qualifications, and unresolved/candidate links;
5. select any node to inspect its local three-layer semantic neighborhood.

Supporting **Records** and **Project** views expose source-side records and project boundaries without replacing the map as the conceptual center.

## Product-facing API

```text
GET /api/health
GET /api/projects
GET /api/projects/{project_id}?graph=1
GET /api/projects/{project_id}/atlas
GET /api/projects/{project_id}/clusters/{cluster_id}
GET /api/projects/{project_id}/graph
GET /api/projects/{project_id}/nodes/{node_id}/coverage?depth=1
```

`ProductWorkspace` is the Python projection behind these endpoints.

Current schemas:

```text
cite_refinery.product_workspace.v2
cite_refinery.clustered_three_layer_map.v1
cite_refinery.cluster_view.v1
cite_refinery.product_node_view.v1
```

## Why not merge repositories

Nocturnal, Cite, and Refinery remain separately testable engines with distinct schemas and authority. Cite-Refinery is the product/control plane that composes them.

```text
                   Cite-Refinery product
                           |
                   clustered semantic map
                           |
          +----------------+----------------+
          |                |                |
      Nocturnal           Cite           Refinery
      Practical         Academic          Program
```

Cite-Agent can remain a standalone research/writing workbench. Cite-Refinery consumes the research capabilities and records it needs without replacing the Cite-Agent product experience.

A future production frontend can replace this prototype shell while preserving the same clustered map and API contract.