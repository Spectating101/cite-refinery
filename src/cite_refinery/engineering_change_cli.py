"""Issue or recheck a revision-bound engineering change dossier from Hardware Splicer evidence.

Exit codes: 0 issued / current, 3 stale edition (nothing issued), 1 rejected input.
"""
from __future__ import annotations

import argparse
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
    check.add_argument("--out", type=Path, help="Write the currency result and, if stale, a stale-marked rendering")
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
            if args.out:
                _write_new(args.out / "currency.json", canonical_bytes(currency))
                _write_new(args.out / "dossier.md", render_markdown(dossier, currency).encode("utf-8"))
            if currency["status"] == "stale" and args.workspace and args.cite_project_id:
                from .app import CiteRefinery

                mark_stale_in_workspace(CiteRefinery(args.workspace), args.cite_project_id, currency)
            result = currency
            code = 0 if currency["status"] == "current" else 3
    except StaleEdition as exc:
        result, code = {**exc.currency, "status": "refused_stale", "currency_status": exc.currency["status"]}, 3
    except (ChangeEvidenceRejected, OSError) as exc:
        result, code = {"status": "rejected", "error": str(exc)}, 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
