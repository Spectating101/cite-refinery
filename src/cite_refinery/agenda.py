from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Iterable


DOMAIN_LABELS = {
    "judicial_legal": "judicial and legal accountability",
    "public_safety_infrastructure": "public safety and infrastructure",
    "corporate_financial": "corporate and financial accountability",
    "health_environment": "health and environmental governance",
    "public_administration_rights": "public administration and rights",
}

_STOPWORDS = {
    "about", "after", "against", "along", "among", "and", "are", "been", "being", "between", "build",
    "capability", "compare", "could", "from", "have", "into", "more", "need", "needs", "preserve", "project",
    "records", "require", "required", "should", "source", "sources", "that", "their", "them", "these", "this",
    "through", "using", "with", "without", "would",
}


def _clean(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def observation_field(observation: dict[str, Any], key: str) -> str | None:
    provenance = observation.get("provenance")
    if isinstance(provenance, dict):
        value = _clean(provenance.get(key))
        if value:
            return value
    return None


def derive_structural_questions(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create conservative research questions from explicit Nocturnal structure.

    These are search prompts, not empirical or academic claims. They are used only
    when upstream Nocturnal output contains no explicit literature-query hints.
    """

    if not observations:
        return []
    countries = sorted({value for row in observations if (value := observation_field(row, "country"))})
    domains = sorted({value for row in observations if (value := observation_field(row, "domain"))})
    stages = sorted({str(row.get("status_stage")) for row in observations if row.get("status_stage")})
    relations = sorted({
        relation
        for row in observations
        for relation in (observation_field(row, "relation_types") or "").split(",")
        if relation
    })
    domain_labels = [DOMAIN_LABELS.get(domain, domain.replace("_", " ")) for domain in domains]
    scope = ", ".join(domain_labels) if domain_labels else "the observed problem domain"
    geography = f" in {', '.join(countries)}" if countries else ""
    stage_context = ", ".join(stages[:8])
    relation_context = ", ".join(relations[:6])

    source_ids = [row["id"] for row in observations]
    questions = [
        {
            "domain": domains[0] if len(domains) == 1 else None,
            "query": (
                f"What mechanisms in the empirical literature explain failures, accountability responses, remediation, "
                f"and durable outcomes in {scope}{geography}?"
            ),
            "reason": "derived_from_nocturnal_structure",
            "origin": "structural_fallback",
            "source_observation_ids": source_ids,
        },
        {
            "domain": domains[0] if len(domains) == 1 else None,
            "query": (
                f"Which interventions or institutional mechanisms have been empirically evaluated for preventing recurrence "
                f"or improving accountability, correction, restitution, safety, compliance, or implementation in {scope}{geography}?"
            ),
            "reason": "derived_from_nocturnal_structure",
            "origin": "structural_fallback",
            "source_observation_ids": source_ids,
        },
    ]
    context = "; ".join(part for part in [f"stages: {stage_context}" if stage_context else "", f"relations: {relation_context}" if relation_context else ""] if part)
    if context:
        questions.append({
            "domain": domains[0] if len(domains) == 1 else None,
            "query": f"What longitudinal evidence explains transitions among the observed institutional states ({context}) in {scope}{geography}?",
            "reason": "derived_from_nocturnal_trajectory",
            "origin": "structural_fallback",
            "source_observation_ids": source_ids,
        })
    return questions


def cluster_observations(
    observations: Iterable[dict[str, Any]],
    *,
    max_observations: int = 30,
) -> list[dict[str, Any]]:
    """Cluster by explicit country/domain/cohort and keep a matter intact when packing."""

    if max_observations < 1:
        raise ValueError("max_observations must be positive")
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        country = observation_field(row, "country") or "unknown"
        domain = observation_field(row, "domain") or "unknown"
        cohort = observation_field(row, "cohort") or "unspecified"
        grouped[(country, domain, cohort)].append(row)

    clusters: list[dict[str, Any]] = []
    for (country, domain, cohort), rows in sorted(grouped.items()):
        matters: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            matters[str(row.get("matter_id") or row["id"])].append(row)
        packed: list[dict[str, Any]] = []
        chunk_index = 1
        for matter_id in sorted(matters):
            matter_rows = sorted(matters[matter_id], key=lambda item: (str(item.get("observed_at") or ""), item["id"]))
            if packed and len(packed) + len(matter_rows) > max_observations:
                clusters.append({"country": country, "domain": domain, "cohort": cohort, "chunk": chunk_index, "observations": packed})
                packed = []
                chunk_index += 1
            packed.extend(matter_rows)
        if packed:
            clusters.append({"country": country, "domain": domain, "cohort": cohort, "chunk": chunk_index, "observations": packed})
    return clusters


def scale_metrics(observations: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(observations)
    matters = {str(row.get("matter_id") or row["id"]) for row in rows}
    countries = Counter(observation_field(row, "country") or "unknown" for row in rows)
    domains = Counter(observation_field(row, "domain") or "unknown" for row in rows)
    cohorts = Counter(observation_field(row, "cohort") or "unspecified" for row in rows)
    quality = Counter(observation_field(row, "quality_state") or "unspecified" for row in rows)
    explicit_query_rows = sum(bool(row.get("literature_queries")) for row in rows)
    source_rows = sum(bool(row.get("sources")) for row in rows)
    source_links = sum(len(row.get("sources") or []) for row in rows)
    return {
        "observations": len(rows),
        "matters": len(matters),
        "countries": dict(sorted(countries.items())),
        "domains": dict(sorted(domains.items())),
        "cohorts": dict(sorted(cohorts.items())),
        "quality_states": dict(sorted(quality.items())),
        "observations_with_sources": source_rows,
        "source_links": source_links,
        "observations_with_explicit_literature_queries": explicit_query_rows,
        "explicit_literature_query_coverage": round(explicit_query_rows / len(rows), 4) if rows else 0.0,
    }


def requirement_search_probes(text: str, tags: list[str] | None = None, *, max_terms: int = 6) -> list[str]:
    """Generate transparent literal probes for Refinery's current substring search."""

    probes: list[str] = []
    for value in [text, *(tags or [])]:
        cleaned = " ".join(str(value).strip().split())
        if cleaned and cleaned.casefold() not in {item.casefold() for item in probes}:
            probes.append(cleaned)
    tokens = [
        token.casefold()
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_+-]{3,}", text)
        if token.casefold() not in _STOPWORDS
    ]
    counts = Counter(tokens)
    for token, _ in sorted(counts.items(), key=lambda item: (-item[1], -len(item[0]), item[0]))[:max_terms]:
        if token not in {item.casefold() for item in probes}:
            probes.append(token)
    return probes
