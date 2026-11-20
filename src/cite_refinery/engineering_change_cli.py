"""Issue or recheck a revision-bound engineering change dossier from Hardware Splicer evidence.

Exit codes: 0 issued / current, 3 stale edition (nothing issued), 1 rejected input.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from .engineering_change_dossier import (ChangeEvidenceRejected, StaleEdition, canonical_bytes, check_currency,
                                         issue_dossier, mark_stale_in_workspace, read_json, record_in_workspace,
                                         render_markdown)


def _write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # An issued edition is never overwritten; a new edition goes to a new directory.
    with path.open("xb") as handle:
        handle.write(data)


def _new_check_dir(out: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for counter in range(1000):
        target = out / f"check-{stamp}-{counter:03d}"
        try:
            target.mkdir(parents=True)
            return target
        except FileExistsError:
            continue
    raise OSError("no free check directory under " + str(out))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cite-refinery-change-dossier", description=__doc__.splitlines()[0])
    actions = parser.add_subparsers(dest="command", required=True)
    issue = actions.add_parser("issue", help="Verify HS change evidence and issue a dossier edition.")
    issue.add_argument("--packet", type=Path, required=True)
    issue.add_argument("--root", type=Path, required=True, help="Directory the packet's file paths are relative to")
    issue.add_argument("--head", type=Path, required=True, help="HS revision head exported now")
    issue.add_argument("--out", type=Path, required=True)
    issue.add_argument("--workspace", type=Path, help="Also record the edition in this Cite-Refinery workspace")
    check = actions.add_parser("check", help="Recheck an issued edition against HS's current revision head.")
    check.add_argument("--dossier", type=Path, required=True)
    check.add_argument("--head", type=Path, required=True)
    check.add_argument("--out", type=Path,
                       help="Write the currency result and a currency-marked rendering to a new check-* subdirectory")
    check.add_argument("--workspace", type=Path)
    check.add_argument("--cite-project-id")
    args = parser.parse_args(argv)
    try:
        if args.command == "issue":
            dossier, currency = issue_dossier(args.packet.read_bytes(), args.root, args.head.read_bytes())
            _write_new(args.out / "dossier.json", canonical_bytes(dossier))
            _write_new(args.out / "dossier.md", render_markdown(dossier, currency).encode("utf-8"))
            result = {"status": "issued", "edition_id": dossier["edition"]["edition_id"],
                      "bound_to_revision": dossier["edition"]["bound_to"]["revision"], "out": str(args.out),
                      "physical_authority_granted": False}
            if args.workspace:
                from .app import CiteRefinery

                result["workspace_record"] = record_in_workspace(CiteRefinery(args.workspace), dossier)
            code = 0
        else:
            dossier = read_json(args.dossier.read_bytes(), "dossier")
            currency = check_currency(dossier, args.head.read_bytes())
            if bool(args.workspace) != bool(args.cite_project_id):
                raise ChangeEvidenceRejected("--workspace and --cite-project-id must be given together")
            result = dict(currency)
            if args.out:
                # Never write into an issued edition: each check gets its own new directory.
                target = _new_check_dir(args.out)
                _write_new(target / "currency.json", canonical_bytes(currency))
                _write_new(target / "dossier.md", render_markdown(dossier, currency).encode("utf-8"))
                result["out"] = str(target)
            if currency["status"] == "stale" and args.workspace:
                from .app import CiteRefinery

                try:
                    mark_stale_in_workspace(CiteRefinery(args.workspace), args.cite_project_id, currency)
                except ValueError as exc:
                    raise ChangeEvidenceRejected(str(exc)) from exc
                result["workspace_marked_stale"] = True
            code = 0 if currency["status"] == "current" else 3
    except StaleEdition as exc:
        result, code = {**exc.currency, "status": "refused_stale", "currency_status": exc.currency["status"]}, 3
    except (ChangeEvidenceRejected, OSError) as exc:
        result, code = {"status": "rejected", "error": str(exc)}, 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
