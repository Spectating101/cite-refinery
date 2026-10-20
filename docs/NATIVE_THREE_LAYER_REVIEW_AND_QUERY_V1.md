# Native three-layer safety and bidirectional investigation — 21 October 2026

## Problem addressed

Cite–Refinery's three-layer read-only atlas had evidence-normalized Practical, Academic and Implementation nodes but had not yet entered the real project-scoped native SemanticGraph. The native graph also allowed a repeat `add_edge` call to overwrite an existing edge status. That could silently turn candidate material into qualified evidence (or downgrade evidence), even though the separate packet review flow already computed changed-status warnings.

This branch fixes that narrow integrity flaw and provides controlled bridge-in and reverse navigation. The system remains one conceptual graph with **three layers**. `program` is the native persistence label used for Implementations; neutral source records are metadata/provenance, not a fourth conceptual layer.

## What is implemented

**1. Existing-edge status guard.** The native `SemanticGraph.add_edge` no longer overwrites any existing relation's status on a repeat call. Same-status idempotent writes still work. A staged in-memory preview can model proposed transitions, but direct persistent mutation cannot bypass approval by calling `add_edge`.

**2. Explicit status-change review.** `preview_packet` returns exact `changed_existing_edge_statuses` and a `status_change_requires_explicit_approval` flag. `ingest_packet` requires a matching previous state digest, the entire exact list of transitions, and a nontrivial operator rationale for changing any existing edge. The receipt records the reviewed state, transition list, rationale and packet digest. Graph-review CLI requires both digests and, on transitions, `--approve-status-changes --approval-reason '...'`. This is a locally explicit operator acknowledgement—not cryptographically verified human identity, RBAC, or multi-writer database authorization.

**3. Candidate-only native atlas packet exporter.** The new `cite-refinery-three-layer-native-packet` CLI prepares a standard `semantic_graph.v1` packet from the unified atlas. It maps conceptual Practical, Academic, and Implementation into native `practical`, `academic`, and `program` respectively. Every node and relationship stays tagged `source_lead_only` and `not_an_evidence_claim`. Relations are only `candidate` or (for wrong fits) `not_established`; claims about validated revenue or performance make export fail. Export never changes the workspace.

**4. Hosted role-bound approval.** The private SQLite queue also now requires explicit approval when an existing relation's status would change. A tenant owner must supply the exact reviewed transition set and a rationale at enqueue time. That approval is durably attached to the queued job, verified again by the worker inside a SQLite transaction, and logged as an audit event on success. Tenant editors can continue to ingest new candidate-only records without a status-change approval. Existing SQLite databases gain the new approval column on opening.

**5. Native project-scoped bidirectional navigation.** `graph-investigate --workspace PATH PROJECT_ID NODE_ID --depth 2` reads the persisted SemanticGraph from either an implementation or practical node, follows **existing** edges in either direction, and groups reachable nodes by the three conceptual layers. Assertions without review and explicitly `not_established` relations are returned separately as blocked edges, not traversed as semantic fits. Neutral document/source nodes cannot become academic claims merely through adjacency. Depth is capped and project boundaries enforced.

## Substantive local test

An isolated temporary workspace was initialized with a real Cite–Refinery project. The 50-node typed atlas was converted into a native candidate-only packet, previewed without side effects, then committed with the existing digest-bound ingest mechanism. It could then answer BOTH:

- Battery recycling problem → proposed economic mechanism → LFP recycling analysis candidate.
- LFP recycling analysis repo → the proposed scientific mechanism → the related battery recycling problem.

Candidate status, source references, project isolation and unknown outcomes remain explicit. A separate negative test blocks `asserted` and `not_established` edges and refuses cross-project queries.

Other tests demonstrate that direct status overwrites fail; a packet transition without exact approval fails without touching disk; a stale preview fails; an explicitly acknowledged transition is recorded in a receipt.

## Important remaining limits

This is a controlled native storage **import path**, not an automatic migration of historical projects or a hosted multi-user production deployment. The existing store is a local JSON store; it is not a transaction database across unrelated writers. New qualified edges created through legacy ingestion paths are not yet subject to independent source-entailment review, and same-status evidence additions still need an explicit provenance approval policy. These concerns require a wider source-authority and authorization gate.

The original research corpora and the sealed holdout are unchanged. No third-party code is deployed; a three-layer path still is not scientific, technical or economic validation. No business is selected or contacted.

## Reproduction

    PYTHONPATH=src python -m cite_refinery.three_layer_native_ingest \
      --atlas research_materials/opportunity_atlas/three_layer_unified_atlas.json \
      --project-id EXISTING_PROJECT_ID --output /tmp/three_layer_candidate_packet.json

    PYTHONPATH=src python -m cite_refinery.layered_cli graph-review \
      --workspace LOCAL_WORKSPACE EXISTING_PROJECT_ID \
      --input /tmp/three_layer_candidate_packet.json

Review the displayed state and packet digests, then apply with `--apply --expected-state-digest ... --expected-packet-digest ...`. Existing-edge transitions also require exact explicit approval flags/rationale. Query a stored node:

    PYTHONPATH=src python -m cite_refinery.layered_cli graph-investigate \
      --workspace LOCAL_WORKSPACE EXISTING_PROJECT_ID NATIVE_NODE_ID --depth 2

The code remains stacked on PR #77 in a separate draft branch.
