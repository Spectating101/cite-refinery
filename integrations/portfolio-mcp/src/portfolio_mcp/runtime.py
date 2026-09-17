"""Execute reviewed, fixed argv contracts. Never accept commands from tool callers.

Manifests are trusted executable configuration, not untrusted tool input. This
runner is NOT an OS sandbox: only install manifests and engines you trust.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import signal
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

MAX_BYTES = 1_048_576
SCHEMA = "portfolio.mcp.manifest.v1"
NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
BASE_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "SYSTEMROOT", "TMPDIR", "SSL_CERT_FILE", "SSL_CERT_DIR")
RESULT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "schema": {"const": "portfolio.mcp.result.v1"},
        "project": {"type": "string"}, "tool": {"type": "string"},
        "exit_code": {"type": "integer"}, "result": {},
        "execution": {"type": "object"},
    },
    "required": ["schema", "project", "tool", "exit_code", "result", "execution"],
}


class AdapterError(Exception):
    """Only safe, caller-facing error messages belong here."""
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def encode(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise AdapterError("INVALID_JSON", "A finite, serializable JSON value is required.") from exc


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def decode(raw: bytes | str) -> Any:
    def invalid_constant(_):
        raise ValueError("non-finite JSON value")
    return json.loads(raw, object_pairs_hook=_pairs, parse_constant=invalid_constant)


def _local_refs(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"$ref", "$dynamicRef"} and (not isinstance(item, str) or not item.startswith("#")):
                raise ValueError("Only local JSON Schema references are permitted")
            _local_refs(item)
    elif isinstance(value, list):
        for item in value:
            _local_refs(item)


def _inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError("Expected a repository-relative path")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Repository path escapes the configured root")
    return resolved


def _validate_argv(argv: Any, properties: Mapping[str, Any], *, native=False) -> None:
    if not isinstance(argv, list) or not argv or len(argv) > 64:
        raise ValueError("argv must contain 1 to 64 fixed tokens")
    if not isinstance(argv[0], str):
        raise ValueError("The executable cannot be argument-bound")
    for token in argv:
        if isinstance(token, str):
            if not token or "\x00" in token:
                raise ValueError("Empty/NUL argv token")
        elif not native and isinstance(token, dict) and len(token) == 1:
            kind, name = next(iter(token.items()))
            if kind not in {"arg", "json_file", "env"} or not isinstance(name, str):
                raise ValueError("Invalid argv binding")
            if kind in {"arg", "json_file"} and name not in properties:
                raise ValueError("argv refers to an undeclared argument")
            if kind == "env" and not ENV_NAME.fullmatch(name):
                raise ValueError("Invalid environment binding")
        else:
            raise ValueError("Only fixed tokens and declared bindings are permitted")


@dataclass(frozen=True)
class Manifest:
    document: dict[str, Any]
    digest: str

    @classmethod
    def load(cls, path: str | Path) -> "Manifest":
        raw = Path(path).read_bytes()
        if len(raw) > MAX_BYTES:
            raise ValueError("Manifest exceeds size limit")
        return cls.from_dict(decode(raw))

    @classmethod
    def from_dict(cls, doc: dict[str, Any]) -> "Manifest":
        if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
            raise ValueError("Unsupported manifest schema")
        if not isinstance(doc.get("project"), str) or not NAME.fullmatch(doc["project"]):
            raise ValueError("Invalid project identifier")
        if doc.get("mode") not in {"bridge", "native"}:
            raise ValueError("mode must be bridge or native")
        env_names = doc.get("env_passthrough", [])
        if not isinstance(env_names, list) or any(not isinstance(x, str) or not ENV_NAME.fullmatch(x) for x in env_names):
            raise ValueError("Invalid environment allowlist")
        defaults = doc.get("env_defaults", {})
        if not isinstance(defaults, dict) or any(not ENV_NAME.fullmatch(k) or not isinstance(v, str) for k, v in defaults.items()):
            raise ValueError("Invalid environment defaults")
        paths = doc.get("pythonpath", []) + doc.get("required_files", [])
        if any(not isinstance(x, str) or Path(x).is_absolute() or ".." in Path(x).parts for x in paths):
            raise ValueError("Manifest paths must stay within the repository")
        timeout = doc.get("timeout_seconds", 60)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 600:
            raise ValueError("timeout_seconds must be in (0, 600]")
        if doc["mode"] == "native":
            _validate_argv(doc.get("argv"), {}, native=True)
        else:
            tools = doc.get("tools")
            if not isinstance(tools, list) or not tools or len(tools) > 100:
                raise ValueError("A bridge needs 1 to 100 tools")
            seen = set()
            for tool in tools:
                name = tool.get("name")
                if not isinstance(name, str) or not NAME.fullmatch(name) or name in seen:
                    raise ValueError("Tool names must be valid and unique")
                seen.add(name)
                if tool.get("effect") not in {"read", "compute", "write"}:
                    raise ValueError("Every tool requires an explicit effect")
                if not isinstance(tool.get("description"), str) or not tool["description"].strip():
                    raise ValueError("Every tool needs a description")
                schema = tool.get("input_schema", {})
                if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
                    raise ValueError("Tool inputs must reject unknown top-level arguments")
                _local_refs(schema)
                Draft202012Validator.check_schema(schema)
                _validate_argv(tool.get("argv"), schema.get("properties", {}))
                for item in tool["argv"]:
                    if isinstance(item, dict) and "arg" in item:
                        prop = schema["properties"][item["arg"]]
                        if prop.get("type") not in {"string", "integer", "number", "boolean"}:
                            raise ValueError("argv arg bindings require scalar schemas")
                codes = tool.get("accepted_exit_codes", [0])
                if not isinstance(codes, list) or not codes or any(type(x) is not int or not 0 <= x <= 255 for x in codes):
                    raise ValueError("Invalid accepted exit codes")
        canonical = encode(doc)
        return cls(decode(canonical), hashlib.sha256(canonical).hexdigest())

    @property
    def project(self) -> str:
        return self.document["project"]

    def tools(self) -> list[dict[str, Any]]:
        return sorted(self.document.get("tools", []), key=lambda tool: tool["name"])


class Runner:
    def __init__(self, manifest: Manifest, root: str | Path, *, python: str | None = None,
                 node: str = "node", allow_writes: bool = False, environ: Mapping[str, str] | None = None):
        self.manifest = manifest
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("Repository root must be a directory")
        if type(allow_writes) is not bool:
            raise ValueError("allow_writes must be an explicit boolean")
        self.python, self.node = python or sys.executable, node
        self.allow_writes = allow_writes
        self.environ = dict(os.environ if environ is None else environ)
        self.lock = asyncio.Lock()
        for relative in manifest.document.get("required_files", []):
            if not _inside(self.root, relative).is_file():
                raise ValueError(f"Missing required engine file: {relative}")

    def environment(self) -> dict[str, str]:
        allowed = (*BASE_ENV, *self.manifest.document.get("env_passthrough", []))
        env = {k: self.environ[k] for k in allowed if k in self.environ}
        for key, value in self.manifest.document.get("env_defaults", {}).items():
            env.setdefault(key, value)
        paths = [_inside(self.root, x) for x in self.manifest.document.get("pythonpath", [])]
        if paths:
            env["PYTHONPATH"] = os.pathsep.join(map(str, paths))
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return env

    def argv(self, tokens: list[Any], arguments: dict[str, Any], scratch: Path) -> list[str]:
        result, files = [], {}
        for token in tokens:
            if isinstance(token, str):
                value = {"$PYTHON": self.python, "$NODE": self.node}.get(token, token)
            else:
                kind, key = next(iter(token.items()))
                if kind == "env":
                    value = self.environ.get(key)
                    if not value:
                        raise AdapterError("NOT_CONFIGURED", f"The operator must configure {key}.")
                else:
                    if key not in arguments:
                        raise AdapterError("INVALID_ARGUMENT", f"Missing argument: {key}.")
                    arg = arguments[key]
                    if kind == "json_file":
                        if key not in files:
                            path = scratch / f"input-{len(files)}.json"
                            path.write_bytes(encode(arg))
                            files[key] = str(path)
                        value = files[key]
                    elif isinstance(arg, (dict, list)) or arg is None:
                        raise AdapterError("INVALID_ARGUMENT", "A scalar command argument is required.")
                    else:
                        value = arg if isinstance(arg, str) else json.dumps(arg)
            if "\x00" in value:
                raise AdapterError("INVALID_ARGUMENT", "NUL bytes are not permitted.")
            result.append(value)
        return result

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = next((t for t in self.manifest.tools() if t["name"] == name), None)
        if tool is None:
            raise AdapterError("UNKNOWN_TOOL", "The requested tool is not registered.")
        if tool["effect"] == "write" and not self.allow_writes:
            raise AdapterError("WRITE_DISABLED", "Persistent writes require explicit operator enablement.")
        raw = encode(arguments)
        if len(raw) > MAX_BYTES:
            raise AdapterError("INPUT_TOO_LARGE", "Input exceeds the one-megabyte limit.")
        validator = Draft202012Validator(tool["input_schema"], format_checker=FormatChecker())
        error = next(validator.iter_errors(arguments), None)
        if error:
            raise AdapterError("INVALID_ARGUMENT", f"Input does not satisfy the {error.validator} constraint.")
        async with self.lock:
            with tempfile.TemporaryDirectory(prefix="portfolio-mcp-") as directory:
                argv = self.argv(tool["argv"], arguments, Path(directory))
                code, output = await self._process(argv, raw)
        if code not in tool.get("accepted_exit_codes", [0]):
            raise AdapterError("ENGINE_FAILED", f"The canonical engine exited with code {code}; no success is claimed.")
        try:
            result = decode(output)
        except (ValueError, UnicodeDecodeError, RecursionError) as exc:
            raise AdapterError("INVALID_ENGINE_OUTPUT", "The engine did not return one complete JSON value.") from exc
        return {
            "schema": "portfolio.mcp.result.v1", "project": self.manifest.project,
            "tool": name, "exit_code": code, "result": result,
            "execution": {
                "manifest_sha256": self.manifest.digest,
                "input_sha256": hashlib.sha256(raw).hexdigest(),
                "output_sha256": hashlib.sha256(output).hexdigest(),
                "authority_granted": False,
                "note": "Execution receipt only; native validation and evidence states are unchanged.",
            },
        }

    async def _process(self, argv: list[str], raw: bytes) -> tuple[int, bytes]:
        try:
            process = await asyncio.create_subprocess_exec(
                *argv, cwd=self.root, env=self.environment(), stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                start_new_session=(os.name == "posix"), limit=65_536,
            )
        except (OSError, ValueError) as exc:
            raise AdapterError("ENGINE_UNAVAILABLE", "The configured engine could not be started.") from exc

        async def read_bounded(stream):
            chunks, size = [], 0
            while chunk := await stream.read(16_384):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise AdapterError("OUTPUT_TOO_LARGE", "Engine output exceeds the one-megabyte limit.")
                chunks.append(chunk)
            return b"".join(chunks)

        async def feed():
            try:
                process.stdin.write(raw)
                await process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                process.stdin.close()

        tasks = [asyncio.create_task(read_bounded(process.stdout)),
                 asyncio.create_task(read_bounded(process.stderr)), asyncio.create_task(feed())]
        try:
            async with asyncio.timeout(self.manifest.document.get("timeout_seconds", 60)):
                stdout, _, _ = await asyncio.gather(*tasks)
                code = await process.wait()
            return code, stdout
        except TimeoutError as exc:
            raise AdapterError("ENGINE_TIMEOUT", "The canonical engine exceeded its configured time limit.") from exc
        finally:
            if os.name == "posix" or process.returncode is None:
                try:
                    if os.name == "posix":
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                except ProcessLookupError:
                    pass
                await process.wait()
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
