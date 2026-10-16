from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .cite import CiteAdapter
from .cite_research import CiteAgentResearchCLIAdapter, CiteResearchAdapter
from .feedback import REQUEST_SCHEMA, validate_feedback_result
from .models import Audit, ProblemObservation, SolutionMap, dump_model, machine_id, utcnow
from .pipeline import CiteRefinery as CoreCiteRefinery
from .solution import LayeredRefinerySearchAdapter, RefinerySearchAdapter


class CiteRefinery(CoreCiteRefinery):
    """Default Cite-Refinery application with explicit authority transitions."""

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
        """Run bounded deep literature acquisition for a prepared research brief."""

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

    def create_nocturnal_feedback_request(
        self,
        project_id: str,
        experiment_id: str,
        *,
        observation_ids: list[str] | None = None,
        requested_signals: list[str] | None = None,
        window_start: str | None = None,
        window_end: str | None = None,
    ) -> dict[str, Any]:
        """Create an auditable observation request after a validated intervention."""

        self.get_project(project_id)
        state = self.store.load()
        experiment = state["experiments"].get(experiment_id)
        if experiment is None or experiment.get("project_id") != project_id:
            raise ValueError("experiment does not belong to project")
        if experiment.get("verdict") not in {"passed", "supported"}:
            raise ValueError("Nocturnal feedback requires a passed/supported experiment")

        run_ids = [str(value) for value in experiment.get("run_ids", []) if str(value)]
        runs: list[dict[str, Any]] = []
        for run_id in run_ids:
            run = state["runs"].get(run_id)
            if run is None or run.get("project_id") != project_id:
                raise ValueError(f"experiment references an invalid project run: {run_id}")
            runs.append(run)
        if runs and not any(run.get("status") == "succeeded" for run in runs):
            raise ValueError("feedback for an executable intervention requires a successful linked run")

        baseline = [
            item
            for item in state["problem_observations"].values()
            if item.get("project_id") == project_id and item.get("source_system") != "nocturnal-feedback"
        ]
        if observation_ids is not None:
            requested_ids = {str(value) for value in observation_ids if str(value)}
            if not requested_ids:
                raise ValueError("observation_ids may not be empty when supplied")
            selected = [item for item in baseline if item.get("id") in requested_ids]
            if {item.get("id") for item in selected} != requested_ids:
                raise ValueError("one or more feedback source observations do not belong to project")
        else:
            selected = baseline
        if not selected:
            raise ValueError("feedback request requires at least one originating empirical observation")
        if len(selected) > 1000:
            raise ValueError("feedback request may reference at most 1000 originating observations")

        request_id = machine_id("rfbk")
        signals = requested_signals or [
            "implementation_event",
            "adoption_signal",
            "outcome_signal",
            "adverse_event",
            "persistence_or_reversal",
        ]
        request = {
            "schema": REQUEST_SCHEMA,
            "request_id": request_id,
            "project_id": project_id,
            "experiment_id": experiment_id,
            "run_ids": run_ids,
            "capability_ids": sorted({str(run.get("capability_id")) for run in runs if run.get("capability_id")}),
            "implementation_ids": sorted({str(run.get("implementation_id")) for run in runs if run.get("implementation_id")}),
            "originating_problem_observation_ids": [str(item["id"]) for item in selected],
            "matter_ids": sorted({str(item.get("matter_id")) for item in selected if item.get("matter_id")}),
            "event_ids": sorted({str(item.get("event_id")) for item in selected if item.get("event_id")}),
            "intervention": {
                "name": experiment.get("name"),
                "method": experiment.get("method"),
                "result": experiment.get("result"),
                "verdict": experiment.get("verdict"),
                "metrics": dict(experiment.get("metrics") or {}),
            },
            "observation_window": {"start_at": window_start, "end_at": window_end},
            "requested_signals": sorted({str(value).strip() for value in signals if str(value).strip()}),
            "created_at": utcnow(),
            "boundary": (
                "This packet asks Nocturnal to observe what happens after a validated intervention. It does not instruct "
                "Nocturnal to attribute later events to the intervention, and a follow-up observation is not causal proof."
            ),
        }
        state["feedback_requests"][request_id] = request
        self.store.save(state)
        self._event(project_id, "nocturnal.feedback_requested", {"request_id": request_id, "experiment_id": experiment_id, "run_ids": run_ids})
        return request

    def ingest_nocturnal_feedback_result(self, project_id: str, packet: dict[str, Any]) -> dict[str, Any]:
        """Ingest Nocturnal's post-intervention observations without causal upgrading."""

        self.get_project(project_id)
        state = self.store.load()
        request_id = str(packet.get("request_id") or "").strip()
        request = state["feedback_requests"].get(request_id)
        if request is None or request.get("project_id") != project_id:
            raise ValueError("feedback result does not match a stored project request")
        normalized = validate_feedback_result(packet, request)
        digest = hashlib.sha256(json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        result_id = f"rfresult:{digest[:16]}"

        existing_by_external = {
            (item.get("source_system"), item.get("external_id")): item
            for item in state["problem_observations"].values()
            if item.get("project_id") == project_id
        }
        stored_observation_ids: list[str] = []
        for row in normalized["observations"]:
            existing = existing_by_external.get(("nocturnal-feedback", row["observation_id"]))
            if existing is not None:
                stored_observation_ids.append(str(existing["id"]))
                continue
            observation = ProblemObservation(
                id=machine_id("robs"),
                project_id=project_id,
                source_system="nocturnal-feedback",
                external_id=row["observation_id"],
                matter_id=row.get("matter_id"),
                event_id=row.get("event_id"),
                text=row["text"],
                observed_at=row.get("observed_at"),
                status_stage=row.get("status_stage"),
                frame="post_intervention",
                sources=list(row.get("sources") or []),
                literature_queries=[],
                provenance={
                    **dict(row.get("provenance") or {}),
                    "feedback_request_id": request_id,
                    "feedback_result_id": result_id,
                    "originating_project_id": project_id,
                    "experiment_id": request["experiment_id"],
                    "run_ids": list(request.get("run_ids") or []),
                    "relation_to_intervention": row["relation_to_intervention"],
                    "outcome_direction": row["outcome_direction"],
                    "causal_status": row["causal_status"],
                },
            )
            state["problem_observations"][observation.id] = dump_model(observation)
            stored_observation_ids.append(observation.id)
            existing_by_external[("nocturnal-feedback", row["observation_id"])] = dump_model(observation)

        stored_result = {
            **normalized,
            "result_id": result_id,
            "cite_refinery_observation_ids": stored_observation_ids,
            "ingested_at": utcnow(),
        }
        state["feedback_results"][result_id] = stored_result
        self.store.save(state)
        self._event(
            project_id,
            "nocturnal.feedback_ingested",
            {
                "request_id": request_id,
                "result_id": result_id,
                "experiment_id": request["experiment_id"],
                "observation_count": len(stored_observation_ids),
            },
        )
        return stored_result

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
        feedback_requests = [item for item in state["feedback_requests"].values() if item.get("project_id") == project_id]
        feedback_results = [item for item in state["feedback_results"].values() if item.get("project_id") == project_id]
        report["feedback"] = {
            "requests": len(feedback_requests),
            "results": len(feedback_results),
            "post_intervention_observations": sum(len(item.get("cite_refinery_observation_ids") or []) for item in feedback_results),
        }
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
