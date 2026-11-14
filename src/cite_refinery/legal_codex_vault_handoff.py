"""Cite–Refinery Milestone 014: Nocturnal vault custody gate.

The expected sources are derived from the already pinned 012/013 fixtures.
No text, hash, or receipt supplied by an arbitrary JSON object is accepted as
original-source proof. Production receipts require a real Nocturnal vault
verification at the requested operator-controlled path. Synthetic/test doubles
never satisfy the acquisition gate or authorize factual/legal conclusions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "legal_codex.vault_handoff_014.v1"
PINNED_PUBLIC_COURT_MIRRORS = {
    "judgment_dutch_3535": [
        "https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:RVS:2019:3535"],
    "judgment_dutch_3536": [
        "https://data.rechtspraak.nl/uitspraken/content?Id=ECLI:NL:RVS:2019:3536"],
}


def _base():
    return Path(__file__).resolve().parents[2]


def _expected():
    root = _base() / "examples"
    past = json.loads((root / "legal_codex_outcome_trace_013.json").read_text(encoding="utf-8"))
    courts = json.loads((root / "legal_codex_judgment_reconstruction_012.json").read_text(encoding="utf-8"))
    rows = [{
        "source_id": s["id"], "source_url": s["url"],
        "reference_date": s["data_as_of"], "source_family": "outcome_013",
    } for s in past["sources"]]
    rows += [{
        "source_id": "judgment_" + j["id"],
        "source_url": j["source_url"], "reference_date": j["decided_on"],
        "source_family": "judgment_012",
    } for j in courts["judgments"]]
    for row in rows:
        row["approved_official_alternates"] = PINNED_PUBLIC_COURT_MIRRORS.get(row["source_id"], [])
    return sorted(rows, key=lambda x: x["source_id"])


def _hash(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def validate(bundle):
    if (not isinstance(bundle, dict) or bundle.get("schema") != SCHEMA or
            set(bundle) != {"schema", "as_of", "expected_sources", "originals_archived_in_fixture",
                            "legal_editorial_approval", "case_specific_remedies_proven",
                            "publication_authorized"}):
        raise ValueError("invalid vault handoff fixture")
    if bundle["as_of"] != "2026-11-15" or bundle["expected_sources"] != _expected():
        raise ValueError("unapproved source list or reporting date")
    if any(bundle[name] is not False for name in (
            "originals_archived_in_fixture", "legal_editorial_approval",
            "case_specific_remedies_proven", "publication_authorized")):
        raise ValueError("unreviewed evidence promoted")
    return _expected()


def evaluate(bundle, *, vault_root=None, verifier=None):
    expected = validate(bundle)
    vault = None
    real_loader = vault_root is not None and verifier is None
    if vault_root is not None:
        if verifier is None:
            from src.nocturnal_engine.legal_codex_evidence_vault import verify_vault
            verifier = verify_vault
        vault = verifier(Path(vault_root))
        if (vault.get("schema") != "nocturnal.legal_codex_vault_review.v1" or
                vault.get("publication_authorized") is not False or
                vault.get("source_authenticity_certified") is not False or
                vault.get("factual_corrections_adjudicated") is not False or
                vault.get("external_head_anchor_verified") is not False):
            raise ValueError("invalid or overclaimed Nocturnal vault verification")
        if not isinstance(vault.get("snapshot_receipts"), list):
            raise ValueError("Nocturnal vault did not provide integrity rechecked receipts")
    results = []
    all_receipts = vault["snapshot_receipts"] if vault else []
    for item in expected:
        matches = [s for s in all_receipts if s.get("source_id") == item["source_id"]]
        exact = [s for s in matches if
                 s.get("source_url") in [item["source_url"], *item["approved_official_alternates"]] and
                 s.get("reference_date") == item["reference_date"]]
        authentic = [s for s in exact if
                     real_loader and s.get("acquisition_state") == "live_nocturnal_loader_rechecked"
                     and s.get("source_truth_verified") is False]
        status = ("verified_source_bytes_present" if authentic else
                  "source_identity_or_reference_period_mismatch" if matches and not exact else
                  "synthetic_or_untrusted_capture" if exact else
                  "not_acquired")
        results.append({
            **item, "custody_status": status,
            "verified_byte_captures": len(authentic),
            "snapshot_raw_sha256": [s["raw_sha256"] for s in authentic],
            "acquired_official_source_urls": sorted(set(s["source_url"] for s in authentic)),
            "legal_source_authenticity": "not_established",
            "source_truth_verified": False,
            "individual_remedy_verified": False,
        })
    return {
        "schema": "legal_codex.vault_handoff_result.v1",
        "expected_source_count": len(expected),
        "verified_byte_source_count": sum(row["verified_byte_captures"] > 0 for row in results),
        "missing_or_untrusted_count": sum(not row["verified_byte_captures"] for row in results),
        "source_status": results,
        "nocturnal_hash_chain_rechecked": bool(real_loader and vault),
        "vault_head_event_sha256": vault["head_event_sha256"] if real_loader and vault else None,
        "unreviewed_correction_candidates": vault["revision_candidate_count"] if vault else 0,
        "failed_capture_attempts_logged": vault["failed_attempt_count"] if vault else 0,
        "official_claims_independently_verified": False,
        "external_checkpoint_signature_present": False,
        "factual_corrections_adjudicated": False,
        "court_to_person_payment_links_verified": False,
        "publication_authorized": False,
        "input_digest": _hash(bundle),
    }


def semantic_packet(bundle, result):
    expected = validate(bundle)
    if result.get("input_digest") != _hash(bundle):
        raise ValueError("stale custody result")
    if [r["source_id"] for r in result.get("source_status",[])] != [
            e["source_id"] for e in expected]:
        raise ValueError("source status cannot substitute unauthorized identifiers")
    nodes, edges = [], []
    for row in result["source_status"]:
        sid = row["source_id"]
        nodes.append({"key":"vault-source-"+sid,"kind":"source","layer":"neutral",
                      "statement":row["source_url"],"source_refs":[row["source_url"]]})
        nodes.append({"key":"custody-review-"+sid,"kind":"observation","layer":"neutral",
                      "statement":"Source custody status: "+row["custody_status"],
                      "source_refs":[row["source_url"]],
                      "provenance":{"original_legal_authenticity":False,
                                    "publication_authorized":False,
                                    "verified_byte_capture_count":row["verified_byte_captures"]}})
        edges.append({"source":"vault-source-"+sid,"target":"custody-review-"+sid,
                      "relation":"HAS_CANDIDATE_CUSTODY_STATUS","status":"candidate"})
    return {"schema":"cite_refinery.semantic_graph.v1",
            "source_system":"legal-codex-vault-handoff-014",
            "clusters":[],"nodes":nodes,"edges":edges}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--vault-root", help="Private persistent Nocturnal vault root (optional)")
    p.add_argument("--output", default="legal_codex_vault_handoff_014_result.json")
    p.add_argument("--packet")
    args=p.parse_args(argv)
    bundle=json.loads(Path(args.input).read_text(encoding="utf-8"))
    result=evaluate(bundle,vault_root=args.vault_root)
    Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    if args.packet:
        Path(args.packet).write_text(json.dumps(
            semantic_packet(bundle,result),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"expected":result["expected_source_count"],
                      "source_bytes_verified":result["verified_byte_source_count"],
                      "public_claims_verified":False,"publication_authorized":False}))


if __name__ == "__main__":
    main()
