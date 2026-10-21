from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import cli as core_cli
from .app import CiteRefinery
from .preflight import build_preflight
from .scorecard import build_end_to_end_scorecard
from .semantic import SemanticGraph
from .semantic_projection import SemanticProjection


def _preflight_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery preflight")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument(
        "--require-reviewed-market",
        action="store_true",
        help="Exit nonzero unless the optional broad reviewed-market supply layer is also ready.",
    )
    return parser


def _research_discover_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery research-discover")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    parser.add_argument("brief_id")
    parser.add_argument("--target-count", type=int, default=30)
    parser.add_argument("--snowball-depth", type=int, default=1)
    parser.add_argument("--max-questions", type=int, default=4)
    return parser


def _scorecard_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery scorecard")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    return parser


def _feedback_request_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery feedback-request")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    parser.add_argument("experiment_id")
    parser.add_argument("--observation-id", action="append", default=None)
    parser.add_argument("--signal", action="append", default=None)
    parser.add_argument("--window-start")
    parser.add_argument("--window-end")
    return parser


def _feedback_ingest_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery feedback-ingest")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    parser.add_argument("--input", required=True, help="Nocturnal feedback result JSON")
    return parser


def _graph_ingest_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery graph-ingest")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    parser.add_argument("--input", required=True, help="Semantic graph packet JSON")
    parser.add_argument("--packet-ref")
    return parser


def _graph_review_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery graph-review")
    parser.add_argument("--workspace", default=".cite-refinery", help="Local workspace")
    parser.add_argument("project_id")
    parser.add_argument("--input", required=True, help="Semantic packet JSON")
    parser.add_argument("--packet-ref", help="Provenance packet reference")
    parser.add_argument("--apply", action="store_true", help="Commit approved packet")
    parser.add_argument(
        "--expected-state-digest",
        help="Workspace digest from an earlier graph-review preview; required with --apply",
    )
    parser.add_argument(
        "--expected-packet-digest",
        help="Exact packet digest from an earlier preview; required with --apply",
    )
    parser.add_argument(
        "--approve-status-changes", action="store_true",
        help="Acknowledge every exact existing-edge status transition in the current preview",
    )
    parser.add_argument(
        "--approval-reason",
        help="Required rationale (12+ chars) when approving existing edge status changes",
    )
    return parser


def _graph_bootstrap_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery graph-bootstrap")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    return parser


def _graph_project_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery graph-project")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    return parser


def _graph_neighborhood_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery graph-neighborhood")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    parser.add_argument("node_id")
    parser.add_argument("--depth", type=int, default=1)
    return parser


def _graph_investigate_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery graph-investigate")
    parser.add_argument("--workspace", default=".cite-refinery")
    parser.add_argument("project_id")
    parser.add_argument("node_id")
    parser.add_argument("--depth", type=int, default=2)
    return parser


def _three_layer_ingest_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery three-layer-ingest")
    parser.add_argument("--workspace", default=".cite-refinery")
    parser.add_argument("project_id")
    parser.add_argument("--atlas", required=True, help="Unified three-layer atlas JSON")
    parser.add_argument("--semantic-review", help="Optional semantic review queue JSON")
    parser.add_argument("--functional-overlay", help="Optional functional overlay JSON")
    parser.add_argument("--apply", action="store_true", help="Commit approved packet")
    parser.add_argument("--expected-state-digest")
    parser.add_argument("--expected-packet-digest")
    return parser


def _component_probe_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery component-probe")
    parser.add_argument("--workspace", default=".cite-refinery")
    parser.add_argument("project_id")
    parser.add_argument("--scratch-root", required=True, help="Scratch directory with pinned repo clones")
    parser.add_argument("--probe", action="append", default=None, help="Specific probe(s): battery, flood, co2")
    return parser


def _competitive_gate_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery competitive-gate")
    parser.add_argument("--output", required=True, help="JSON receipt output path")
    parser.add_argument("--markdown", required=True, help="Markdown report output path")
    parser.add_argument("--model", action="append", dest="models", default=None)
    return parser


def _graph_coverage_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery graph-coverage")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    parser.add_argument("node_id")
    parser.add_argument("--depth", type=int, default=1)
    return parser


def _graph_query_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery graph-query")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    parser.add_argument("--present", action="append", default=[])
    parser.add_argument("--absent", action="append", default=[])
    parser.add_argument("--kind")
    parser.add_argument("--cluster-id")
    parser.add_argument("--depth", type=int, default=1)
    return parser


def _graph_trace_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery graph-trace")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    parser.add_argument("node_id")
    parser.add_argument("--steps-json", required=True, help="JSON list of semantic path steps")
    parser.add_argument("--max-paths", type=int, default=200)
    return parser


def _graph_clusters_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery graph-clusters")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    return parser


def _graph_export_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cite-refinery graph-export")
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("project_id")
    parser.add_argument("--out")
    return parser


def _special_args(raw: list[str], command: str) -> list[str]:
    index = raw.index(command)
    return [*raw[:index], *raw[index + 1 :]]


def main(argv: list[str] | None = None) -> int:
    raw = list(argv) if argv is not None else list(sys.argv[1:])

    if raw and raw[0] == "investigate":
        # Reuse the existing resumable investigator, not another orchestration
        # engine or console script. The original cite-refinery-investigate
        # entrypoint remains supported for backward compatibility.
        from .investigation_cli import main as investigation_main
        value = investigation_main(raw[1:])
        return 0 if value is None else value

    if "preflight" in raw:
        args = _preflight_parser().parse_args(_special_args(raw, "preflight"))
        report = build_preflight(args.workspace)
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
        ready = report["full_broad_supply_ready"] if args.require_reviewed_market else report["core_ready"]
        return 0 if ready else 1

    if "research-discover" in raw:
        args = _research_discover_parser().parse_args(_special_args(raw, "research-discover"))
        app = CiteRefinery(args.workspace)
        try:
            audit = app.discover_research_brief(
                args.project_id,
                args.brief_id,
                target_count=args.target_count,
                snowball_depth=args.snowball_depth,
                max_questions=args.max_questions,
            )
            print(json.dumps(asdict(audit), indent=2, ensure_ascii=False, default=str))
            return 0
        except (KeyError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    if "feedback-request" in raw:
        args = _feedback_request_parser().parse_args(_special_args(raw, "feedback-request"))
        app = CiteRefinery(args.workspace)
        try:
            packet = app.create_nocturnal_feedback_request(
                args.project_id,
                args.experiment_id,
                observation_ids=args.observation_id,
                requested_signals=args.signal,
                window_start=args.window_start,
                window_end=args.window_end,
            )
            print(json.dumps(packet, indent=2, ensure_ascii=False, default=str))
            return 0
        except (KeyError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    if "feedback-ingest" in raw:
        args = _feedback_ingest_parser().parse_args(_special_args(raw, "feedback-ingest"))
        app = CiteRefinery(args.workspace)
        try:
            packet = json.loads(Path(args.input).read_text(encoding="utf-8"))
            if not isinstance(packet, dict):
                raise ValueError("feedback input must be a JSON object")
            result = app.ingest_nocturnal_feedback_result(args.project_id, packet)
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return 0
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    if "scorecard" in raw:
        args = _scorecard_parser().parse_args(_special_args(raw, "scorecard"))
        app = CiteRefinery(args.workspace)
        try:
            scorecard = build_end_to_end_scorecard(app.store.load(), args.project_id)
            print(json.dumps(scorecard, indent=2, ensure_ascii=False, default=str))
            return 0
        except KeyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    if "three-layer-ingest" in raw:
        from .three_layer_native_ingest import as_packet
        args = _three_layer_ingest_parser().parse_args(_special_args(raw, "three-layer-ingest"))
        try:
            atlas_doc = json.loads(Path(args.atlas).read_text(encoding="utf-8"))
            sem_doc = json.loads(Path(args.semantic_review).read_text(encoding="utf-8")) if args.semantic_review else None
            func_doc = json.loads(Path(args.functional_overlay).read_text(encoding="utf-8")) if args.functional_overlay else None
            packet = as_packet(
                atlas_doc,
                args.project_id,
                semantic_review=sem_doc,
                functional_overlay=func_doc,
            )
            graph = SemanticGraph(CiteRefinery(args.workspace).store)
            preview = graph.preview_packet(args.project_id, packet, packet_ref=str(args.atlas))
            if args.apply:
                if not args.expected_state_digest or not args.expected_packet_digest:
                    raise ValueError("--apply requires both --expected-state-digest and --expected-packet-digest")
                if preview["packet_digest"] != args.expected_packet_digest:
                    raise ValueError("packet changed after review; preview again")
                receipt = graph.ingest_packet(
                    args.project_id,
                    packet,
                    packet_ref=str(args.atlas),
                    expected_state_digest=args.expected_state_digest,
                )
                print(json.dumps({"action": "applied", "receipt": receipt}, indent=2, ensure_ascii=False))
            else:
                print(json.dumps({"action": "preview_only", **preview}, indent=2, ensure_ascii=False))
            return 0
        except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    if "component-probe" in raw:
        from .functional_component_probes import SubprocessProbeRunner
        args = _component_probe_parser().parse_args(_special_args(raw, "component-probe"))
        try:
            app = CiteRefinery(args.workspace)
            runner = SubprocessProbeRunner()
            result = runner.run_into_project(
                app,
                args.project_id,
                Path(args.scratch_root),
                probes=args.probe,
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        except (OSError, json.JSONDecodeError, KeyError, ValueError, RuntimeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    if "competitive-gate" in raw:
        from .competitive_gate import main as competitive_gate_main
        return competitive_gate_main(_special_args(raw, "competitive-gate"))

    if "graph-review" in raw:
        args = _graph_review_parser().parse_args(_special_args(raw, "graph-review"))
        try:
            input_path = Path(args.input)
            if input_path.stat().st_size > 8 * 1024 * 1024:
                raise ValueError("semantic packet exceeds 8 MiB local review limit")
            packet = json.loads(input_path.read_text(encoding="utf-8"))
            graph = SemanticGraph(CiteRefinery(args.workspace).store)
            if args.apply:
                if not args.expected_state_digest or not args.expected_packet_digest:
                    raise ValueError("--apply requires both --expected-state-digest and --expected-packet-digest")
                reviewed = graph.preview_packet(args.project_id, packet, packet_ref=args.packet_ref or str(input_path))
                if reviewed["packet_digest"] != args.expected_packet_digest:
                    raise ValueError("packet changed after review; preview again")
                result = graph.ingest_packet(
                    args.project_id, packet,
                    packet_ref=args.packet_ref or str(input_path),
                    expected_state_digest=args.expected_state_digest,
                    approved_status_changes=(
                        reviewed["changed_existing_edge_statuses"]
                        if args.approve_status_changes else None
                    ),
                    approval_reason=args.approval_reason,
                )
                print(json.dumps({"action": "applied", "receipt": result}, indent=2, ensure_ascii=False))
            else:
                result = graph.preview_packet(
                    args.project_id, packet,
                    packet_ref=args.packet_ref or str(input_path),
                )
                print(json.dumps({"action": "preview_only", **result}, indent=2, ensure_ascii=False))
            return 0
        except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    graph_commands = {
        "graph-ingest",
        "graph-bootstrap",
        "graph-project",
        "graph-neighborhood",
        "graph-investigate",
        "graph-coverage",
        "graph-query",
        "graph-trace",
        "graph-clusters",
        "graph-export",
    }
    selected_graph_command = next((command for command in graph_commands if command in raw), None)
    if selected_graph_command:
        parser_map = {
            "graph-ingest": _graph_ingest_parser,
            "graph-bootstrap": _graph_bootstrap_parser,
            "graph-project": _graph_project_parser,
            "graph-neighborhood": _graph_neighborhood_parser,
            "graph-investigate": _graph_investigate_parser,
            "graph-coverage": _graph_coverage_parser,
            "graph-query": _graph_query_parser,
            "graph-trace": _graph_trace_parser,
            "graph-clusters": _graph_clusters_parser,
            "graph-export": _graph_export_parser,
        }
        args = parser_map[selected_graph_command]().parse_args(_special_args(raw, selected_graph_command))
        app = CiteRefinery(args.workspace)
        graph = SemanticGraph(app.store)
        try:
            if selected_graph_command == "graph-ingest":
                input_path = Path(args.input)
                packet = json.loads(input_path.read_text(encoding="utf-8"))
                if not isinstance(packet, dict):
                    raise ValueError("semantic graph input must be a JSON object")
                result = graph.ingest_packet(
                    args.project_id,
                    packet,
                    packet_ref=args.packet_ref or str(input_path),
                )
            elif selected_graph_command == "graph-bootstrap":
                result = graph.bootstrap_project_records(args.project_id)
            elif selected_graph_command == "graph-project":
                result = SemanticProjection(graph).project_all(args.project_id)
            elif selected_graph_command == "graph-neighborhood":
                result = graph.neighborhood(args.project_id, args.node_id, depth=args.depth)
            elif selected_graph_command == "graph-investigate":
                result = graph.investigate_three_layers(
                    args.project_id, args.node_id, max_depth=args.depth,
                )
            elif selected_graph_command == "graph-coverage":
                result = graph.coverage(args.project_id, args.node_id, depth=args.depth)
            elif selected_graph_command == "graph-query":
                result = graph.query_coverage(
                    args.project_id,
                    present=args.present,
                    absent=args.absent,
                    kind=args.kind,
                    cluster_id=args.cluster_id,
                    depth=args.depth,
                )
            elif selected_graph_command == "graph-trace":
                steps = json.loads(args.steps_json)
                if not isinstance(steps, list):
                    raise ValueError("--steps-json must decode to a JSON list")
                result = graph.trace_pattern(
                    args.project_id,
                    args.node_id,
                    steps,
                    max_paths=args.max_paths,
                )
            elif selected_graph_command == "graph-clusters":
                result = graph.cluster_map(args.project_id)
            else:
                result = graph.export(args.project_id)
                if args.out:
                    Path(args.out).write_text(
                        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n",
                        encoding="utf-8",
                    )
                    print(args.out)
                    return 0
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return 0
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    core_cli.CiteRefinery = CiteRefinery
    return core_cli.main(raw)


if __name__ == "__main__":
    raise SystemExit(main())
