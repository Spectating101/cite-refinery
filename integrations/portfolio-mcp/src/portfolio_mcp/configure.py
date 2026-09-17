"""Build local MCP client configuration from explicit, installed engine paths.

No installs, cloning, subprocess calls, server launches, or execution admission.
The output can contain credentials supplied by the operator: keep it private.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from typing import Any
from .runtime import Manifest, NAME, Runner, decode


def executable(value: Any) -> str:
    if not isinstance(value, str) or not Path(value).expanduser().is_absolute():
        raise ValueError("Interpreters must be explicit absolute paths")
    # Do not resolve interpreter symlinks: that would leave the selected venv.
    path = Path(value).expanduser().absolute()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError("A configured interpreter is missing or not executable")
    return str(path)


def build_client_config(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict) or set(spec) != {"runner_python", "servers"}:
        raise ValueError("Expected exactly runner_python and servers")
    interpreter = executable(spec["runner_python"])
    if not isinstance(spec["servers"], dict) or not spec["servers"]:
        raise ValueError("Configure at least one named server")
    entries = {}
    for name, entry in spec["servers"].items():
        if not isinstance(name, str) or not NAME.fullmatch(name) or not isinstance(entry, dict):
            raise ValueError("Invalid server entry")
        if set(entry) - {"root", "engine_python", "env", "allow_writes"} or not {"root", "engine_python"} <= set(entry):
            raise ValueError("Server requires root and engine_python; unknown options are rejected")
        if not isinstance(entry["root"], str) or not Path(entry["root"]).expanduser().is_absolute():
            raise ValueError("Repository roots must be absolute paths")
        root = Path(entry["root"]).expanduser().resolve(strict=True)
        manifest_path = root / "integrations/mcp/manifest.json"
        manifest = Manifest.load(manifest_path)
        engine_python = executable(entry["engine_python"])
        allow_writes = entry.get("allow_writes", False)
        if type(allow_writes) is not bool:
            raise ValueError("allow_writes must be an explicit boolean")
        if allow_writes and manifest.document["mode"] == "native":
            raise ValueError("Native permissions use the owning server configuration, not allow_writes")
        env = entry.get("env", {})
        if not isinstance(env, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in env.items()):
            raise ValueError("env must map names to strings")
        Runner(manifest, root, python=engine_python, allow_writes=allow_writes, environ=env)
        args = ["-m", "portfolio_mcp.cli", "serve", "--manifest", str(manifest_path),
                "--root", str(root), "--engine-python", engine_python]
        if allow_writes:
            args.append("--allow-writes")
        entries[name] = {"command": interpreter, "args": args, "env": dict(env)}
    return {"mcpServers": entries}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connections", required=True)
    parser.add_argument("--output", required=True, help="New private config file; existing files are never overwritten")
    args = parser.parse_args()
    try:
        raw = Path(args.connections).read_bytes()
        if len(raw) > 1_048_576:
            raise ValueError("Connection configuration exceeds size limit")
        result = build_client_config(decode(raw))
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")
        print(f"Wrote {len(result['mcpServers'])} connection definitions; no server was started.")
        return 0
    except (ValueError, OSError, TypeError) as exc:
        print(f"Configuration failed: {type(exc).__name__}", file=__import__('sys').stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
