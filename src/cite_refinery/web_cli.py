from __future__ import annotations

import argparse

from .web import serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cite-refinery-web",
        description="Serve the unified Cite-Refinery project workspace.",
    )
    parser.add_argument("--workspace", default=".cite-refinery", help="State directory")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8765, help="Bind port")
    args = parser.parse_args(argv)
    serve(args.workspace, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
