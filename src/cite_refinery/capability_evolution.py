"""Read-only, provenance-aware comparison of two private project revisions.

Snapshots are chronological workspace states, not population/time-matched
experiments. We describe graph deltas and source-attested episodes, never
infer scientific improvement, adoption, deployment, or solved problems.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

SCHEMA = "cite_refinery.capability_evolution.v1"
BUCKETS = ("semantic_clusters", "semantic_nodes", "semantic_edges", "semantic_packets")
PRIMARY = ("practical", "academic", "program")
VALID_STATES = {"asserted", "qualified", "candidate", "unresolved", "not_established"}
EVIDENCE_KINDS = {"capability", "implementation", "outcome", "limitation", "requirement", "comparison", "event"}


def _canonical(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(v: Any) -> str:
    return hashlib.sha256(_canonical(v).encode("utf-8")).hexdigest()


def _owned(state: dict[str, Any], project: str, bucket: str) -> dict[str, dict]:
    raw = state.get(bucket) or {}
    if not isinstance(raw, dict):
        raise ValueError("semantic bucket must be keyed object")
    return {k: v for k, v in raw.items()
            if isinstance(v, dict) and v.get("project_id") == project}


def _semantic(v: dict[str, Any]) -> dict[str, Any]:
    """Exclude formatting clocks; retain claim, citations, origin and statuses."""
    return {k: x for k, x in v.items()
            if k not in {"created_at", "updated_at"}}


def _lineage(node: dict[str, Any]) -> list[str]:
    """Typed source identities only: never group by fuzzy lexical similarity."""
    tokens = set()
    if node.get("layer") != "program":
        return []
    for p in node.get("provenance_receipts") or []:
        if not isinstance(p, dict):
            continue
        source = p.get("source_system")
        if source in {"repository_portfolio", "refinery", "refinery_history"}:
            if node.get("kind") == "repository" and p.get("repository"):
                tokens.add("repository:" + str(p["repository"]).lower())
            if node.get("kind") == "capability" and p.get("capability_key"):
                tokens.add("refinery-capability:" + str(p["capability_key"]))
            if node.get("kind") == "implementation" and p.get("implementation_key"):
                tokens.add("refinery-implementation:" + str(p["implementation_key"]))
            if node.get("kind") == "implementation" and p.get("upstream_repository") and p.get("upstream_revision"):
                tokens.add("pinned-implementation:" +
                           str(p["upstream_repository"]).lower() + "@" + str(p["upstream_revision"]))
    return sorted(tokens)


def compare_states(
    before: dict[str, Any], after: dict[str, Any], project_id: str, *,
    old_revision: int, new_revision: int,
    old_capture: str, new_capture: str,
) -> dict[str, Any]:
    if type(old_revision) is not int or type(new_revision) is not int or not 0 <= old_revision < new_revision:
        raise ValueError("two ascending project revisions are required")
    if project_id not in before.get("projects", {}) or project_id not in after.get("projects", {}):
        raise ValueError("both snapshots must contain the same project")
    old = {b: _owned(before, project_id, b) for b in BUCKETS}
    new = {b: _owned(after, project_id, b) for b in BUCKETS}
    if any(set(old[b]) - set(new[b]) for b in BUCKETS):
        # Append-only today; a future retraction needs a deliberate signed
        # tombstone event, not silent erasure interpreted as project decline.
        raise ValueError("historical record removal detected; explicit retraction contract required")

    added = {b: sorted(set(new[b]) - set(old[b])) for b in BUCKETS}
    changed = {b: [
        key for key in sorted(set(old[b]) & set(new[b]))
        if _sha(_semantic(old[b][key])) != _sha(_semantic(new[b][key]))
    ] for b in BUCKETS}
    new_nodes = [new["semantic_nodes"][nid] for nid in added["semantic_nodes"]]
    layer_counts = Counter(n.get("layer", "neutral") for n in new_nodes)
    kind_counts = Counter(n.get("kind", "concept") for n in new_nodes)
    added_qualifications = []
    for edge_id in changed["semantic_edges"]:
        start = old["semantic_edges"][edge_id]
        finish = new["semantic_edges"][edge_id]
        if start.get("status") != finish.get("status"):
            if start.get("status") not in VALID_STATES or finish.get("status") not in VALID_STATES:
                raise ValueError("unknown edge status in historical snapshot")
            added_qualifications.append({
                "edge_id": edge_id, "relation": finish.get("relation"),
                "old_status": start.get("status"),
                "new_status": finish.get("status"),
                "boundary": "Status changed in project graph; not independent truth validation",
            })
    # Counts do not indicate improved performance or real-world outcomes.
    new_outcomes = []
    for node in new_nodes:
        if node.get("layer") != "program" or node.get("kind") not in EVIDENCE_KINDS:
            continue
        receipts = node.get("provenance_receipts") or []
        scopes = []
        for p in receipts:
            if isinstance(p, dict):
                scopes.append({
                    "source_system": p.get("source_system"),
                    "source_commit": p.get("refinery_commit") or p.get("snapshot_commit") or p.get("commit"),
                    "recorded_decision": p.get("decision_code") or p.get("decision"),
                    "execution_ready": p.get("execution_ready"),
                    "limitation_probe_leaks": p.get("limitation_probe_leaks"),
                    "verification_scope": p.get("verification_scope") or p.get("boundary"),
                })
        new_outcomes.append({
            "node_id": node.get("id"), "kind": node.get("kind"),
            "statement": node.get("statement"),
            "source_refs": (node.get("source_refs") or [])[:8],
            "source_boundaries": scopes[:6],
        })
    # Cross-version identity is only a navigation hint, not identical test subjects.
    groups: dict[str, set[str]] = {}
    for node in new["semantic_nodes"].values():
        for token in _lineage(node):
            groups.setdefault(token, set()).add(str(node["id"]))
    longitudinal = [
        {"source_identity": key, "node_ids": sorted(ids),
         "boundary": "Shared explicit source identity; not evidence of comparable evaluation or quality improvement"}
        for key, ids in sorted(groups.items()) if len(ids) > 1
    ][:100]

    candidate = [new["semantic_edges"][key] for key in added["semantic_edges"]
                 if new["semantic_edges"][key].get("status") in {"candidate", "unresolved", "not_established"}]
    materialized = [new["semantic_edges"][key] for key in added["semantic_edges"]
                    if new["semantic_edges"][key].get("status") in {"qualified", "asserted"}]
    return {
        "schema": SCHEMA, "project_id": project_id,
        "before": {"snapshot_id": old_capture, "revision": old_revision, "state_digest": _sha(before)},
        "after": {"snapshot_id": new_capture, "revision": new_revision, "state_digest": _sha(after)},
        "record_delta": {b: {"added": len(added[b]), "revised_existing": len(changed[b])} for b in BUCKETS},
        "new_node_layers": dict(sorted(layer_counts.items())),
        "new_node_kinds": dict(sorted(kind_counts.items())),
        "new_asserted_or_qualified_edges": len(materialized),
        "new_candidate_or_unresolved_edges": len(candidate),
        "edge_status_transitions": added_qualifications,
        "new_program_evidence": new_outcomes[:80],
        "same_source_identity_groups": longitudinal,
        "interpretation": {
            "unit": "two private workspace graph revisions, not two scientific study cohorts",
            "comparability": "not_established",
            "performance_improvement_estimate": None,
            "market_adoption_estimate": None,
            "production_readiness_estimate": None,
            "warnings": [
                "New evidence or newly represented Program nodes are not proof of higher quality.",
                "Changes in project repository commit histories are not popularity or adoption trends.",
                "Reported test pass counts from different contracts are not directly comparable.",
                "Candidate links remain unverified, even when one endpoint gains new source evidence.",
                "Missing or newly discovered limitations must not be interpreted as clearance.",
            ],
        },
    }
