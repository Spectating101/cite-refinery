# Unified Product Shell

Cite-Refinery v0.11 introduces a thin web product layer over the existing control plane. It does **not** merge the Nocturnal, Cite, or Refinery engines into one codebase. Instead, it presents their project-local outputs inside one problem-intelligence workspace.

## Product boundary

The user-facing workspace is organized by task rather than internal repository name:

```text
Overview
Reality      -> Nocturnal empirical observations
Research     -> Cite research briefs, discovery, grounding
Graph        -> Cite-Refinery semantic problem graph
Solutions    -> Refinery requirements, candidates, capabilities
Build        -> implementations, runs, artifacts
Validate     -> experiments and Nocturnal feedback
```

The engines retain their authority boundaries:

- a Nocturnal observation remains empirical context;
- a Cite paper discovery does not automatically support a claim;
- a Refinery candidate does not automatically solve a requirement;
- an adopted capability is not automatically effective;
- a semantic missing edge means the relationship is not represented in the graph, not that it is absent from the world.

## Run the prototype

```bash
pip install -e .
cite-refinery-web --workspace .cite-refinery --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`.

The server uses only the Python standard library and the existing Cite-Refinery state. No frontend or web-framework dependency is required for this prototype.

## Read-only first milestone

The v0.11 shell is intentionally read-only. It is designed to answer one product question before a larger frontend investment:

> Can one Cite-Refinery project coherently contain empirical reality, academic research, semantic structure, solution supply, implementation, and feedback without forcing the user to move between separate products?

The shell reads the same workspace used by the CLI and exposes:

- project selection;
- project overview counts;
- Reality observation/source/status views;
- Research brief/audit summaries;
- Semantic Graph node search and node-local three-layer coverage inspection;
- Solutions requirement/supply/capability summaries;
- Build run/artifact summaries;
- Validate experiment/feedback summaries.

## HTTP API

The prototype also establishes a small product-facing read API that can later be consumed by a React/Next/Vercel frontend without changing the underlying engine model.

```text
GET /api/health
GET /api/projects
GET /api/projects/{project_id}?graph=1
GET /api/projects/{project_id}/graph
GET /api/projects/{project_id}/nodes/{node_id}/coverage?depth=1
```

`ProductWorkspace` is the Python projection behind these endpoints. Its schema is `cite_refinery.product_workspace.v1`.

## Why not merge repositories

Nocturnal, Cite, and Refinery remain separately testable engines with distinct schemas and authority. Cite-Refinery is the product/control plane that composes them.

This preserves modularity while avoiding a fragmented user experience:

```text
                   Cite-Refinery product
                           |
          +----------------+----------------+
          |                |                |
      Nocturnal           Cite           Refinery
       reality          research          supply
          |                |                |
          +----------------+----------------+
                           |
                     Semantic Graph
```

A future production frontend can replace the prototype shell while keeping this product projection and API contract.
