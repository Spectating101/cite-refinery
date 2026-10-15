# Three-layer problem-to-solution loop

Cite-Refinery coordinates three independent authorities rather than merging them into one evidence pool.

```text
Nocturnal
real-world matters, events, claims, sources, chronology
        |
        | empirical observations + literature-query hints
        v
Cite-Agent
academic concepts, mechanisms, interventions, literature claims
        |
        | explicit capability requirements
        v
Refinery
capabilities, repositories, implementations, execution routes
        |
        | adopted project-local implementation
        v
Cite-Refinery validation loop
run -> artifact -> experiment -> validated promotion -> reuse
        |
        +--------------------------> later observation / evaluation
```

## Authority boundaries

### Nocturnal owns empirical problem mapping

Nocturnal answers what happened, where, when, to whom, what changed, which source supports an observation, and how a matter developed over time. Cite-Refinery imports those records as `robs:*` problem observations and preserves the upstream matter/event identifiers and source provenance.

An observation is **not** automatically an academic claim and is never marked supported because Cite-Agent completed a literature pass.

### Cite-Agent owns academic grounding

Cite-Refinery converts selected Nocturnal observations and their `literature_queries` into an `rbrief:*` research brief. The prompt explicitly labels the observations as empirical context rather than academic evidence. A Cite run is stored as an `raudit:*` whose purpose is `research_brief`.

The current adapter deliberately reuses Cite-Agent's existing `tool ground` surface. A later structured/MCP adapter can replace that transport without changing the lifecycle IDs.

### Refinery owns the implementation landscape

Literature findings do not become software automatically. Cite-Refinery records explicit `rreq:*` capability requirements, optionally linked to the research brief and Cite audit that motivated them. `solution-map` searches canonical Refinery through its read-only `search` CLI and also checks the project's local Cite-Refinery overlay.

A chosen candidate can be adopted as an `rcap:*` project capability while retaining the requirement, brief, audit, solution-map, and candidate references in provenance. Existing implementation execution, experiment gates, and promotion rules then apply unchanged.

## New machine objects

| Prefix | Meaning |
| --- | --- |
| `robs:*` | empirical problem observation imported from Nocturnal |
| `rbrief:*` | literature-research brief derived from observations |
| `rreq:*` | explicit capability requirement |
| `rmap:*` | canonical/local Refinery solution map |

Existing `rclaim:*`, `revidence:*`, `raudit:*`, `rcap:*`, `rimpl:*`, `rrun:*`, `rart:*`, and `rexp:*` retain their previous roles.

## CLI flow

```bash
cite-refinery init "Public record revisions" \
  --problem "Understand and address silent changes in public records"

cite-refinery nocturnal-ingest rproject:... evidence_history_packet.json
cite-refinery research-brief rproject:...
cite-refinery research-ground rproject:... rbrief:...

cite-refinery requirement-add rproject:... \
  "Preserve and compare revisions to public records with source provenance" \
  --source-brief-id rbrief:... --source-audit-id raudit:...

cite-refinery solution-map rproject:... rreq:...
cite-refinery cap-adopt rproject:... rreq:... "Versioned public-record diff" \
  --description "Preserve source history and compare successive revisions" \
  --solution-map-id rmap:... --candidate-ref record.version.diff
```

From `cap-adopt` onward, the existing Cite-Refinery lifecycle continues: register an implementation, execute it, record artifacts and experiments, and promote only after the existing validation gates pass.

## Invariants

1. Nocturnal observations remain empirical objects; Cite grounding cannot rewrite them into supported academic claims.
2. Nocturnal imports are idempotent within a project by upstream external/event ID.
3. Duplicate literature-query hints across observations collapse into one research question while preserving all source observation IDs.
4. Capability requirements are explicit boundary objects; Cite output is not silently converted into a build decision.
5. Canonical Refinery integration is read-only at discovery time. Adoption creates a project-local Cite-Refinery capability and retains the external candidate reference.
6. Existing execution and promotion gates remain authoritative for deciding whether an implementation becomes reusable shared capability state.
