"""Official case-directory corroboration, separate from signed procurement custody.

A court directory HTML listing can establish a *registry record* without
establishing that its downloadable PDF has been retrieved, hashed or read.
This module does not infer criminal liability or signatory authority.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlsplit
import re

SCHEMA = "legal_codex.official_docket.v1"
OFFICIAL_HOST = "putusan3.mahkamahagung.go.id"
DOCKET_PATTERN = re.compile(r"^(14[789])/Pid\.Sus-TPK/2025/PN Jkt\.Pst$")
URL_PATTERN = re.compile(r"^/direktori/putusan/[a-z0-9]+\.html$")
KEY_PATTERN = re.compile(r"^case_[a-z0-9_]+$")


def validate(payload):
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ValueError("invalid official docket schema")
    cases = payload.get("cases")
    links = payload.get("cross_case_references")
    if not isinstance(cases, list) or len(cases) != 3 or not isinstance(links, list):
        raise ValueError("three scoped docket cases and explicit cross-case references required")
    indexed = {}
    numbers = set()
    for case in cases:
        key = case.get("id")
        if not isinstance(key, str) or not KEY_PATTERN.fullmatch(key) or key in indexed:
            raise ValueError("invalid/duplicate case id")
        match = DOCKET_PATTERN.fullmatch(case.get("docket", ""))
        if not match or match.group(1) in numbers:
            raise ValueError("invalid or duplicate 2025 Jakarta case docket")
        numbers.add(match.group(1))
        date.fromisoformat(case["judgment_date_reported"])
        if (case.get("pdf_bytes_obtained") is not False
                or case.get("pdf_sha256") is not None
                or case.get("full_judgment_reviewed") is not False
                or case.get("signed_2020_ppk_instrument_verified") is not False
                or case.get("e_catalog_order_matched") is not False
                or case.get("criminal_liability_inferred_by_this_audit") is not False):
            raise ValueError("court locator illegally promoted to document or liability proof")
        status = case.get("registry_status")
        url = case.get("registry_url")
        if status == "official_listing_indexed":
            if not isinstance(url, str):
                raise ValueError("missing official registry URL")
            u = urlsplit(url)
            if (u.scheme != "https" or u.netloc != OFFICIAL_HOST
                    or not URL_PATTERN.fullmatch(u.path) or u.query or u.fragment
                    or not case.get("pdf_attachment_listed") is True
                    or case.get("date_basis") != "official_directory"):
                raise ValueError("invalid official court directory provenance")
        elif status == "reported_docket_official_page_unlocated":
            if (url is not None or case.get("pdf_attachment_listed") is not False
                    or case.get("date_basis") != "secondary_reporting"
                    or not isinstance(case.get("reporting_url"), str)
                    or urlsplit(case["reporting_url"]).scheme != "https"):
                raise ValueError("unlocated docket masquerading as verified registry")
        else:
            raise ValueError("unsupported docket registry status")
        indexed[key] = case
    if numbers != {"147", "148", "149"}:
        raise ValueError("must preserve three distinct trial dockets")
    for relation in links:
        if (relation.get("from") not in indexed or relation.get("to") not in indexed
                or relation["from"] == relation["to"]
                or indexed[relation["from"]]["registry_status"] != "official_listing_indexed"
                or relation.get("kind") != "exhibit_disposition_mentions_separate_case"
                or relation.get("common_purchase_order_proved") is not False
                or relation.get("joint_criminal_liability_proved") is not False):
            raise ValueError("cross-case linkage cannot prove joint wrongdoing or procurement")
        if relation.get("source_url") != indexed[relation["from"]]["registry_url"]:
            raise ValueError("cross-case citation must originate in indexed court case")
    if not any(c["registry_status"] == "reported_docket_official_page_unlocated" for c in cases):
        raise ValueError("missing-case distinction lost")
    return indexed


def evaluate(payload):
    indexed = validate(payload)
    located = sorted((c for c in indexed.values() if c["registry_status"] == "official_listing_indexed"),
                     key=lambda c: c["docket"])
    missing = sorted((c for c in indexed.values()
                      if c["registry_status"] == "reported_docket_official_page_unlocated"),
                     key=lambda c: c["docket"])
    return {
        "schema": "legal_codex.official_docket_result.v1",
        "verified_official_directory_listing_count": len(located),
        "reported_but_unlocated_docket_count": len(missing),
        "listed_pdf_download_count": sum(c["pdf_attachment_listed"] is True for c in located),
        "pdf_files_obtained": 0,
        "pdf_hashes_verified": 0,
        "judgments_read_full_text": 0,
        "court_directory_is_not_signed_purchase_order": True,
        "2020_ppk_appointment_verified": False,
        "2020_sd_purchase_order_matched": False,
        "cross_case_references": [
            {"from": r["from"], "to": r["to"], "kind": r["kind"],
             "status": "candidate_reference_only", "common_transaction_verified": False}
            for r in payload["cross_case_references"]],
        "official_cases": [
            {"id": c["id"], "docket": c["docket"], "registry_url": c["registry_url"],
             "judgment_date": c["judgment_date_reported"], "pdf_listed_not_obtained": True}
            for c in located],
        "unlocated_cases": [
            {"id": c["id"], "docket": c["docket"],
             "reporting_url": c["reporting_url"], "judgment_date_only_reported": c["judgment_date_reported"]}
            for c in missing],
        "publication_authorized": False,
    }


def semantic_packet(payload):
    """Preview-only interop: even a court registry's cross-case link stays a candidate."""
    indexed = validate(payload)
    nodes = []
    edges = []
    for c in indexed.values():
        source = c.get("registry_url") or c["reporting_url"]
        nodes.append({"key": "docket-" + c["id"], "kind": "concept", "layer": "neutral",
                      "statement": c["docket"] + " — " + c["defendant_as_listed"],
                      "source_refs": [source],
                      "provenance": {
                          "registry_status": c["registry_status"],
                          "pdf_bytes_obtained": False,
                          "ppk_appointment_verified": False,
                          "transaction_matched": False}})
    for r in payload["cross_case_references"]:
        edges.append({
            "source": "docket-" + r["from"],
            "target": "docket-" + r["to"],
            "relation": "REFERENCES_EXHIBITS_FOR_SEPARATE_CASE",
            "status": "candidate"})
    return {"schema": "cite_refinery.semantic_graph.v1",
            "source_system": "legal-codex-official-dockets-009",
            "clusters": [], "nodes": nodes, "edges": edges}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--output", default="official_docket_009_result.json")
    parser.add_argument("--packet")
    args = parser.parse_args(argv)
    bundle = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = evaluate(bundle)
    Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.packet:
        Path(args.packet).write_text(json.dumps(semantic_packet(bundle), indent=2, ensure_ascii=False) + "\n",
                                     encoding="utf-8")
    print(json.dumps({
        "official_listing_count": report["verified_official_directory_listing_count"],
        "judgment_pdfs_obtained": 0, "appointment_and_purchase_verified": False}))


if __name__ == "__main__":
    main()
