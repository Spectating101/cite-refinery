"""Legal Codex actor bridge: source-named identities and Nocturnal relationships.

Production review is delegated to Nocturnal's analyze_relationships. Never
merge identical names, infer collusion, upgrade a reported link, or publish
an unreviewed criminal allegation as a fact. Read-only; no Nocturnal writes.
"""
from __future__ import annotations

from datetime import date
import json
import re
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

INPUT_SCHEMA = "legal_codex.actor_register.v1"
GRAPH_SCHEMA = "cite_refinery.semantic_graph.v1"
REL_SCHEMA = "nocturnal_relationship_graph.v1"
KINDS = {"person", "institution", "organization", "court_case", "document", "position"}
CASE_TYPES = {"court_case", "investigation_matter"}
IDENTITY_STATES = {"source_named_unreviewed", "source_initials_unresolved"}
RELATIONS = {
    "DEFENDANT_IN", "PROSECUTOR_IN", "PRESIDED_OVER", "HEARD_BY",
    "TESTIFIED_IN", "NAMED_IN_RECORD", "SAT_ON_PANEL", "SIGNED_DOCUMENT",
    "APPOINTED_TO", "CONTRACTED_WITH", "REVIEWED_BY", "REPORTED_TO",
}
_ID = re.compile(r"[a-z][a-z0-9_-]{2,63}\Z")
_ENTITY = re.compile(r"[a-z][a-z0-9_-]{2,99}\Z")


def _url(value):
    if not isinstance(value, str):
        return False
    try:
        u = urlsplit(value)
        return u.scheme == "https" and bool(u.hostname) and not (u.username or u.password)
    except ValueError:
        return False


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("observation date must be ISO YYYY-MM-DD")
    date.fromisoformat(value)


def _checked(data):
    if not isinstance(data, dict) or data.get("schema") != INPUT_SCHEMA:
        raise ValueError("invalid legal actor-register schema")
    cases = data.get("cases")
    entities = data.get("entities")
    observations = data.get("relationships")
    if not all(isinstance(x, list) and x for x in (cases, entities, observations)):
        raise ValueError("cases, entities and relationships are required")
    if len(cases) > 30 or len(entities) > 250 or len(observations) > 500:
        raise ValueError("actor register exceeds review budget")
    by_case = {}
    for c in cases:
        cid = c.get("id")
        if not isinstance(cid, str) or not _ID.fullmatch(cid) or cid in by_case:
            raise ValueError("invalid or duplicate case identifier")
        if (not _url(c.get("source_url")) or not c.get("reference")
                or not isinstance(c.get("jurisdiction"), str) or not c["jurisdiction"].strip()):
            raise ValueError("case lacks an official source locator and reference")
        if c.get("case_type", "court_case") not in CASE_TYPES:
            raise ValueError("case kind must distinguish judicial proceeding from investigation")
        by_case[cid] = c
    by_entity = {}
    for entity in entities:
        ident = entity.get("id")
        if not isinstance(ident, str) or not _ENTITY.fullmatch(ident) or ident in by_entity:
            raise ValueError("invalid or duplicate entity identifier")
        if entity.get("case_id") not in by_case or entity.get("kind") not in KINDS:
            raise ValueError("entity has unknown case or kind")
        name = entity.get("name")
        aliases = entity.get("aliases", [])
        refs = entity.get("source_refs")
        if (not isinstance(name, str) or not name.strip() or len(name) > 180
                or not isinstance(aliases, list) or len(aliases) > 12
                or any(not isinstance(a, str) or not a.strip() or len(a) > 180 for a in aliases)):
            raise ValueError("entity name/aliases invalid")
        if not isinstance(refs, list) or not refs or any(not _url(u) for u in refs):
            raise ValueError("entity lacks source locators")
        if entity.get("identity_status") not in IDENTITY_STATES:
            raise ValueError("source-named actors cannot self-certify identity")
        if entity["identity_status"] == "source_initials_unresolved" and entity["kind"] != "person":
            raise ValueError("initials-only identity must be a person lead")
        by_entity[ident] = entity
    seen_rel = set()
    for row in observations:
        src, dst = row.get("source_entity_id"), row.get("target_entity_id")
        if src not in by_entity or dst not in by_entity or src == dst:
            raise ValueError("relationship refers to unknown or self entity")
        if row.get("relation") not in RELATIONS:
            raise ValueError("unapproved relation type: legal guilt or collusion is not a graph edge")
        if not _url(row.get("source_url")) or not isinstance(row.get("evidence_ref"), str) or not row["evidence_ref"].strip():
            raise ValueError("relationship lacks evidence locator")
        _date(row.get("observed_at"))
        if row["source_url"] not in by_entity[src]["source_refs"]:
            raise ValueError("relationship source not listed for source actor")
        if row["source_url"] not in by_entity[dst]["source_refs"]:
            raise ValueError("relationship source not listed for target actor")
        if row.get("review_state") not in {"pending", "accepted", "rejected"}:
            raise ValueError("invalid relationship review state")
        if row.get("evidence_basis") not in {"native_record", "source_report"}:
            raise ValueError("invalid evidence basis")
        # No accidental cross-case graph link. Explicit linking requires a
        # separately reviewed source identity crosswalk in a future milestone.
        if by_entity[src]["case_id"] != by_entity[dst]["case_id"] and row["review_state"] == "accepted":
            raise ValueError("cross-case relationship needs reviewed identity crosswalk")
        if row["review_state"] == "accepted" and any(
                by_entity[e]["identity_status"] == "source_initials_unresolved"
                for e in (src, dst)):
            raise ValueError("unresolved initials may not be accepted as an identified signatory")
        if row["review_state"] == "accepted" and (not row.get("reviewer") or not row.get("reviewed_at")):
            raise ValueError("accepted relationship must have a reviewer")
        key = (src, dst, row["relation"], row["source_url"], row["evidence_ref"], row["observed_at"])
        if key in seen_rel:
            raise ValueError("duplicate relationship source observation")
        seen_rel.add(key)
    return by_case, by_entity


def _identity_candidates(entities):
    """Same display name is an investigative lead, NEVER a merged identity."""
    people = sorted((e for e in entities.values() if e["kind"] == "person" and
                     e["identity_status"] == "source_named_unreviewed"), key=lambda e: e["id"])
    candidates = []
    for i, a in enumerate(people):
        names_a = {a["name"].casefold().strip(), *(s.casefold().strip() for s in a.get("aliases", []))}
        for b in people[i + 1:]:
            if a["case_id"] == b["case_id"]:
                continue
            names_b = {b["name"].casefold().strip(), *(s.casefold().strip() for s in b.get("aliases", []))}
            matched = sorted(names_a & names_b)
            if matched:
                candidates.append({
                    "left_entity_id": a["id"], "right_entity_id": b["id"],
                    "matching_labels": matched,
                    "status": "unverified_possible_same_person",
                    "merged": False,
                    "authority": "none",
                })
    return candidates


def build_actor_graph(data: dict, *, analyzer: Callable | None = None) -> dict:
    """Project Nocturnal-reviewed direct records into candidate-only Cite graph.

    analyzer=None imports the actual installed Nocturnal engine; injecting an
    analyzer is for contract tests and produces **simulated** provenance only.
    """
    cases, entities = _checked(data)
    live = analyzer is None
    if live:
        try:
            from src.nocturnal_engine.relationships import analyze_relationships
        except ImportError as exc:
            raise RuntimeError(
                "Nocturnal relationship engine not installed; no verification performed"
            ) from exc
        analyzer = analyze_relationships
    analysis = analyzer(data["relationships"])
    if not isinstance(analysis, dict) or analysis.get("schema") != REL_SCHEMA:
        raise ValueError("unrecognized Nocturnal relationship output")
    boundaries = analysis.get("boundaries", {})
    if (boundaries.get("reported_edges_excluded_from_graph") is not True
            or boundaries.get("common_operator_attribution") != "not_established"
            or boundaries.get("payment_attribution") != "not_established"):
        raise ValueError("Nocturnal relationship attribution boundary violated")
    group_keys = ("direct_reviewed_edges", "source_report_edges", "pending_review", "rejected_observations")
    classified = []
    for group in group_keys:
        rows = analysis.get(group)
        if not isinstance(rows, list):
            raise ValueError("Nocturnal output lacks review-status partitions")
        classified.extend(rows)
    if len(classified) != len(data["relationships"]):
        raise ValueError("Nocturnal lost or duplicated relationship observations")
    original = {(
        r["source_entity_id"], r["target_entity_id"], r["relation"],
        r["source_url"], r["evidence_ref"], r["observed_at"]
    ): r for r in data["relationships"]}
    seen = set()
    for group in group_keys:
        for r in analysis[group]:
            key = (
                r.get("source_entity_id"), r.get("target_entity_id"), r.get("relation"),
                r.get("source_url"), r.get("evidence_ref"), r.get("observed_at"))
            if key not in original or key in seen:
                raise ValueError("Nocturnal returned unknown or duplicate evidence")
            seen.add(key)
            row = original[key]
            expected_group = (
                "rejected_observations" if row["review_state"] == "rejected" else
                "pending_review" if row["review_state"] == "pending" else
                "source_report_edges" if row["evidence_basis"] == "source_report" else
                "direct_reviewed_edges")
            if group != expected_group:
                raise ValueError("Nocturnal review category conflicts with source observation")
    nodes = []
    for c in cases.values():
        nodes.append({
            "key": "case-" + c["id"], "kind": "concept", "layer": "neutral",
            "statement": ("Court case " if c.get("case_type", "court_case") == "court_case"
                          else "Investigation matter ") + c["reference"],
            "source_refs": [c["source_url"]],
            "provenance": {"jurisdiction": c["jurisdiction"], "case_id": c["id"],
                           "publication_authorized": False},
        })
    for e in entities.values():
        nodes.append({
            "key": "actor-" + e["id"], "kind": ("person" if e["kind"] == "person" else
                     "concept" if e["kind"] in {"court_case", "position"} else
                     "source" if e["kind"] == "document" else "institution"),
            "layer": "neutral", "statement": e["name"],
            "aliases": e.get("aliases", []),
            "source_refs": e["source_refs"],
            "tags": ["identity_unresolved", e["kind"]],
            "provenance": {"case_id": e["case_id"], "source_entity_id": e["id"],
                           "identity_status": e["identity_status"],
                           "same_name_is_not_same_identity": True,
                           "publication_authorized": False},
        })
    edges = []
    for r in analysis["direct_reviewed_edges"]:
        edges.append({
            "source": "actor-" + r["source_entity_id"],
            "target": "actor-" + r["target_entity_id"],
            "relation": r["relation"], "status": "candidate",
            "evidence_refs": [r["source_url"]],
            "provenance": {
                "nocturnal_observation_id": r.get("observation_id"),
                "source_url": r["source_url"],
                "evidence_ref": r["evidence_ref"],
                "observed_at": r["observed_at"],
                "review_state": "accepted",
                "evidence_basis": "native_record",
                "source_integrity_verified": False,
                "nocturnal_validation": "live" if live else "simulated_contract_test",
                "authority": "candidate_only",
                "publication_authorized": False,
            },
        })
    return {
        "schema": "legal_codex.actor_projection.v1",
        "graph_packet": {"schema": GRAPH_SCHEMA,
                         "source_system": "legal-codex-nocturnal-actors",
                         "clusters": [], "nodes": nodes, "edges": edges},
        "identity_candidates": _identity_candidates(entities),
        "pending_observations": analysis["pending_review"],
        "source_report_observations": analysis["source_report_edges"],
        "rejected_observations": analysis["rejected_observations"],
        "reviewed_direct_relationship_count": len(edges) if live else 0,
        "simulated_relationship_count": len(edges) if not live else 0,
        "nocturnal_validator": "installed_runtime" if live else "test_double",
        "publication_authorized": False,
        "personal_guilt_established": False,
        "common_control_established": False,
    }


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", help="Evidence register JSON file")
    p.add_argument("--output", default="legal_codex_actor_projection.json")
    args = p.parse_args(argv)
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = build_actor_graph(data)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "actors": len(data["entities"]),
        "reviewed_direct_edges": result["reviewed_direct_relationship_count"],
        "pending": len(result["pending_observations"]),
        "identity_candidates": len(result["identity_candidates"]),
        "publication_authorized": False,
    }))


if __name__ == "__main__":
    main()
