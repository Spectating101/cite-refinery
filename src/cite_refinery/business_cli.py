"""Private, read-only-by-default Atlas commercial workbench CLI.

An opt-in activity ledger lives outside the repository and is chmod 0600.
No APIs, model calls, outreach, invoice generation or graph mutation.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import tempfile
from contextlib import contextmanager

from .market_demand_screen import screen as screen_public_demand, render as render_public_demand
from .business_workbench import (
    ROOT, append_event, build_board, new_ledger, render_board,
    validate_ledger, validate_plan,
)


def private_path(p: str) -> Path:
    path = Path(p).expanduser()
    if not path.is_absolute():
        raise ValueError("Private activity ledger requires an absolute path")
    resolved = path.resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError("Private activity must not be written to the public repository")
    if path.is_symlink():
        raise ValueError("Ledger cannot be a symlink")
    return resolved


def _read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object")
    return data


@contextmanager
def _exclusive_lock(path: Path):
    lock = path.with_name(path.name + ".lock")
    # O_NOFOLLOW is available on Linux / Optiplex.
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _write_atomic(path: Path, data: dict):
    fd, temp_name = tempfile.mkstemp(prefix=".atlas-business-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cite-refinery-business")
    parser.add_argument("command", choices=("board", "init", "record"))
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--ledger", help="absolute local private ledger path, outside checkout")
    parser.add_argument("--event", type=Path, help="JSON event file, record command only")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--demand-scan", type=Path, help="optional separately sourced public demand lead register")
    parser.add_argument("--as-of", help="ISO screen date, explicit for reproducible public listing deadlines")
    args = parser.parse_args(argv)
    plan = validate_plan(_read_json(args.plan))
    if args.command == "board":
        ledger = None
        if args.ledger:
            target = private_path(args.ledger)
            with _exclusive_lock(target):
                ledger = validate_ledger(plan, _read_json(target))
        board = build_board(plan, ledger)
        public = None
        if args.demand_scan:
            from datetime import date
            public = screen_public_demand(_read_json(args.demand_scan),
                                          as_of=args.as_of or date.today().isoformat())
        if args.format == "json":
            print(json.dumps({**board, **({"public_demand_screen": public} if public else {})},
                             indent=2, ensure_ascii=False))
        else:
            print(render_board(board) + ("\n" + render_public_demand(public) if public else ""))
        return 0

    if not args.ledger:
        parser.error("init/record require --ledger")
    path = private_path(args.ledger)
    if args.command == "init":
        if args.event:
            parser.error("init does not accept --event")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with _exclusive_lock(path):
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                         | getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                json.dump(new_ledger(plan), output, indent=2)
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
        print("Initialized private activity ledger (0 events).")
        return 0

    if args.event is None:
        parser.error("record requires --event")
    event = _read_json(args.event)
    with _exclusive_lock(path):
        ledger = validate_ledger(plan, _read_json(path))
        revised = append_event(plan, ledger, event)
        _write_atomic(path, revised)
    print("Recorded private operator-reported event; no verified revenue or buyer promotion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
