from __future__ import annotations

from pathlib import Path
from typing import Any

from .cite import CiteAdapter
from .models import Audit, ProblemObservation, Requirement, ResearchBrief, SolutionMap, dump_model, machine_id
from .nocturnal import parse_nocturnal_packet
from .orchestrator import CiteRefinery as BaseCiteRefinery
from .solution import CanonicalRefineryCLIAdapter, RefinerySearchAdapter


class CiteRefinery(BaseCiteRefinery):
    """Cite-Refinery with Nocturnal -> Cite -> Refinery orchestration.

    Empirical observations, academic grounding, and implementation candidates
    remain distinct objects. The integration layer records lineage between them
    without changing authority in any upstream system.
    """

    def __init__(
        self,
        workspace: str | Path = ".cite-refinery",
        cite: CiteAdapter | None = None,
        solution_refinery: RefinerySearchAdapter | None = None,
    ) -> None:
        super().__init__(workspace=workspace, cite=cite)
        self.solution_refinery = solution_refinery or CanonicalRefineryCLIAdapter()

    # Nocturnal: real-world observations and problem mapping.
    def ingest_nocturnal_packet(
        self,
        project_id: str,
        packet: dict[str, Any],
        *,
        packet_ref: str | None = None,
    ) -> list[ProblemObservation]:
        self.get_project(project_id)
        records = parse_nocturnal_packet(packet)
        state = self.store.load()
        existing = {
            (item.get("source_system"), item.get("external_id")): item
            for item in state["problem_observations"].values()
            if item.get("project_id") == project_id
        }
        observations: list[ProblemObservation] = []
        created_ids: list[str] = []
        for record in records:
            key = ("nocturnal", record.external_id)
            if key in existing:
                observations.append(ProblemObservation(**existing[key]))
                continue
            provenance = dict(record.provenance)
            if packet_ref:
                provenance["packet_ref"] = packet_ref
            observation = ProblemObservation(
                id=machine_id("robs"),
                project_id=project_id,
                source_system="nocturnal",
                external_id=record.external_id,
                matter_id=record.matter_id,
                event_id=record.event_id,
                text=record.text,
                observed_at=record.observed_at,
                status_stage=record.status_stage,
                frame=record.frame,
                sources=record.sources,
                literature_queries=record.literature_queries,
                provenance=provenance,
            )
            state["problem_observations"][observation.id] = dump_model(observation)
            existing[key] = state["problem_observations"][observation.id]
            observations.append(observation)
            created_ids.append(observation.id)
        self.store.save(state)
        self._event(
            project_id,
            "nocturnal.ingested",
            {
                "observation_ids": created_ids,
                "record_count": len(records),
                "created_count": len(created_ids),
                "packet_ref": packet_ref,
            },
        )
        return observations

    # Nocturnal -> Cite: translate empirical observations into literature questions.
    def prepare_research_brief(
        self,
        project_id: str,
        *,
        observation_ids: list[str] | None = None,
        title: str | None = None,
        extra_questions: list[str] | None = None,
    ) -> ResearchBrief:
        project = self.get_project(project_id)
        state = self.store.load()
        selected = [
            item
            for item in state["problem_observations"].values()
            if item.get("project_id") == project_id
            and (observation_ids is None or item.get("id") in observation_ids)
        ]
        if not selected:
            raise ValueError("project has no matching problem observations")
        if observation_ids is not None:
            found = {item["id"] for item in selected}
            missing = [item for item in observation_ids if item not in found]
            if missing:
                raise ValueError(f"observation does not belong to project: {missing[0]}")

        question_index: dict[tuple[str, str, str], dict[str, Any]] = {}
        for observation in selected:
            for raw in observation.get("literature_queries", []):
                if not isinstance(raw, dict):
                    continue
                query = str(raw.get("query") or "").strip()
                if not query:
                    continue
                domain = str(raw.get("domain") or "").strip()
                reason = str(raw.get("reason") or "").strip()
                key = (domain.lower(), query.lower(), reason.lower())
                question = question_index.setdefault(
                    key,
                    {
                        "domain": domain or None,
                        "query": query,
                        "reason": reason or None,
                        "source_observation_ids": [],
                    },
                )
                if observation["id"] not in question["source_observation_ids"]:
                    question["source_observation_ids"].append(observation["id"])

        for raw_query in extra_questions or []:
            query = raw_query.strip()
            if not query:
                continue
            key = ("", query.lower(), "manual")
            question_index.setdefault(
                key,
                {
                    "domain": None,
                    "query": query,
                    "reason": "manual",
                    "source_observation_ids": [item["id"] for item in selected],
                },
            )
        if not question_index:
            raise ValueError("selected observations contain no literature queries; add an explicit research question")

        brief = ResearchBrief(
            id=machine_id("rbrief"),
            project_id=project_id,
            title=title or f"Literature brief: {project['title']}",
            observation_ids=[item["id"] for item in selected],
            questions=list(question_index.values()),
        )
        state["research_briefs"][brief.id] = dump_model(brief)
        self.store.save(state)
        self._event(
            project_id,
            "research_brief.prepared",
            {"brief_id": brief.id, "observation_count": len(selected), "question_count": len(brief.questions)},
        )
        return brief

    def ground_research_brief(self, project_id: str, brief_id: str) -> Audit:
        self.get_project(project_id)
        state = self.store.load()
        brief = state["research_briefs"].get(brief_id)
        if brief is None or brief.get("project_id") != project_id:
            raise ValueError("research brief does not belong to project")
        observations = [
            state["problem_observations"][obs_id]
            for obs_id in brief.get("observation_ids", [])
            if obs_id in state["problem_observations"]
        ]
        if not observations:
            raise ValueError("research brief has no available observations")

        lines = [
            "Problem-mapping handoff from Nocturnal to Cite-Agent.",
            "Treat the observations as empirical context, not as academic evidence.",
            "Ground literature-derived claims that explain the observed problems or support candidate interventions.",
            "Keep observed facts separate from literature claims and preserve citation/provenance for every literature claim.",
            "",
            "EMPIRICAL OBSERVATIONS:",
        ]
        for observation in observations:
            lines.append(f"- [{observation['id']}] {observation['text']} sources={len(observation.get('sources', []))}")
        lines.extend(["", "RESEARCH QUESTIONS:"])
        for question in brief.get("questions", []):
            domain = f"[{question.get('domain')}] " if question.get("domain") else ""
            lines.append(f"- {domain}{question.get('query')}")

        result = self.cite.ground("\n".join(lines))
        audit = Audit(
            id=machine_id("raudit"),
            project_id=project_id,
            claim_ids=[],
            engine=result.engine,
            status=result.status,
            raw=result.raw,
            structured=result.structured,
            purpose="research_brief",
            target_ids=[brief_id],
        )
        state = self.store.load()
        state["audits"][audit.id] = dump_model(audit)
        stored_brief = state["research_briefs"][brief_id]
        stored_brief.setdefault("audit_ids", []).append(audit.id)
        if result.status == "completed":
            stored_brief["status"] = "grounded"
        self.store.save(state)
        self._event(
            project_id,
            "cite.research_grounded",
            {"brief_id": brief_id, "audit_id": audit.id, "status": audit.status},
        )
        return audit

    # Cite -> Refinery: explicit capability requirements, then solution mapping.
    def add_requirement(
        self,
        project_id: str,
        text: str,
        *,
        kind: str = "capability",
        tags: list[str] | None = None,
        source_brief_id: str | None = None,
        source_audit_id: str | None = None,
    ) -> Requirement:
        self.get_project(project_id)
        state = self.store.load()
        if source_brief_id:
            brief = state["research_briefs"].get(source_brief_id)
            if brief is None or brief.get("project_id") != project_id:
                raise ValueError("source research brief does not belong to project")
        if source_audit_id:
            audit = state["audits"].get(source_audit_id)
            if audit is None or audit.get("project_id") != project_id:
                raise ValueError("source audit does not belong to project")
        requirement = Requirement(
            id=machine_id("rreq"),
            project_id=project_id,
            text=text,
            kind=kind,
            tags=sorted(set(tags or [])),
            source_brief_id=source_brief_id,
            source_audit_id=source_audit_id,
        )
        state["requirements"][requirement.id] = dump_model(requirement)
        self.store.save(state)
        self._event(project_id, "requirement.added", {"requirement_id": requirement.id, "kind": kind})
        return requirement

    def map_requirements(
        self,
        project_id: str,
        requirement_ids: list[str] | None = None,
        *,
        limit: int = 20,
    ) -> SolutionMap:
        self.get_project(project_id)
        state = self.store.load()
        requirements = [
            item
            for item in state["requirements"].values()
            if item.get("project_id") == project_id
            and (requirement_ids is None or item.get("id") in requirement_ids)
        ]
        if not requirements:
            raise ValueError("project has no matching requirements to map")
        if requirement_ids is not None:
            found = {item["id"] for item in requirements}
            missing = [item for item in requirement_ids if item not in found]
            if missing:
                raise ValueError(f"requirement does not belong to project: {missing[0]}")

        statuses: list[str] = []
        engines: set[str] = set()
        results: dict[str, Any] = {}
        for requirement in requirements:
            external = self.solution_refinery.search(requirement["text"], limit=limit)
            statuses.append(external.status)
            engines.add(external.engine)
            results[requirement["id"]] = {
                "requirement": requirement["text"],
                "canonical_refinery": {
                    "engine": external.engine,
                    "status": external.status,
                    "raw": external.raw,
                    "structured": external.structured,
                },
                "project_overlay": self.refinery.search(requirement["text"], project_id=project_id, limit=limit),
            }

        if statuses and all(status == "completed" for status in statuses):
            status = "completed"
        elif any(status == "completed" for status in statuses):
            status = "partial"
        elif any(status == "error" for status in statuses):
            status = "error"
        else:
            status = "not_run"
        solution_map = SolutionMap(
            id=machine_id("rmap"),
            project_id=project_id,
            requirement_ids=[item["id"] for item in requirements],
            engine=",".join(sorted(engines)),
            status=status,
            results=results,
        )
        state = self.store.load()
        state["solution_maps"][solution_map.id] = dump_model(solution_map)
        self.store.save(state)
        self._event(
            project_id,
            "refinery.mapped",
            {"solution_map_id": solution_map.id, "status": status, "requirement_count": len(requirements)},
        )
        return solution_map

    def adopt_capability(
        self,
        project_id: str,
        requirement_id: str,
        *,
        name: str,
        description: str,
        tags: list[str] | None = None,
        solution_map_id: str | None = None,
        candidate_ref: str | None = None,
    ):
        self.get_project(project_id)
        state = self.store.load()
        requirement = state["requirements"].get(requirement_id)
        if requirement is None or requirement.get("project_id") != project_id:
            raise ValueError("requirement does not belong to project")
        if solution_map_id:
            solution_map = state["solution_maps"].get(solution_map_id)
            if solution_map is None or solution_map.get("project_id") != project_id:
                raise ValueError("solution map does not belong to project")
            if requirement_id not in solution_map.get("requirement_ids", []):
                raise ValueError("solution map does not cover requirement")
        provenance = {
            "requirement_id": requirement_id,
            "source_brief_id": requirement.get("source_brief_id"),
            "source_audit_id": requirement.get("source_audit_id"),
            "solution_map_id": solution_map_id,
            "candidate_ref": candidate_ref,
        }
        provenance = {key: value for key, value in provenance.items() if value is not None}
        capability = self.refinery.register_capability(
            project_id=project_id,
            name=name,
            description=description,
            tags=tags,
            provenance=provenance,
        )
        self._event(
            project_id,
            "capability.adopted",
            {"capability_id": capability.id, "requirement_id": requirement_id, "solution_map_id": solution_map_id},
        )
        return capability

    def dossier(self, project_id: str) -> dict[str, Any]:
        data = super().dossier(project_id)
        state = self.store.load()
        owned = lambda bucket: [item for item in state[bucket].values() if item.get("project_id") == project_id]
        data["problem_observations"] = owned("problem_observations")
        data["research_briefs"] = owned("research_briefs")
        data["requirements"] = owned("requirements")
        data["solution_maps"] = owned("solution_maps")
        return data
