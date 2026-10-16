from __future__ import annotations

import hashlib
import json
from typing import Any

from .semantic import SemanticGraph, _normal_text


class SemanticProjection:
    """Project existing Cite-Refinery lifecycle records into the semantic graph.

    Projection is intentionally conservative. It records what each subsystem actually
    produced and uses lineage/candidate relations rather than silently upgrading
    discovery into support or supply into solution effectiveness.
    """

    def __init__(self, graph: SemanticGraph) -> None:
        self.graph = graph
        self.store = graph.store

    @staticmethod
    def _node_by_source_ref(state: dict[str, Any], project_id: str, ref: str) -> dict[str, Any] | None:
        for node in state.get("semantic_nodes", {}).values():
            if node.get("project_id") == project_id and ref in node.get("source_refs", []):
                return node
        return None

    @staticmethod
    def _candidate_label(candidate: dict[str, Any]) -> str:
        for key in ("name", "capability", "repository", "subject_id", "implementation", "entity_id", "id"):
            value = candidate.get(key)
            if value:
                return str(value)
        return json.dumps(candidate, sort_keys=True, ensure_ascii=False, default=str)[:1000]

    @staticmethod
    def _candidate_kind(candidate: dict[str, Any]) -> str:
        raw_kind = str(candidate.get("kind") or "").casefold()
        if candidate.get("repository") or "repo" in raw_kind:
            return "repository"
        if "implementation" in raw_kind:
            return "implementation"
        if "capability" in raw_kind:
            return "capability"
        return "program"

    @staticmethod
    def _candidate_refs(candidate: dict[str, Any]) -> list[str]:
        refs: list[str] = []
        for key in ("subject_id", "entity_id", "repository", "capability", "implementation", "id"):
            value = candidate.get(key)
            if value:
                refs.append(f"{key}:{value}")
        if refs:
            return refs
        payload = json.dumps(candidate, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        return [f"candidate-json:{hashlib.sha256(payload).hexdigest()[:24]}"]

    @classmethod
    def _candidate_ref(cls, candidate: dict[str, Any]) -> str:
        return cls._candidate_refs(candidate)[0]

    def project_all(self, project_id: str) -> dict[str, Any]:
        bootstrap = self.graph.bootstrap_project_records(project_id)
        research = self.project_research(project_id)
        supply = self.project_solution_supply(project_id)
        adoption = self.project_adopted_capabilities(project_id)
        identity = self.reconcile_exact_identity(project_id)
        return {
            "project_id": project_id,
            "bootstrap": bootstrap,
            "research": research,
            "solution_supply": supply,
            "adoption": adoption,
            "identity": identity,
        }

    def project_research(self, project_id: str) -> dict[str, Any]:
        state = self.store.load()
        self.graph._project(state, project_id)

        question_nodes: dict[tuple[str, str], str] = {}
        questions_created = 0
        lineage_edges = 0
        for brief in state.get("research_briefs", {}).values():
            if brief.get("project_id") != project_id:
                continue
            brief_id = str(brief.get("id"))
            for index, question in enumerate(brief.get("questions", []) or []):
                if not isinstance(question, dict):
                    continue
                query = _normal_text(str(question.get("query") or ""))
                if not query:
                    continue
                qnode = self.graph.add_node(
                    project_id,
                    query,
                    kind="research_question",
                    layer="neutral",
                    tags=["academic_agenda", str(question.get("origin") or "")],
                    source_refs=[f"research_brief:{brief_id}", f"research_question:{brief_id}:{index}"],
                    provenance={
                        "source_system": "cite",
                        "record_type": "research_question",
                        "brief_id": brief_id,
                        "origin": question.get("origin"),
                    },
                    external_key=f"research_question:{brief_id}:{index}",
                )
                question_nodes[(brief_id, query.casefold())] = qnode["id"]
                questions_created += 1
                for observation_id in question.get("source_observation_ids", []) or []:
                    current = self.store.load()
                    onode = self._node_by_source_ref(current, project_id, f"problem_observation:{observation_id}")
                    if onode is None:
                        continue
                    self.graph.add_edge(
                        project_id,
                        qnode["id"],
                        "DERIVED_FROM",
                        onode["id"],
                        provenance={
                            "source_system": "cite-refinery",
                            "record_type": "research_question_lineage",
                            "brief_id": brief_id,
                        },
                    )
                    lineage_edges += 1

        papers_created = 0
        discovery_edges = 0
        for audit in state.get("audits", {}).values():
            if audit.get("project_id") != project_id or audit.get("purpose") != "literature_discovery":
                continue
            structured = audit.get("structured") if isinstance(audit.get("structured"), dict) else {}
            brief_id = str(structured.get("brief_id") or (audit.get("target_ids") or [""])[0] or "")
            for receipt_index, receipt in enumerate(structured.get("receipts", []) or []):
                if not isinstance(receipt, dict):
                    continue
                query = _normal_text(str(receipt.get("question") or ""))
                qnode_id = question_nodes.get((brief_id, query.casefold()))
                payload = receipt.get("structured") if isinstance(receipt.get("structured"), dict) else {}
                for paper_index, paper in enumerate(payload.get("papers", []) or []):
                    if not isinstance(paper, dict):
                        continue
                    title = _normal_text(str(paper.get("title") or paper.get("doi") or paper.get("url") or ""))
                    if not title:
                        continue
                    refs = [
                        str(value)
                        for value in (paper.get("doi"), paper.get("url"))
                        if value
                    ]
                    pnode = self.graph.add_node(
                        project_id,
                        title,
                        kind="source",
                        layer="academic",
                        tags=["literature_discovery", str(paper.get("year") or "")],
                        source_refs=refs,
                        provenance={
                            "source_system": "cite",
                            "record_type": "literature_discovery_paper",
                            "audit_id": audit.get("id"),
                            "brief_id": brief_id,
                            "receipt_index": receipt_index,
                            "paper_index": paper_index,
                            "paper": paper,
                            "boundary": "discovery_only_not_claim_support",
                        },
                        external_key=f"paper:{paper.get('doi') or paper.get('url') or title}",
                    )
                    papers_created += 1
                    if qnode_id:
                        self.graph.add_edge(
                            project_id,
                            pnode["id"],
                            "DISCOVERED_FOR",
                            qnode_id,
                            status="candidate",
                            provenance={
                                "source_system": "cite",
                                "audit_id": audit.get("id"),
                                "boundary": "paper_discovery_does_not_establish_support",
                            },
                        )
                        discovery_edges += 1

        return {
            "questions_projected": questions_created,
            "question_lineage_edges": lineage_edges,
            "papers_projected": papers_created,
            "paper_discovery_edges": discovery_edges,
            "boundary": "Research questions and discovered papers are projected without asserting that a paper supports a problem claim.",
        }

    def project_solution_supply(self, project_id: str) -> dict[str, Any]:
        state = self.store.load()
        self.graph._project(state, project_id)
        projected = 0
        candidate_edges = 0
        authority_counts: dict[str, int] = {}

        for solution_map in state.get("solution_maps", {}).values():
            if solution_map.get("project_id") != project_id:
                continue
            map_id = str(solution_map.get("id"))
            for requirement_id, result in (solution_map.get("results") or {}).items():
                if not isinstance(result, dict):
                    continue
                current = self.store.load()
                rnode = self._node_by_source_ref(current, project_id, f"requirement:{requirement_id}")
                if rnode is None:
                    continue
                candidates = result.get("supply_candidates")
                if not isinstance(candidates, list):
                    candidates = result.get("canonical_candidates") if isinstance(result.get("canonical_candidates"), list) else []
                for index, candidate in enumerate(candidates):
                    if not isinstance(candidate, dict):
                        continue
                    authority = str(candidate.get("authority") or "unspecified")
                    authority_counts[authority] = authority_counts.get(authority, 0) + 1
                    refs = self._candidate_refs(candidate)
                    ref = refs[0]
                    node = self.graph.add_node(
                        project_id,
                        self._candidate_label(candidate),
                        kind=self._candidate_kind(candidate),
                        layer="program",
                        tags=["supply_candidate", authority],
                        source_refs=[*refs, f"solution_map:{map_id}"],
                        provenance={
                            "source_system": "refinery",
                            "record_type": "solution_supply_candidate",
                            "solution_map_id": map_id,
                            "requirement_id": requirement_id,
                            "candidate_index": index,
                            "authority": authority,
                            "candidate": candidate,
                            "boundary": "candidate_supply_not_adoption_validation_or_effectiveness",
                        },
                        external_key=f"solution_candidate:{map_id}:{requirement_id}:{ref}",
                    )
                    self.graph.add_edge(
                        project_id,
                        node["id"],
                        "CANDIDATE_FOR",
                        rnode["id"],
                        status="candidate",
                        provenance={
                            "source_system": "refinery",
                            "solution_map_id": map_id,
                            "authority": authority,
                            "boundary": "candidate_relation_only",
                        },
                    )
                    projected += 1
                    candidate_edges += 1

        return {
            "candidates_projected": projected,
            "candidate_edges": candidate_edges,
            "authority_counts": dict(sorted(authority_counts.items())),
            "boundary": "Supply candidates are connected to requirements as candidates only; projection does not assert that they solve the requirement.",
        }

    def project_adopted_capabilities(self, project_id: str) -> dict[str, Any]:
        state = self.store.load()
        self.graph._project(state, project_id)
        edges = 0
        for capability in state.get("capabilities", {}).values():
            if capability.get("project_id") != project_id:
                continue
            requirement_id = str((capability.get("provenance") or {}).get("requirement_id") or "")
            if not requirement_id:
                continue
            current = self.store.load()
            cnode = self._node_by_source_ref(current, project_id, f"capability:{capability.get('id')}")
            rnode = self._node_by_source_ref(current, project_id, f"requirement:{requirement_id}")
            if cnode is None or rnode is None:
                continue
            self.graph.add_edge(
                project_id,
                cnode["id"],
                "ADOPTED_FOR",
                rnode["id"],
                status="candidate",
                provenance={
                    "source_system": "cite-refinery",
                    "record_type": "project_capability_adoption",
                    "capability_id": capability.get("id"),
                    "requirement_id": requirement_id,
                    "boundary": "project_adoption_not_effectiveness",
                },
            )
            edges += 1
        return {"adoption_edges": edges, "boundary": "Project adoption is recorded separately from validation/effectiveness."}

    def reconcile_exact_identity(self, project_id: str) -> dict[str, Any]:
        """Add SAME_AS edges only for exact normalized semantic identity.

        This is deliberately not fuzzy/embedding clustering. Near-synonyms need an
        explicit semantic resolver or reviewed packet. Exact normalization gives us
        a safe baseline without pretending lexical similarity proves equivalence.
        """

        state = self.store.load()
        self.graph._project(state, project_id)
        groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for node in state.get("semantic_nodes", {}).values():
            if node.get("project_id") != project_id:
                continue
            key = (str(node.get("kind") or "concept"), _normal_text(str(node.get("statement") or "")).casefold())
            groups.setdefault(key, []).append(node)

        edges = 0
        groups_linked = 0
        for members in groups.values():
            if len(members) < 2:
                continue
            groups_linked += 1
            anchor = sorted(members, key=lambda node: str(node.get("id")))[0]
            for other in sorted(members, key=lambda node: str(node.get("id")))[1:]:
                if anchor["id"] == other["id"]:
                    continue
                self.graph.add_edge(
                    project_id,
                    anchor["id"],
                    "SAME_AS",
                    other["id"],
                    provenance={
                        "source_system": "cite-refinery",
                        "record_type": "exact_identity_reconciliation",
                        "rule": "same_kind_and_exact_normalized_statement",
                    },
                )
                edges += 1
        return {
            "identity_groups_linked": groups_linked,
            "same_as_edges": edges,
            "boundary": "Only exact normalized statements of the same kind are reconciled automatically; semantic near-equivalence requires reviewed resolution.",
        }
