from __future__ import annotations

from collections import Counter
from typing import Any

from .semantic import SemanticGraph


class ProductWorkspace:
    """Read-only product projection over the Cite-Refinery state.

    The underlying engines keep their own authority and records. This layer only
    assembles them into one user-facing project model:

    - Reality: Nocturnal / empirical observations
    - Research: Cite briefs, discovery and grounding
    - Graph: semantic problem map
    - Solutions: Refinery requirements and supply
    - Build: implementations, runs and artifacts
    - Validate: experiments and post-intervention feedback
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
            projects.append(
                {
                    "id": project_id,
                    "title": project.get("title"),
                    "problem": project.get("problem"),
                    "status": project.get("status"),
                    "created_at": project.get("created_at"),
                    "counts": {
                        "reality": len(observations),
                        "research": len(briefs),
                        "graph_nodes": len(nodes),
                        "requirements": len(requirements),
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
        clusters = self.graph.cluster_map(project_id)

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
            "overview": {
                "reality_observations": len(observations),
                "research_briefs": len(briefs),
                "semantic_nodes": graph_summary["node_count"],
                "semantic_edges": graph_summary["edge_count"],
                "open_requirements": sum(item.get("status", "open") == "open" for item in requirements),
                "solution_candidates": candidate_count,
                "project_capabilities": len(capabilities),
                "runs": len(runs),
                "experiments": len(experiments),
                "feedback_results": len(feedback_results),
            },
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
                "clusters": clusters.get("clusters", []),
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
            "schema": "cite_refinery.product_workspace.v1",
            "project": project,
            "navigation": [
                "overview",
                "reality",
                "research",
                "graph",
                "solutions",
                "build",
                "validate",
            ],
            "sections": sections,
            "product_boundary": {
                "reality": "Nocturnal remains the empirical authority; this view projects its records.",
                "research": "Cite remains the research authority; discovery is not automatically support.",
                "solutions": "Refinery remains the supply authority; candidates are not automatically validated solutions.",
                "graph": "The semantic graph joins exact modules while preserving source authority and uncertainty.",
            },
        }
        if include_graph:
            result["graph_export"] = graph_export
        return result

    def node_view(self, project_id: str, node_id: str, *, depth: int = 1) -> dict[str, Any]:
        coverage = self.graph.coverage(project_id, node_id, depth=depth)
        return {
            "schema": "cite_refinery.product_node_view.v1",
            "project_id": project_id,
            "coverage": coverage,
        }
