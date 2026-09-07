from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .problem_commons import AttemptStatus, ProblemCommons, ProblemSignal, ProblemStatus, Visibility


DEFAULT_STATE = Path(".cite-refinery/problem-commons.json")


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="problem-commons", description="Living Problem Commons V0.1")
    parser.add_argument("--state", default=str(DEFAULT_STATE), help="state JSON path")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a candidate problem")
    init.add_argument("title")
    init.add_argument("--condition", required=True)
    init.add_argument("--unresolved", required=True)
    init.add_argument("--steward", required=True)
    init.add_argument("--domain", default="general")
    init.add_argument("--geography")
    init.add_argument("--owner", default="")

    signal_import = sub.add_parser("signal-import", help="Import provenance-preserving candidate signals from JSON")
    signal_import.add_argument("path")
    signal_import.add_argument("--steward", required=True)

    listing = sub.add_parser("list", help="List problems")
    listing.add_argument("--public", action="store_true")

    show = sub.add_parser("show", help="Show one problem")
    show.add_argument("problem_id")
    show.add_argument("--public", action="store_true")

    ready = sub.add_parser("readiness", help="Check publication readiness")
    ready.add_argument("problem_id")
    ready.add_argument("--open", action="store_true", help="also require decomposition")

    trans = sub.add_parser("transition", help="Move problem lifecycle state")
    trans.add_argument("problem_id")
    trans.add_argument("status", choices=[x.value for x in ProblemStatus])
    trans.add_argument("--actor", required=True)
    trans.add_argument("--reason", required=True)

    sp = sub.add_parser("subproblem-add", help="Add a contribution path")
    sp.add_argument("problem_id")
    sp.add_argument("title")
    sp.add_argument("--description", required=True)
    sp.add_argument("--kind", required=True)
    sp.add_argument("--skill", action="append", default=[])
    sp.add_argument("--interest", action="append", default=[])
    sp.add_argument("--output", action="append", default=[])
    sp.add_argument("--effort", default="unspecified")
    sp.add_argument("--credential", action="append", default=[])

    attempt = sub.add_parser("attempt-start", help="Start an attempt")
    attempt.add_argument("problem_id")
    attempt.add_argument("title")
    attempt.add_argument("--contributor", required=True)
    attempt.add_argument("--subproblem", action="append", required=True)
    attempt.add_argument("--note", default="")

    asub = sub.add_parser("attempt-submit", help="Submit an active attempt")
    asub.add_argument("problem_id")
    asub.add_argument("attempt_id")

    arev = sub.add_parser("attempt-review", help="Review a submitted attempt")
    arev.add_argument("problem_id")
    arev.add_argument("attempt_id")
    arev.add_argument("--reviewer", required=True)
    arev.add_argument("--verdict", required=True, choices=["accept", "reject", "revise"])
    arev.add_argument("--note", default="")

    auth = sub.add_parser("authorize", help="Record competent authority decision")
    auth.add_argument("problem_id")
    auth.add_argument("--actor", required=True)
    auth.add_argument("--scope", required=True)
    auth.add_argument("--decision", required=True, choices=["authorized", "denied", "conditional"])
    auth.add_argument("--rationale", default="")
    auth.add_argument("--receipt")

    out = sub.add_parser("outcome-add", help="Record observed outcome")
    out.add_argument("problem_id")
    out.add_argument("--summary", required=True)
    out.add_argument("--change", required=True)
    out.add_argument("--disposition", default="observed")
    out.add_argument("--attribution", default="not_established")
    out.add_argument("--evidence-ref", action="append", default=[])

    match = sub.add_parser("match", help="Match a contributor to open subproblems")
    match.add_argument("problem_id")
    match.add_argument("--skill", action="append", default=[])
    match.add_argument("--interest", action="append", default=[])
    match.add_argument("--credential", action="append", default=[])
    match.add_argument("--kind", action="append", default=[])

    export = sub.add_parser("export-public", help="Export redacted public catalog")
    export.add_argument("--out", required=True)

    search = sub.add_parser("search", help="Search problem objects")
    search.add_argument("query")
    search.add_argument("--public", action="store_true")

    return parser


def _import_signals(commons: ProblemCommons, path: Path, steward: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "problem-signals/v0.1":
        raise ValueError(f"unsupported signal schema: {payload.get('schema')}")
    rows = payload.get("signals")
    if not isinstance(rows, list):
        raise ValueError("signal file requires a signals list")

    existing = {(ref.system, ref.ref) for packet in commons.problems.values() for ref in packet.external_refs if ref.relation == "problem_candidate"}
    created: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    for raw in rows:
        signal = ProblemSignal(
            id=str(raw["id"]),
            source_system=str(raw["source_system"]),
            source_ref=str(raw["source_ref"]),
            title=str(raw["title"]),
            observed_condition=str(raw["observed_condition"]),
            domain=str(raw.get("domain", "general")),
            geography=raw.get("geography"),
            observed_at=raw.get("observed_at"),
            visibility=Visibility(raw.get("visibility", Visibility.RESTRICTED.value)),
            metadata=dict(raw.get("metadata") or {}),
        )
        key = (signal.source_system, signal.source_ref)
        if key in existing:
            skipped.append({"signal_id": signal.id, "reason": "source_ref_already_imported"})
            continue
        packet = commons.create_from_signal(signal, steward=steward)
        packet.summary = "Candidate signal imported for curation; not a verified public problem."
        packet.tags.extend(["signal-import", str(signal.metadata.get("signal_type", "candidate"))])
        if signal.metadata.get("do_not_publish"):
            packet.tags.append("do-not-publish-before-curation")
        if packet.external_refs:
            packet.external_refs[-1].notes = json.dumps({"signal_id": signal.id, **signal.metadata}, ensure_ascii=False, sort_keys=True)
        created.append({"signal_id": signal.id, "problem_id": packet.id})
        existing.add(key)
    return {"created": created, "skipped": skipped}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    commons = ProblemCommons.load(args.state)
    changed = False

    try:
        if args.command == "init":
            packet = commons.create_problem(title=args.title, observed_condition=args.condition, unresolved_core=args.unresolved, steward=args.steward, domain=args.domain, geography=args.geography, problem_owner=args.owner)
            _print(packet.to_dict())
            changed = True
        elif args.command == "signal-import":
            result = _import_signals(commons, Path(args.path), args.steward)
            _print(result)
            changed = bool(result["created"])
        elif args.command == "list":
            rows = commons.list_public() if args.public else list(commons.problems.values())
            _print([{"id": p.id, "title": p.title, "status": p.status.value, "domain": p.domain} for p in rows])
        elif args.command == "show":
            packet = commons.get(args.problem_id)
            _print(packet.public_snapshot() if args.public else packet.to_dict())
        elif args.command == "readiness":
            report = commons.get(args.problem_id).publishability(require_decomposition=args.open)
            _print({"publishable": report.publishable, "missing": report.missing, "warnings": report.warnings, "checks": report.checks, "completeness": report.completeness})
        elif args.command == "transition":
            packet = commons.get(args.problem_id)
            _print(packet.transition(ProblemStatus(args.status), actor=args.actor, reason=args.reason))
            changed = True
        elif args.command == "subproblem-add":
            packet = commons.get(args.problem_id)
            _print(packet.add_subproblem(args.title, args.description, args.kind, skill_tags=args.skill, interest_tags=args.interest, expected_outputs=args.output, effort=args.effort, required_credentials=args.credential))
            changed = True
        elif args.command == "attempt-start":
            packet = commons.get(args.problem_id)
            _print(packet.start_attempt(title=args.title, contributor=args.contributor, subproblem_ids=args.subproblem, notes=args.note))
            changed = True
        elif args.command == "attempt-submit":
            packet = commons.get(args.problem_id)
            _print(packet.update_attempt_status(args.attempt_id, AttemptStatus.SUBMITTED))
            changed = True
        elif args.command == "attempt-review":
            packet = commons.get(args.problem_id)
            _print(packet.review_attempt(args.attempt_id, reviewer=args.reviewer, verdict=args.verdict, notes=args.note))
            changed = True
        elif args.command == "authorize":
            packet = commons.get(args.problem_id)
            _print(packet.authorize(actor=args.actor, scope=args.scope, decision=args.decision, rationale=args.rationale, receipt_ref=args.receipt))
            changed = True
        elif args.command == "outcome-add":
            packet = commons.get(args.problem_id)
            _print(packet.record_outcome(summary=args.summary, observed_change=args.change, evidence_refs=args.evidence_ref, disposition=args.disposition, attribution=args.attribution))
            changed = True
        elif args.command == "match":
            packet = commons.get(args.problem_id)
            _print([{"subproblem_id": x.subproblem_id, "title": x.title, "kind": x.kind, "score": x.score, "matched_skills": x.matched_skills, "matched_interests": x.matched_interests, "missing_credentials": x.missing_credentials, "rationale": x.rationale} for x in packet.match_contributions(skills=args.skill, interests=args.interest, credentials=args.credential, kinds=args.kind)])
        elif args.command == "search":
            rows = commons.search(args.query, public_only=args.public)
            _print([{"id": p.id, "title": p.title, "status": p.status.value, "domain": p.domain} for p in rows])
        elif args.command == "export-public":
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(commons.public_catalog(), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
            _print({"written": str(target), "problems": len(commons.list_public())})
        else:
            parser.error("unknown command")
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    if changed:
        commons.save(args.state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
