from __future__ import annotations
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from .runtime import AdapterError, Manifest, Runner, decode


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run reviewed portfolio MCP contracts without replacing their engines.")
    parser.add_argument("action", choices=["validate", "serve", "probe", "call"])
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--root", required=True, help="Trusted local checkout containing the owning engine")
    parser.add_argument("--engine-python", default=sys.executable, help="Interpreter with the owning project's dependencies")
    parser.add_argument("--node", default="node")
    parser.add_argument("--allow-writes", action="store_true", help="Enable declared bridge write tools; never bypasses engine gates")
    parser.add_argument("--tool")
    parser.add_argument("--arguments-json", default="{}")
    args = parser.parse_args(argv)
    try:
        manifest = Manifest.load(args.manifest)
        runner = Runner(manifest, args.root, python=args.engine_python, node=args.node, allow_writes=args.allow_writes)
        if args.action == "validate":
            print(json.dumps({"schema": "portfolio.mcp.validation.v1", "project": manifest.project,
                              "manifest_sha256": manifest.digest, "mode": manifest.document["mode"],
                              "tool_count": len(manifest.tools()), "runtime_exercised": False}))
            return 0
        if args.action == "serve":
            if manifest.document["mode"] == "native":
                command = runner.argv(manifest.document["argv"], {}, runner.root)
                os.chdir(runner.root)
                os.execvpe(command[0], command, runner.environment())
            from .server import serve_stdio
            asyncio.run(serve_stdio(runner))
            return 0
        from .client import StdioConnection, inspect_server, invoke
        command_args = ["-m", "portfolio_mcp.cli", "serve", "--manifest", str(Path(args.manifest).resolve()),
                        "--root", str(runner.root), "--engine-python", args.engine_python, "--node", args.node]
        if args.allow_writes:
            command_args.append("--allow-writes")
        connection = StdioConnection(sys.executable, tuple(command_args), dict(os.environ))
        if args.action == "probe":
            result = asyncio.run(inspect_server(connection))
            expected = set(manifest.document.get("expected_tools", [])) if manifest.document["mode"] == "native" else {t["name"] for t in manifest.tools() if args.allow_writes or t["effect"] != "write"}
            observed = {t["name"] for t in result["tools"]}
            result.update(project=manifest.project, missing_tools=sorted(expected - observed), empty_catalog=not observed, domain_workflow_exercised=False)
            print(json.dumps(result, indent=2))
            return int(bool(expected - observed) or not observed)
        if not args.tool:
            parser.error("call requires --tool")
        result = asyncio.run(invoke(connection, args.tool, decode(args.arguments_json)))
        print(json.dumps(result, indent=2))
        return int(result["is_error"])
    except (AdapterError, ValueError, OSError, ImportError) as exc:
        print(f"portfolio-mcp: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
