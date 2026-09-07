from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .problem_governance import (
    GateKind,
    GateStatus,
    GovernanceRegistry,
    InterventionEnvelope,
    Reversibility,
)


DEFAULT_STATE = Path(".cite-refinery/problem-governance.json")


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="problem-governance", description="Problem Commons Public-Good governance extension")
    parser.add_argument("--state", dest="state_path", default=str(DEFAULT_STATE))
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create")
    create.add_argument("problem_id")
    create.add_argument("subproblem_id")
    create.add_argument("title")
    create.add_argument("--target-transition", required=True)
    create.add_argument("--diagnosis", required=True)
    create.add_argument("--intervention-class", required=True)
    create.add_argument("--smallest-change", required=True)
    create.add_argument("--mechanism", required=True)
    create.add_argument("--reversibility", choices=[x.value for x in Reversibility], default="unknown")
    create.add_argument("--rollback", default="")
    create.add_argument("--evidence-ref", action="append", default=[])
    create.add_argument("--capability-ref", action="append", default=[])
    create.add_argument("--outcome-metric", action="append", default=[])
    create.add_argument("--monitoring-plan", required=True)
    create.add_argument("--public-good-ref", default="")

    listing = sub.add_parser("list")
    listing.add_argument("--problem")

    show = sub.add_parser("show")
    show.add_argument("envelope_id")

    gate = sub.add_parser("gate-set")
    gate.add_argument("envelope_id")
    gate.add_argument("kind", choices=[x.value for x in GateKind])
    gate.add_argument("status", choices=[x.value for x in GateStatus])
    gate.add_argument("--requirement", default="")
    gate.add_argument("--evidence-ref", action="append", default=[])
    gate.add_argument("--reviewer", default="")
    gate.add_argument("--notes", default="")

    ready = sub.add_parser("readiness")
    ready.add_argument("envelope_id")
    ready.add_argument("--target", choices=["review", "test", "deploy"], default="deploy")

    review = sub.add_parser("mark-reviewed")
    review.add_argument("envelope_id")

    test_ready = sub.add_parser("mark-test-ready")
    test_ready.add_argument("envelope_id")

    test = sub.add_parser("test-record")
    test.add_argument("envelope_id")
    test.add_argument("--evaluator", required=True)
    test.add_argument("--scope", required=True)
    test.add_argument("--passed", action="store_true")
    test.add_argument("--summary", required=True)
    test.add_argument("--evidence-ref", action="append", default=[])
    test.add_argument("--guardrail-breach", action="append", default=[])

    handoff = sub.add_parser("authorize")
    handoff.add_argument("envelope_id")
    handoff.add_argument("--actor", required=True)
    handoff.add_argument("--scope", required=True)
    handoff.add_argument("--decision", choices=["authorized", "denied", "conditional"], required=True)
    handoff.add_argument("--receipt-ref", required=True)
    handoff.add_argument("--notes", default="")

    deploy_ready = sub.add_parser("mark-deploy-ready")
    deploy_ready.add_argument("envelope_id")

    handed_off = sub.add_parser("mark-handed-off")
    handed_off.add_argument("envelope_id")

    export = sub.add_parser("export")
    export.add_argument("path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    registry = GovernanceRegistry.load(args.state_path)
    changed = False
    try:
        if args.command == "create":
            envelope = InterventionEnvelope(
                problem_id=args.problem_id,
                subproblem_id=args.subproblem_id,
                title=args.title,
                target_transition=args.target_transition,
                diagnosis_hypothesis=args.diagnosis,
                intervention_class=args.intervention_class,
                smallest_feasible_change=args.smallest_change,
                expected_mechanism=args.mechanism,
                reversibility=Reversibility(args.reversibility),
                rollback_plan=args.rollback,
                evidence_refs=args.evidence_ref,
                capability_refs=args.capability_ref,
                outcome_metrics=args.outcome_metric,
                monitoring_plan=args.monitoring_plan,
                public_good_ref=args.public_good_ref,
            )
            registry.add(envelope); _print(envelope.to_dict()); changed = True
        elif args.command == "list":
            rows = registry.for_problem(args.problem) if args.problem else list(registry.envelopes.values())
            _print([{"id": x.id, "problem_id": x.problem_id, "subproblem_id": x.subproblem_id, "title": x.title, "state": x.state.value} for x in rows])
        elif args.command == "show":
            _print(registry.get(args.envelope_id).to_dict())
        elif args.command == "gate-set":
            envelope = registry.get(args.envelope_id)
            gate = envelope.set_gate(GateKind(args.kind), GateStatus(args.status), requirement=args.requirement, evidence_refs=args.evidence_ref, reviewer=args.reviewer, notes=args.notes)
            _print({"envelope_id": envelope.id, "gate": gate.kind.value, "status": gate.status.value}); changed = True
        elif args.command == "readiness":
            _print(registry.get(args.envelope_id).readiness(args.target).__dict__)
        elif args.command == "mark-reviewed":
            envelope = registry.get(args.envelope_id); envelope.mark_reviewed(); _print(envelope.to_dict()); changed = True
        elif args.command == "mark-test-ready":
            envelope = registry.get(args.envelope_id); envelope.mark_test_ready(); _print(envelope.to_dict()); changed = True
        elif args.command == "test-record":
            envelope = registry.get(args.envelope_id)
            receipt = envelope.record_test(evaluator=args.evaluator, scope=args.scope, passed=args.passed, summary=args.summary, evidence_refs=args.evidence_ref, guardrail_breaches=args.guardrail_breach)
            _print(receipt); changed = True
        elif args.command == "authorize":
            envelope = registry.get(args.envelope_id)
            receipt = envelope.authorize_handoff(authority_actor=args.actor, authority_scope=args.scope, decision=args.decision, receipt_ref=args.receipt_ref, notes=args.notes)
            _print(receipt); changed = True
        elif args.command == "mark-deploy-ready":
            envelope = registry.get(args.envelope_id); envelope.mark_deploy_ready(); _print(envelope.to_dict()); changed = True
        elif args.command == "mark-handed-off":
            envelope = registry.get(args.envelope_id); envelope.mark_handed_off(); _print(envelope.to_dict()); changed = True
        elif args.command == "export":
            Path(args.path).write_text(json.dumps(registry.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
            _print({"written": args.path, "envelopes": len(registry.envelopes)})
        else:
            parser.error("unknown command")
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if changed:
        registry.save(args.state_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
