from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import CiteRefinery


def _print(value) -> None:
    if hasattr(value, "__dataclass_fields__"):
        from dataclasses import asdict
        value = asdict(value)
    elif isinstance(value, list) and value and hasattr(value[0], "__dataclass_fields__"):
        from dataclasses import asdict
        value = [asdict(item) for item in value]
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def _packet_paths(values: list[str]) -> list[Path]:
    paths: list[Path] = []
    for raw in values:
        path = Path(raw)
        if path.is_dir():
            paths.extend(sorted(path.rglob("*.json")))
        else:
            paths.append(path)
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery", description="Problem-to-evidence-to-solution lifecycle")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a project branch")
    init.add_argument("title")
    init.add_argument("--problem", required=True)
    init.add_argument("--branch")

    nocturnal = sub.add_parser("nocturnal-ingest", help="Import one Nocturnal evidence-history/research packet")
    nocturnal.add_argument("project_id")
    nocturnal.add_argument("packet")
    nocturnal.add_argument("--packet-ref")

    nocturnal_many = sub.add_parser("nocturnal-ingest-many", help="Import Nocturnal JSON case files from files or directories")
    nocturnal_many.add_argument("project_id")
    nocturnal_many.add_argument("packets", nargs="+")

    brief = sub.add_parser("research-brief", help="Build a Cite research brief from Nocturnal observations")
    brief.add_argument("project_id")
    brief.add_argument("--observation-id", action="append", default=[])
    brief.add_argument("--question", action="append", default=[])
    brief.add_argument("--title")
    brief.add_argument("--no-structural-fallback", action="store_true")

    agenda = sub.add_parser("research-agenda", help="Cluster a large Nocturnal corpus into bounded Cite research briefs")
    agenda.add_argument("project_id")
    agenda.add_argument("--max-observations", type=int, default=30)
    agenda.add_argument("--country", action="append", default=[])
    agenda.add_argument("--domain", action="append", default=[])
    agenda.add_argument("--cohort", action="append", default=[])

    research_ground = sub.add_parser("research-ground", help="Ground a problem research brief through Cite-Agent")
    research_ground.add_argument("project_id")
    research_ground.add_argument("brief_id")
    research_ground.add_argument("--max-prompt-chars", type=int, default=30000)
    research_ground.add_argument("--max-observation-chars", type=int, default=900)

    scale_report = sub.add_parser("scale-report", help="Report empirical, research and solution coverage for a project")
    scale_report.add_argument("project_id")

    claim = sub.add_parser("claim-add", help="Add an empirical/technical claim")
    claim.add_argument("project_id")
    claim.add_argument("text")

    ground = sub.add_parser("ground", help="Audit project claims with Cite-Agent ground_claims")
    ground.add_argument("project_id")
    ground.add_argument("claim_ids", nargs="*")

    req = sub.add_parser("requirement-add", help="Record a capability requirement derived from the research layer")
    req.add_argument("project_id")
    req.add_argument("text")
    req.add_argument("--kind", default="capability")
    req.add_argument("--tag", action="append", default=[])
    req.add_argument("--source-brief-id")
    req.add_argument("--source-audit-id")

    solmap = sub.add_parser("solution-map", help="Search canonical Refinery for requirement coverage")
    solmap.add_argument("project_id")
    solmap.add_argument("requirement_ids", nargs="*")
    solmap.add_argument("--limit", type=int, default=20)

    adopt = sub.add_parser("cap-adopt", help="Adopt a mapped solution as a project-local capability")
    adopt.add_argument("project_id")
    adopt.add_argument("requirement_id")
    adopt.add_argument("name")
    adopt.add_argument("--description", required=True)
    adopt.add_argument("--tag", action="append", default=[])
    adopt.add_argument("--solution-map-id")
    adopt.add_argument("--candidate-ref")

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

    invoke = sub.add_parser("invoke", help="Execute a registered implementation and record the run")
    invoke.add_argument("project_id")
    invoke.add_argument("implementation_id")
    invoke.add_argument("--input-json", default="null")

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
    exp.add_argument("--run-id", action="append", default=[])

    promote = sub.add_parser("promote", help="Promote a validated project capability to shared registry")
    promote.add_argument("project_id")
    promote.add_argument("capability_id")
    promote.add_argument("--experiment-id", required=True)

    dossier = sub.add_parser("dossier", help="Export the project's problem/research/build chain")
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
        elif args.command == "nocturnal-ingest":
            packet_path = Path(args.packet)
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            _print(app.ingest_nocturnal_packet(args.project_id, packet, packet_ref=args.packet_ref or str(packet_path)))
        elif args.command == "nocturnal-ingest-many":
            imported = []
            failures = []
            for packet_path in _packet_paths(args.packets):
                try:
                    packet = json.loads(packet_path.read_text(encoding="utf-8"))
                    observations = app.ingest_nocturnal_packet(args.project_id, packet, packet_ref=str(packet_path))
                    imported.append({"packet": str(packet_path), "observations": len(observations)})
                except (ValueError, json.JSONDecodeError, OSError) as exc:
                    failures.append({"packet": str(packet_path), "error": str(exc)})
            _print({"packets_imported": len(imported), "imports": imported, "failures": failures})
            if failures:
                return 1
        elif args.command == "research-brief":
            _print(app.prepare_research_brief(
                args.project_id,
                observation_ids=args.observation_id or None,
                title=args.title,
                extra_questions=args.question,
                allow_structural_fallback=not args.no_structural_fallback,
            ))
        elif args.command == "research-agenda":
            _print(app.prepare_research_agenda(
                args.project_id,
                max_observations_per_brief=args.max_observations,
                countries=args.country or None,
                domains=args.domain or None,
                cohorts=args.cohort or None,
            ))
        elif args.command == "research-ground":
            _print(app.ground_research_brief(
                args.project_id,
                args.brief_id,
                max_prompt_chars=args.max_prompt_chars,
                max_observation_chars=args.max_observation_chars,
            ))
        elif args.command == "scale-report":
            _print(app.scale_report(args.project_id))
        elif args.command == "claim-add":
            _print(app.add_claim(args.project_id, args.text))
        elif args.command == "ground":
            _print(app.ground(args.project_id, args.claim_ids or None))
        elif args.command == "requirement-add":
            _print(app.add_requirement(args.project_id, args.text, kind=args.kind, tags=args.tag, source_brief_id=args.source_brief_id, source_audit_id=args.source_audit_id))
        elif args.command == "solution-map":
            _print(app.map_requirements(args.project_id, args.requirement_ids or None, limit=args.limit))
        elif args.command == "cap-adopt":
            _print(app.adopt_capability(args.project_id, args.requirement_id, name=args.name, description=args.description, tags=args.tag, solution_map_id=args.solution_map_id, candidate_ref=args.candidate_ref))
        elif args.command == "cap-add":
            _print(app.refinery.register_capability(name=args.name, description=args.description, tags=args.tag, project_id=args.project_id))
        elif args.command == "impl-add":
            _print(app.refinery.register_implementation(capability_id=args.capability_id, provider=args.provider, invocation=json.loads(args.invocation_json), project_id=args.project_id, validated=args.validated))
        elif args.command == "cap-search":
            _print(app.refinery.search(args.query, project_id=args.project_id, limit=args.limit))
        elif args.command == "invoke":
            _print(app.invoke(args.project_id, args.implementation_id, json.loads(args.input_json)))
        elif args.command == "artifact-add":
            _print(app.add_artifact(args.project_id, name=args.name, kind=args.kind, uri=args.uri, description=args.description, reusable=args.reusable, capability_id=args.capability_id))
        elif args.command == "experiment-add":
            _print(app.add_experiment(args.project_id, name=args.name, method=args.method, result=args.result, verdict=args.verdict, metrics=json.loads(args.metrics_json), claim_ids=args.claim_id, artifact_ids=args.artifact_id, run_ids=args.run_id))
        elif args.command == "promote":
            _print(app.promote_capability(args.project_id, args.capability_id, args.experiment_id))
        elif args.command == "dossier":
            output = app.dossier_markdown(args.project_id) if args.format == "markdown" else json.dumps(app.dossier(args.project_id), indent=2, ensure_ascii=False)
            if args.out:
                Path(args.out).write_text(output + ("" if output.endswith("\n") else "\n"), encoding="utf-8")
                print(args.out)
            else:
                print(output)
        return 0
    except (KeyError, ValueError, json.JSONDecodeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
