from __future__ import annotations

from pathlib import Path

from .cite import CiteAdapter
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
