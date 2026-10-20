"""Assemble existing reviewed practical / academic / program relationships into
source-bounded investigator findings, without treating graph connectivity as truth.

This runs on stored semantic packets, not keyword matching or cached topic names.
The source-review state of every traversed edge is retained. This layer never
changes evidence status, performs search, or writes to persisted graph state.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

SCHEMA = "cite_refinery.semantic_graph.v1"
TRUSTED_STATES = {"qualified", "candidate", "unresolved", "not_established", "asserted"}
ACTIVE_STATES = {"qualified", "candidate", "unresolved"}
PROBLEM_KINDS = {"problem_claim"}
PRACTICAL_LINKS = {"SUPPORTS", "OBSERVES", "EXPLAINS"}
ACADEMIC_LINKS = {"SUPPORTS", "QUALIFIES", "EXPLAINS"}
METHOD_LINKS = {"MEASURED_BY", "EVALUATED_BY"}
PROGRAM_LINKS = {"ADDRESSES", "PARTIALLY_ADDRESSES"}
UNVERIFIED_TAGS = {"source_lead_only", "discovery_only", "not_an_evidence_claim"}


def _refs(*records: dict[str, Any]) -> list[str]:
    values = []
    for record in records:
        values.extend(record.get("source_refs") or record.get("evidence_refs") or [])
    return sorted(set(str(v) for v in values if isinstance(v, str) and v.startswith("https://")))


def _compact_node(node: dict[str, Any]) -> dict[str, Any]:
    return {"id": node["key"], "layer": node["layer"], "kind": node["kind"],
            "statement": node["statement"], "sources": _refs(node)}


def stack_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Produce typed, inspectable chains from explicitly connected source-reviewed nodes.

    Same-cluster membership alone can NEVER create a semantic match.
    Fail closed for unsupported or asserted graph edges. Input can be passed
    directly from a reviewed semantic_graph.v1 packet before persistence.
    """
    if not isinstance(packet, dict) or packet.get("schema") != SCHEMA:
        raise ValueError("expected cite_refinery.semantic_graph.v1")
    rows, links = packet.get("nodes"), packet.get("edges")
    if not isinstance(rows, list) or not isinstance(links, list) or len(rows) > 1000 or len(links) > 4000:
        raise ValueError("invalid/beyond-limit semantic packet")
    nodes = {}
    for node in rows:
        if not isinstance(node, dict):
            raise ValueError("bad node")
        key = node.get("key")
        if not isinstance(key, str) or not key or key in nodes:
            raise ValueError("duplicate or invalid node identity")
        if node.get("layer") not in {"neutral", "practical", "academic", "program"}:
            raise ValueError("invalid semantic layer")
        if not isinstance(node.get("statement"), str):
            raise ValueError("statement required")
        nodes[key] = node
    indexed = defaultdict(list)
    for edge in links:
        if not isinstance(edge, dict) or edge.get("source") not in nodes or edge.get("target") not in nodes:
            raise ValueError("edge refers to unknown node")
        status = edge.get("status", "asserted")
        if status not in TRUSTED_STATES:
            raise ValueError("invalid edge state")
        # Asserted links are not interpreted: older packets omit status and
        # prior acceptance requires downgrading implicit authority first.
        if status in ACTIVE_STATES and not (set(nodes[edge["source"]].get("tags") or []) |
                                               set(nodes[edge["target"]].get("tags") or [])) & UNVERIFIED_TAGS:
            indexed[(edge["source"], edge.get("relation"))].append(edge)
            indexed[("->", edge["target"])].append(edge)
    for edges in indexed.values():
        edges.sort(key=lambda e: (e["source"], e["target"], e.get("relation", "")))
    problems = []
    for root in sorted(nodes.values(), key=lambda n: n["key"]):
        if root.get("kind") not in PROBLEM_KINDS:
            continue
        pk = root["key"]
        incoming = indexed.get(("->", pk), [])
        practical = []
        academic = []
        programs = []
        for edge in incoming:
            node = nodes[edge["source"]]
            if node["layer"] == "practical" and edge["relation"] in PRACTICAL_LINKS:
                practical.append((node, edge))
            if node["layer"] == "academic" and edge["relation"] in ACADEMIC_LINKS:
                academic.append((node, edge))
            if node["layer"] == "program" and edge["relation"] in PROGRAM_LINKS:
                programs.append((node, edge))
        methods = []
        for rel in METHOD_LINKS:
            for edge in indexed.get((pk, rel), []):
                node = nodes[edge["target"]]
                if node["layer"] == "academic":
                    methods.append((node, edge))
        findings = []
        seen_findings = set()

        def append_finding(kind: str, *, claim: str, why: str,
                           node_ids: list[str], edge_chain: list[dict[str, Any]],
                           next_check: str, status: str) -> None:
            unique_ids = list(dict.fromkeys(node_ids))
            chain_ids = [(e["source"], e["relation"], e["target"]) for e in edge_chain]
            fingerprint = (kind, tuple(unique_ids), tuple(chain_ids))
            if fingerprint in seen_findings:
                return
            seen_findings.add(fingerprint)
            source_refs = _refs(*(nodes[i] for i in unique_ids), *edge_chain)
            findings.append({
                "type": kind, "interpretation": claim, "why": why,
                "source_refs": source_refs, "nodes": unique_ids,
                "reasoning_chain": [{
                    "from": e["source"], "relation": e["relation"],
                    "to": e["target"], "status": e["status"],
                    "evidence_refs": _refs(e),
                } for e in edge_chain],
                "review_state": status, "next_check": next_check,
            })

        for observed, obs_edge in practical:
            # An observation can be independently qualified, without equating
            # a nonsignificant difference with no population change.
            for qedge in indexed.get(("->", observed["key"]), []):
                modifier = nodes[qedge["source"]]
                if qedge["relation"] == "QUALIFIES" and modifier["key"] != observed["key"]:
                    append_finding(
                        "scope_qualification",
                        claim=modifier["statement"],
                        why="This qualification changes how the practical observation can be interpreted.",
                        node_ids=[observed["key"], modifier["key"], pk],
                        edge_chain=[obs_edge, qedge],
                        next_check="Review sampling, significance and whether a causal interpretation is supported.",
                        status="source_bounded_qualification_requires_review",
                    )
        for program, program_edge in programs:
            limits = [(nodes[e["target"]], e)
                      for e in indexed.get((program["key"], "LIMITED_BY"), [])
                      if nodes[e["target"]]["kind"] in {"limitation", "requirement"}]
            for method, method_edge in methods:
                for need_edge in indexed.get((method["key"], "REQUIRES"), []):
                    need = nodes[need_edge["target"]]
                    if need["kind"] != "requirement":
                        continue
                    for limitation, limit_edge in limits:
                        # Require the *same* requirement identity linked by an
                        # explicit unresolved edge. Topical similarity is forbidden.
                        for missing_edge in indexed.get((limitation["key"], "MISSING_LINK"), []):
                            if missing_edge["target"] != need["key"] or missing_edge["status"] not in {"unresolved", "not_established"}:
                                continue
                            append_finding(
                                "method_implementation_mismatch",
                                claim=(f"{program['statement']} However: {limitation['statement']} "
                                       f"The scientific method requires: {need['statement']}"),
                                why="The implementation limitation interrupts a named requirement of the linked scientific method.",
                                node_ids=[pk, method["key"], need["key"], program["key"], limitation["key"]],
                                edge_chain=[program_edge, method_edge, need_edge, limit_edge, missing_edge],
                                next_check=f"Verify whether {program['key']} can actually satisfy: {need['statement']}",
                                status="unresolved_capability_fit_not_a_proven_incompatibility",
                            )
            # A program which addresses the problem is not proof its outcomes
            # were observed, even with a qualified review relationship.
            evaluations = [e for e in indexed.get((program["key"], "EVALUATED_BY"), [])
                           if nodes[e["target"]]["kind"] in {"outcome", "metric"}]
            if not evaluations and program_edge["relation"] == "ADDRESSES":
                append_finding(
                    "implementation_outcome_unestablished",
                    claim=program["statement"],
                    why="The reviewed graph links a documented program to this problem but provides no outcome-evaluation edge.",
                    node_ids=[pk, program["key"]],
                    edge_chain=[program_edge],
                    next_check="Locate an independent intervention evaluation with a specified outcome, baseline and population.",
                    status="absence_only_in_this_reviewed_graph",
                )
        if practical or academic or programs or methods:
            problems.append({
                "problem": _compact_node(root),
                "practical": [{**_compact_node(n), "relation": e["relation"], "edge_status": e["status"]}
                              for n, e in practical],
                "academic": [{**_compact_node(n), "relation": e["relation"], "edge_status": e["status"]}
                             for n, e in [*academic, *methods]],
                "implementations": [{**_compact_node(n), "relation": e["relation"], "edge_status": e["status"]}
                                    for n, e in programs],
                "findings": findings,
                "coverage": {"practical": bool(practical), "academic": bool(academic or methods),
                             "program": bool(programs)},
                "boundary": "Path synthesis is based only on explicit reviewed relationships; it cannot establish causal outcomes or global absence.",
            })
    return {"schema": "cite_refinery.cross_layer_stack.v1",
            "source_system": packet.get("source_system"),
            "problems": problems,
            "disconnected_or_unmatched_nodes": len(rows) - len(set(
                x for p in problems for x in (
                    [p["problem"]["id"]] +
                    [n["id"] for a in ("practical", "academic", "implementations") for n in p[a]] +
                    [n for f in p["findings"] for n in f["nodes"]]))),
            "authority": "source_bounded_candidate_interpretation_only",
            "no_graph_mutation": True}


def stack_project_graph(graph: Any, project_id: str) -> dict[str, Any]:
    """Use the real persistent SemanticGraph project; never cross tenant/project IDs."""
    state = graph.store.load()
    if project_id not in state.get("projects", {}):
        raise KeyError("unknown semantic project")
    selected_nodes = [n for n in state.get("semantic_nodes", {}).values()
                      if n.get("project_id") == project_id]
    ids = {n["id"] for n in selected_nodes}
    converted_nodes = [{
        "key": n["id"], "layer": n["layer"], "kind": n["kind"],
        "statement": n["statement"], "source_refs": n.get("source_refs", []),
        "tags": n.get("tags", []),
    } for n in selected_nodes]
    converted_edges = []
    for edge in state.get("semantic_edges", {}).values():
        if edge.get("project_id") != project_id:
            continue
        if edge.get("source_id") not in ids or edge.get("target_id") not in ids:
            raise ValueError("cross-project semantic edge detected")
        converted_edges.append({
            "source": edge["source_id"], "target": edge["target_id"],
            "relation": edge["relation"], "status": edge["status"],
            "evidence_refs": edge.get("evidence_refs", []),
        })
    report = stack_packet({
        "schema": SCHEMA, "source_system": "persistent_semantic_project",
        "nodes": converted_nodes, "edges": converted_edges,
    })
    report["project_id"] = project_id
    return report
