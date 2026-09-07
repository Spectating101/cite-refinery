from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


class GateKind(StrEnum):
    EVIDENCE = "evidence"
    SAFETY = "safety"
    INTEGRITY = "integrity"
    RIGHTS = "rights"
    DATA_ACCESS = "data-access"
    REVERSIBILITY = "reversibility"
    PROFESSIONAL = "professional"
    AUTHORITY = "authority"


class GateStatus(StrEnum):
    PENDING = "pending"
    SATISFIED = "satisfied"
    FAILED = "failed"
    NOT_APPLICABLE = "not-applicable"


class Reversibility(StrEnum):
    REVERSIBLE = "reversible"
    PARTIAL = "partially-reversible"
    IRREVERSIBLE = "irreversible"
    UNKNOWN = "unknown"


class EnvelopeState(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    TEST_READY = "test-ready"
    TESTED = "tested"
    DEPLOY_READY = "deploy-ready"
    HANDED_OFF = "handed-off"
    MONITORING = "monitoring"
    CLOSED = "closed"


BASE_DEPLOY_GATES = {
    GateKind.EVIDENCE,
    GateKind.SAFETY,
    GateKind.INTEGRITY,
    GateKind.RIGHTS,
    GateKind.DATA_ACCESS,
    GateKind.REVERSIBILITY,
    GateKind.AUTHORITY,
}


@dataclass(slots=True)
class GovernanceGate:
    kind: GateKind
    status: GateStatus = GateStatus.PENDING
    requirement: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    reviewer: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        self.kind = GateKind(self.kind)
        self.status = GateStatus(self.status)


@dataclass(slots=True)
class TestReceipt:
    id: str
    evaluator: str
    scope: str
    passed: bool
    summary: str
    evidence_refs: list[str] = field(default_factory=list)
    guardrail_breaches: list[str] = field(default_factory=list)


@dataclass(slots=True)
class HandoffReceipt:
    id: str
    authority_actor: str
    authority_scope: str
    decision: str
    receipt_ref: str
    notes: str = ""


@dataclass(slots=True)
class GovernanceReadiness:
    ready: bool
    target: str
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class InterventionEnvelope:
    """Reviewed projection of Public-Good intervention reasoning.

    The envelope does not execute an intervention or grant authority. It records
    the bounded reasoning and receipts required to move a contribution from
    Design toward Test and, only after external authorization, a real handoff.
    """

    problem_id: str
    subproblem_id: str
    title: str
    target_transition: str
    diagnosis_hypothesis: str
    intervention_class: str
    smallest_feasible_change: str
    expected_mechanism: str
    reversibility: Reversibility = Reversibility.UNKNOWN
    rollback_plan: str = ""
    preconditions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    rights_impacts: list[str] = field(default_factory=list)
    safety_risks: list[str] = field(default_factory=list)
    integrity_risks: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    capability_refs: list[str] = field(default_factory=list)
    outcome_metrics: list[str] = field(default_factory=list)
    monitoring_plan: str = ""
    authority_actor: str = ""
    authority_scope: str = ""
    public_good_ref: str = ""
    state: EnvelopeState = EnvelopeState.DRAFT
    gates: list[GovernanceGate] = field(default_factory=list)
    tests: list[TestReceipt] = field(default_factory=list)
    handoffs: list[HandoffReceipt] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.reversibility = Reversibility(self.reversibility)
        self.state = EnvelopeState(self.state)
        self.gates = [gate if isinstance(gate, GovernanceGate) else GovernanceGate(**gate) for gate in self.gates]
        self.tests = [item if isinstance(item, TestReceipt) else TestReceipt(**item) for item in self.tests]
        self.handoffs = [item if isinstance(item, HandoffReceipt) else HandoffReceipt(**item) for item in self.handoffs]

    @property
    def id(self) -> str:
        return f"governance:{self.problem_id}:{self.subproblem_id}"

    def gate(self, kind: GateKind) -> GovernanceGate | None:
        kind = GateKind(kind)
        return next((gate for gate in self.gates if gate.kind == kind), None)

    def set_gate(
        self,
        kind: GateKind,
        status: GateStatus,
        *,
        requirement: str = "",
        evidence_refs: list[str] | None = None,
        reviewer: str = "",
        notes: str = "",
    ) -> GovernanceGate:
        kind, status = GateKind(kind), GateStatus(status)
        gate = self.gate(kind)
        if gate is None:
            gate = GovernanceGate(kind=kind)
            self.gates.append(gate)
        gate.status = status
        if requirement:
            gate.requirement = requirement
        if evidence_refs is not None:
            gate.evidence_refs = list(evidence_refs)
        if reviewer:
            gate.reviewer = reviewer
        if notes:
            gate.notes = notes
        return gate

    def record_test(
        self,
        *,
        evaluator: str,
        scope: str,
        passed: bool,
        summary: str,
        evidence_refs: list[str] | None = None,
        guardrail_breaches: list[str] | None = None,
    ) -> TestReceipt:
        readiness = self.readiness("test")
        if not readiness.ready:
            raise ValueError("test is blocked: " + "; ".join(readiness.blockers))
        receipt = TestReceipt(
            id=f"ptest:{uuid4().hex[:12]}",
            evaluator=evaluator,
            scope=scope,
            passed=passed,
            summary=summary,
            evidence_refs=list(evidence_refs or []),
            guardrail_breaches=list(guardrail_breaches or []),
        )
        self.tests.append(receipt)
        self.state = EnvelopeState.TESTED
        return receipt

    def authorize_handoff(
        self,
        *,
        authority_actor: str,
        authority_scope: str,
        decision: str,
        receipt_ref: str,
        notes: str = "",
    ) -> HandoffReceipt:
        decision = decision.strip().lower()
        if decision not in {"authorized", "denied", "conditional"}:
            raise ValueError("decision must be authorized, denied, or conditional")
        if decision == "authorized":
            self.authority_actor = authority_actor
            self.authority_scope = authority_scope
            self.set_gate(
                GateKind.AUTHORITY,
                GateStatus.SATISFIED,
                requirement=authority_scope,
                evidence_refs=[receipt_ref],
                reviewer=authority_actor,
                notes=notes,
            )
        elif decision == "denied":
            self.set_gate(
                GateKind.AUTHORITY,
                GateStatus.FAILED,
                requirement=authority_scope,
                evidence_refs=[receipt_ref],
                reviewer=authority_actor,
                notes=notes,
            )
        receipt = HandoffReceipt(
            id=f"phandoff:{uuid4().hex[:12]}",
            authority_actor=authority_actor,
            authority_scope=authority_scope,
            decision=decision,
            receipt_ref=receipt_ref,
            notes=notes,
        )
        self.handoffs.append(receipt)
        return receipt

    def readiness(self, target: str = "deploy") -> GovernanceReadiness:
        target = target.strip().lower()
        if target not in {"review", "test", "deploy"}:
            raise ValueError("target must be review, test, or deploy")
        blockers: list[str] = []
        warnings: list[str] = []

        required_text = {
            "problem_id": self.problem_id,
            "subproblem_id": self.subproblem_id,
            "title": self.title,
            "target_transition": self.target_transition,
            "diagnosis_hypothesis": self.diagnosis_hypothesis,
            "intervention_class": self.intervention_class,
            "smallest_feasible_change": self.smallest_feasible_change,
            "expected_mechanism": self.expected_mechanism,
            "monitoring_plan": self.monitoring_plan,
        }
        blockers.extend(f"missing {name}" for name, value in required_text.items() if not value.strip())
        if not self.evidence_refs:
            blockers.append("no evidence refs attached")
        if not self.outcome_metrics:
            blockers.append("no outcome metrics defined")
        if self.reversibility == Reversibility.UNKNOWN:
            blockers.append("reversibility is unknown")
        if self.reversibility in {Reversibility.REVERSIBLE, Reversibility.PARTIAL} and not self.rollback_plan.strip():
            blockers.append("rollback plan required for reversible/partially reversible intervention")
        if self.reversibility == Reversibility.IRREVERSIBLE:
            warnings.append("irreversible intervention requires heightened domain review; this envelope alone cannot justify action")

        required_gates = set(BASE_DEPLOY_GATES)
        if target in {"review", "test"}:
            required_gates.discard(GateKind.AUTHORITY)
        if target == "review":
            required_gates -= {GateKind.REVERSIBILITY, GateKind.DATA_ACCESS}

        for kind in sorted(required_gates, key=lambda item: item.value):
            gate = self.gate(kind)
            if gate is None:
                blockers.append(f"missing {kind.value} gate")
            elif gate.status == GateStatus.FAILED:
                blockers.append(f"{kind.value} gate failed")
            elif gate.status == GateStatus.PENDING:
                blockers.append(f"{kind.value} gate pending")

        professional = self.gate(GateKind.PROFESSIONAL)
        if professional and professional.status in {GateStatus.PENDING, GateStatus.FAILED}:
            blockers.append(f"professional gate {professional.status.value}")

        if target == "deploy":
            passed_tests = [test for test in self.tests if test.passed and not test.guardrail_breaches]
            if not passed_tests:
                blockers.append("no passed test receipt without guardrail breach")
            if not self.authority_actor.strip() or not self.authority_scope.strip():
                blockers.append("named external authority and scope required")

        return GovernanceReadiness(ready=not blockers, target=target, blockers=blockers, warnings=warnings)

    def mark_reviewed(self) -> None:
        readiness = self.readiness("review")
        if not readiness.ready:
            raise ValueError("review is blocked: " + "; ".join(readiness.blockers))
        self.state = EnvelopeState.REVIEWED

    def mark_test_ready(self) -> None:
        readiness = self.readiness("test")
        if not readiness.ready:
            raise ValueError("test readiness is blocked: " + "; ".join(readiness.blockers))
        self.state = EnvelopeState.TEST_READY

    def mark_deploy_ready(self) -> None:
        readiness = self.readiness("deploy")
        if not readiness.ready:
            raise ValueError("deployment is blocked: " + "; ".join(readiness.blockers))
        self.state = EnvelopeState.DEPLOY_READY

    def mark_handed_off(self) -> None:
        if self.state != EnvelopeState.DEPLOY_READY:
            raise ValueError("handoff requires deploy-ready state")
        self.state = EnvelopeState.HANDED_OFF

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["id"] = self.id
        data["reversibility"] = self.reversibility.value
        data["state"] = self.state.value
        for gate in data["gates"]:
            gate["kind"] = str(gate["kind"])
            gate["status"] = str(gate["status"])
        data["review_readiness"] = asdict(self.readiness("review"))
        data["test_readiness"] = asdict(self.readiness("test"))
        data["deploy_readiness"] = asdict(self.readiness("deploy"))
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "InterventionEnvelope":
        data = dict(raw)
        for derived in ("id", "review_readiness", "test_readiness", "deploy_readiness"):
            data.pop(derived, None)
        return cls(**data)


class GovernanceRegistry:
    def __init__(self) -> None:
        self.envelopes: dict[str, InterventionEnvelope] = {}

    def add(self, envelope: InterventionEnvelope) -> InterventionEnvelope:
        self.envelopes[envelope.id] = envelope
        return envelope

    def get(self, envelope_id: str) -> InterventionEnvelope:
        try:
            return self.envelopes[envelope_id]
        except KeyError as exc:
            raise KeyError(f"unknown governance envelope: {envelope_id}") from exc

    def for_problem(self, problem_id: str) -> list[InterventionEnvelope]:
        return [item for item in self.envelopes.values() if item.problem_id == problem_id]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "problem-governance/v0.1",
            "envelopes": [item.to_dict() for item in self.envelopes.values()],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "GovernanceRegistry":
        if raw.get("schema") not in {None, "problem-governance/v0.1"}:
            raise ValueError(f"unsupported governance schema: {raw.get('schema')}")
        registry = cls()
        for item in raw.get("envelopes", []):
            registry.add(InterventionEnvelope.from_dict(item))
        return registry

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> "GovernanceRegistry":
        target = Path(path)
        if not target.exists():
            return cls()
        return cls.from_dict(json.loads(target.read_text(encoding="utf-8")))
