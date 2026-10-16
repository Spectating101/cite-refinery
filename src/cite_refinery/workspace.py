from __future__ import annotations

from collections import Counter
from typing import Any

from .semantic import SemanticGraph


PRIMARY_LAYERS = ("practical", "academic", "program")


class ProductWorkspace:
    """Read-only product projection over Cite-Refinery state.

    The product center is a clustered semantic atlas. Each module is mapped across
    three independent evidence/supply families:

    - practical: empirical reality / Nocturnal-origin material
    - academic: scholarly knowledge / Cite-origin material
    - program: programs, repositories, capabilities and implementations / Refinery

    Lifecycle records remain available as supporting context, but they do not define
    the primary interface and they are never collapsed into one authority.
    """

    def __init__(self, store: Any) -> None:
        self.store = store
        self.graph = SemanticGraph(store)

    @staticmethod
    def _owned(state: dict[str, Any], bucket: str, project_id: str) -> list[dict[str, Any]]:
        return [
            item
            for item in state.get(bucket, {}).values()
            if isinstance(item, dict) and item.get("project_id") == project_id
        ]

    @staticmethod
    def _project_capabilities(state: dict[str, Any], project_id: str) -> list[dict[str, Any]]:
        return [
            item
            for item in state.get("capabilities", {}).values()
            if isinstance(item, dict) and item.get("project_id") == project_id
        ]

    @staticmethod
    def _project_implementations(
        state: dict[str, Any], project_id: str, capabilities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        capability_ids = {str(item.get("id")) for item in capabilities}
        return [
            item
            for item in state.get("implementations", {}).values()
            if isinstance(item, dict)
            and (
                item.get("project_id") == project_id
                or str(item.get("capability_id")) in capability_ids
            )
        ]

    @staticmethod
    def _candidate_count(solution_maps: list[dict[str, Any]]) -> tuple[int, Counter[str]]:
        count = 0
        authorities: Counter[str] = Counter()
        for solution_map in solution_maps:
            for result in (solution_map.get("results") or {}).values():
                if not isinstance(result, dict):
                    continue
                candidates = result.get("supply_candidates")
                if not isinstance(candidates, list):
                    candidates = result.get("canonical_candidates")
                if not isinstance(candidates, list):
                    candidates = []
                for candidate in candidates:
                    if not isinstance(candidate, dict):
                        continue
                    count += 1
                    authorities[str(candidate.get("authority") or "unspecified")] += 1
        return count, authorities

    @staticmethod
    def _graph_summary(graph_export: dict[str, Any]) -> dict[str, Any]:
        nodes = list((graph_export.get("nodes") or {}).values())
        edges = list((graph_export.get("edges") or {}).values())
        layers = Counter(str(node.get("layer") or "neutral") for node in nodes)
        kinds = Counter(str(node.get("kind") or "concept") for node in nodes)
        relations = Counter(str(edge.get("relation") or "RELATED_TO") for edge in edges)
        unresolved = [
            edge
            for edge in edges
            if edge.get("relation") == "MISSING_LINK"
            or edge.get("status") in {"candidate", "unresolved", "not_established"}
        ]
        contradictions = [edge for edge in edges if edge.get("relation") == "CONTRADICTS"]
        return {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "layer_counts": dict(sorted(layers.items())),
            "kind_counts": dict(sorted(kinds.items())),
            "relation_counts": dict(sorted(relations.items())),
            "unresolved_or_candidate_edges": len(unresolved),
            "contradiction_edges": len(contradictions),
        }

    @staticmethod
    def _intersection(layer_presence: dict[str, bool]) -> str:
        p = bool(layer_presence.get("practical"))
        a = bool(layer_presence.get("academic"))
        s = bool(layer_presence.get("program"))
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

    @classmethod
    def _cluster_atlas(cls, graph_export: dict[str, Any]) -> dict[str, Any]:
        nodes = dict(graph_export.get("nodes") or {})
        edges = dict(graph_export.get("edges") or {})
        raw_clusters = dict(graph_export.get("clusters") or {})

        membership: dict[str, set[str]] = {
            cluster_id: set() for cluster_id in raw_clusters
        }
        unclustered: set[str] = set()
        for node_id, node in nodes.items():
            cluster_ids = [
                str(value)
                for value in (node.get("cluster_ids") or [])
                if str(value) in raw_clusters
            ]
            if not cluster_ids:
                unclustered.add(str(node_id))
            for cluster_id in cluster_ids:
                membership.setdefault(cluster_id, set()).add(str(node_id))

        cluster_rows: list[dict[str, Any]] = []
        child_map: dict[str, list[str]] = {}
        for cluster_id, cluster in raw_clusters.items():
            parent = cluster.get("parent_cluster_id")
            if parent:
                child_map.setdefault(str(parent), []).append(str(cluster_id))

        def build_cluster(
            cluster_id: str,
            cluster: dict[str, Any],
            member_ids: set[str],
            *,
            synthetic: bool = False,
        ) -> dict[str, Any]:
            members = [nodes[node_id] for node_id in sorted(member_ids) if node_id in nodes]
            layers = {
                layer: [node for node in members if node.get("layer") == layer]
                for layer in PRIMARY_LAYERS
            }
            neutral_nodes = [node for node in members if node.get("layer") == "neutral"]
            presence = {layer: bool(layers[layer]) for layer in PRIMARY_LAYERS}
            missing_layers = [layer for layer in PRIMARY_LAYERS if not presence[layer]]

            internal_edges: list[dict[str, Any]] = []
            cross_edges: list[dict[str, Any]] = []
            for edge in edges.values():
                source_in = str(edge.get("source_id")) in member_ids
                target_in = str(edge.get("target_id")) in member_ids
                if source_in and target_in:
                    internal_edges.append(edge)
                elif source_in or target_in:
                    cross_edges.append(edge)

            relevant_edges = [*internal_edges, *cross_edges]
            relations = Counter(str(edge.get("relation") or "RELATED_TO") for edge in internal_edges)
            statuses = Counter(str(edge.get("status") or "asserted") for edge in relevant_edges)
            unresolved = [
                edge
                for edge in relevant_edges
                if edge.get("relation") == "MISSING_LINK"
                or edge.get("status") in {"candidate", "unresolved", "not_established"}
            ]
            contradictions = [
                edge for edge in relevant_edges if edge.get("relation") == "CONTRADICTS"
            ]
            qualifications = [
                edge
                for edge in relevant_edges
                if edge.get("relation") in {"QUALIFIES", "LIMITED_BY", "FAILS_WHEN"}
                or edge.get("status") == "qualified"
            ]

            return {
                "id": cluster_id,
                "title": cluster.get("title") or "Unclustered",
                "parent_cluster_id": cluster.get("parent_cluster_id"),
                "child_cluster_ids": sorted(child_map.get(cluster_id, [])),
                "tags": list(cluster.get("tags") or []),
                "external_key": cluster.get("external_key"),
                "synthetic": synthetic,
                "node_ids": sorted(member_ids),
                "node_count": len(members),
                "layers": layers,
                "neutral_nodes": neutral_nodes,
                "layer_presence": presence,
                "layer_counts": {layer: len(layers[layer]) for layer in PRIMARY_LAYERS},
                "missing_layers": missing_layers,
                "intersection": cls._intersection(presence),
                "internal_edges": internal_edges,
                "cross_edges": cross_edges,
                "internal_edge_count": len(internal_edges),
                "cross_edge_count": len(cross_edges),
                "relation_counts": dict(sorted(relations.items())),
                "status_counts": dict(sorted(statuses.items())),
                "unresolved_or_missing": unresolved,
                "contradictions": contradictions,
                "qualifications": qualifications,
                "provenance_receipts": list(cluster.get("provenance_receipts") or []),
            }

        for cluster_id, cluster in raw_clusters.items():
            cluster_rows.append(
                build_cluster(str(cluster_id), cluster, membership.get(str(cluster_id), set()))
            )

        if unclustered:
            cluster_rows.append(
                build_cluster(
                    "__unclustered__",
                    {"title": "Unclustered", "tags": ["synthetic"]},
                    unclustered,
                    synthetic=True,
                )
            )

        cluster_rows.sort(key=lambda row: (row["synthetic"], str(row["title"]).casefold(), row["id"]))
        intersection_counts = Counter(row["intersection"] for row in cluster_rows)
        missing_layer_counts = Counter(
            layer for row in cluster_rows for layer in row["missing_layers"]
        )
        represented_by_layer = Counter()
        for row in cluster_rows:
            for layer in PRIMARY_LAYERS:
                if row["layer_presence"][layer]:
                    represented_by_layer[layer] += 1

        return {
            "schema": "cite_refinery.clustered_three_layer_map.v1",
            "layers": list(PRIMARY_LAYERS),
            "clusters": cluster_rows,
            "summary": {
                "cluster_count": len(cluster_rows),
                "three_layer_clusters": intersection_counts.get("practical_academic_program", 0),
                "intersection_counts": dict(sorted(intersection_counts.items())),
                "missing_layer_counts": dict(sorted(missing_layer_counts.items())),
                "clusters_represented_by_layer": {
                    layer: represented_by_layer.get(layer, 0) for layer in PRIMARY_LAYERS
                },
                "unclustered_node_count": len(unclustered),
            },
            "boundary": (
                "The atlas is a structural map, not a score. A populated layer means that material from that authority family "
                "is represented in the cluster. An empty layer or missing edge is a research/navigation gap in the current graph, "
                "not proof that the corresponding evidence, knowledge, program, or relationship does not exist in the world."
            ),
        }

    def list_projects(self) -> list[dict[str, Any]]:
        state = self.store.load()
        projects = []
        for project in state.get("projects", {}).values():
            if not isinstance(project, dict):
                continue
            project_id = str(project.get("id"))
            observations = self._owned(state, "problem_observations", project_id)
            briefs = self._owned(state, "research_briefs", project_id)
            requirements = self._owned(state, "requirements", project_id)
            experiments = self._owned(state, "experiments", project_id)
            nodes = [
                node
                for node in state.get("semantic_nodes", {}).values()
                if isinstance(node, dict) and node.get("project_id") == project_id
            ]
            cluster_ids = {
                str(cluster_id)
                for node in nodes
                for cluster_id in (node.get("cluster_ids") or [])
            }
            projects.append(
                {
                    "id": project_id,
                    "title": project.get("title"),
                    "problem": project.get("problem"),
                    "status": project.get("status"),
                    "created_at": project.get("created_at"),
                    "counts": {
                        "practical_records": len(observations),
                        "academic_briefs": len(briefs),
                        "semantic_nodes": len(nodes),
                        "semantic_clusters": len(cluster_ids),
                        "program_requirements": len(requirements),
                        "experiments": len(experiments),
                    },
                }
            )
        return sorted(projects, key=lambda item: str(item.get("created_at") or ""), reverse=True)

    def project_view(self, project_id: str, *, include_graph: bool = True) -> dict[str, Any]:
        state = self.store.load()
        project = state.get("projects", {}).get(project_id)
        if project is None:
            raise KeyError(f"unknown project: {project_id}")

        observations = self._owned(state, "problem_observations", project_id)
        briefs = self._owned(state, "research_briefs", project_id)
        agendas = self._owned(state, "research_agendas", project_id)
        audits = self._owned(state, "audits", project_id)
        requirements = self._owned(state, "requirements", project_id)
        solution_maps = self._owned(state, "solution_maps", project_id)
        capabilities = self._project_capabilities(state, project_id)
        implementations = self._project_implementations(state, project_id, capabilities)
        runs = self._owned(state, "runs", project_id)
        artifacts = self._owned(state, "artifacts", project_id)
        experiments = self._owned(state, "experiments", project_id)
        feedback_requests = self._owned(state, "feedback_requests", project_id)
        feedback_results = self._owned(state, "feedback_results", project_id)

        discovery_audits = [item for item in audits if item.get("purpose") == "literature_discovery"]
        grounding_audits = [item for item in audits if item.get("purpose") in {"research_brief", "claim_grounding"}]
        candidate_count, authority_counts = self._candidate_count(solution_maps)

        graph_export = self.graph.export(project_id)
        graph_summary = self._graph_summary(graph_export)
        atlas = self._cluster_atlas(graph_export)

        status_stages = Counter(str(item.get("status_stage") or "unspecified") for item in observations)
        source_systems = Counter(str(item.get("source_system") or "unknown") for item in observations)
        matters = {str(item.get("matter_id")) for item in observations if item.get("matter_id")}
        source_links = sum(len(item.get("sources") or []) for item in observations)

        research_questions = sum(len(item.get("questions") or []) for item in briefs)
        paper_receipts = 0
        for audit in discovery_audits:
            structured = audit.get("structured") if isinstance(audit.get("structured"), dict) else {}
            paper_receipts += int(structured.get("paper_count_total") or 0)

        succeeded_runs = sum(item.get("status") == "succeeded" for item in runs)
        passed_experiments = sum(item.get("verdict") in {"passed", "supported"} for item in experiments)

        sections = {
            "practical": {
                "engine": "Nocturnal",
                "authority": "empirical reality",
                "observations": observations,
                "matter_count": len(matters),
                "source_link_count": source_links,
                "source_system_counts": dict(sorted(source_systems.items())),
                "status_stage_counts": dict(sorted(status_stages.items())),
            },
            "academic": {
                "engine": "Cite",
                "authority": "academic knowledge",
                "agendas": agendas,
                "briefs": briefs,
                "research_question_count": research_questions,
                "literature_discovery_audits": discovery_audits,
                "grounding_audits": grounding_audits,
                "paper_receipts": paper_receipts,
            },
            "program": {
                "engine": "Refinery",
                "authority": "program and implementation supply",
                "requirements": requirements,
                "solution_maps": solution_maps,
                "candidate_count": candidate_count,
                "candidate_authority_counts": dict(sorted(authority_counts.items())),
                "capabilities": capabilities,
                "implementations": implementations,
            },
            "execution": {
                "runs": runs,
                "artifacts": artifacts,
                "experiments": experiments,
                "feedback_requests": feedback_requests,
                "feedback_results": feedback_results,
                "succeeded_runs": succeeded_runs,
                "passed_or_supported_experiments": passed_experiments,
            },
            # Compatibility aliases for the v0.11 prototype API. They remain
            # supporting records; the primary product view is the atlas above.
            "reality": {
                "engine": "Nocturnal",
                "observations": observations,
                "matter_count": len(matters),
                "source_link_count": source_links,
                "source_system_counts": dict(sorted(source_systems.items())),
                "status_stage_counts": dict(sorted(status_stages.items())),
            },
            "research": {
                "engine": "Cite",
                "agendas": agendas,
                "briefs": briefs,
                "research_question_count": research_questions,
                "literature_discovery_audits": discovery_audits,
                "grounding_audits": grounding_audits,
                "paper_receipts": paper_receipts,
            },
            "graph": {
                "engine": "Cite-Refinery Semantic Graph",
                "summary": graph_summary,
                "clusters": atlas["clusters"],
            },
            "solutions": {
                "engine": "Refinery",
                "requirements": requirements,
                "solution_maps": solution_maps,
                "candidate_count": candidate_count,
                "candidate_authority_counts": dict(sorted(authority_counts.items())),
                "capabilities": capabilities,
                "implementations": implementations,
            },
            "build": {
                "implementations": implementations,
                "runs": runs,
                "artifacts": artifacts,
                "succeeded_runs": succeeded_runs,
            },
            "validate": {
                "experiments": experiments,
                "passed_or_supported_experiments": passed_experiments,
                "feedback_requests": feedback_requests,
                "feedback_results": feedback_results,
            },
        }

        result = {
            "schema": "cite_refinery.product_workspace.v2",
            "project": project,
            "primary_view": "map",
            "navigation": ["map", "records", "project"],
            "atlas": atlas,
            "sections": sections,
            "product_boundary": {
                "practical": "Nocturnal remains the empirical authority; empirical material is not automatically academic support.",
                "academic": "Cite remains the research authority; discovery is not automatically support or causality.",
                "program": "Refinery remains the supply authority; candidates and implementations are not automatically effective solutions.",
                "map": "Cite-Refinery clusters exact semantic modules and maps the three authority families around them without collapsing them.",
                "ai": "AI may assist discovery, classification and interpretation, but the map, provenance and project records remain directly inspectable and operable without a chat interface.",
            },
        }
        if include_graph:
            result["graph_export"] = graph_export
        return result

    def cluster_atlas(self, project_id: str) -> dict[str, Any]:
        return self._cluster_atlas(self.graph.export(project_id))

    def cluster_view(self, project_id: str, cluster_id: str) -> dict[str, Any]:
        atlas = self.cluster_atlas(project_id)
        for cluster in atlas["clusters"]:
            if cluster["id"] == cluster_id:
                return {
                    "schema": "cite_refinery.cluster_view.v1",
                    "project_id": project_id,
                    "cluster": cluster,
                    "boundary": atlas["boundary"],
                }
        raise KeyError(f"unknown semantic cluster for project: {cluster_id}")

    def node_view(self, project_id: str, node_id: str, *, depth: int = 1) -> dict[str, Any]:
        coverage = self.graph.coverage(project_id, node_id, depth=depth)
        return {
            "schema": "cite_refinery.product_node_view.v1",
            "project_id": project_id,
            "coverage": coverage,
        }
