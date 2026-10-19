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
