from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .cite import CiteAdapter, CiteAgentCLIAdapter
from .models import (
    Artifact,
    Audit,
    Claim,
    Event,
    Experiment,
    Project,
    Run,
    dump_model,
    machine_id,
    utcnow,
)
from .refinery import RefineryKernel
from .store import JsonStore


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "project"


class CiteRefinery:
    """Deterministic project lifecycle joining evidence and execution."""

    def __init__(self, workspace: str | Path = ".cite-refinery", cite: CiteAdapter | None = None) -> None:
        self.store = JsonStore(workspace)
        self.refinery = RefineryKernel(self.store)
        self.cite = cite or CiteAgentCLIAdapter()

    def _event(self, project_id: str | None, event_type: str, payload: dict[str, Any]) -> None:
        state = self.store.load()
        event = Event(id=machine_id("revt"), project_id=project_id, event_type=event_type, payload=payload)
        state["events"].append(dump_model(event))
        self.store.save(state)

    def init_project(self, title: str, problem: str, branch: str | None = None) -> Project:
        project = Project(
            id=machine_id("rproject"),
            title=title,
            problem=problem,
            branch=branch or _slug(title),
        )
        state = self.store.load()
        state["projects"][project.id] = dump_model(project)
        self.store.save(state)
        self._event(project.id, "project.created", {"title": title, "branch": project.branch})
        return project

    def get_project(self, project_id: str) -> dict[str, Any]:
        state = self.store.load()
        project = state["projects"].get(project_id)
        if project is None:
            raise KeyError(f"unknown project: {project_id}")
        return project

    def add_claim(self, project_id: str, text: str) -> Claim:
        self.get_project(project_id)
        claim = Claim(id=machine_id("rclaim"), project_id=project_id, text=text)
        state = self.store.load()
        state["claims"][claim.id] = dump_model(claim)
        self.store.save(state)
        self._event(project_id, "claim.added", {"claim_id": claim.id})
        return claim

    def ground(self, project_id: str, claim_ids: list[str] | None = None) -> Audit:
        self.get_project(project_id)
        state = self.store.load()
        claims = [
            claim
            for claim in state["claims"].values()
            if claim["project_id"] == project_id and (claim_ids is None or claim["id"] in claim_ids)
        ]
        if not claims:
            raise ValueError("project has no matching claims to ground")
        text = "\n".join(f"- {claim['text']}" for claim in claims)
        result = self.cite.ground(text)
        audit = Audit(
            id=machine_id("raudit"),
            project_id=project_id,
            claim_ids=[claim["id"] for claim in claims],
            engine=result.engine,
            status=result.status,
            raw=result.raw,
            structured=result.structured,
        )
        state = self.store.load()
        state["audits"][audit.id] = dump_model(audit)
        for claim in claims:
            stored = state["claims"][claim["id"]]
            stored.setdefault("audit_ids", []).append(audit.id)
            # "audited" means a grounding pass ran. It intentionally does not mean supported.
            if result.status == "completed":
                stored["status"] = "audited"
        self.store.save(state)
        self._event(project_id, "cite.grounded", {"audit_id": audit.id, "status": audit.status})
        return audit

    def add_evidence(
        self,
        project_id: str,
        *,
        source: str,
        locator: str | None = None,
        summary: str | None = None,
        claim_ids: list[str] | None = None,
        provenance: dict[str, Any] | None = None,
    ):
        from .models import Evidence

        self.get_project(project_id)
        evidence = Evidence(
            id=machine_id("revidence"),
            project_id=project_id,
            source=source,
            locator=locator,
            summary=summary,
            provenance=provenance or {},
        )
        state = self.store.load()
        state["evidence"][evidence.id] = dump_model(evidence)
        for claim_id in claim_ids or []:
            claim = state["claims"].get(claim_id)
            if claim is None or claim["project_id"] != project_id:
                raise ValueError(f"claim does not belong to project: {claim_id}")
            claim.setdefault("evidence_ids", []).append(evidence.id)
        self.store.save(state)
        self._event(project_id, "evidence.added", {"evidence_id": evidence.id})
        return evidence

    def invoke(self, project_id: str, implementation_id: str, input_data: Any = None) -> Run:
        self.get_project(project_id)
        implementation = self.refinery.get_implementation(implementation_id, project_id=project_id)
        result = self.refinery.execute(implementation_id, project_id=project_id, input_data=input_data)
        run = Run(
            id=machine_id("rrun"),
            project_id=project_id,
            implementation_id=implementation_id,
            capability_id=implementation["capability_id"],
            provider=implementation["provider"],
            input=input_data,
            status=result.status,
            output=result.output,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
        )
        state = self.store.load()
        state["runs"][run.id] = dump_model(run)
        self.store.save(state)
        self._event(
            project_id,
            "implementation.ran",
            {
                "run_id": run.id,
                "implementation_id": implementation_id,
                "capability_id": run.capability_id,
                "status": run.status,
            },
        )
        return run

    def add_artifact(
        self,
        project_id: str,
        *,
        name: str,
        kind: str,
        uri: str | None = None,
        description: str = "",
        reusable: bool = False,
        capability_id: str | None = None,
    ) -> Artifact:
        self.get_project(project_id)
        artifact = Artifact(
            id=machine_id("rart"),
            project_id=project_id,
            name=name,
            kind=kind,
            uri=uri,
            description=description,
            reusable=reusable,
            capability_id=capability_id,
        )
        state = self.store.load()
        state["artifacts"][artifact.id] = dump_model(artifact)
        self.store.save(state)
        self._event(project_id, "artifact.added", {"artifact_id": artifact.id})
        return artifact

    def add_experiment(
        self,
        project_id: str,
        *,
        name: str,
        method: str,
        result: str,
        verdict: str = "inconclusive",
        metrics: dict[str, Any] | None = None,
        claim_ids: list[str] | None = None,
        artifact_ids: list[str] | None = None,
        run_ids: list[str] | None = None,
    ) -> Experiment:
        self.get_project(project_id)
        state = self.store.load()
        for claim_id in claim_ids or []:
            if state["claims"].get(claim_id, {}).get("project_id") != project_id:
                raise ValueError(f"claim does not belong to project: {claim_id}")
        for artifact_id in artifact_ids or []:
            if state["artifacts"].get(artifact_id, {}).get("project_id") != project_id:
                raise ValueError(f"artifact does not belong to project: {artifact_id}")
        for run_id in run_ids or []:
            if state["runs"].get(run_id, {}).get("project_id") != project_id:
                raise ValueError(f"run does not belong to project: {run_id}")
        experiment = Experiment(
            id=machine_id("rexp"),
            project_id=project_id,
            name=name,
            method=method,
            result=result,
            verdict=verdict,
            metrics=metrics or {},
            claim_ids=claim_ids or [],
            artifact_ids=artifact_ids or [],
            run_ids=run_ids or [],
        )
        state["experiments"][experiment.id] = dump_model(experiment)
        self.store.save(state)
        self._event(project_id, "experiment.recorded", {"experiment_id": experiment.id, "verdict": verdict})
        return experiment

    def promote_capability(self, project_id: str, capability_id: str, experiment_id: str):
        state = self.store.load()
        cap = state["capabilities"].get(capability_id)
        if cap is None or cap.get("project_id") != project_id:
            raise ValueError("capability does not belong to project")
        experiment = state["experiments"].get(experiment_id)
        if experiment is None or experiment["project_id"] != project_id:
            raise ValueError("experiment does not belong to project")
        if experiment["verdict"] not in {"passed", "supported"}:
            raise ValueError("promotion requires a passed/supported experiment")

        implementations = [
            impl for impl in state["implementations"].values()
            if impl["capability_id"] == capability_id
        ]
        successful_runs = [
            state["runs"][run_id]
            for run_id in experiment.get("run_ids", [])
            if run_id in state["runs"]
            and state["runs"][run_id].get("capability_id") == capability_id
            and state["runs"][run_id].get("status") == "succeeded"
        ]
        if implementations and not successful_runs:
            raise ValueError("promotion of an executable capability requires a successful run linked to the experiment")

        successful_impl_ids = {run["implementation_id"] for run in successful_runs}
        for impl in implementations:
            if impl["id"] in successful_impl_ids:
                impl["validated"] = True
        self.store.save(state)

        validation = {
            "experiment_id": experiment_id,
            "verdict": experiment["verdict"],
            "metrics": experiment.get("metrics", {}),
            "run_ids": [run["id"] for run in successful_runs],
        }
        promoted = self.refinery.promote(capability_id, evidence=validation)
        self._event(project_id, "capability.promoted", {"from": capability_id, "to": promoted.id, "experiment_id": experiment_id})
        return promoted

    def dossier(self, project_id: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        state = self.store.load()
        owned = lambda bucket: [item for item in state[bucket].values() if item.get("project_id") == project_id]
        local_caps = owned("capabilities")
        return {
            "project": project,
            "claims": owned("claims"),
            "evidence": owned("evidence"),
            "audits": owned("audits"),
            "capabilities": local_caps,
            "implementations": [
                item
                for item in state["implementations"].values()
                if item.get("project_id") == project_id
            ],
            "artifacts": owned("artifacts"),
            "runs": owned("runs"),
            "experiments": owned("experiments"),
            "events": [event for event in state["events"] if event.get("project_id") == project_id],
            "generated_at": utcnow(),
        }

    def dossier_markdown(self, project_id: str) -> str:
        data = self.dossier(project_id)
        project = data["project"]
        lines = [
            f"# {project['title']}",
            "",
            "## Problem",
            project["problem"],
            "",
            "## Claims",
        ]
        if data["claims"]:
            lines.extend(f"- `{c['id']}` [{c['status']}] {c['text']}" for c in data["claims"])
        else:
            lines.append("- None")
        lines.extend(["", "## Capabilities"])
        if data["capabilities"]:
            lines.extend(f"- `{c['id']}` **{c['name']}** — {c['description']}" for c in data["capabilities"])
        else:
            lines.append("- None")
        lines.extend(["", "## Artifacts"])
        if data["artifacts"]:
            lines.extend(f"- `{a['id']}` **{a['name']}** ({a['kind']}) — {a['description']}" for a in data["artifacts"])
        else:
            lines.append("- None")
        lines.extend(["", "## Runs"])
        if data["runs"]:
            lines.extend(f"- `{r['id']}` `{r['implementation_id']}` — {r['status']} ({r['duration_ms']} ms)" for r in data["runs"])
        else:
            lines.append("- None")
        lines.extend(["", "## Experiments"])
        if data["experiments"]:
            lines.extend(f"- `{e['id']}` **{e['name']}** — {e['verdict']}: {e['result']}" for e in data["experiments"])
        else:
            lines.append("- None")
        lines.extend(["", "## Cite audits"])
        if data["audits"]:
            lines.extend(f"- `{a['id']}` {a['engine']} — {a['status']}" for a in data["audits"])
        else:
            lines.append("- None")
        return "\n".join(lines) + "\n"
