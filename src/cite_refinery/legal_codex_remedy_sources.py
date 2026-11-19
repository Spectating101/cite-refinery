"""Load reviewed public decisions and run the obligation tracker.

Existing 019 snapshots can be reused without rewriting their acquisition record.
New Dutch captures and the new Finlex endpoint have separate receipts. Dates
in the real example use the capture of these exact bytes, not presumed historic
availability of a later revised text.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

from .legal_codex_access_outcomes import SOURCE_PINS, digest, _capture_module
from .legal_codex_remedy_tracker import evaluate, semantic_packet

DUTCH = ("hospital_2024", "hospital_2026", "staff_identity_2025")


def finlex_module():
    path = Path(__file__).resolve().parents[2] / "scripts/legal_codex_capture_020.py"
    spec = importlib.util.spec_from_file_location("legal_codex_finlex_capture_020", path)
    if spec is None or spec.loader is None:
        raise ValueError("Finlex parser unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_dutch(folder):
    root = Path(folder)
    capture = _capture_module()
    receipt_path = root / "receipt.json"
    if receipt_path.is_symlink():
        raise ValueError("source receipt symlink refused")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "legal_codex.cross_case_sources_019.v1":
        raise ValueError("wrong Dutch receipt schema")
    rows = receipt.get("sources", [])
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise ValueError("malformed source receipt")
    registry = {r.get("source_id"): r for r in rows}
    if len(registry) != len(rows) or not set(DUTCH).issubset(registry):
        raise ValueError("duplicate or missing Dutch source")
    sources = {}
    for sid in DUTCH:
        row = registry[sid]
        url, fmt, identity = capture.SOURCES[sid]
        if (row.get("status") != "captured_and_reextracted" or row.get("url") != url
                or row.get("final_url") != url or row.get("identity") != identity
                or row.get("format") != fmt or row.get("tls_hostname_verified") is not True):
            raise ValueError("source identity or capture state mismatch")
        when = datetime.fromisoformat(row["attempted_at"].replace("Z", "+00:00"))
        if when.tzinfo is None:
            raise ValueError("capture timestamp lacks timezone")
        raw_path, parsed_path = root / (sid + ".xml"), root / (sid + ".json")
        if raw_path.is_symlink() or parsed_path.is_symlink():
            raise ValueError("source symlink refused")
        raw = raw_path.read_bytes()
        pin, decided, sector = SOURCE_PINS[sid]
        if digest(raw) != pin or row.get("raw_sha256") != pin or row.get("raw_bytes") != len(raw):
            raise ValueError("reviewed source bytes or receipt changed")
        doc = capture.extract(raw, fmt, identity)
        if decided not in doc["metadata"]["decision_dates"]:
            raise ValueError("source decision date changed")
        if json.loads(parsed_path.read_text(encoding="utf-8")) != doc:
            raise ValueError("saved extraction differs from reviewed bytes")
        sources[sid] = {**doc, "source_id": sid, "source_url": url, "raw_sha256": pin,
            "date": decided, "date_kind": "decision_date", "sector": sector,
            "captured_at": row["attempted_at"], "historical_version_verified": False}
    return sources


def capture_dutch(folder):
    """Acquire only the three previously reviewed Dutch decisions for a new run."""
    root = Path(folder)
    root.mkdir(parents=True, exist_ok=False)
    capture = _capture_module()
    rows = []
    for sid in DUTCH:
        url, fmt, identity = capture.SOURCES[sid]
        row = {"source_id": sid, "url": url, "format": fmt, "identity": identity,
               "attempted_at": datetime.now(timezone.utc).isoformat()}
        try:
            raw, ctype, final = capture.fetch(url)
            if "xml" not in ctype.lower() or final != url:
                raise ValueError("unexpected source content type or URL")
            if digest(raw) != SOURCE_PINS[sid][0]:
                raise ValueError("source changed; substantive re-review required")
            parsed = capture.extract(raw, fmt, identity)
            (root / (sid + ".xml")).write_bytes(raw)
            (root / (sid + ".json")).write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            row.update(status="captured_and_reextracted", final_url=final, raw_sha256=digest(raw),
                       raw_bytes=len(raw), block_count=len(parsed["blocks"]), tls_hostname_verified=True)
        except Exception as exc:
            row.update(status="failed", detail=str(exc)[:240])
        rows.append(row)
    receipt = {"schema": "legal_codex.cross_case_sources_019.v1",
               "scope": "Three Dutch snapshots reused by the 020 remedy tracker; not a rerun of the original five-target 019 acquisition.",
               "sources": rows, "captured_count": sum(r["status"] == "captured_and_reextracted" for r in rows)}
    (root / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if receipt["captured_count"] != len(DUTCH):
        raise ValueError("Dutch acquisition incomplete; inspect source receipt")
    load_dutch(root)
    return receipt


def load_inputs(dutch_folder, finlex_folder, ledger_path):
    sources = load_dutch(dutch_folder)
    finnish = finlex_module().load(finlex_folder)
    sources[finnish["source_id"]] = finnish
    ledger = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    # Null explicitly requests a date derived from the verified receipt of this
    # input version. Explicit dates are never overwritten to pass validation.
    ledger = deepcopy(ledger)
    for sid, binding in ledger["sources"].items():
        if binding.get("available_on") is None:
            if binding.get("availability_basis") != "first_verified_capture":
                raise ValueError("only capture-bound availability can be derived")
            binding["available_on"] = sources[sid]["captured_at"][:10]
    return ledger, sources


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dutch")
    parser.add_argument("--dutch-evidence-dir")
    parser.add_argument("--finlex-evidence-dir")
    parser.add_argument("--ledger")
    parser.add_argument("--as-of")
    parser.add_argument("--output")
    parser.add_argument("--packet")
    args = parser.parse_args(argv)
    if args.capture_dutch:
        result = capture_dutch(args.capture_dutch)
        print(json.dumps({"captured_dutch_sources": result["captured_count"]}))
        return 0
    if not all((args.dutch_evidence_dir, args.finlex_evidence_dir, args.ledger, args.output, args.as_of)):
        parser.error("tracking requires Dutch and Finlex evidence directories, ledger, as-of date and output")
    ledger, sources = load_inputs(args.dutch_evidence_dir, args.finlex_evidence_dir, args.ledger)
    result = evaluate(ledger, sources, args.as_of)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.packet:
        Path(args.packet).write_text(json.dumps(semantic_packet(ledger, sources, args.as_of), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sources": len(result["sources"]), "obligations": len(result["obligations"]),
        "events": len(result["events"]), "public_source_confirmed_components": result["confirmed_obligation_count"],
        "original_record_custody": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
