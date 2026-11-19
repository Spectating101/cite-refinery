"""Build, validate, browse and natively ingest the independent repository layer."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from .repository_layer import (
    _identity, build_repository_layer, repository_layer_packet, validate_repository_layer,
)
from .repository_layer_import import connected_snapshot, current_catalog_snapshot, legacy_snapshot, source_lock_snapshot
from .repository_layer_index import build_repository_layer_index
from .repository_layer_view import render_repository_layer


def _write(path: Path, value: dict | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    fd, name = tempfile.mkstemp(prefix=".repository-layer-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build(args: argparse.Namespace) -> dict:
    out = Path(args.output).resolve()
    inputs = out / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    surveys, supplements, summaries = [], [], {}
    for number, path in enumerate(args.survey or []):
        destination = inputs / (f"survey_{number:02d}_" + Path(path).name)
        if Path(path).resolve() != destination.resolve():
            shutil.copyfile(path, destination)
        surveys.append(destination)
    for number, path in enumerate(args.supplemental or []):
        destination = inputs / (f"supplemental_{number:02d}_" + Path(path).name)
        if Path(path).resolve() != destination.resolve():
            shutil.copyfile(path, destination)
        supplements.append(destination)
    if args.connected_profiles:
        normalized = connected_snapshot(args.connected_profiles, args.mapping_audit,
                                        observed_at=args.connected_observed_at)
        destination = inputs / "connected_repository_snapshot.json"
        _write(destination, normalized)
        supplements.append(destination)
        summaries["connected_catalogue"] = normalized["import_summary"]
    elif args.mapping_audit:
        raise ValueError("--mapping-audit requires --connected-profiles")
    for number, path in enumerate(args.current_catalog or []):
        normalized = current_catalog_snapshot(path)
        destination = inputs / f"current_repository_snapshot_{number:02d}.json"
        _write(destination, normalized)
        supplements.append(destination)
        summaries[f"current_catalogue_{number:02d}"] = normalized["import_summary"]
    for number, path in enumerate(getattr(args, "refresh_export", None) or []):
        from .repository_layer_refresh import refresh_snapshot

        normalized = refresh_snapshot(path)
        destination = inputs / f"source_refresh_snapshot_{number:02d}.json"
        _write(destination, normalized)
        supplements.append(destination)
        summaries[f"source_refresh_{number:02d}"] = normalized["import_summary"]
    for number, path in enumerate(args.source_lock or []):
        normalized = source_lock_snapshot(path)
        destination = inputs / f"source_lock_{number:02d}.json"
        _write(destination, normalized)
        supplements.append(destination)
        summaries[f"source_lock_{number:02d}"] = normalized["import_summary"]
    if args.legacy_root:
        normalized = legacy_snapshot(args.legacy_root, args.portfolio)
        destination = inputs / "legacy_repository_observations.json"
        _write(destination, normalized)
        supplements.append(destination)
        summaries["legacy_observations"] = normalized["import_summary"]
    elif args.portfolio:
        raise ValueError("--portfolio requires --legacy-root")
    evidence = None
    if args.evidence:
        evidence = inputs / "reviewed_repository_evidence.json"
        if Path(args.evidence).resolve() != evidence.resolve():
            shutil.copyfile(args.evidence, evidence)
    catalog = build_repository_layer(surveys, supplemental_paths=supplements, evidence_path=evidence)
    expected, inputs_summary = set(), []
    for path in [*surveys, *supplements, *([evidence] if evidence else [])]:
        data = _load(path)
        ids = {_identity(row) for row in data.get("repositories", [])}
        ids.update(_identity(row) for row in data.get("sources", []))
        ids.discard(None)
        expected.update(ids)
        inputs_summary.append({"file": str(path.relative_to(out)), "repository_identities": len(ids),
                               "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    actual = {r["id"] for r in catalog["repositories"]}
    missing, unexpected = sorted(expected - actual), sorted(actual - expected)
    if missing or unexpected:
        raise ValueError("repository identity reconciliation failed")
    packet = repository_layer_packet(catalog)
    if any(n.get("layer") != "program" for n in packet["nodes"]):
        raise ValueError("nonrepository layer entered native projection")
    reconciliation = {
        "schema": "cite_refinery.repository_layer_reconciliation.v1", "scope": "repository_only",
        "catalog_digest": catalog["catalog_digest"], "expected_repository_count": len(expected),
        "actual_repository_count": len(actual), "missing_repository_ids": missing,
        "unexpected_repository_ids": unexpected, "input_sources": inputs_summary,
        "source_summaries": summaries, "native_node_count": len(packet["nodes"]),
        "native_edge_count": len(packet["edges"]), "all_native_nodes_program_layer": True,
        "boundary": "Complete against the identified input snapshots; source capture, reviewed capability and scoped execution are separate measures.",
    }
    _write(out / "repository_catalog.json", catalog)
    _write(out / "repository_layer.html", render_repository_layer(catalog))
    _write(out / "repository_graph_packet.json", packet)
    _write(out / "validation.json", validate_repository_layer(catalog))
    _write(out / "reconciliation.json", reconciliation)
    index = build_repository_layer_index(catalog, out / ("repository_layer_" + catalog["catalog_digest"] + ".sqlite3"))
    _write(out / "index_receipt.json", index)
    return {"output": str(out), "catalog_digest": catalog["catalog_digest"], **catalog["coverage"],
            "missing_repository_count": 0, "native_nodes": len(packet["nodes"]), "native_edges": len(packet["edges"])}


def import_catalog(args: argparse.Namespace) -> dict:
    # Import only when requested. Creating a catalogue does not mutate a workspace.
    from .app import CiteRefinery
    from .repository_layer_workspace import save_repository_layer
    from .semantic import SemanticGraph

    catalog = _load(args.catalog)
    validate_repository_layer(catalog)
    app = CiteRefinery(args.workspace)
    project_id = args.project_id
    if project_id:
        app.get_project(project_id)
    else:
        # This record supplies a local project identity. Direct packet ingestion
        # deliberately avoids SemanticProjection's problem-root bootstrap.
        project = app.init_project(args.title, "Independent repository inventory and technical evidence.")
        project_id = project.id
    graph = SemanticGraph(app.store)
    packet = repository_layer_packet(catalog, project_id)
    preview = graph.preview_packet(project_id, packet, packet_ref=str(Path(args.catalog).resolve()))
    if preview.get("changed_existing_edge_statuses"):
        raise ValueError("import would change existing graph authority; review that transition separately")
    receipt = graph.ingest_packet(project_id, packet, packet_ref=str(Path(args.catalog).resolve()),
                                  expected_state_digest=preview.get("state_digest"))
    saved = save_repository_layer(app.store, project_id, catalog)
    result = {"schema": "cite_refinery.repository_layer_import.v1", "project_id": project_id,
              "workspace": str(Path(args.workspace).resolve()), "catalog_digest": catalog["catalog_digest"],
              "saved_layer": saved, "native_receipt": receipt,
              "view_path": "/repositories/" + project_id}
    if args.receipt:
        _write(Path(args.receipt), result)
    return result


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    create = commands.add_parser("build", help="reconcile known repository inputs into a standalone layer")
    create.add_argument("--survey", action="append", help="complete repository survey JSON; repeatable")
    create.add_argument("--supplemental", action="append", help="normalized repository snapshot JSON; repeatable")
    create.add_argument("--connected-profiles")
    create.add_argument("--mapping-audit")
    create.add_argument("--connected-observed-at", help="known observation date for the connected snapshot")
    create.add_argument("--current-catalog", action="append", help="frozen technical export of the current software catalogue")
    create.add_argument("--refresh-export", action="append", help="retained source-mapping, identity and interface review export; repeatable")
    create.add_argument("--source-lock", action="append")
    create.add_argument("--legacy-root")
    create.add_argument("--portfolio")
    create.add_argument("--evidence", help="separately reviewed capability evidence JSON")
    create.add_argument("--output", required=True)
    ingest = commands.add_parser("import", help="ingest Program-only graph and save the repository view")
    ingest.add_argument("--catalog", required=True)
    ingest.add_argument("--workspace", required=True)
    ingest.add_argument("--project-id")
    ingest.add_argument("--title", default="Repository layer")
    ingest.add_argument("--receipt")
    validate = commands.add_parser("validate")
    validate.add_argument("catalog")
    view = commands.add_parser("view", help="render an existing validated catalogue")
    view.add_argument("catalog")
    view.add_argument("--output", required=True)
    return cli


def main(argv: list[str] | None = None) -> int:
    cli = parser()
    args = cli.parse_args(argv)
    try:
        if args.command == "build":
            result = build(args)
        elif args.command == "import":
            result = import_catalog(args)
        else:
            catalog = _load(args.catalog)
            result = validate_repository_layer(catalog)
            if args.command == "view":
                _write(Path(args.output), render_repository_layer(catalog))
                result["output"] = str(Path(args.output).resolve())
    except (OSError, ValueError, KeyError) as exc:
        cli.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
