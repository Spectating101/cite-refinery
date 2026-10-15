from __future__ import annotations

from collections import Counter
from pathlib import Path

from .cite import CiteAdapter
from .models import SolutionMap
from .pipeline import CiteRefinery as CoreCiteRefinery
from .solution import LayeredRefinerySearchAdapter, RefinerySearchAdapter


class CiteRefinery(CoreCiteRefinery):
    """Default Cite-Refinery application with layered Refinery discovery.

    Canonical Commons/operational supply remains authoritative for reusable or
    executable capability state. Reviewed-market supply is optional descriptive
    evidence and is kept visibly separate by the layered adapter.
    """

    def __init__(
        self,
        workspace: str | Path = ".cite-refinery",
        cite: CiteAdapter | None = None,
        solution_refinery: RefinerySearchAdapter | None = None,
    ) -> None:
        super().__init__(
            workspace=workspace,
            cite=cite,
            solution_refinery=solution_refinery or LayeredRefinerySearchAdapter(),
        )

    @staticmethod
    def _candidate_authority(candidate: dict) -> str:
        explicit = str(candidate.get("authority") or "").strip()
        if explicit:
            return explicit
        kind = str(candidate.get("kind") or "").strip()
        if kind in {"capability", "commons_capability"}:
            return "commons"
        if kind in {"implementation", "operational_implementation"}:
            return "operational"
        return "unspecified"

    def map_requirements(
        self,
        project_id: str,
        requirement_ids: list[str] | None = None,
        *,
        limit: int = 20,
    ) -> SolutionMap:
        solution_map = super().map_requirements(project_id, requirement_ids, limit=limit)
        state = self.store.load()
        stored = state["solution_maps"][solution_map.id]
        for result in stored.get("results", {}).values():
            if not isinstance(result, dict):
                continue
            candidates = [
                candidate
                for candidate in result.get("canonical_candidates", [])
                if isinstance(candidate, dict)
            ]
            counts = Counter(self._candidate_authority(candidate) for candidate in candidates)
            result["supply_candidates"] = candidates
            result["supply_candidate_count"] = len(candidates)
            result["supply_authority_counts"] = dict(sorted(counts.items()))
            result["supply_boundary"] = (
                "Authority is per candidate. reviewed_market_graph is descriptive reviewed supply only; "
                "it is not Commons admission, validation, rights clearance, recommendation, or execution permission."
            )
        self.store.save(state)
        return SolutionMap(**state["solution_maps"][solution_map.id])
