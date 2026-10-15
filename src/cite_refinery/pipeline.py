from __future__ import annotations

from pathlib import Path
from typing import Any

from .agenda import (
    cluster_observations,
    derive_structural_questions,
    observation_field,
    requirement_search_probes,
    scale_metrics,
)
from .cite import CiteAdapter
from .models import (
    Audit,
    ProblemObservation,
    Requirement,
    ResearchAgenda,
    ResearchBrief,
    SolutionMap,
    dump_model,
    machine_id,
)
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

    @staticmethod
    def _brief_scope_metadata(selected: list[dict[str, Any]]) -> dict[str, Any]:
        values: dict[str, list[str]] = {}
        for key in ("country", "domain", "cohort", "quality_state", "selection_freeze"):
            distinct = sorted({value for item in selected if (value := observation_field(item, key))})
            if distinct:
                values[key] = distinct
        values["matter_count"] = len({str(item.get("matter_id") or item["id"]) for item in selected})
        values["observation_count"] = len(selected)
        values["source_link_count"] = sum(len(item.get("sources") or []) for item in selected)
        return values

    # Nocturnal -> Cite: translate empirical observations into literature questions.
    def prepare_research_brief(
        self,
        project_id: str,
        *,
        observation_ids: list[str] | None = None,
        title: str | None = None,
        extra_questions: list[str] | None = None,
        allow_structural_fallback: bool = True,
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
                        "origin": raw.get("origin") or "nocturnal_explicit",
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
                    "origin": "manual",
                    "source_observation_ids": [item["id"] for item in selected],
                },
            )

        if not question_index and allow_structural_fallback:
            for question in derive_structural_questions(selected):
                key = (
                    str(question.get("domain") or "").lower(),
                    str(question.get("query") or "").lower(),
                    str(question.get("reason") or "").lower(),
                )
                question_index[key] = question

        if not question_index:
            raise ValueError("selected observations contain no literature queries and structural fallback is disabled")

        questions = list(question_index.values())
        scope = self._brief_scope_metadata(selected)
        origins: dict[str, int] = {}
        for question in questions:
            origin = str(question.get("origin") or "unspecified")
            origins[origin] = origins.get(origin, 0) + 1
        scope["question_origins"] = dict(sorted(origins.items()))
        scope["explicit_question_count"] = sum(1 for question in questions if question.get("origin") == "nocturnal_explicit")
        scope["fallback_question_count"] = sum(1 for question in questions if question.get("origin") == "structural_fallback")

        brief = ResearchBrief(
            id=machine_id("rbrief"),
            project_id=project_id,
            title=title or f"Literature brief: {project['title']}",
            observation_ids=[item["id"] for item in selected],
            questions=questions,
            metadata=scope,
        )
        state["research_briefs"][brief.id] = dump_model(brief)
        self.store.save(state)
        self._event(
            project_id,
            "research_brief.prepared",
            {
                "brief_id": brief.id,
                "observation_count": len(selected),
                "question_count": len(brief.questions),
                "fallback_question_count": scope["fallback_question_count"],
            },
        )
        return brief

    def prepare_research_agenda(
        self,
        project_id: str,
        *,
        max_observations_per_brief: int = 30,
        countries: list[str] | None = None,
        domains: list[str] | None = None,
        cohorts: list[str] | None = None,
    ) -> ResearchAgenda:
        self.get_project(project_id)
        state = self.store.load()
        observations = [item for item in state["problem_observations"].values() if item.get("project_id") == project_id]
        if countries:
            wanted = {value.casefold() for value in countries}
            observations = [item for item in observations if (observation_field(item, "country") or "").casefold() in wanted]
        if domains:
            wanted = {value.casefold() for value in domains}
            observations = [item for item in observations if (observation_field(item, "domain") or "").casefold() in wanted]
        if cohorts:
            wanted = {value.casefold() for value in cohorts}
            observations = [item for item in observations if (observation_field(item, "cohort") or "").casefold() in wanted]
        if not observations:
            raise ValueError("project has no observations matching the agenda filters")

        clusters = cluster_observations(observations, max_observations=max_observations_per_brief)
        brief_ids: list[str] = []
        cluster_receipts: list[dict[str, Any]] = []
        for cluster in clusters:
            rows = cluster["observations"]
            label = "/".join([cluster["country"], cluster["domain"], cluster["cohort"]])
            if cluster["chunk"] > 1:
                label += f" chunk {cluster['chunk']}"
            brief = self.prepare_research_brief(
                project_id,
                observation_ids=[item["id"] for item in rows],
                title=f"Research agenda — {label}",
                allow_structural_fallback=True,
            )
            brief_ids.append(brief.id)
            cluster_receipts.append({
                "brief_id": brief.id,
                "country": cluster["country"],
                "domain": cluster["domain"],
                "cohort": cluster["cohort"],
                "chunk": cluster["chunk"],
                "observation_count": len(rows),
                "matter_count": brief.metadata.get("matter_count", 0),
                "question_origins": brief.metadata.get("question_origins", {}),
            })

        metrics = scale_metrics(observations)
        metrics["brief_count"] = len(brief_ids)
        metrics["clusters"] = cluster_receipts
        agenda = ResearchAgenda(
            id=machine_id("ragenda"),
            project_id=project_id,
            brief_ids=brief_ids,
            grouping={
                "keys": ["country", "domain", "cohort"],
                "matter_atomic": True,
                "max_observations_per_brief": max_observations_per_brief,
                "filters": {"countries": countries or [], "domains": domains or [], "cohorts": cohorts or []},
            },
            metrics=metrics,
        )
        state = self.store.load()
        state["research_agendas"][agenda.id] = dump_model(agenda)
        self.store.save(state)
        self._event(
            project_id,
            "research_agenda.prepared",
            {"agenda_id": agenda.id, "brief_count": len(brief_ids), "observation_count": metrics["observations"]},
        )
        return agenda

    @staticmethod
    def _bounded_observation_line(observation: dict[str, Any], *, max_chars: int = 900) -> tuple[str, bool]:
        text = " ".join(str(observation.get("text") or "").split())
        truncated = len(text) > max_chars
        if truncated:
            text = text[: max_chars - 1].rstrip() + "…"
        provenance = observation.get("provenance") if isinstance(observation.get("provenance"), dict) else {}
        labels = [
            provenance.get("country"),
            provenance.get("domain"),
            provenance.get("cohort"),
            provenance.get("quality_state"),
            observation.get("status_stage"),
        ]
        scope = "/".join(str(value) for value in labels if value)
        prefix = f" [{scope}]" if scope else ""
        return f"- [{observation['id']}]{prefix} {text} sources={len(observation.get('sources', []))}", truncated

    def ground_research_brief(
        self,
        project_id: str,
        brief_id: str,
        *,
        max_prompt_chars: int = 30000,
        max_observation_chars: int = 900,
    ) -> Audit:
        self.get_project(project_id)
        if max_prompt_chars < 4000:
            raise ValueError("max_prompt_chars must be at least 4000")
        if max_observation_chars < 200:
            raise ValueError("max_observation_chars must be at least 200")
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

        header = [
            "Problem-mapping handoff from Nocturnal to Cite-Agent.",
            "Treat the observations as empirical context, not as academic evidence.",
            "Ground literature-derived claims that explain the observed problems or support candidate interventions.",
            "Keep observed facts separate from literature claims and preserve citation/provenance for every literature claim.",
            "Questions marked structural_fallback were generated from explicit Nocturnal metadata to make raw corpora searchable; they are not findings.",
            "",
            "EMPIRICAL OBSERVATIONS:",
        ]
        lines = list(header)
        truncated_count = 0
        omitted_count = 0
        for observation in observations:
            line, truncated = self._bounded_observation_line(observation, max_chars=max_observation_chars)
            prospective = "\n".join([*lines, line, "", "RESEARCH QUESTIONS:"])
            if len(prospective) > max_prompt_chars:
                omitted_count += 1
                continue
            lines.append(line)
            truncated_count += int(truncated)
        lines.extend(["", "RESEARCH QUESTIONS:"])
        for question in brief.get("questions", []):
            domain = f"[{question.get('domain')}] " if question.get("domain") else ""
            origin = question.get("origin") or "unspecified"
            line = f"- ({origin}) {domain}{question.get('query')}"
            if len("\n".join([*lines, line])) > max_prompt_chars:
                omitted_count += 1
                continue
            lines.append(line)
        prompt = "\n".join(lines)

        result = self.cite.ground(prompt)
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
        stored_brief.setdefault("metadata", {})["last_grounding"] = {
            "prompt_chars": len(prompt),
            "max_prompt_chars": max_prompt_chars,
            "truncated_observations": truncated_count,
            "omitted_items": omitted_count,
            "engine": result.engine,
            "status": result.status,
        }
        if result.status == "completed":
            stored_brief["status"] = "grounded"
        self.store.save(state)
        self._event(
            project_id,
            "cite.research_grounded",
            {
                "brief_id": brief_id,
                "audit_id": audit.id,
                "status": audit.status,
                "prompt_chars": len(prompt),
                "omitted_items": omitted_count,
            },
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

    @staticmethod
    def _structured_candidates(structured: Any) -> list[dict[str, Any]]:
        if isinstance(structured, list):
            return [item for item in structured if isinstance(item, dict)]
        if not isinstance(structured, dict):
            return []
        candidates: list[dict[str, Any]] = []
        for key in ("commons", "operational", "results", "matches"):
            value = structured.get(key)
            if isinstance(value, list):
                candidates.extend(item for item in value if isinstance(item, dict))
        return candidates

    @staticmethod
    def _candidate_key(candidate: dict[str, Any]) -> str:
        for key in ("subject_id", "object_id", "capability", "key", "id", "implementation"):
            value = candidate.get(key)
            if value:
                return f"{key}:{value}"
        return repr(sorted(candidate.items()))

    def _search_requirement(self, requirement: dict[str, Any], *, limit: int) -> dict[str, Any]:
        probes = requirement_search_probes(requirement["text"], requirement.get("tags") or [])
        attempts: list[dict[str, Any]] = []
        merged: dict[str, dict[str, Any]] = {}
        primary = None
        for index, probe in enumerate(probes):
            external = self.solution_refinery.search(probe, limit=limit)
            receipt = {
                "query": probe,
                "engine": external.engine,
                "status": external.status,
                "raw": external.raw,
                "structured": external.structured,
            }
            attempts.append(receipt)
            if index == 0:
                primary = receipt
            for candidate in self._structured_candidates(external.structured):
                key = self._candidate_key(candidate)
                if key not in merged:
                    enriched = dict(candidate)
                    enriched["matched_by_probe"] = probe
                    merged[key] = enriched
            # Preserve the simple/old path when a full requirement already finds candidates.
            if index == 0 and merged:
                break
        statuses = [attempt["status"] for attempt in attempts]
        if statuses and all(status == "completed" for status in statuses):
            status = "completed"
        elif any(status == "completed" for status in statuses):
            status = "partial"
        elif any(status == "error" for status in statuses):
            status = "error"
        else:
            status = "not_run"
        return {
            "status": status,
            "primary": primary,
            "search_probes": attempts,
            "merged_candidates": list(merged.values()),
        }

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
            mapped = self._search_requirement(requirement, limit=limit)
            statuses.append(mapped["status"])
            primary = mapped["primary"] or {"engine": "unavailable", "status": "not_run", "raw": "", "structured": None}
            engines.update(attempt["engine"] for attempt in mapped["search_probes"])
            results[requirement["id"]] = {
                "requirement": requirement["text"],
                "canonical_refinery": primary,
                "canonical_search_probes": mapped["search_probes"],
                "canonical_candidates": mapped["merged_candidates"],
                "canonical_candidate_count": len(mapped["merged_candidates"]),
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
            {
                "solution_map_id": solution_map.id,
                "status": status,
                "requirement_count": len(requirements),
                "candidate_count": sum(item["canonical_candidate_count"] for item in results.values()),
            },
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

    def scale_report(self, project_id: str) -> dict[str, Any]:
        self.get_project(project_id)
        state = self.store.load()
        owned = lambda bucket: [item for item in state[bucket].values() if item.get("project_id") == project_id]
        observations = owned("problem_observations")
        metrics = scale_metrics(observations)
        briefs = owned("research_briefs")
        agendas = owned("research_agendas")
        requirements = owned("requirements")
        solution_maps = owned("solution_maps")
        capabilities = owned("capabilities")
        audits = [item for item in owned("audits") if item.get("purpose") == "research_brief"]
        candidate_counts = [
            result.get("canonical_candidate_count", 0)
            for solution_map in solution_maps
            for result in solution_map.get("results", {}).values()
            if isinstance(result, dict)
        ]
        fallback_briefs = sum(bool(brief.get("metadata", {}).get("fallback_question_count")) for brief in briefs)
        grounded = sum(brief.get("status") == "grounded" for brief in briefs)
        prompt_omissions = sum(
            int(brief.get("metadata", {}).get("last_grounding", {}).get("omitted_items", 0))
            for brief in briefs
        )
        warnings: list[str] = []
        if metrics["explicit_literature_query_coverage"] < 0.5 and observations:
            warnings.append("Most Nocturnal observations lack explicit literature-query hints; structural fallback questions are doing substantial agenda work.")
        if any(key in {"minimal", "unspecified"} for key in metrics["quality_states"]):
            warnings.append("Observation quality is heterogeneous; downstream synthesis must preserve quality/cohort boundaries rather than treat all observations equally.")
        if prompt_omissions:
            warnings.append(f"Cite prompt bounds omitted {prompt_omissions} agenda items; reduce brief size or increase the explicit prompt budget.")
        if candidate_counts and sum(candidate_counts) == 0:
            warnings.append("Canonical Refinery returned no solution candidates for mapped requirements; registry coverage/search recall is a blocking constraint.")
        return {
            "project_id": project_id,
            "empirical": metrics,
            "research": {
                "agendas": len(agendas),
                "briefs": len(briefs),
                "briefs_using_structural_fallback": fallback_briefs,
                "grounded_briefs": grounded,
                "research_audits": len(audits),
                "prompt_omitted_items": prompt_omissions,
            },
            "solution": {
                "requirements": len(requirements),
                "solution_maps": len(solution_maps),
                "canonical_candidate_counts": candidate_counts,
                "canonical_candidates_total": sum(candidate_counts),
                "project_capabilities": len(capabilities),
            },
            "warnings": warnings,
        }

    def dossier(self, project_id: str) -> dict[str, Any]:
        data = super().dossier(project_id)
        state = self.store.load()
        owned = lambda bucket: [item for item in state[bucket].values() if item.get("project_id") == project_id]
        data["problem_observations"] = owned("problem_observations")
        data["research_briefs"] = owned("research_briefs")
        data["research_agendas"] = owned("research_agendas")
        data["requirements"] = owned("requirements")
        data["solution_maps"] = owned("solution_maps")
        return data
