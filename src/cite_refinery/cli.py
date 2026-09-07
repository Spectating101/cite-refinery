from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .orchestrator import CiteRefinery


def _print(value) -> None:
    if hasattr(value, "__dataclass_fields__"):
        from dataclasses import asdict
        value = asdict(value)
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery", description="Evidence-to-solution project lifecycle")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a project branch")
    init.add_argument("title")
    init.add_argument("--problem", required=True)
    init.add_argument("--branch")

    claim = sub.add_parser("claim-add", help="Add an empirical/technical claim")
    claim.add_argument("project_id")
    claim.add_argument("text")

    ground = sub.add_parser("ground", help="Audit project claims with Cite-Agent ground_claims")
    ground.add_argument("project_id")
    ground.add_argument("claim_ids", nargs="*")

    cap = sub.add_parser("cap-add", help="Register a project capability")
    cap.add_argument("project_id")
    cap.add_argument("name")
    cap.add_argument("--description", required=True)
    cap.add_argument("--tag", action="append", default=[])

    impl = sub.add_parser("impl-add", help="Bind an implementation to a capability")
    impl.add_argument("project_id")
    impl.add_argument("capability_id")
    impl.add_argument("provider")
    impl.add_argument("--invocation-json", default="{}")
    impl.add_argument("--validated", action="store_true")

    search = sub.add_parser("cap-search", help="Search local overlay then shared capabilities")
    search.add_argument("project_id")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)

    artifact = sub.add_parser("artifact-add", help="Record a build output")
    artifact.add_argument("project_id")
    artifact.add_argument("name")
    artifact.add_argument("--kind", required=True)
    artifact.add_argument("--uri")
    artifact.add_argument("--description", default="")
    artifact.add_argument("--reusable", action="store_true")
    artifact.add_argument("--capability-id")

    exp = sub.add_parser("experiment-add", help="Record empirical/technical validation")
    exp.add_argument("project_id")
    exp.add_argument("name")
    exp.add_argument("--method", required=True)
    exp.add_argument("--result", required=True)
    exp.add_argument("--verdict", choices=["passed", "supported", "failed", "refuted", "inconclusive"], default="inconclusive")
    exp.add_argument("--metrics-json", default="{}")
    exp.add_argument("--claim-id", action="append", default=[])
    exp.add_argument("--artifact-id", action="append", default=[])

    promote = sub.add_parser("promote", help="Promote a validated project capability to shared registry")
    promote.add_argument("project_id")
    promote.add_argument("capability_id")
    promote.add_argument("--experiment-id")

    dossier = sub.add_parser("dossier", help="Export the project's evidence/build chain")
    dossier.add_argument("project_id")
    dossier.add_argument("--format", choices=["json", "markdown"], default="json")
    dossier.add_argument("--out")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    app = CiteRefinery(args.workspace)
    try:
        if args.command == "init":
            _print(app.init_project(args.title, args.problem, args.branch))
        elif args.command == "claim-add":
            _print(app.add_claim(args.project_id, args.text))
        elif args.command == "ground":
            _print(app.ground(args.project_id, args.claim_ids or None))
        elif args.command == "cap-add":
            _print(app.refinery.register_capability(name=args.name, description=args.description, tags=args.tag, project_id=args.project_id))
        elif args.command == "impl-add":
            _print(app.refinery.register_implementation(capability_id=args.capability_id, provider=args.provider, invocation=json.loads(args.invocation_json), project_id=args.project_id, validated=args.validated))
        elif args.command == "cap-search":
            _print(app.refinery.search(args.query, project_id=args.project_id, limit=args.limit))
        elif args.command == "artifact-add":
            _print(app.add_artifact(args.project_id, name=args.name, kind=args.kind, uri=args.uri, description=args.description, reusable=args.reusable, capability_id=args.capability_id))
        elif args.command == "experiment-add":
            _print(app.add_experiment(args.project_id, name=args.name, method=args.method, result=args.result, verdict=args.verdict, metrics=json.loads(args.metrics_json), claim_ids=args.claim_id, artifact_ids=args.artifact_id))
        elif args.command == "promote":
            _print(app.promote_capability(args.project_id, args.capability_id, args.experiment_id))
        elif args.command == "dossier":
            if args.format == "markdown":
                output = app.dossier_markdown(args.project_id)
            else:
                output = json.dumps(app.dossier(args.project_id), indent=2, ensure_ascii=False)
            if args.out:
                Path(args.out).write_text(output + ("" if output.endswith("\n") else "\n"), encoding="utf-8")
                print(args.out)
            else:
                print(output)
        return 0
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
