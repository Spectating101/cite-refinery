from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol


@dataclass(slots=True)
class ExecutionResult:
    provider: str
    status: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    output: Any = None
    duration_ms: int = 0


class Executor(Protocol):
    def execute(self, invocation: dict[str, Any], input_data: Any) -> ExecutionResult: ...


class SubprocessExecutor:
    """Execute an explicitly registered argv command without a shell.

    Project input is delivered as JSON on stdin by default, which avoids command
    interpolation and keeps executable configuration separate from runtime data.
    """

    provider = "subprocess"

    def execute(self, invocation: dict[str, Any], input_data: Any) -> ExecutionResult:
        argv = invocation.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
            raise ValueError("subprocess invocation requires a non-empty string argv list")

        input_mode = invocation.get("input_mode", "json_stdin")
        if input_mode not in {"json_stdin", "none"}:
            raise ValueError("subprocess input_mode must be 'json_stdin' or 'none'")

        timeout = invocation.get("timeout_seconds", 120)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("timeout_seconds must be positive")
        timeout = min(float(timeout), 600.0)

        stdin = json.dumps(input_data, ensure_ascii=False) if input_mode == "json_stdin" else None
        started = perf_counter()
        try:
            proc = subprocess.run(
                argv,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                shell=False,
            )
            elapsed = int((perf_counter() - started) * 1000)
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            output: Any = stdout.rstrip("\n")
            stripped = stdout.strip()
            if stripped:
                try:
                    output = json.loads(stripped)
                except json.JSONDecodeError:
                    pass
            return ExecutionResult(
                provider=self.provider,
                status="succeeded" if proc.returncode == 0 else "failed",
                stdout=stdout,
                stderr=stderr,
                exit_code=proc.returncode,
                output=output,
                duration_ms=elapsed,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = int((perf_counter() - started) * 1000)
            return ExecutionResult(
                provider=self.provider,
                status="error",
                stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
                stderr=f"execution timed out after {timeout:g}s",
                exit_code=None,
                duration_ms=elapsed,
            )
        except OSError as exc:
            elapsed = int((perf_counter() - started) * 1000)
            return ExecutionResult(
                provider=self.provider,
                status="error",
                stderr=str(exc),
                exit_code=None,
                duration_ms=elapsed,
            )


class ExecutorRegistry:
    def __init__(self) -> None:
        subprocess_executor = SubprocessExecutor()
        self._executors: dict[str, Executor] = {
            "subprocess": subprocess_executor,
        }

    def register(self, provider: str, executor: Executor) -> None:
        if not provider:
            raise ValueError("provider name cannot be empty")
        self._executors[provider] = executor

    def execute(self, provider: str, invocation: dict[str, Any], input_data: Any) -> ExecutionResult:
        executor = self._executors.get(provider)
        if executor is None:
            raise ValueError(f"no executor registered for provider: {provider}")
        result = executor.execute(invocation, input_data)
        result.provider = provider
        return result
