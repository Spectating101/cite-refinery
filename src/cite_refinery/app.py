from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .cite import CiteAdapter
from .cite_research import CiteAgentResearchCLIAdapter, CiteResearchAdapter
from .models import Audit, SolutionMap, dump_model, machine_id
from .pipeline import CiteRefinery as CoreCiteRefinery
from .solution import LayeredRefinerySearchAdapter, RefinerySearchAdapter


class CiteRefinery(CoreCiteRefinery):
    """Default Cite-Refinery application with layered research and solution discovery.

    Literature acquisition, claim grounding, reviewed market supply, canonical
    capability state, and execution remain separate authorities with explicit
    receipts between them.
    """

    def __init__(
        self,
        workspace: str | Path = ".cite-refinery",
        cite: CiteAdapter | None = None,
        solution_refinery: RefinerySearchAdapter | None = None,
        cite_research: CiteResearchAdapter | None = None,
    ) -> None:
        super().__init__(
            workspace=workspace,
            cite=cite,
            solution_refinery=solution_refinery or LayeredRefinerySearchAdapter(),
        )
        self.cite_research = cite_research or CiteAgentResearchCLIAdapter()

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

    def discover_research_brief(
        self,
        project_id: str,
        brief_id: str,
        *,
        target_count: int = 30,
        snowball_depth: int = 1,
        max_questions: int = 4,
    ) -> Audit:
        """Run bounded deep literature acquisition for a prepared research brief.

        Discovery receipts are stored as audits with purpose=literature_discovery.
        Finding papers never changes empirical observations or marks a research
        question/claim as supported; grounding remains a separate operation.
        """

        self.get_project(project_id)
        if not 1 <= int(target_count) <= 200:
            raise ValueError("target_count must be between 1 and 200")
        if not 0 <= int(snowball_depth) <= 3:
            raise ValueError("snowball_depth must be between 0 and 3")
        if not 1 <= int(max_questions) <= 20:
            raise ValueError("max_questions must be between 1 and 20")

        state = self.store.load()
        brief = state["research_briefs"].get(brief_id)
        if brief is None or brief.get("project_id") != project_id:
            raise ValueError("research brief does not belong to project")
        questions = [question for question in brief.get("questions", []) if isinstance(question, dict)]
        selected = questions[: int(max_questions)]
        if not selected:
            raise ValueError("research brief has no research questions")

        receipts: list[dict[str, Any]] = []
        engines: set[str] = set()
        statuses: list[str] = []
        paper_keys: set[str] = set()
        paper_count_total = 0
        for question in selected:
            topic = str(question.get("query") or "").strip()
            if not topic:
                continue
            result = self.cite_research.deep(
                topic,
                target_count=int(target_count),
                snowball_depth=int(snowball_depth),
            )
            engines.add(result.engine)
            statuses.append(result.status)
            structured = result.structured if isinstance(result.structured, dict) else None
            papers = structured.get("papers", []) if isinstance(structured, dict) and isinstance(structured.get("papers"), list) else []
            paper_count_total += len(papers)
            for paper in papers:
                if not isinstance(paper, dict):
                    continue
                key = str(paper.get("doi") or paper.get("url") or paper.get("title") or "").strip().casefold()
                if key:
                    paper_keys.add(key)
            receipts.append({
                "question": topic,
                "origin": question.get("origin"),
                "source_observation_ids": list(question.get("source_observation_ids") or []),
                "engine": result.engine,
                "status": result.status,
                "raw": result.raw,
                "structured": structured,
            })

        if statuses and all(status == "completed" for status in statuses):
            status = "completed"
        elif any(status == "completed" for status in statuses):
            status = "partial"
        elif any(status == "error" for status in statuses):
            status = "error"
        else:
            status = "not_run"
        structured_audit = {
            "brief_id": brief_id,
            "target_count_per_question": int(target_count),
            "snowball_depth": int(snowball_depth),
            "max_questions": int(max_questions),
            "questions_available": len(questions),
            "questions_attempted": len(receipts),
            "questions_omitted_by_bound": max(0, len(questions) - len(selected)),
            "paper_count_total": paper_count_total,
            "unique_paper_keys": len(paper_keys),
            "receipts": receipts,
            "boundary": (
                "This audit records literature acquisition only. Paper discovery does not establish support for empirical "
                "observations, mechanisms, interventions, or capability requirements; synthesis/grounding is separate."
            ),
        }
        audit = Audit(
            id=machine_id("raudit"),
            project_id=project_id,
            claim_ids=[],
            engine=",".join(sorted(engines)) or "unavailable",
            status=status,
            raw=json.dumps(structured_audit, ensure_ascii=False, sort_keys=True),
            structured=structured_audit,
            purpose="literature_discovery",
            target_ids=[brief_id],
        )
        state = self.store.load()
        state["audits"][audit.id] = dump_model(audit)
        stored_brief = state["research_briefs"][brief_id]
        stored_brief.setdefault("audit_ids", []).append(audit.id)
        metadata = stored_brief.setdefault("metadata", {})
        metadata.setdefault("literature_discovery_audit_ids", []).append(audit.id)
        metadata["last_literature_discovery"] = {
            "status": status,
            "questions_attempted": len(receipts),
            "paper_count_total": paper_count_total,
            "unique_paper_keys": len(paper_keys),
        }
        self.store.save(state)
        self._event(
            project_id,
            "cite.literature_discovered",
            {
                "brief_id": brief_id,
                "audit_id": audit.id,
                "status": status,
                "questions_attempted": len(receipts),
                "paper_count_total": paper_count_total,
                "unique_paper_keys": len(paper_keys),
            },
        )
        return audit

    def scale_report(self, project_id: str) -> dict[str, Any]:
        report = super().scale_report(project_id)
        state = self.store.load()
        discovery_audits = [
            audit
            for audit in state["audits"].values()
            if audit.get("project_id") == project_id and audit.get("purpose") == "literature_discovery"
        ]
        discovery_completed = sum(audit.get("status") == "completed" for audit in discovery_audits)
        discovery_partial = sum(audit.get("status") == "partial" for audit in discovery_audits)
        paper_total = 0
        unique_keys = 0
        questions_attempted = 0
        for audit in discovery_audits:
            structured = audit.get("structured") if isinstance(audit.get("structured"), dict) else {}
            paper_total += int(structured.get("paper_count_total") or 0)
            unique_keys += int(structured.get("unique_paper_keys") or 0)
            questions_attempted += int(structured.get("questions_attempted") or 0)
        research = report.setdefault("research", {})
        research.update({
            "literature_discovery_audits": len(discovery_audits),
            "literature_discovery_completed": discovery_completed,
            "literature_discovery_partial": discovery_partial,
            "literature_questions_attempted": questions_attempted,
            "literature_paper_receipts_total": paper_total,
            "literature_unique_keys_sum": unique_keys,
        })
        brief_count = int(research.get("briefs") or 0)
        if brief_count and not discovery_audits:
            report.setdefault("warnings", []).append(
                "Research briefs exist but no deep literature acquisition receipts are recorded; Cite grounding is operating without the structured discovery layer."
            )
        if discovery_audits and discovery_completed < len(discovery_audits):
            report.setdefault("warnings", []).append(
                "Some literature discovery audits are not completed; inspect acquisition receipts before treating research coverage as sufficient."
            )
        return report

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
