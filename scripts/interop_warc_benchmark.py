#!/usr/bin/env python3
"""Nocturnal WARC -> independent warcio validation -> pywb archive index/replay.

Uses one synthetic source URL and injected HTML. Zero third-party-site access,
no Nocturnal repository writes, no source allegations or public publishing.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

SCHEMA = "cite_refinery.nocturnal_warc_interop.v1"
SOURCE = "http://example.invalid/nocturnal-interop-fixture"
HTML = "<!doctype html><html><head><title>Evidence control fixture</title></head><body><article><h1>Published source capture</h1><p>Original evidence claim: sample amount 64.00 under unit price.</p></article></body></html>"


def run(repo: Path, destination: Path) -> dict:
    if not (repo / "src/fleet_research/adapters/evidence_custody.py").is_file():
        raise ValueError("specified source checkout is not Nocturnal evidence custody")
    if destination.exists():
        raise FileExistsError("benchmark output must be new")
    destination.mkdir(parents=True, mode=0o700)
    sys.path.insert(0, str(repo))
    from src.fleet_research.adapters.evidence_custody import EvidenceCustodyAdapter
    from warcio.archiveiterator import ArchiveIterator

    setup = destination / "custody"
    t0 = time.perf_counter()
    native = EvidenceCustodyAdapter(setup, enable_archivebox=False, enable_wayback=False)
    record = native.capture(SOURCE, claim_id="interop-fixture-001", html=HTML)
    native_ms = round((time.perf_counter()-t0)*1000,1)
    warc = record["steps"]["warc"]
    if warc.get("status") != "written":
        raise RuntimeError("Nocturnal failed to write WARC; " + json.dumps(warc))
    warc_path = Path(warc["path"])
    inspection = []
    with warc_path.open("rb") as raw:
        for entry in ArchiveIterator(raw):
            body = entry.content_stream().read()
            inspection.append({
                "kind":entry.rec_type,
                "uri":entry.rec_headers.get_header("WARC-Target-URI"),
                "http_status":entry.http_headers.get_statuscode() if entry.http_headers else None,
                "header_digest":entry.http_headers.get_header("X-Watchdog-SHA256") if entry.http_headers else None,
                "body_sha256":hashlib.sha256(body).hexdigest(),
                "payload_matches":body==HTML.encode(),
            })
    written_ok = bool(inspection) and any(
        r["kind"] == "response" and r["uri"] == SOURCE and r["payload_matches"]
        and r["body_sha256"] == r["header_digest"] for r in inspection
    )

    # Independent pywb engine, isolated collection. No live-web / proxy / recording.
    collection_root = destination / "pywb"
    collection_root.mkdir()
    binpath = Path(sys.executable).parent
    manager = binpath / "wb-manager"
    wayback = binpath / "wayback"
    indexing = {"available":manager.is_file(),"successful":False,"stderr":""}
    replay = {"available":wayback.is_file(),"successful":False,"status":None,"reason":None}
    if manager.is_file() and written_ok:
        t1 = time.perf_counter()
        init = subprocess.run([str(manager),"init","nocturnal"],cwd=collection_root,
                              capture_output=True,text=True,timeout=20)
        if init.returncode == 0:
            add = subprocess.run([str(manager),"add","nocturnal",str(warc_path)],cwd=collection_root,
                                 capture_output=True,text=True,timeout=30)
            indexing.update(successful=add.returncode==0,
                            stderr=(add.stderr or "")[-220:],duration_ms=round((time.perf_counter()-t1)*1000,1))
        else:
            indexing["stderr"] = (init.stderr or "")[-220:]
    if indexing["successful"] and wayback.is_file():
        # Use ephemeral localhost port; never bind remote address.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        server = subprocess.Popen([str(wayback),"-b","127.0.0.1","-p",str(port),"-d",str(collection_root)],
                                  cwd=collection_root, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.PIPE, text=True)
        try:
            # Request replay *only* from localhost. No live-web behavior enabled.
            path = f"http://127.0.0.1:{port}/nocturnal/20261102090000id_/{SOURCE}"
            reason = ""
            for attempt in range(28):
                try:
                    req = urllib.request.Request(path,headers={"User-Agent":"AtlasInterop/1.0"})
                    with urllib.request.urlopen(req,timeout=2) as response:
                        content=response.read(200_000)
                        replay.update(status=response.status,
                                      successful=(response.status==200 and b"Original evidence claim" in content),
                                      response_sha256=hashlib.sha256(content).hexdigest(),
                                      payload_contains_control=b"Original evidence claim" in content)
                    break
                except Exception as e:
                    reason=type(e).__name__ + ": " + str(e)[:110]
                    if server.poll() is not None:break
                    time.sleep(.3)
            if not replay["successful"]:
                replay["reason"]=reason
        finally:
            server.terminate()
            try:server.communicate(timeout=4)
            except subprocess.TimeoutExpired:server.kill();server.communicate(timeout=4)
    verdict={
        "schema":SCHEMA,
        "source_repo":str(repo),
        "authority":"ISOLATED_SYNTHETIC_INTEROP_NOT_REAL_INVESTIGATION",
        "nocturnal_native_ms":native_ms,
        "native_warc": {"status":warc["status"],"size_bytes":warc_path.stat().st_size,
                        "readable_by_warcio":written_ok,"records":inspection},
        "pywb_index":indexing, "pywb_replay":replay,
        "limitations":[
            "Single synthetic HTML page, injected directly into the Nocturnal adapter; does not test live source acquisition.",
            "Replay success does not establish fidelity for JavaScript-heavy sites, robots restrictions, dynamic media or corrections.",
            "ArchiveBox already exists as a first-class optional native adapter, not a newly invented integration.",
            "No original Nocturnal source repository modified; archive and CLI outputs remain in temporary local folder."
        ],
    }
    (destination / "summary.json").write_text(json.dumps(verdict,indent=2)+"\n")
    return verdict


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--nocturnal-repo",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    z=run(a.nocturnal_repo.resolve(),a.out.resolve())
    print(json.dumps({"native_warc":z["native_warc"]["readable_by_warcio"],
        "pywb_index":z["pywb_index"]["successful"],"pywb_replay":z["pywb_replay"]["successful"],
        "duration_ms":z["nocturnal_native_ms"],"output":str(a.out.resolve()/"summary.json")},indent=2))


if __name__=="__main__":
    main()
