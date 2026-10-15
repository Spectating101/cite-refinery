from __future__ import annotations

from collections import Counter
from typing import Any


def _owned(state: dict[str, Any], bucket: str, project_id: str) -> list[dict[str, Any]]:
    values = state.get(bucket, {})
    if isinstance(values, dict):
        return [item for item in values.values() if isinstance(item, dict) and item.get("project_id") == project_id]
    return []


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _candidate_authority(candidate: dict[str, Any]) -> str:
    explicit = str(candidate.get("authority") or "").strip()
    if explicit:
        return explicit
    kind = str(candidate.get("kind") or "").strip()
    if kind in {"capability", "commons_capability"}:
        return "commons"
    if kind in {"implementation", "operational_implementation"}:
        return "operational"
    return "unspecified"


def build_end_to_end_scorecard(state: dict[str, Any], project_id: str) -> dict[str, Any]:
    """Build an inspectable gate-by-gate project scorecard without a composite score."""

    project = (state.get("projects") or {}).get(project_id)
    if not isinstance(project, dict):
        raise KeyError(f"unknown project: {project_id}")

    observations = _owned(state, "problem_observations", project_id)
    briefs = _owned(state, "research_briefs", project_id)
    audits = _owned(state, "audits", project_id)
    requirements = _owned(state, "requirements", project_id)
    solution_maps = _owned(state, "solution_maps", project_id)
    capabilities = _owned(state, "capabilities", project_id)
    implementations = _owned(state, "implementations", project_id)
    runs = _owned(state, "runs", project_id)
    experiments = _owned(state, "experiments", project_id)

    matter_count = len({str(item.get("matter_id") or item.get("id")) for item in observations})
    source_observations = sum(bool(item.get("sources")) for item in observations)
    explicit_query_observations = sum(bool(item.get("literature_queries")) for item in observations)
    quality_states = Counter(
        str((item.get("provenance") or {}).get("quality_state") or "unspecified")
        for item in observations
    )

    fallback_briefs = sum(
        int((brief.get("metadata") or {}).get("fallback_question_count") or 0) > 0
        for brief in briefs
    )
    discovery_audits = [audit for audit in audits if audit.get("purpose") == "literature_discovery"]
    discovery_completed_briefs = {
        target_id
        for audit in discovery_audits
        if audit.get("status") == "completed"
        for target_id in audit.get("target_ids", [])
    }
    discovery_partial_briefs = {
        target_id
        for audit in discovery_audits
        if audit.get("status") == "partial"
        for target_id in audit.get("target_ids", [])
    }
    paper_receipts = sum(
        int((audit.get("structured") or {}).get("paper_count_total") or 0)
        for audit in discovery_audits
        if isinstance(audit.get("structured"), dict)
    )
    literature_questions_attempted = sum(
        int((audit.get("structured") or {}).get("questions_attempted") or 0)
        for audit in discovery_audits
        if isinstance(audit.get("structured"), dict)
    )

    grounding_audits = [audit for audit in audits if audit.get("purpose") == "research_brief"]
    grounded_briefs = {
        target_id
        for audit in grounding_audits
        if audit.get("status") == "completed"
        for target_id in audit.get("target_ids", [])
    }
    grounded_briefs.update(brief.get("id") for brief in briefs if brief.get("status") == "grounded")

    linked_requirements = sum(
        bool(requirement.get("source_brief_id") or requirement.get("source_audit_id"))
        for requirement in requirements
    )

    mapped_requirement_ids: set[str] = set()
    candidate_requirement_ids: set[str] = set()
    candidate_authorities: Counter[str] = Counter()
    candidate_total = 0
    for solution_map in solution_maps:
        for requirement_id in solution_map.get("requirement_ids", []) or []:
            mapped_requirement_ids.add(str(requirement_id))
        results = solution_map.get("results") if isinstance(solution_map.get("results"), dict) else {}
        for requirement_id, result in results.items():
            if not isinstance(result, dict):
                continue
            candidates = result.get("supply_candidates")
            if not isinstance(candidates, list):
                candidates = result.get("canonical_candidates") if isinstance(result.get("canonical_candidates"), list) else []
            usable = [candidate for candidate in candidates if isinstance(candidate, dict)]
            if usable:
                candidate_requirement_ids.add(str(requirement_id))
            candidate_total += len(usable)
            for candidate in usable:
                candidate_authorities[_candidate_authority(candidate)] += 1

    successful_runs = sum(run.get("status") == "succeeded" for run in runs)
    passed_experiments = sum(experiment.get("verdict") in {"passed", "supported"} for experiment in experiments)
    global_capabilities = [
        capability
        for capability in (state.get("capabilities") or {}).values()
        if isinstance(capability, dict)
        and capability.get("scope") == "global"
        and (capability.get("provenance") or {}).get("promoted_from_project") == project_id
    ]

    # No v0.6 object currently links a post-intervention Nocturnal observation
    # back to an experiment/run. Keep this visible rather than implying closure.
    feedback_links = [
        observation
        for observation in observations
        if any(
            key in (observation.get("provenance") or {})
            for key in ("experiment_id", "intervention_run_id", "originating_project_id")
        )
    ]

    brief_count = len(briefs)
    requirement_count = len(requirements)
    stages = {
        "empirical_problem_map": {
            "status": "ready" if observations else "not_started",
            "matters": matter_count,
            "observations": len(observations),
            "observations_with_sources": source_observations,
            "source_presence_coverage": _ratio(source_observations, len(observations)),
            "observations_with_explicit_literature_queries": explicit_query_observations,
            "explicit_query_coverage": _ratio(explicit_query_observations, len(observations)),
            "quality_states": dict(sorted(quality_states.items())),
            "boundary": "Source presence is not source fidelity, accessibility, or truth validation.",
        },
        "research_agenda": {
            "status": "ready" if brief_count else "not_started",
            "briefs": brief_count,
            "briefs_using_structural_fallback": fallback_briefs,
            "fallback_brief_coverage": _ratio(fallback_briefs, brief_count),
        },
        "literature_discovery": {
            "status": (
                "ready" if brief_count and len(discovery_completed_briefs) >= brief_count
                else "partial" if discovery_completed_briefs or discovery_partial_briefs
                else "not_started"
            ),
            "completed_briefs": len(discovery_completed_briefs),
            "partial_briefs": len(discovery_partial_briefs),
            "brief_coverage": _ratio(len(discovery_completed_briefs), brief_count),
            "questions_attempted": literature_questions_attempted,
            "paper_receipts": paper_receipts,
            "boundary": "Paper discovery is acquisition evidence, not support for a mechanism or intervention.",
        },
        "literature_grounding": {
            "status": (
                "ready" if brief_count and len(grounded_briefs) >= brief_count
                else "partial" if grounded_briefs
                else "not_started"
            ),
            "grounded_briefs": len(grounded_briefs),
            "brief_coverage": _ratio(len(grounded_briefs), brief_count),
        },
        "requirement_translation": {
            "status": "ready" if requirements else "not_started",
            "requirements": requirement_count,
            "requirements_with_research_lineage": linked_requirements,
            "lineage_coverage": _ratio(linked_requirements, requirement_count),
            "boundary": "Requirements are explicit human/orchestrator decisions; literature output is not auto-converted into a build instruction.",
        },
        "solution_mapping": {
            "status": (
                "ready" if requirement_count and len(mapped_requirement_ids) >= requirement_count
                else "partial" if mapped_requirement_ids
                else "not_started"
            ),
            "mapped_requirements": len(mapped_requirement_ids),
            "mapping_coverage": _ratio(len(mapped_requirement_ids), requirement_count),
            "requirements_with_candidates": len(candidate_requirement_ids),
            "candidate_coverage": _ratio(len(candidate_requirement_ids), requirement_count),
            "candidate_total": candidate_total,
            "candidate_authorities": dict(sorted(candidate_authorities.items())),
        },
        "execution_validation": {
            "status": (
                "ready" if passed_experiments and successful_runs
                else "partial" if capabilities or implementations or runs or experiments
                else "not_started"
            ),
            "project_capabilities": len(capabilities),
            "implementations": len(implementations),
            "runs": len(runs),
            "successful_runs": successful_runs,
            "experiments": len(experiments),
            "passed_or_supported_experiments": passed_experiments,
            "promoted_global_capabilities": len(global_capabilities),
        },
        "nocturnal_feedback_loop": {
            "status": "partial" if feedback_links else "not_implemented",
            "linked_post_intervention_observations": len(feedback_links),
            "boundary": "Cite-Refinery v0.6 has no formal experiment/run -> new Nocturnal observation contract yet.",
        },
    }

    bottlenecks: list[str] = []
    if observations and source_observations < len(observations):
        bottlenecks.append("Some empirical observations have no source links.")
    if brief_count and fallback_briefs:
        bottlenecks.append("Part of the research agenda depends on structural fallback questions rather than upstream Nocturnal literature hints.")
    if brief_count and len(discovery_completed_briefs) < brief_count:
        bottlenecks.append("Deep literature acquisition is incomplete across research briefs.")
    if brief_count and len(grounded_briefs) < brief_count:
        bottlenecks.append("Literature grounding/synthesis is incomplete across research briefs.")
    if not requirements:
        bottlenecks.append("No explicit capability requirements have been translated from the research layer.")
    elif len(mapped_requirement_ids) < requirement_count:
        bottlenecks.append("Some capability requirements have not been mapped against Refinery supply.")
    if requirement_count and len(candidate_requirement_ids) < requirement_count:
        bottlenecks.append("Some mapped requirements have no discovered solution candidate.")
    if candidate_authorities.get("reviewed_market_graph", 0) and not (
        candidate_authorities.get("commons", 0) or candidate_authorities.get("operational", 0)
    ):
        bottlenecks.append("Solution supply is descriptive reviewed-market evidence only; no canonical reusable/executable candidate is present.")
    if capabilities and not successful_runs:
        bottlenecks.append("Project capabilities exist but no successful implementation run is recorded.")
    if successful_runs and not passed_experiments:
        bottlenecks.append("Successful runs exist but no passed/supported validation experiment is recorded.")
    if not feedback_links:
        bottlenecks.append("The closed-loop return from validated intervention to new Nocturnal observation is not implemented.")

    return {
        "schema_version": 1,
        "project": {
            "id": project_id,
            "title": project.get("title"),
            "problem": project.get("problem"),
            "status": project.get("status"),
        },
        "stages": stages,
        "bottlenecks": bottlenecks,
        "boundary": (
            "This scorecard reports pipeline coverage and authority transitions. It intentionally has no composite numeric score: "
            "a later-stage success cannot compensate for missing empirical, literature, or validation evidence upstream."
        ),
    }
