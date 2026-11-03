"""Build and serve the public, read-only reviewer demo on loopback only."""
from __future__ import annotations

import argparse
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_public_preview import build


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766, help="local HTTP port (default: 8766)")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")

    with TemporaryDirectory(prefix="cite-refinery-review-demo-") as temp_dir:
        output = Path(temp_dir)
        summary = build(output)
        handler = partial(SimpleHTTPRequestHandler, directory=str(output))
        try:
            with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
                print("Cite-Refinery source-reviewed demo")
                print(f"Project: {summary['project_id']}")
                print(
                    f"Map: {summary['clusters']} clusters · {summary['nodes']} nodes "
                    f"· {summary['edges']} edges"
                )
                print(f"Open http://127.0.0.1:{server.server_port}")
                print("Loopback only; public sources; read-only; no model/API key required. Press Ctrl+C to stop.")
                server.serve_forever()
        except OSError as exc:
            parser.error(f"could not start local preview on port {args.port}: {exc}")
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
