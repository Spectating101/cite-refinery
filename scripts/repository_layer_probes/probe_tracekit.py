"""A real harmless file read, SDK gate/record, offline verification and content tampering.

The signer and in-process test witness are same-user development components, not
independent security boundaries. No existing agent integration is modified.
"""
from __future__ import annotations

import argparse

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import traceback
import zipfile

from tracekit.demo_server import Witness, _serve, export_final
from tracekit.deploy import files
from tracekit.sdk.client import Client, result_field
from tracekit.signer.service import DEFAULT_POLICY, SignerService, load_policy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output-dir", required=True, type=Path)
parser.add_argument("--installation-receipt", required=True, type=Path)
args = parser.parse_args()
OUT = args.output_dir.resolve()
OUT.mkdir(parents=True, exist_ok=True)
INSTALL_REPORT = args.installation_receipt.resolve()
if not INSTALL_REPORT.is_file():
    parser.error("--installation-receipt must be the pip --report JSON for the executed environment")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(path, trust):
    command = [sys.executable, "-m", "tracekit", "verify", str(path), "--trust", str(trust), "--json"]
    process = subprocess.run(command, text=True, capture_output=True, timeout=30)
    try:
        report = json.loads(process.stdout)
    except ValueError:
        report = {"stdout": process.stdout}
    return {"command": command, "exit_code": process.returncode, "report": report, "stderr": process.stderr}


receipt = {"schema": "cite_refinery.bounded_execution.v1", "repository_id": "github:cygnux-labs/tracekit",
           "observed_at": datetime.now(timezone.utc).isoformat(), "result": "blocked",
           "scope": "One harmless fixture file read through the v2 SDK; same-user signer and in-process test witness; offline verification after signer shutdown, followed by a changed record negative case.",
           "versions": {name: importlib.metadata.version(name) for name in ("tracekit-ai", "cryptography", "rfc8785")},
           "environment": {"python": sys.version, "platform": platform.platform()},
           "limitations": ["The signer and test witness are same-user; this does not test isolation from an adversarial agent or independent witness availability.",
                           "Integrity of recorded events is not factual truth, complete capture, authorization correctness or preservation of original source documents.",
                           "This is a bounded SDK test with a local file read; it is not a Nocturnal integration or real model run."],
           "script": {"path": str(Path(__file__).resolve()), "sha256": sha(__file__)},
           "installation_receipt": {"path": str(INSTALL_REPORT), "sha256": sha(INSTALL_REPORT)}}
service = server = client = None
directory = Path(tempfile.mkdtemp(prefix="cite-repo-probe-", dir="/tmp"))
try:
    fixture = OUT / "bounded-input.txt"
    fixture.write_text("Cite-Refinery bounded fixture: alpha 17, beta 23.\n", encoding="utf-8")
    witness = Witness()
    policy = Path(DEFAULT_POLICY).parent / "server.yaml"
    service = SignerService(str(directory / "data"), witnesses=[witness], isolation="same-user", grace_s=0.5,
                            fsck_every_s=0, policy=load_policy(str(policy)))
    endpoint, server = _serve(str(directory), service)
    client = Client(endpoint)
    with client.run(agent="cite-refinery-bounded-probe") as run:
        arguments = {"file_path": str(fixture)}
        decision = run.decide("fixture-read-1", "Read", arguments)
        assert decision["decision"] == "allow", decision
        consumed = run.approval_consume("fixture-read-1", "Read", arguments)
        assert consumed["ok"]
        actual_text = fixture.read_text(encoding="utf-8")
        completed = run.complete("fixture-read-1", result=result_field(decision.get("send_result"), {"content": actual_text}))
        assert completed is not None
        run_id = run.run_id
    client.close()
    client = None
    original = OUT / "original.tkb"
    trust = OUT / "trust.json"
    export_final(str(directory / "data" / "store"), run_id, witness, str(original))
    files.write_json(str(trust), {"logs": [service.vkey], "witnesses": [{"vkey": witness.vkey, "class": "operator"}],
                                "algs": ["ed25519"], "witnesses_required": 1}, 0o644)
    server.shutdown()
    server.server_close()
    server = None
    service.close()
    service = None
    # Signature/hash-chain verification is performed in a fresh process with the signer stopped.
    positive = verify(original, trust)
    with zipfile.ZipFile(original) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    run_file = next(name for name in contents if name.startswith("runs/"))
    records = [json.loads(line) for line in contents[run_file].splitlines() if line]
    altered = False
    for record in records:
        event = record["event"]
        if event.get("type") == "policy.decision":
            # Preserve valid ZIP and JSON, but change one signed semantic field.
            assert event["data"]["decision"] == "allow"
            event["data"]["decision"] = "deny"
            altered = True
            break
    assert altered, [record["event"].get("type") for record in records]
    contents[run_file] = b"".join(json.dumps(record, separators=(",", ":")).encode() + b"\n" for record in records)
    bad = OUT / "tampered.tkb"
    with zipfile.ZipFile(bad, "w") as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    negative = verify(bad, trust)
    receipt.update(result="pass" if positive["exit_code"] == 0 and negative["exit_code"] != 0 else "fail",
                   executed_operation={"tool": "Read", "arguments": arguments, "actual_output_sha256": hashlib.sha256(actual_text.encode()).hexdigest(),
                                       "decision": decision["decision"], "consumed": consumed["ok"], "completion_recorded": completed is not None},
                   policy={"path": str(policy), "sha256": sha(policy)},
                   original_verification=positive, tampered_verification=negative,
                   original_record_count=len(records), mutation="First policy.decision changed from allow to deny without re-signing; JSON and ZIP remain readable.",
                   artifacts=[{"path": str(path), "sha256": sha(path), "bytes": path.stat().st_size} for path in (fixture, original, trust, bad)])
except Exception as error:
    receipt.update(result="blocked", error={"class": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()})
finally:
    if client:
        client.close()
    if server:
        server.shutdown()
        server.server_close()
    if service:
        service.close()
    shutil.rmtree(directory)
    (OUT / "execution.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"result": receipt["result"], "original_exit": receipt.get("original_verification", {}).get("exit_code"),
                      "tampered_exit": receipt.get("tampered_verification", {}).get("exit_code"), "error": receipt.get("error")}))
sys.exit(0 if receipt["result"] == "pass" else 1)
