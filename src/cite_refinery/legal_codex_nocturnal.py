"""Fail-closed Nocturnal capture bridge for the Legal Codex.

Uses Nocturnal's own local capture loader. Its bytes/text/identity rechecks are
required; hashes in an arbitrary supplied JSON file are not authentication.
The bridge never treats excerpt integrity as truth, entailment, or permission
to publish. Nothing is written to the Nocturnal case or its ledger.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from .legal_codex_benchmark import evaluate, checked

CAPTURE_SCHEMA = "nocturnal_source_capture.v2"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verified_passage(
    source: dict[str, Any],
    *,
    state_dir: str | Path,
    case_id: str,
    capture_id: str,
    proposal_id: str,
    loader: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Check a source using the real Nocturnal loader (injectable for tests).

    Loader must perform Nocturnal's file read + source identity + raw response,
    extracted text and proposal re-derivation checks. Passing a fake loader is
    never a live verification and must not be reported as one.
    """
    if loader is None:
        try:
            from src.nocturnal_engine.source_capture import load_verified_capture
        except ImportError as exc:
            raise RuntimeError(
                "Nocturnal is unavailable; install/checkout nocturnal-oversight "
                "in this Python environment before requesting a capture check"
            ) from exc
        loader = load_verified_capture
    if not re.fullmatch(r"cap-[0-9a-f]{24}", capture_id):
        raise ValueError("invalid Nocturnal capture identifier")
    if not re.fullmatch(r"prop-[0-9a-f]{24}", proposal_id):
        raise ValueError("invalid Nocturnal proposal identifier")
    capture = loader(state_dir=Path(state_dir), case_id=case_id, capture_id=capture_id)
    if capture.get("schema") != CAPTURE_SCHEMA or capture.get("case_id") != case_id:
        raise ValueError("unexpected Nocturnal capture schema or case")
    if capture.get("capture_id") != capture_id or capture.get("http_status") != 200:
        raise ValueError("Nocturnal capture identity/HTTP status mismatch")
    constraints = capture.get("constraints") or {}
    if (constraints.get("tls_hostname_verified") is not True
            or constraints.get("injected_test_fetcher") is not False
            or constraints.get("source_authenticity_established") is not False
            or constraints.get("publication_authorized") is not False):
        raise ValueError("capture did not use approved live TLS verification")
    if capture.get("source_url") != source.get("url"):
        raise ValueError("source URL does not match the Nocturnal capture")
    if urlsplit(source["url"]).scheme != "https":
        raise ValueError("source URL must be HTTPS")
    proposal = next((x for x in capture.get("proposals", [])
                     if x.get("proposal_id") == proposal_id), None)
    if proposal is None or proposal.get("extraction_method") != "unicode_verbatim_sentence_v2":
        raise ValueError("Nocturnal verbatim proposal not found")
    excerpt = source.get("excerpt", "")
    if not excerpt or excerpt not in proposal.get("quote", ""):
        raise ValueError("source excerpt not found in verified Nocturnal passage")
    if source.get("excerpt_sha256") != _digest(excerpt):
        raise ValueError("source excerpt digest mismatch")
    for name in ("raw_sha256", "extracted_sha256"):
        if not re.fullmatch("[0-9a-f]{64}", str(capture.get(name, ""))):
            raise ValueError("missing capture byte/text digest")
    if proposal.get("text_sha256") != capture["extracted_sha256"]:
        raise ValueError("proposal text digest mismatch")
    return {
        "source_id": source["id"],
        "case_id": case_id,
        "capture_id": capture_id,
        "proposal_id": proposal_id,
        "raw_sha256": capture["raw_sha256"],
        "extracted_sha256": capture["extracted_sha256"],
        "excerpt_sha256": _digest(excerpt),
        "integrity": "nocturnal_loader_rechecked",
        "source_authenticity": "not_established",
        "claim_truth": "not_adjudicated",
        "publication_authorized": False,
    }


def evaluate_captures(bundle: dict[str, Any], references: list[dict[str, Any]],
                      *, loader: Callable[..., dict[str, Any]] | None = None
                      ) -> dict[str, Any]:
    """Evaluate input plus Nocturnal evidence, without upgrading the claims."""
    sources, _, _, _ = checked(bundle)
    if not isinstance(references, list) or not references:
        raise ValueError("Nocturnal references required; no verification by omission")
    seen = set()
    receipts = []
    for r in references:
        ident = r.get("source_id")
        if ident in seen or ident not in sources:
            raise ValueError("repeated or unknown Nocturnal source")
        seen.add(ident)
        receipts.append(verified_passage(
            sources[ident],
            state_dir=r["state_dir"], case_id=r["case_id"],
            capture_id=r["capture_id"], proposal_id=r["proposal_id"], loader=loader))
    result = evaluate(bundle)
    result["nocturnal_receipts"] = receipts
    result["source_integrity"] = {
        "checked_sources": len(receipts),
        "total_sources": len(sources),
        "scope": "rechecked_source_bytes_and_extractions_not_source_truth",
        "live_verification": loader is None,
    }
    # In particular: DO NOT change authority, approval status, or causal estimates.
    return result


def main(argv=None):
    """Revalidate existing Nocturnal captures before making audit candidates.

    The private Nocturnal checkout/package must be installed in the caller's
    Python environment. A JSON receipt is never accepted as evidence by itself.
    """
    import argparse
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("benchmark")
    p.add_argument("capture_references",
                   help="JSON list: source_id, state_dir, case_id, capture_id, proposal_id")
    p.add_argument("--output", default="legal_codex_nocturnal_result.json")
    args = p.parse_args(argv)
    bundle = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
    refs = json.loads(Path(args.capture_references).read_text(encoding="utf-8"))
    result = evaluate_captures(bundle, refs)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")
    print(json.dumps({"capture_integrity_checked": len(result["nocturnal_receipts"]),
                      "claim_truth_verified": False, "publication_authorized": False}))


if __name__ == "__main__":
    main()
