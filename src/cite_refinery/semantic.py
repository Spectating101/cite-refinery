from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from collections import Counter, deque
from typing import Any, Iterable

from .models import machine_id, utcnow


SEMANTIC_PACKET_SCHEMA = "cite_refinery.semantic_graph.v1"
SEMANTIC_GRAPH_VERSION = 1

LAYERS = {"practical", "academic", "program", "neutral"}
EDGE_STATES = {"asserted", "qualified", "candidate", "unresolved", "not_established"}

# These are intentionally broad. The graph is semantic and extensible: callers may
# use additional snake-case node kinds and UPPER_SNAKE_CASE relations as long as
# they pass the lexical guards below.
NODE_KINDS = {
    "problem_claim",
    "observation",
    "academic_claim",
    "mechanism",
    "method",
    "dataset",
    "metric",
    "intervention",
    "program",
    "capability",
    "implementation",
    "repository",
    "institution",
    "outcome",
    "limitation",
    "requirement",
    "research_question",
    "source",
    "event",
    "population",
    "policy",
    "concept",
}

RELATIONS = {
    "SUPPORTS",
    "CONTRADICTS",
    "QUALIFIES",
    "OBSERVES",
    "OBSERVED_BY",
    "CONTEXT_FOR",
    "EXPLAINS",
    "CAUSES",
    "EXACERBATES",
    "MEASURES",
    "MEASURED_BY",
    "ESTIMATES",
    "ESTIMATED_BY",
    "REQUIRES",
    "PROVIDES_DATA_FOR",
    "ADDRESSES",
    "PARTIALLY_ADDRESSES",
    "IMPLEMENTS",
    "IMPLEMENTED_BY",
    "DEPLOYED_BY",
    "LIMITED_BY",
    "FAILS_WHEN",
    "PRODUCES",
    "EVALUATED_BY",
    "ADAPTABLE_TO",
    "TRANSITIONS_INTO",
    "DERIVED_FROM",
    "DEPENDS_ON",
    "ENABLES",
    "MISSING_LINK",
    "SAME_AS",
    "BROADER_THAN",
    "NARROWER_THAN",
    "RELATED_TO",
}

_NODE_KIND_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_RELATION_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _normal_text(value: str) -> str:
    return " ".join(str(value).strip().split())


def _unique_strings(values: Iterable[Any]) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value).strip()})


def _merge_receipt(receipts: list[dict[str, Any]], receipt: dict[str, Any] | None) -> None:
    if not receipt:
        return
    canonical = _canonical_json(receipt)
    if all(_canonical_json(existing) != canonical for existing in receipts):
        receipts.append(dict(receipt))


def _validate_kind(kind: str) -> str:
    value = str(kind or "concept").strip().lower()
    if value not in NODE_KINDS and not _NODE_KIND_RE.fullmatch(value):
        raise ValueError(f"invalid semantic node kind: {kind!r}")
    return value


def _validate_layer(layer: str) -> str:
    value = str(layer or "neutral").strip().lower()
    if value not in LAYERS:
        raise ValueError(f"semantic layer must be one of {sorted(LAYERS)}")
    return value


def _validate_relation(relation: str) -> str:
    value = str(relation or "").strip().upper()
    if value not in RELATIONS and not _RELATION_RE.fullmatch(value):
        raise ValueError(f"invalid semantic relation: {relation!r}")
    return value


def _validate_state(status: str) -> str:
    value = str(status or "asserted").strip().lower()
    if value not in EDGE_STATES:
        raise ValueError(f"semantic edge status must be one of {sorted(EDGE_STATES)}")
    return value


class _StagedStore:
    """In-memory store used to fully apply and validate a packet before writing."""

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = deepcopy(state)

    def load(self) -> dict[str, Any]:
        return deepcopy(self.state)

    def save(self, state: dict[str, Any]) -> None:
        self.state = deepcopy(state)


class SemanticGraph:
    """Typed, provenance-preserving semantic graph over one Cite-Refinery store.

    Coverage is deliberately structural, not numerical. It reports which practical,
    academic and program neighborhoods are populated around a node, which relations
    qualify or contradict it, and where requested semantic paths break.
    """

    def __init__(self, store: Any) -> None:
        self.store = store

    @staticmethod
    def _project(state: dict[str, Any], project_id: str) -> dict[str, Any]:
        project = state.get("projects", {}).get(project_id)
        if project is None:
            raise KeyError(f"unknown project: {project_id}")
        return project

    @staticmethod
    def _project_nodes(state: dict[str, Any], project_id: str) -> dict[str, dict[str, Any]]:
        return {
            node_id: node
            for node_id, node in state.get("semantic_nodes", {}).items()
            if node.get("project_id") == project_id
        }

    @staticmethod
    def _project_edges(state: dict[str, Any], project_id: str) -> dict[str, dict[str, Any]]:
        return {
            edge_id: edge
            for edge_id, edge in state.get("semantic_edges", {}).items()
            if edge.get("project_id") == project_id
        }

    def add_cluster(
        self,
        project_id: str,
        title: str,
        *,
        parent_cluster_id: str | None = None,
        tags: list[str] | None = None,
        provenance: dict[str, Any] | None = None,
        external_key: str | None = None,
    ) -> dict[str, Any]:
        title_value = _normal_text(title)
        if not title_value:
            raise ValueError("semantic cluster title may not be empty")
        state = self.store.load()
        self._project(state, project_id)
        if parent_cluster_id:
            parent = state.get("semantic_clusters", {}).get(parent_cluster_id)
            if parent is None or parent.get("project_id") != project_id:
                raise ValueError("parent semantic cluster does not belong to project")

        fingerprint = _digest({
            "project_id": project_id,
            "title": title_value.casefold(),
            "parent_cluster_id": parent_cluster_id,
            "external_key": str(external_key or ""),
        })
        for cluster in state.get("semantic_clusters", {}).values():
            if cluster.get("project_id") == project_id and cluster.get("fingerprint") == fingerprint:
                cluster["tags"] = _unique_strings([*cluster.get("tags", []), *(tags or [])])
                _merge_receipt(cluster.setdefault("provenance_receipts", []), provenance)
                cluster["updated_at"] = utcnow()
                self.store.save(state)
                return dict(cluster)

        cluster_id = machine_id("sgcluster")
        cluster = {
            "id": cluster_id,
            "project_id": project_id,
            "title": title_value,
            "parent_cluster_id": parent_cluster_id,
            "tags": _unique_strings(tags or []),
            "external_key": external_key,
            "fingerprint": fingerprint,
            "provenance_receipts": [dict(provenance)] if provenance else [],
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        state.setdefault("semantic_clusters", {})[cluster_id] = cluster
        self.store.save(state)
        return dict(cluster)

    def add_node(
        self,
        project_id: str,
        statement: str,
        *,
        kind: str = "concept",
        layer: str = "neutral",
        aliases: list[str] | None = None,
        tags: list[str] | None = None,
        cluster_ids: list[str] | None = None,
        source_refs: list[str] | None = None,
        provenance: dict[str, Any] | None = None,
        external_key: str | None = None,
    ) -> dict[str, Any]:
        statement_value = _normal_text(statement)
        if not statement_value:
            raise ValueError("semantic node statement may not be empty")
        if len(statement_value) > 10000:
            raise ValueError("semantic node statement may not exceed 10000 characters")
        kind_value = _validate_kind(kind)
        layer_value = _validate_layer(layer)

        state = self.store.load()
        self._project(state, project_id)
        requested_clusters = _unique_strings(cluster_ids or [])
        for cluster_id in requested_clusters:
            cluster = state.get("semantic_clusters", {}).get(cluster_id)
            if cluster is None or cluster.get("project_id") != project_id:
                raise ValueError(f"semantic cluster does not belong to project: {cluster_id}")

        fingerprint = _digest({
            "project_id": project_id,
            "kind": kind_value,
            "layer": layer_value,
            "statement": statement_value.casefold(),
            "external_key": str(external_key or ""),
        })
        for node in state.get("semantic_nodes", {}).values():
            if node.get("project_id") == project_id and node.get("fingerprint") == fingerprint:
                node["aliases"] = _unique_strings([*node.get("aliases", []), *(aliases or [])])
                node["tags"] = _unique_strings([*node.get("tags", []), *(tags or [])])
                node["cluster_ids"] = _unique_strings([*node.get("cluster_ids", []), *requested_clusters])
                node["source_refs"] = _unique_strings([*node.get("source_refs", []), *(source_refs or [])])
                _merge_receipt(node.setdefault("provenance_receipts", []), provenance)
                node["updated_at"] = utcnow()
                self.store.save(state)
                return dict(node)

        node_id = machine_id("sgnode")
        node = {
            "id": node_id,
            "project_id": project_id,
            "statement": statement_value,
            "kind": kind_value,
            "layer": layer_value,
            "aliases": _unique_strings(aliases or []),
            "tags": _unique_strings(tags or []),
            "cluster_ids": requested_clusters,
            "source_refs": _unique_strings(source_refs or []),
            "external_key": external_key,
            "fingerprint": fingerprint,
            "provenance_receipts": [dict(provenance)] if provenance else [],
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        state.setdefault("semantic_nodes", {})[node_id] = node
        self.store.save(state)
        return dict(node)

    def add_edge(
        self,
        project_id: str,
        source_id: str,
        relation: str,
        target_id: str,
        *,
        status: str = "asserted",
        evidence_refs: list[str] | None = None,
        tags: list[str] | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        relation_value = _validate_relation(relation)
        status_value = _validate_state(status)
        state = self.store.load()
        self._project(state, project_id)
        nodes = self._project_nodes(state, project_id)
        if source_id not in nodes:
            raise ValueError(f"unknown semantic source node for project: {source_id}")
        if target_id not in nodes:
            raise ValueError(f"unknown semantic target node for project: {target_id}")
        if source_id == target_id and relation_value not in {"SAME_AS", "RELATED_TO"}:
            raise ValueError("semantic self-edges are only allowed for SAME_AS/RELATED_TO")

        fingerprint = _digest({
            "project_id": project_id,
            "source_id": source_id,
            "relation": relation_value,
            "target_id": target_id,
        })
        for edge in state.get("semantic_edges", {}).values():
            if edge.get("project_id") == project_id and edge.get("fingerprint") == fingerprint:
                edge["status"] = status_value
                edge["evidence_refs"] = _unique_strings([*edge.get("evidence_refs", []), *(evidence_refs or [])])
                edge["tags"] = _unique_strings([*edge.get("tags", []), *(tags or [])])
                _merge_receipt(edge.setdefault("provenance_receipts", []), provenance)
                edge["updated_at"] = utcnow()
                self.store.save(state)
                return dict(edge)

        edge_id = machine_id("sgedge")
        edge = {
            "id": edge_id,
            "project_id": project_id,
            "source_id": source_id,
            "relation": relation_value,
            "target_id": target_id,
            "status": status_value,
            "evidence_refs": _unique_strings(evidence_refs or []),
            "tags": _unique_strings(tags or []),
            "fingerprint": fingerprint,
            "provenance_receipts": [dict(provenance)] if provenance else [],
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        state.setdefault("semantic_edges", {})[edge_id] = edge
        self.store.save(state)
        return dict(edge)

    def _stage_packet(
        self,
        project_id: str,
        packet: dict[str, Any],
        packet_ref: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        current = self.store.load()
        staged_store = _StagedStore(current)
        receipt = SemanticGraph(staged_store)._ingest_packet_unchecked(
            project_id, packet, packet_ref=packet_ref
        )
        return current, staged_store.load(), receipt

    def preview_packet(
        self,
        project_id: str,
        packet: dict[str, Any],
        *,
        packet_ref: str | None = None,
    ) -> dict[str, Any]:
        """Validate the *entire* semantic packet without mutating persisted state."""
        current, proposed, receipt = self._stage_packet(project_id, packet, packet_ref)
        buckets = ("semantic_clusters", "semantic_nodes", "semantic_edges", "semantic_packets")
        delta = {
            bucket: len(set(proposed[bucket]) - set(current[bucket]))
            for bucket in buckets
        }
        created_ids = set(proposed["semantic_edges"]) - set(current["semantic_edges"])
        statuses = Counter(
            proposed["semantic_edges"][key]["status"]
            for key in created_ids
        )
        status_changes = []
        for key in sorted(set(current["semantic_edges"]) & set(proposed["semantic_edges"])):
            before = current["semantic_edges"][key].get("status")
            after = proposed["semantic_edges"][key].get("status")
            if before != after:
                status_changes.append({"edge_id": key, "from": before, "to": after})
        source_label = str(packet.get("source_system") or "").strip().casefold()
        authority = {
            "nocturnal": "practical",
            "nocturnal-oversight": "practical",
            "cite": "academic",
            "cite-agent": "academic",
            "refinery": "program",
        }.get(source_label)
        declared_layers = Counter(
            str(node.get("layer") or "neutral").strip().lower()
            for node in packet.get("nodes", []) or []
        )
        boundary_warnings = []
        if authority:
            unexpected = sorted(layer for layer in declared_layers
                                if layer not in {authority, "neutral"})
            if unexpected:
                boundary_warnings.append(
                    f"{source_label} packet proposes nodes outside its {authority} authority: "
                    + ", ".join(unexpected) + "; review original sources and provenance"
                )
        if status_changes:
            boundary_warnings.append(
                "Import would change existing edge statuses; inspect every transition "
                "before approving the packet"
            )
        return {
            "declared_node_layers": dict(sorted(declared_layers.items())),
            "authority_boundary_warnings": boundary_warnings,
            "changed_existing_edge_statuses": status_changes,
            "schema": "cite_refinery.semantic_ingest_preview.v1",
            "project_id": project_id,
            "packet_digest": _digest(packet),
            "state_digest": _digest(current),
            "source_system": packet.get("source_system"),
            "already_imported": bool(receipt["id"] in current["semantic_packets"]),
            "projected_new_records": delta,
            "new_relation_statuses": dict(sorted(statuses.items())),
            "boundary": (
                "Preview validates structure and local graph consistency, not evidence truth, "
                "source authority, causal validity, or suitability for public release."
            ),
        }

    def ingest_packet(
        self,
        project_id: str,
        packet: dict[str, Any],
        *,
        packet_ref: str | None = None,
        expected_state_digest: str | None = None,
    ) -> dict[str, Any]:
        """Commit only a completely valid packet in one state write.

        Optimistic digest guards explicitly reviewed imports. This local JSON
        store is not a multi-writer transaction database: other write entrypoints
        do not coordinate on locks; hosted operation needs a proper DB transaction.
        """
        current, proposed, receipt = self._stage_packet(project_id, packet, packet_ref)
        if expected_state_digest is not None and _digest(current) != expected_state_digest:
            raise ValueError("workspace state changed after review; preview again")
        if proposed != current:
            # Check once more before the single commit; prevents common stale previews.
            if _digest(self.store.load()) != _digest(current):
                raise ValueError("workspace state changed during ingestion; retry")
            self.store.save(proposed)
        return receipt

    def _ingest_packet_unchecked(
        self,
        project_id: str,
        packet: dict[str, Any],
        *,
        packet_ref: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(packet, dict):
            raise ValueError("semantic packet must be a JSON object")
        if packet.get("schema") != SEMANTIC_PACKET_SCHEMA:
            raise ValueError(f"semantic packet schema must be {SEMANTIC_PACKET_SCHEMA}")
        packet_project = packet.get("project_id")
        if packet_project and str(packet_project) != project_id:
            raise ValueError("semantic packet project_id does not match target project")
        source_system = _normal_text(str(packet.get("source_system") or ""))
        if not source_system:
            raise ValueError("semantic packet requires source_system")

        state = self.store.load()
        self._project(state, project_id)
        digest = _digest(packet)
        receipt_id = f"sgpacket:{_digest({'project_id': project_id, 'packet_digest': digest})[:16]}"
        existing = state.get("semantic_packets", {}).get(receipt_id)
        if existing is not None:
            return dict(existing)

        key_to_cluster: dict[str, str] = {}
        for raw in packet.get("clusters", []) or []:
            if not isinstance(raw, dict):
                raise ValueError("semantic packet clusters must be objects")
            key = _normal_text(str(raw.get("key") or ""))
            if not key or key in key_to_cluster:
                raise ValueError("semantic packet cluster keys must be unique and non-empty")
            parent_ref = raw.get("parent")
            parent_id = key_to_cluster.get(str(parent_ref), str(parent_ref)) if parent_ref else None
            provenance = {
                "source_system": source_system,
                "packet_ref": packet_ref,
                "packet_digest": digest,
                "external_key": key,
                **dict(raw.get("provenance") or {}),
            }
            cluster = self.add_cluster(
                project_id,
                str(raw.get("title") or ""),
                parent_cluster_id=parent_id,
                tags=list(raw.get("tags") or []),
                provenance=provenance,
                external_key=key,
            )
            key_to_cluster[key] = cluster["id"]

        key_to_node: dict[str, str] = {}
        nodes_created: list[str] = []
        for raw in packet.get("nodes", []) or []:
            if not isinstance(raw, dict):
                raise ValueError("semantic packet nodes must be objects")
            key = _normal_text(str(raw.get("key") or ""))
            if not key or key in key_to_node:
                raise ValueError("semantic packet node keys must be unique and non-empty")
            raw_clusters = list(raw.get("clusters") or [])
            cluster_ids = [key_to_cluster.get(str(value), str(value)) for value in raw_clusters]
            provenance = {
                "source_system": source_system,
                "packet_ref": packet_ref,
                "packet_digest": digest,
                "external_key": key,
                **dict(raw.get("provenance") or {}),
            }
            node = self.add_node(
                project_id,
                str(raw.get("statement") or ""),
                kind=str(raw.get("kind") or "concept"),
                layer=str(raw.get("layer") or "neutral"),
                aliases=list(raw.get("aliases") or []),
                tags=list(raw.get("tags") or []),
                cluster_ids=cluster_ids,
                source_refs=list(raw.get("source_refs") or []),
                provenance=provenance,
                external_key=f"{source_system}:{key}",
            )
            key_to_node[key] = node["id"]
            nodes_created.append(node["id"])

        edges_created: list[str] = []
        for raw in packet.get("edges", []) or []:
            if not isinstance(raw, dict):
                raise ValueError("semantic packet edges must be objects")
            source_ref = str(raw.get("source") or "")
            target_ref = str(raw.get("target") or "")
            source_id = key_to_node.get(source_ref, source_ref)
            target_id = key_to_node.get(target_ref, target_ref)
            provenance = {
                "source_system": source_system,
                "packet_ref": packet_ref,
                "packet_digest": digest,
                **dict(raw.get("provenance") or {}),
            }
            edge = self.add_edge(
                project_id,
                source_id,
                str(raw.get("relation") or ""),
                target_id,
                status=str(raw.get("status") or "asserted"),
                evidence_refs=list(raw.get("evidence_refs") or []),
                tags=list(raw.get("tags") or []),
                provenance=provenance,
            )
            edges_created.append(edge["id"])

        # add_node/add_edge reload and save independently, so reload before storing
        # the packet receipt to avoid overwriting those writes with stale state.
        state = self.store.load()
        receipt = {
            "id": receipt_id,
            "schema": SEMANTIC_PACKET_SCHEMA,
            "graph_version": SEMANTIC_GRAPH_VERSION,
            "project_id": project_id,
            "source_system": source_system,
            "packet_ref": packet_ref,
            "packet_digest": digest,
            "cluster_ids": list(key_to_cluster.values()),
            "node_ids": nodes_created,
            "edge_ids": edges_created,
            "created_at": utcnow(),
        }
        state.setdefault("semantic_packets", {})[receipt_id] = receipt
        self.store.save(state)
        return dict(receipt)

    def bootstrap_project_records(self, project_id: str) -> dict[str, Any]:
        """Expose existing lifecycle records as graph nodes without inventing claims.

        This bootstrap deliberately uses only structurally safe relations. It does not
        infer that an observation supports a claim, that literature proves a mechanism,
        or that a capability solves a requirement.
        """

        state = self.store.load()
        project = self._project(state, project_id)
        root = self.add_node(
            project_id,
            str(project.get("problem") or project.get("title") or "Project problem"),
            kind="problem_claim",
            layer="neutral",
            tags=["project_root"],
            source_refs=[f"project:{project_id}"],
            provenance={"source_system": "cite-refinery", "record_type": "project", "record_id": project_id},
            external_key=f"project:{project_id}",
        )

        counts = {"observations": 0, "requirements": 0, "capabilities": 0, "implementations": 0}
        for record in state.get("problem_observations", {}).values():
            if record.get("project_id") != project_id:
                continue
            node = self.add_node(
                project_id,
                str(record.get("text") or ""),
                kind="observation",
                layer="practical",
                tags=[str(record.get("frame") or "")] if record.get("frame") else [],
                source_refs=[f"problem_observation:{record.get('id')}", *list(record.get("sources") or [])],
                provenance={
                    "source_system": str(record.get("source_system") or "unknown"),
                    "record_type": "problem_observation",
                    "record_id": record.get("id"),
                    "external_id": record.get("external_id"),
                },
                external_key=f"problem_observation:{record.get('id')}",
            )
            self.add_edge(
                project_id,
                node["id"],
                "CONTEXT_FOR",
                root["id"],
                provenance={"source_system": "cite-refinery", "boundary": "context_only_not_support"},
            )
            counts["observations"] += 1

        for record in state.get("requirements", {}).values():
            if record.get("project_id") != project_id:
                continue
            self.add_node(
                project_id,
                str(record.get("text") or ""),
                kind="requirement",
                layer="neutral",
                tags=list(record.get("tags") or []),
                source_refs=[f"requirement:{record.get('id')}"],
                provenance={"source_system": "cite-refinery", "record_type": "requirement", "record_id": record.get("id")},
                external_key=f"requirement:{record.get('id')}",
            )
            counts["requirements"] += 1

        capability_nodes: dict[str, str] = {}
        for record in state.get("capabilities", {}).values():
            if record.get("scope") == "project" and record.get("project_id") != project_id:
                continue
            if record.get("project_id") not in {None, project_id}:
                continue
            statement = str(record.get("description") or record.get("name") or "")
            node = self.add_node(
                project_id,
                statement,
                kind="capability",
                layer="program",
                tags=[str(record.get("name") or ""), *list(record.get("tags") or [])],
                source_refs=[f"capability:{record.get('id')}"],
                provenance={"source_system": "refinery", "record_type": "capability", "record_id": record.get("id")},
                external_key=f"capability:{record.get('id')}",
            )
            capability_nodes[str(record.get("id"))] = node["id"]
            counts["capabilities"] += 1

        for record in state.get("implementations", {}).values():
            if record.get("project_id") not in {None, project_id}:
                continue
            capability_id = str(record.get("capability_id") or "")
            if capability_id not in capability_nodes:
                continue
            node = self.add_node(
                project_id,
                f"{record.get('provider') or 'implementation'} implementation of {capability_id}",
                kind="implementation",
                layer="program",
                tags=[str(record.get("provider") or "")],
                source_refs=[f"implementation:{record.get('id')}"],
                provenance={"source_system": "refinery", "record_type": "implementation", "record_id": record.get("id")},
                external_key=f"implementation:{record.get('id')}",
            )
            self.add_edge(
                project_id,
                node["id"],
                "IMPLEMENTS",
                capability_nodes[capability_id],
                provenance={"source_system": "refinery", "record_type": "implementation_binding"},
            )
            counts["implementations"] += 1

        return {"project_id": project_id, "root_node_id": root["id"], "materialized": counts}

    def neighborhood(self, project_id: str, node_id: str, *, depth: int = 1) -> dict[str, Any]:
        if not 0 <= int(depth) <= 8:
            raise ValueError("semantic neighborhood depth must be between 0 and 8")
        state = self.store.load()
        self._project(state, project_id)
        nodes = self._project_nodes(state, project_id)
        edges = self._project_edges(state, project_id)
        if node_id not in nodes:
            raise ValueError("semantic node does not belong to project")

        visited = {node_id}
        frontier = deque([(node_id, 0)])
        edge_ids: set[str] = set()
        while frontier:
            current, current_depth = frontier.popleft()
            if current_depth >= int(depth):
                continue
            for edge_id, edge in edges.items():
                other: str | None = None
                if edge.get("source_id") == current:
                    other = str(edge.get("target_id"))
                elif edge.get("target_id") == current:
                    other = str(edge.get("source_id"))
                if other is None:
                    continue
                edge_ids.add(edge_id)
                if other not in visited:
                    visited.add(other)
                    frontier.append((other, current_depth + 1))

        selected_nodes = [nodes[value] for value in sorted(visited)]
        selected_edges = [edges[value] for value in sorted(edge_ids)]
        return {
            "project_id": project_id,
            "anchor_node_id": node_id,
            "depth": int(depth),
            "nodes": selected_nodes,
            "edges": selected_edges,
        }

    def coverage(self, project_id: str, node_id: str, *, depth: int = 1) -> dict[str, Any]:
        graph = self.neighborhood(project_id, node_id, depth=depth)
        anchor = next(node for node in graph["nodes"] if node["id"] == node_id)
        layer_nodes: dict[str, list[dict[str, Any]]] = {"practical": [], "academic": [], "program": []}
        for node in graph["nodes"]:
            layer = node.get("layer")
            if layer in layer_nodes:
                layer_nodes[layer].append(node)

        presence = {layer: bool(items) for layer, items in layer_nodes.items()}
        signature = self._coverage_signature(presence)
        contradictions = [
            edge for edge in graph["edges"]
            if edge.get("relation") == "CONTRADICTS"
        ]
        qualifications = [
            edge for edge in graph["edges"]
            if edge.get("relation") in {"QUALIFIES", "LIMITED_BY", "FAILS_WHEN"}
            or edge.get("status") == "qualified"
        ]
        unresolved = [
            edge for edge in graph["edges"]
            if edge.get("relation") == "MISSING_LINK"
            or edge.get("status") in {"candidate", "unresolved", "not_established"}
        ]
        relation_groups: dict[str, list[dict[str, Any]]] = {}
        for edge in graph["edges"]:
            relation_groups.setdefault(str(edge.get("relation")), []).append(edge)

        return {
            "project_id": project_id,
            "node": anchor,
            "depth": int(depth),
            "layer_presence": presence,
            "intersection": signature,
            "layers": layer_nodes,
            "relations": relation_groups,
            "contradictions": contradictions,
            "qualifications": qualifications,
            "unresolved_or_missing": unresolved,
            "boundary": (
                "Coverage is structural and semantic, not a score. Presence means that at least one node from the layer "
                "is connected within the requested neighborhood; it does not by itself establish truth, adequacy, or causality."
            ),
        }

    @staticmethod
    def _coverage_signature(presence: dict[str, bool]) -> str:
        p = bool(presence.get("practical"))
        a = bool(presence.get("academic"))
        s = bool(presence.get("program"))
        if p and a and s:
            return "practical_academic_program"
        if p and a:
            return "practical_academic_no_program"
        if p and s:
            return "practical_program_no_academic"
        if a and s:
            return "academic_program_no_practical"
        if p:
            return "practical_only"
        if a:
            return "academic_only"
        if s:
            return "program_only"
        return "no_layer_connected"

    def query_coverage(
        self,
        project_id: str,
        *,
        present: list[str] | None = None,
        absent: list[str] | None = None,
        kind: str | None = None,
        cluster_id: str | None = None,
        depth: int = 1,
    ) -> dict[str, Any]:
        requested_present = {_validate_layer(value) for value in (present or [])}
        requested_absent = {_validate_layer(value) for value in (absent or [])}
        requested_present.discard("neutral")
        requested_absent.discard("neutral")
        overlap = requested_present & requested_absent
        if overlap:
            raise ValueError(f"semantic layers cannot be both present and absent: {sorted(overlap)}")
        kind_value = _validate_kind(kind) if kind else None

        state = self.store.load()
        self._project(state, project_id)
        matches: list[dict[str, Any]] = []
        for node in self._project_nodes(state, project_id).values():
            if kind_value and node.get("kind") != kind_value:
                continue
            if cluster_id and cluster_id not in node.get("cluster_ids", []):
                continue
            report = self.coverage(project_id, node["id"], depth=depth)
            presence = report["layer_presence"]
            if any(not presence.get(layer, False) for layer in requested_present):
                continue
            if any(presence.get(layer, False) for layer in requested_absent):
                continue
            matches.append({
                "node": node,
                "intersection": report["intersection"],
                "layer_presence": presence,
                "contradiction_count": len(report["contradictions"]),
                "unresolved_or_missing_count": len(report["unresolved_or_missing"]),
            })
        return {
            "project_id": project_id,
            "present": sorted(requested_present),
            "absent": sorted(requested_absent),
            "kind": kind_value,
            "cluster_id": cluster_id,
            "matches": matches,
            "count": len(matches),
        }

    def trace_pattern(
        self,
        project_id: str,
        anchor_node_id: str,
        steps: list[dict[str, Any]],
        *,
        max_paths: int = 200,
    ) -> dict[str, Any]:
        if not 1 <= int(max_paths) <= 5000:
            raise ValueError("max_paths must be between 1 and 5000")
        if not isinstance(steps, list) or not steps:
            raise ValueError("semantic trace requires at least one step")
        if len(steps) > 12:
            raise ValueError("semantic trace supports at most 12 steps")

        state = self.store.load()
        self._project(state, project_id)
        nodes = self._project_nodes(state, project_id)
        edges = self._project_edges(state, project_id)
        if anchor_node_id not in nodes:
            raise ValueError("semantic anchor node does not belong to project")

        normalized_steps = [self._normalize_trace_step(step) for step in steps]
        paths: list[dict[str, Any]] = [{"node_ids": [anchor_node_id], "edge_ids": []}]
        breaks: list[dict[str, Any]] = []

        for step_index, step in enumerate(normalized_steps):
            next_paths: list[dict[str, Any]] = []
            for path in paths:
                current_id = path["node_ids"][-1]
                matched = self._matching_edges(current_id, step, nodes, edges)
                if not matched:
                    breaks.append({
                        "at_node_id": current_id,
                        "step_index": step_index,
                        "expected": step,
                        "path": dict(path),
                    })
                    continue
                for edge, target_id in matched:
                    if len(next_paths) >= int(max_paths):
                        break
                    next_paths.append({
                        "node_ids": [*path["node_ids"], target_id],
                        "edge_ids": [*path["edge_ids"], edge["id"]],
                    })
            paths = next_paths
            if not paths:
                break

        completed = [
            {
                "node_ids": path["node_ids"],
                "edge_ids": path["edge_ids"],
                "nodes": [nodes[node_id] for node_id in path["node_ids"]],
                "edges": [edges[edge_id] for edge_id in path["edge_ids"]],
            }
            for path in paths
        ]
        return {
            "project_id": project_id,
            "anchor_node_id": anchor_node_id,
            "steps": normalized_steps,
            "completed_paths": completed,
            "breaks": breaks,
            "complete": bool(completed) and not breaks,
            "boundary": (
                "A break means the requested semantic path is not represented in the current graph. It is a candidate "
                "coverage gap, not proof that the relationship or implementation does not exist in the world."
            ),
        }

    @staticmethod
    def _normalize_trace_step(step: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(step, dict):
            raise ValueError("semantic trace steps must be objects")
        raw_relations = step.get("relations", step.get("relation", []))
        if isinstance(raw_relations, str):
            raw_relations = [raw_relations]
        relations = [_validate_relation(value) for value in (raw_relations or [])]
        raw_kinds = step.get("target_kinds", step.get("target_kind", []))
        if isinstance(raw_kinds, str):
            raw_kinds = [raw_kinds]
        target_kinds = [_validate_kind(value) for value in (raw_kinds or [])]
        raw_layers = step.get("target_layers", step.get("target_layer", []))
        if isinstance(raw_layers, str):
            raw_layers = [raw_layers]
        target_layers = [_validate_layer(value) for value in (raw_layers or [])]
        direction = str(step.get("direction") or "out").strip().lower()
        if direction not in {"out", "in", "either"}:
            raise ValueError("semantic trace direction must be out, in, or either")
        statuses = step.get("statuses", step.get("status", []))
        if isinstance(statuses, str):
            statuses = [statuses]
        normalized_statuses = [_validate_state(value) for value in (statuses or [])]
        return {
            "relations": relations,
            "target_kinds": target_kinds,
            "target_layers": target_layers,
            "direction": direction,
            "statuses": normalized_statuses,
        }

    @staticmethod
    def _matching_edges(
        current_id: str,
        step: dict[str, Any],
        nodes: dict[str, dict[str, Any]],
        edges: dict[str, dict[str, Any]],
    ) -> list[tuple[dict[str, Any], str]]:
        matched: list[tuple[dict[str, Any], str]] = []
        for edge in edges.values():
            target_id: str | None = None
            if step["direction"] in {"out", "either"} and edge.get("source_id") == current_id:
                target_id = str(edge.get("target_id"))
            elif step["direction"] in {"in", "either"} and edge.get("target_id") == current_id:
                target_id = str(edge.get("source_id"))
            if target_id is None or target_id not in nodes:
                continue
            target = nodes[target_id]
            if step["relations"] and edge.get("relation") not in step["relations"]:
                continue
            if step["target_kinds"] and target.get("kind") not in step["target_kinds"]:
                continue
            if step["target_layers"] and target.get("layer") not in step["target_layers"]:
                continue
            if step["statuses"] and edge.get("status") not in step["statuses"]:
                continue
            matched.append((edge, target_id))
        return matched

    def cluster_map(self, project_id: str) -> dict[str, Any]:
        state = self.store.load()
        self._project(state, project_id)
        nodes = self._project_nodes(state, project_id)
        clusters = [
            cluster for cluster in state.get("semantic_clusters", {}).values()
            if cluster.get("project_id") == project_id
        ]
        result = []
        for cluster in clusters:
            members = [node for node in nodes.values() if cluster["id"] in node.get("cluster_ids", [])]
            result.append({
                **cluster,
                "node_ids": [node["id"] for node in members],
                "layer_presence": {
                    layer: any(node.get("layer") == layer for node in members)
                    for layer in ("practical", "academic", "program")
                },
            })
        return {"project_id": project_id, "clusters": result, "count": len(result)}

    def export(self, project_id: str) -> dict[str, Any]:
        state = self.store.load()
        project = self._project(state, project_id)
        nodes = self._project_nodes(state, project_id)
        edges = self._project_edges(state, project_id)
        clusters = {
            cluster_id: cluster
            for cluster_id, cluster in state.get("semantic_clusters", {}).items()
            if cluster.get("project_id") == project_id
        }
        packets = {
            packet_id: packet
            for packet_id, packet in state.get("semantic_packets", {}).items()
            if packet.get("project_id") == project_id
        }
        return {
            "schema": "cite_refinery.semantic_graph_export.v1",
            "graph_version": SEMANTIC_GRAPH_VERSION,
            "project": project,
            "clusters": clusters,
            "nodes": nodes,
            "edges": edges,
            "packets": packets,
            "boundary": (
                "This export preserves asserted graph structure and provenance. Missing edges are unknown unless explicitly "
                "represented or surfaced by a trace/query; they are not proof of real-world absence."
            ),
        }
