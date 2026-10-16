# Semantic Problem Graph

Cite-Refinery v0.10 adds a provenance-preserving semantic graph across three source families:

- **practical** — real-world observations, incidents, institutions, failures, consequences, persistence;
- **academic** — claims, mechanisms, methods, measurements, interventions, qualifications and contradictions;
- **program** — programs, datasets, repositories, capabilities, implementations and deployed systems.

These are **source/evidence layers, not the unit of analysis**. The unit of analysis is a specific semantic node or local module such as:

> Current local free-roaming dog population is not continuously known.

Coverage is derived from the graph neighborhood around that node. Cite-Refinery does **not** assign a composite coverage score.

## Why this model exists

A broad topic can look well covered while one operational subproblem remains disconnected. For example:

```text
periodic field surveys -------- SUPPORTS --------> population is not continuously known
academic detection research --- SUPPORTS --------> population is not continuously known
population problem ------------ MEASURED_BY -----> capture-recapture method
street survey app ------------- PARTIALLY_ADDRESSES -> population problem
```

The important question may be whether this path exists:

```text
population problem
    -> MEASURED_BY method
    -> IMPLEMENTED_BY repository/program
    -> DEPLOYED_BY institution
    -> PRODUCES outcome
```

If the graph contains the method but the `IMPLEMENTED_BY` step is absent, the system reports a **broken represented path**. That means the connection is not established in the current graph; it is not proof that no implementation exists in the world.

## Semantic packet

Generic suppliers can contribute graph material with `cite_refinery.semantic_graph.v1` packets. This lets Nocturnal, Cite, Refinery, manual research, or another agent populate the same problem graph without collapsing their authority.

```json
{
  "schema": "cite_refinery.semantic_graph.v1",
  "source_system": "manual-public-research",
  "clusters": [
    {"key": "observability", "title": "Population observability"}
  ],
  "nodes": [
    {
      "key": "problem",
      "statement": "Current local free-roaming dog population is not continuously known.",
      "kind": "problem_claim",
      "layer": "neutral",
      "clusters": ["observability"]
    },
    {
      "key": "field",
      "statement": "Periodic field surveys observe only sampled places and times.",
      "kind": "observation",
      "layer": "practical",
      "clusters": ["observability"],
      "source_refs": ["https://example.org/survey"]
    },
    {
      "key": "method",
      "statement": "Repeated individually reconciled sightings can feed capture-recapture estimation.",
      "kind": "method",
      "layer": "academic",
      "clusters": ["observability"],
      "source_refs": ["doi:10.example/example"]
    },
    {
      "key": "app",
      "statement": "A street-survey application records geolocated dog sightings.",
      "kind": "program",
      "layer": "program",
      "clusters": ["observability"],
      "source_refs": ["repo:street-survey"]
    }
  ],
  "edges": [
    {"source": "field", "relation": "SUPPORTS", "target": "problem"},
    {"source": "problem", "relation": "MEASURED_BY", "target": "method"},
    {"source": "app", "relation": "PARTIALLY_ADDRESSES", "target": "problem"}
  ]
}
```

Every imported node/edge receives a provenance receipt containing the source system, packet digest, packet reference when supplied, and the packet-local key. Re-ingesting the exact same packet is idempotent.

## Node kinds and relations

The graph ships with common semantic kinds including:

`problem_claim`, `observation`, `academic_claim`, `mechanism`, `method`, `dataset`, `metric`, `intervention`, `program`, `capability`, `implementation`, `repository`, `institution`, `outcome`, `limitation`, `requirement`, `policy`, `event` and `concept`.

It also accepts additional lower-snake-case kinds to avoid forcing every domain into a fixed ontology.

Common relations include:

`SUPPORTS`, `CONTRADICTS`, `QUALIFIES`, `OBSERVES`, `EXPLAINS`, `CAUSES`, `EXACERBATES`, `MEASURES`, `MEASURED_BY`, `ESTIMATES`, `REQUIRES`, `PROVIDES_DATA_FOR`, `ADDRESSES`, `PARTIALLY_ADDRESSES`, `IMPLEMENTS`, `IMPLEMENTED_BY`, `DEPLOYED_BY`, `LIMITED_BY`, `FAILS_WHEN`, `PRODUCES`, `EVALUATED_BY`, `ADAPTABLE_TO`, `TRANSITIONS_INTO`, `DEPENDS_ON`, `ENABLES` and `MISSING_LINK`.

Additional `UPPER_SNAKE_CASE` relations are accepted so domain-specific semantics such as `EFFECT_MODIFIED_BY`, `DISCOVERED_FOR`, `CANDIDATE_FOR`, and `ADOPTED_FOR` can be preserved instead of flattened into generic edges.

## Clusters

Clusters organize semantic modules, not authority layers. One broad problem may contain clusters such as:

```text
Free-roaming dog management
├── population observability
├── population replenishment
├── intervention effectiveness
├── wildlife externalities
└── governance / feedback
```

A node can belong to multiple clusters. Clusters may also have parents, allowing module/topic hierarchies without requiring the graph itself to become a tree.

## Coverage query

`graph-coverage` returns the node-local neighborhood partitioned by the practical, academic and program source layers.

```bash
cite-refinery graph-coverage PROJECT_ID NODE_ID --depth 1
```

The result contains:

- `layer_presence`: booleans for the three source layers;
- `intersection`: e.g. `practical_academic_no_program`;
- the actual neighboring nodes from each layer;
- typed relations;
- contradictions;
- qualifications/limitations;
- unresolved or explicitly missing links.

`intersection` is a Venn-style semantic projection only. It is not a quality score and does not imply that the connected evidence is sufficient or true.

Find nodes represented in practical + academic material but without program-side representation:

```bash
cite-refinery graph-query PROJECT_ID \
  --present practical \
  --present academic \
  --absent program
```

The reverse query can find potential solutionism:

```bash
cite-refinery graph-query PROJECT_ID \
  --present program \
  --absent practical
```

## Broken-path / missing-edge discovery

A path template describes the semantic chain we want to test. Example:

```json
[
  {"relation": "MEASURED_BY", "target_kind": "method"},
  {"relation": "IMPLEMENTED_BY", "target_kind": "repository"},
  {"relation": "DEPLOYED_BY", "target_kind": "institution"}
]
```

Run it with:

```bash
cite-refinery graph-trace PROJECT_ID NODE_ID \
  --steps-json '[{"relation":"MEASURED_BY","target_kind":"method"},{"relation":"IMPLEMENTED_BY","target_kind":"repository"}]'
```

The tracer returns completed paths and exact break points. A break is a **candidate coverage gap in the represented knowledge graph**, not proof of real-world absence.

This supports queries such as:

- a practical problem and academic measurement method exist, but no implementation is connected;
- an intervention and program exist, but no outcome-evaluation path is represented;
- a repository supplies a capability, but no evidence connects that capability to the exact problem module;
- a mechanism is academically established but not connected to any practical observation;
- practical and academic nodes agree on a problem while program supply attaches only to a neighboring, narrower problem.

## Bootstrapping and projecting the existing lifecycle

Existing Cite-Refinery state can be exposed to the semantic graph without inventing authority transitions:

```bash
cite-refinery graph-bootstrap PROJECT_ID
```

The bootstrap materializes:

- project problem as a neutral root;
- empirical problem observations as practical nodes;
- requirements as neutral requirement nodes;
- capabilities and implementations as program nodes.

Empirical observations are connected to the project root using `CONTEXT_FOR`, **not** `SUPPORTS`.

For the fuller lifecycle projection use:

```bash
cite-refinery graph-project PROJECT_ID
```

This first runs the safe bootstrap and then projects the existing research and supply records:

```text
Nocturnal / problem observations
    -> practical observation nodes

research brief questions
    -> neutral research-question nodes
    -> DERIVED_FROM practical observations

Cite deep-research paper receipts
    -> academic source nodes
    -> DISCOVERED_FOR research questions [candidate]

Refinery solution-map candidates
    -> program/repository/capability nodes
    -> CANDIDATE_FOR requirements [candidate]

project-local adopted capability
    -> ADOPTED_FOR requirement [candidate]
```

Those relation names are intentionally weaker than `SUPPORTS`, `ADDRESSES`, `IMPLEMENTS`, or `PRODUCES`.

A paper discovered for a question is **not** automatically a supporting academic claim. A Refinery hit is **not** automatically a solution. A project-local adoption is **not** automatically effective. Stronger edges have to be asserted from reviewed evidence with their own provenance.

The projection also performs a conservative exact-identity reconciliation. Nodes of the same kind whose normalized statements are exactly equal may be linked with `SAME_AS`. Fuzzy or embedding-based near-equivalence is deliberately not asserted automatically; it requires a reviewed resolver or a supplier packet that explicitly provides the semantic relationship.

Repeated projection is idempotent and candidate fallback identities use deterministic content digests.

## Commands

```text
cite-refinery graph-ingest
cite-refinery graph-bootstrap
cite-refinery graph-project
cite-refinery graph-neighborhood
cite-refinery graph-coverage
cite-refinery graph-query
cite-refinery graph-trace
cite-refinery graph-clusters
cite-refinery graph-export
```

## Authority boundary

The semantic graph records and queries relationships; it does not silently upgrade them.

- a practical observation is not automatically an academic claim;
- a discovered paper is not automatically evidence for a claim;
- an academic mechanism is not automatically a requirement;
- a repository is not automatically a solution;
- an implementation is not automatically effective;
- a post-intervention observation is not automatically causal evidence;
- an absent edge is not proof of real-world absence.

The graph is designed to make those distinctions visible while still allowing the three source families to meet at the exact semantic node where they actually overlap.
