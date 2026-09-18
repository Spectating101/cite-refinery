import asyncio
import copy
import json
import os
from pathlib import Path
import pytest
from portfolio_mcp.runtime import AdapterError, Manifest, Runner, SCHEMA, encode


def manifest(argv=None, effect="compute", **extra):
    return {"schema": SCHEMA, "project": "test-engine", "mode": "bridge", "timeout_seconds": 2,
            "tools": [{"name": "engine_call", "description": "Test-only transport fixture, not a portfolio engine.",
                       "effect": effect, "input_schema": {"type": "object", "properties": {"payload": {}},
                       "required": ["payload"], "additionalProperties": False},
                       "argv": argv or ["$PYTHON", "engine.py"]}], **extra}


def runner(tmp_path, code="import sys; print(sys.stdin.read())", document=None, **kwargs):
    (tmp_path / "engine.py").write_text(code)
    return Runner(Manifest.from_dict(document or manifest()), tmp_path, **kwargs)


def call(r, args=None):
    return asyncio.run(r.call("engine_call", {"payload": {"ref": "dataset:one"}} if args is None else args))


def test_native_value_and_identifiers_are_preserved(tmp_path):
    result = call(runner(tmp_path))
    assert result["result"] == {"payload": {"ref": "dataset:one"}}
    assert result["execution"]["authority_granted"] is False
    assert result["exit_code"] == 0
    assert len(result["execution"]["input_sha256"]) == 64


@pytest.mark.parametrize("args", [{}, {"payload": 1, "command": "touch nope"}, [], None])
def test_bad_input_never_runs_engine(tmp_path, args):
    r = runner(tmp_path, "from pathlib import Path; Path('executed').touch(); print('{}')")
    with pytest.raises(AdapterError, match="constraint"):
        asyncio.run(r.call("engine_call", args))
    assert not (tmp_path / "executed").exists()


def test_unknown_tool_fails(tmp_path):
    with pytest.raises(AdapterError) as caught:
        asyncio.run(runner(tmp_path).call("shell", {}))
    assert caught.value.code == "UNKNOWN_TOOL"


def test_write_disabled_before_execution(tmp_path):
    r = runner(tmp_path, document=manifest(effect="write"))
    with pytest.raises(AdapterError) as caught:
        call(r)
    assert caught.value.code == "WRITE_DISABLED"
    assert call(runner(tmp_path, document=manifest(effect="write"), allow_writes=True))["exit_code"] == 0


def test_literal_shell_input_cannot_execute(tmp_path):
    attack = "$(touch owned); rm -rf / #"
    result = call(runner(tmp_path), {"payload": attack})
    assert result["result"]["payload"] == attack
    assert not (tmp_path / "owned").exists()


def test_json_file_is_private_and_cleaned(tmp_path):
    code = "import json,sys; from pathlib import Path; p=Path(sys.argv[1]); print(json.dumps({'path':str(p),'data':json.loads(p.read_text()),'mode':p.parent.stat().st_mode & 0o777}))"
    r = runner(tmp_path, code, manifest(["$PYTHON", "engine.py", {"json_file": "payload"}]))
    data = call(r)["result"]
    assert data["data"] == {"ref": "dataset:one"}
    assert data["mode"] == 0o700
    assert not Path(data["path"]).exists()


def test_stderr_is_not_returned(tmp_path):
    code = "import sys; print('secret-token-private-path',file=sys.stderr); print('{}')"
    assert "secret-token" not in str(call(runner(tmp_path, code)))


def test_unlisted_environment_is_not_forwarded(tmp_path):
    code = "import json,os; print(json.dumps(dict(os.environ)))"
    r = runner(tmp_path, code, environ={"SECRET": "sensitive", "HOME": str(tmp_path), "PATH": os.environ["PATH"]})
    assert "SECRET" not in call(r)["result"]


def test_explicit_environment_allowlist(tmp_path):
    code = "import json,os; print(json.dumps({'key':os.getenv('ENGINE_KEY')}))"
    r = runner(tmp_path, code, manifest(env_passthrough=["ENGINE_KEY"]), environ={"ENGINE_KEY": "explicit"})
    assert call(r)["result"]["key"] == "explicit"


@pytest.mark.parametrize("code,error", [
    ("print('not-json')", "INVALID_ENGINE_OUTPUT"),
    ("print('{\"x\":1,\"x\":2}')", "INVALID_ENGINE_OUTPUT"),
    ("print('NaN')", "INVALID_ENGINE_OUTPUT"),
    ("import sys; sys.exit(3)", "ENGINE_FAILED"),
    ("print('x'*1100000)", "OUTPUT_TOO_LARGE"),
    ("import sys; print('x'*1100000,file=sys.stderr)", "OUTPUT_TOO_LARGE"),
])
def test_errors_fail_closed(tmp_path, code, error):
    with pytest.raises(AdapterError) as caught:
        call(runner(tmp_path, code))
    assert caught.value.code == error


def test_domain_failure_is_preserved_when_exit_one_is_declared(tmp_path):
    doc = manifest()
    doc["tools"][0]["accepted_exit_codes"] = [0, 1]
    result = call(runner(tmp_path, "import sys; print('{\"ok\":false}'); sys.exit(1)", doc))
    assert result["result"]["ok"] is False
    assert result["exit_code"] == 1
    assert not result["execution"]["authority_granted"]


def test_timeout(tmp_path):
    doc = manifest(timeout_seconds=0.05)
    with pytest.raises(AdapterError) as caught:
        call(runner(tmp_path, "import time; time.sleep(20)", doc))
    assert caught.value.code == "ENGINE_TIMEOUT"


def test_request_size_bound(tmp_path):
    with pytest.raises(AdapterError) as caught:
        call(runner(tmp_path), {"payload": "x" * 1_048_577})
    assert caught.value.code == "INPUT_TOO_LARGE"


@pytest.mark.parametrize("value", [float('nan'), float('inf'), {1, 2}])
def test_non_json_values_rejected(value):
    with pytest.raises(AdapterError):
        encode(value)


def test_manifest_hash_is_key_order_independent():
    doc = manifest()
    assert Manifest.from_dict(doc).digest == Manifest.from_dict(dict(reversed(list(doc.items())))).digest


def test_manifest_is_copied_not_mutated():
    doc = manifest()
    frozen = Manifest.from_dict(doc)
    doc["tools"][0]["name"] = "changed"
    assert frozen.tools()[0]["name"] == "engine_call"


@pytest.mark.parametrize("change", [
    lambda d: d.update(schema="unknown"),
    lambda d: d.update(project="../escape"),
    lambda d: d.update(mode="shell"),
    lambda d: d.update(timeout_seconds=601),
    lambda d: d.update(timeout_seconds=True),
    lambda d: d.update(pythonpath=["../outside"]),
    lambda d: d.update(required_files=["/etc/passwd"]),
    lambda d: d.update(env_passthrough=["bad-name"]),
    lambda d: d["tools"].append(copy.deepcopy(d["tools"][0])),
    lambda d: d["tools"][0].update(effect="administrator"),
    lambda d: d["tools"][0].update(argv=[{"arg": "payload"}]),
    lambda d: d["tools"][0].update(argv=["$PYTHON", {"json_file": "unknown"}]),
    lambda d: d["tools"][0].update(argv=["$PYTHON", {"arg": "payload"}]),
    lambda d: d["tools"][0]["input_schema"].update(additionalProperties=True),
    lambda d: d["tools"][0]["input_schema"].update(**{"$ref": "https://attacker.invalid/schema"}),
])
def test_invalid_manifest_rejected(change):
    doc = manifest()
    change(doc)
    with pytest.raises((ValueError, TypeError)):
        Manifest.from_dict(doc)


def test_source_file_symlink_cannot_escape(tmp_path):
    (tmp_path / "escape").symlink_to("/etc/passwd")
    with pytest.raises(ValueError):
        Runner(Manifest.from_dict(manifest(required_files=["escape"])), tmp_path)


def test_missing_required_source_is_detected(tmp_path):
    with pytest.raises(ValueError, match="Missing"):
        Runner(Manifest.from_dict(manifest(required_files=["missing.py"])), tmp_path)


def test_missing_binary(tmp_path):
    with pytest.raises(AdapterError) as caught:
        call(runner(tmp_path, document=manifest(["/nonexistent/engine"])))
    assert caught.value.code == "ENGINE_UNAVAILABLE"


def test_defaults_do_not_override_explicit_native_settings(tmp_path):
    r = runner(tmp_path, document=manifest(env_defaults={"READ_ONLY": "true"}, env_passthrough=["READ_ONLY"]), environ={"READ_ONLY": "false"})
    assert r.environment()["READ_ONLY"] == "false"


@pytest.mark.skipif(os.name != "posix", reason="POSIX process group check")
def test_descendant_pipe_is_bounded_after_parent_exits(tmp_path):
    doc = manifest(timeout_seconds=0.1)
    code = "import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); print('{}')"
    with pytest.raises(AdapterError) as caught:
        call(runner(tmp_path, code, doc))
    assert caught.value.code == "ENGINE_TIMEOUT"
