# Public Atlas Preview

This Vercel target is **not the hosted multi-user Cite-Refinery service**. It is a strictly read-only, interactive snapshot derived solely from `examples/free_roaming_dog_semantic_pilot.json`, a public-source semantic pilot. It does not read local `.cite-refinery` state, authenticate into Nocturnal or Cite, accept submissions, run AI, or write state.

Build locally with:

```bash
python3 scripts/build_public_preview.py
python3 -m http.server 8766 --directory dist
```

The generated `dist/index.html` preserves the map-first interface and `dist/snapshot.json` contains a self-contained three-layer project projection. The UI's read-only API is satisfied by that local snapshot. Vercel's `vercel.json` runs the same builder and publishes `dist`.

**Public-demo data boundary:** only the checked-in public pilot is included. Inspect the example's source and provenance receipts before changing it. Generated `dist/` is gitignored. Do not deploy an arbitrary project workspace or live JsonStore on an unauthenticated public site.

For a multi-user launch, add server-side authentication, tenant isolation, authorization, audit controls, durable storage, ingestion/job boundaries, and independent security review. This preview intentionally does not claim any of those.

## v0.12 trace and audit behavior

Selecting a node shows shortest **represented** asserted/qualified paths to Practical,
Academic and Program nodes, and opens source citations/provenance receipts. Candidate,
unresolved, not-established and MISSING_LINK edges are explicitly separate and never
counted as established connectivity. Reverse traversal is visually marked, and a graph
path does not assert causality or effectiveness. The selected module can be exported as
an auditable JSON packet containing member and adjacent nodes, typed internal/cross
edges, status, source refs and provenance. The structural layer filters describe
only the current map, not what exists in the world.

For local dynamic workspaces, GET /api/projects/{id}/nodes/{node_id}/trace?depth=4
returns the same read-only trace. The static public preview precomputes depth-4 traces
for its approved public data and does not permit writes or private uploads.
