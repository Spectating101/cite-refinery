from __future__ import annotations

import re
from typing import Any

from .execution import ExecutionResult, ExecutorRegistry
from .models import Capability, Implementation, dump_model, machine_id
from .store import JsonStore


def _terms(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9_+-]+", text.lower()) if len(token) > 1}


class RefineryKernel:
    """Capability registry with global state plus per-project overlays.

    Local capabilities are visible to their project immediately. Promotion copies
    a proven local capability into the shared registry so later projects inherit it.
    """

    def __init__(self, store: JsonStore, executors: ExecutorRegistry | None = None) -> None:
        self.store = store
        self.executors = executors or ExecutorRegistry()

    def register_capability(
        self,
        *,
        name: str,
        description: str,
        tags: list[str] | None = None,
        project_id: str | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> Capability:
        capability = Capability(
            id=machine_id("rcap"),
            name=name,
            description=description,
            tags=sorted(set(tags or [])),
            scope="project" if project_id else "global",
            project_id=project_id,
            provenance=provenance or {},
        )
        state = self.store.load()
        state["capabilities"][capability.id] = dump_model(capability)
        self.store.save(state)
        return capability

    def register_implementation(
        self,
        *,
        capability_id: str,
        provider: str,
        invocation: dict[str, Any] | None = None,
        project_id: str | None = None,
        validated: bool = False,
    ) -> Implementation:
        state = self.store.load()
        capability = state["capabilities"].get(capability_id)
        if capability is None:
            raise KeyError(f"unknown capability: {capability_id}")
        if capability.get("project_id") and capability.get("project_id") != project_id:
            raise ValueError("implementation project must match its project-scoped capability")
        implementation = Implementation(
            id=machine_id("rimpl"),
            capability_id=capability_id,
            provider=provider,
            invocation=invocation or {},
            scope=capability["scope"],
            project_id=capability.get("project_id"),
            validated=validated,
        )
        state["implementations"][implementation.id] = dump_model(implementation)
        self.store.save(state)
        return implementation

    def get_implementation(self, implementation_id: str, *, project_id: str) -> dict[str, Any]:
        state = self.store.load()
        implementation = state["implementations"].get(implementation_id)
        if implementation is None:
            raise KeyError(f"unknown implementation: {implementation_id}")
        owner = implementation.get("project_id")
        if implementation.get("scope") == "project" and owner != project_id:
            raise ValueError("project cannot invoke another project's local implementation")
        return implementation

    def execute(self, implementation_id: str, *, project_id: str, input_data: Any = None) -> ExecutionResult:
        implementation = self.get_implementation(implementation_id, project_id=project_id)
        return self.executors.execute(
            implementation["provider"],
            dict(implementation.get("invocation", {})),
            input_data,
        )

    def search(self, query: str, *, project_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        state = self.store.load()
        needle = _terms(query)
        ranked: list[tuple[float, dict[str, Any]]] = []
        for capability in state["capabilities"].values():
            owner = capability.get("project_id")
            if capability.get("scope") == "project" and owner != project_id:
                continue
            haystack = _terms(" ".join([capability["name"], capability["description"], *capability.get("tags", [])]))
            overlap = len(needle & haystack)
            phrase_bonus = 2.0 if query.lower() in capability["name"].lower() else 0.0
            local_bonus = 0.25 if project_id and owner == project_id else 0.0
            if not needle:
                score = local_bonus
            elif overlap == 0 and phrase_bonus == 0:
                continue
            else:
                score = overlap / max(len(needle), 1) + phrase_bonus + local_bonus
            item = dict(capability)
            item["score"] = round(score, 4)
            item["implementations"] = [
                impl
                for impl in state["implementations"].values()
                if impl["capability_id"] == capability["id"]
            ]
            ranked.append((score, item))
        ranked.sort(key=lambda pair: (-pair[0], pair[1]["name"].lower(), pair[1]["id"]))
        return [item for _, item in ranked[:limit]]

    def promote(self, capability_id: str, *, evidence: dict[str, Any] | None = None) -> Capability:
        state = self.store.load()
        raw = state["capabilities"].get(capability_id)
        if raw is None:
            raise KeyError(f"unknown capability: {capability_id}")
        if raw.get("scope") != "project":
            raise ValueError("only project-scoped capabilities can be promoted")

        promoted = Capability(
            id=machine_id("rcap"),
            name=raw["name"],
            description=raw["description"],
            tags=list(raw.get("tags", [])),
            scope="global",
            project_id=None,
            provenance={
                **raw.get("provenance", {}),
                "promoted_from": capability_id,
                "promoted_from_project": raw.get("project_id"),
                "validation": evidence or {},
            },
        )
        state["capabilities"][promoted.id] = dump_model(promoted)
        for impl in list(state["implementations"].values()):
            if impl["capability_id"] != capability_id:
                continue
            clone = Implementation(
                id=machine_id("rimpl"),
                capability_id=promoted.id,
                provider=impl["provider"],
                invocation=dict(impl.get("invocation", {})),
                scope="global",
                project_id=None,
                validated=bool(impl.get("validated")),
            )
            state["implementations"][clone.id] = dump_model(clone)
        self.store.save(state)
        return promoted
