"""Capture and re-extract one reviewed public Finlex decision for milestone 020.

The documented unauthenticated Akoma Ntoso endpoint supplies a public decision,
not the taxpayer's underlying logs. A source update requires explicit review and
a new pin; capture never accepts a changed body automatically. Receipt fields
record this fetch and are not a cryptographic certification of the publisher.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import ssl
import sys
import time
from urllib.error import HTTPError
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree as ET


SOURCE_ID = "finnish_tax_2026"
IDENTITY = "TSV/238/2022"
WORK_URI = "/akn/fi/judgment/data-protection-ombudsman-decision/2026/37"
SOURCE_URL = (
    "https://opendata.finlex.fi/finlex/avoindata/v1"
    + WORK_URI
    + "/fin%40"
)
PINNED_SHA256 = "aa73bd6c9e220e235fb1d27b275c6b0be3769dde4ac8815d2738ff8a1688848f"
SCHEMA = "legal_codex.finlex_source_020.v1"
ISSUED_DATE = "2026-10-23"
FINALITY_TEXT = "Päätös ei ole lainvoimainen."
AKN = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
NS = {"akn": AKN}
MAX_BYTES = 1024 * 1024
SOCKET_TIMEOUT_SECONDS = 25
MAX_ELAPSED_SECONDS = 60
USER_AGENT = "LegalCodex/020 public jurisprudence research"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _timestamp(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("capture timestamp must be a timezone-aware ISO string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("invalid capture timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("capture timestamp must include its timezone")
    return value


def _only(parent: ET.Element, path: str, label: str) -> ET.Element:
    found = parent.findall(path, NS)
    if len(found) != 1:
        raise ValueError(f"exactly one {label} required")
    return found[0]


def extract(
    raw: bytes, *, captured_at: str | None = None, require_pin: bool = True
) -> dict:
    """Validate a reviewed decision and extract its numbered paragraph elements.

    Numbered blocks preserve the text inside each numbered XML ``p`` element.
    Unnumbered quotations/list continuations remain available in the complete
    archived XML; the blocks are not represented as a complete text edition.
    ``require_pin=False`` permits structural test fixtures only. Both capture()
    and load() always use the reviewed pin and offer no unpinned CLI mode.
    """
    if not isinstance(raw, bytes) or not 40 < len(raw) <= MAX_BYTES:
        raise ValueError("source byte budget or type invalid")
    try:
        decoded = raw.decode("utf-8-sig", errors="strict")
    except UnicodeError as exc:
        raise ValueError("source is not UTF-8 XML") from exc
    if "<!DOCTYPE" in decoded.upper() or "<!ENTITY" in decoded.upper():
        raise ValueError("XML document type and entity declarations refused")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError("malformed XML") from exc
    if root.tag != f"{{{AKN}}}akomaNtoso":
        raise ValueError("expected Akoma Ntoso XML, not an HTML shell")
    judgment = _only(root, "akn:judgment", "judgment")
    if judgment.get("name") != "main":
        raise ValueError("expected main judgment")
    identification = _only(judgment, "akn:meta/akn:identification", "identification")
    work = _only(identification, "akn:FRBRWork", "FRBRWork")
    if _only(work, "akn:FRBRuri", "work URI").get("value") != WORK_URI:
        raise ValueError("wrong canonical work URI")
    if _only(work, "akn:FRBRthis", "work identifier").get("value") != WORK_URI + "/!main":
        raise ValueError("wrong canonical work identifier")
    aliases = work.findall("akn:FRBRalias[@name='diaryNumber']", NS)
    if len(aliases) != 1 or aliases[0].get("value") != IDENTITY:
        raise ValueError("wrong diary identity")
    issue_dates = [e.get("date") for e in work.findall("akn:FRBRdate[@name='dateIssued']", NS)]
    if issue_dates != [ISSUED_DATE]:
        raise ValueError("wrong work decision date")
    expression = _only(identification, "akn:FRBRExpression", "FRBRExpression")
    if _only(expression, "akn:FRBRuri", "expression URI").get("value") != WORK_URI + "/fin@":
        raise ValueError("wrong Finnish expression URI")
    if _only(expression, "akn:FRBRlanguage", "expression language").get("language") != "fin":
        raise ValueError("wrong decision language")
    expression_dates = [
        e.get("date") for e in expression.findall("akn:FRBRdate[@name='dateIssued']", NS)
    ]
    if expression_dates != [ISSUED_DATE]:
        raise ValueError("conflicting expression decision date")
    manifestation = _only(identification, "akn:FRBRManifestation", "FRBRManifestation")
    if _only(manifestation, "akn:FRBRformat", "manifestation format").get("value") != "xml":
        raise ValueError("wrong manifestation format")
    produced_dates = [
        e.get("date") for e in manifestation.findall("akn:FRBRdate[@name='dateProduced']", NS)
    ]
    for value in produced_dates:
        if not isinstance(value, str):
            raise ValueError("missing production date")
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("invalid production date") from exc
    publication_values = [
        e.get("date") for e in identification.findall(".//akn:FRBRdate[@name='datePublished']", NS)
    ]
    body = _only(judgment, "akn:judgmentBody", "judgment body")
    numbered: list[tuple[int, str]] = []
    finality: list[str] = []
    for paragraph in body.iter(f"{{{AKN}}}p"):
        text = normalize("".join(paragraph.itertext()))
        match = re.match(r"^([0-9]+)\.\s", text)
        if match:
            numbered.append((int(match[1]), text))
        if text == FINALITY_TEXT:
            finality.append(text)
    if [n for n, _ in numbered] != list(range(1, 68)):
        raise ValueError("numbered paragraphs 1..67 required exactly once, in order")
    if len(finality) != 1:
        raise ValueError("explicit nonfinal status missing or duplicated")
    raw_hash = digest(raw)
    if require_pin and raw_hash != PINNED_SHA256:
        raise ValueError("source differs from reviewed raw pin; review required")
    if captured_at is not None:
        _timestamp(captured_at)
    blocks = [
        {"id": f"p{number:04d}", "text": text, "sha256": digest(text.encode("utf-8"))}
        for number, text in numbered
    ]
    blocks.append({
        "id": "p_finality", "text": finality[0],
        "sha256": digest(finality[0].encode("utf-8")),
    })
    return {
        "source_id": SOURCE_ID, "identity": IDENTITY, "format": "xml",
        "source_url": SOURCE_URL, "raw_sha256": raw_hash,
        "date": ISSUED_DATE, "date_kind": "decision_date", "captured_at": captured_at,
        "metadata": {
            "publication_values": publication_values,
            "decision_dates": issue_dates,
            "produced_dates": produced_dates,
            "decision_finality": "not_final_as_published",
            "work_uri": WORK_URI,
        },
        "blocks": blocks,
    }


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "redirect refused for pinned endpoint", headers, fp)


def _xml_content_type(content_type: str) -> bool:
    return isinstance(content_type, str) and content_type.split(";", 1)[0].strip().lower() in {
        "application/xml", "text/xml",
    }


def fetch() -> tuple[bytes, str, str]:
    """Fetch only the fixed endpoint with normal certificate/hostname validation.

    Each socket operation has a 25-second timeout. The read loop additionally
    enforces a 60-second elapsed budget between bounded reads; a single in-flight
    operation can consume up to its socket timeout before that check runs.
    """
    context = ssl.create_default_context()
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        raise ValueError("TLS certificate and hostname verification required")
    opener = build_opener(HTTPSHandler(context=context), _NoRedirect())
    request = Request(SOURCE_URL, headers={
        "User-Agent": USER_AGENT, "Accept": "application/xml", "Accept-Encoding": "identity",
    })
    started = time.monotonic()
    with opener.open(request, timeout=SOCKET_TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}; not captured")
        final_url = response.geturl()
        if final_url != SOURCE_URL:
            raise ValueError("response URL differs from fixed endpoint")
        content_type = response.headers.get("Content-Type", "")
        if not _xml_content_type(content_type):
            raise ValueError("response is not XML")
        if response.headers.get("Content-Encoding", "identity").strip().lower() not in ("", "identity"):
            raise ValueError("unexpected content encoding")
        length_header = response.headers.get("Content-Length")
        if length_header is not None:
            try:
                declared_length = int(length_header)
            except ValueError as exc:
                raise ValueError("invalid Content-Length") from exc
            if not 40 < declared_length <= MAX_BYTES:
                raise ValueError("source byte budget")
        chunks: list[bytes] = []
        total = 0
        while True:
            if time.monotonic() - started > MAX_ELAPSED_SECONDS:
                raise TimeoutError("source elapsed-time budget exceeded")
            chunk = response.read1(min(65536, MAX_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_BYTES:
                raise ValueError("source byte budget")
        if time.monotonic() - started > MAX_ELAPSED_SECONDS:
            raise TimeoutError("source elapsed-time budget exceeded")
    raw = b"".join(chunks)
    if length_header is not None and len(raw) != declared_length:
        raise ValueError("truncated body or inconsistent Content-Length")
    return raw, content_type, final_url


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def capture(output_dir: str | Path) -> dict:
    """Capture into a new directory, leaving a failed receipt on fetch rejection."""
    dest = Path(output_dir)
    dest.mkdir(parents=True, exist_ok=False)
    attempted_at = datetime.now(timezone.utc).isoformat()
    receipt = {
        "schema": SCHEMA, "source_id": SOURCE_ID, "identity": IDENTITY,
        "status": "failed", "format": "xml", "url": SOURCE_URL, "final_url": None,
        "attempted_at": attempted_at, "raw_sha256": None, "raw_bytes": 0,
        "content_type": None, "http_status": None, "block_count": 0,
        "tls_hostname_verified": False,
    }
    raw_path = dest / f"{SOURCE_ID}.xml"
    parsed_path = dest / f"{SOURCE_ID}.json"
    try:
        raw, content_type, final_url = fetch()
        # True is set only after the fixed endpoint returned through the
        # validated standard-library TLS fetch, never for an imported snapshot.
        receipt.update({
            "final_url": final_url, "content_type": content_type, "http_status": 200,
            "raw_sha256": digest(raw), "raw_bytes": len(raw), "tls_hostname_verified": True,
        })
        parsed = extract(raw, captured_at=attempted_at)
        raw_path.write_bytes(raw)
        if extract(raw_path.read_bytes(), captured_at=attempted_at) != parsed:
            raise ValueError("written raw source re-extraction differs")
        _write_json(parsed_path, parsed)
        receipt.update(status="captured_and_reextracted", block_count=len(parsed["blocks"]))
    except Exception as exc:
        for path in (raw_path, parsed_path):
            if path.exists():
                path.unlink()
        receipt.update(status="failed", error=type(exc).__name__, detail=str(exc)[:240])
    _write_json(dest / "receipt.json", receipt)
    return receipt


def _unique_json_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _read_json(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError("JSON byte budget")
    value = json.loads(raw, object_pairs_hook=_unique_json_pairs)
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def load(folder: str | Path) -> dict:
    """Admit only this receipt schema, reviewed bytes and matching re-extraction."""
    folder = Path(folder)
    receipt = _read_json(folder / "receipt.json")
    expected = {
        "schema": SCHEMA, "source_id": SOURCE_ID, "identity": IDENTITY,
        "status": "captured_and_reextracted", "format": "xml", "url": SOURCE_URL,
        "final_url": SOURCE_URL, "http_status": 200, "block_count": 68,
        "raw_sha256": PINNED_SHA256,
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError("unaccepted Finlex receipt schema, identity, status or pin")
    if receipt.get("tls_hostname_verified") is not True:
        raise ValueError("receipt lacks verified TLS fetch")
    if not _xml_content_type(receipt.get("content_type")):
        raise ValueError("receipt content type is not XML")
    captured_at = _timestamp(receipt.get("attempted_at"))
    raw_path = folder / f"{SOURCE_ID}.xml"
    if not 40 < raw_path.stat().st_size <= MAX_BYTES:
        raise ValueError("stored source byte budget")
    raw = raw_path.read_bytes()
    if type(receipt.get("raw_bytes")) is not int or receipt["raw_bytes"] != len(raw):
        raise ValueError("receipt source byte count differs")
    if digest(raw) != PINNED_SHA256:
        raise ValueError("stored source differs from reviewed raw pin")
    parsed = extract(raw, captured_at=captured_at)
    if _read_json(folder / f"{SOURCE_ID}.json") != parsed:
        raise ValueError("stored extraction differs from original source")
    return parsed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    try:
        receipt = capture(args.output_dir)
    except OSError as exc:
        print(f"capture directory unavailable: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(receipt))
    return 0 if receipt["status"] == "captured_and_reextracted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
