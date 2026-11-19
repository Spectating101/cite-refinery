"""Reconcile frozen, already-produced source reviews into the repository layer.

This adapter does not acquire sources, run models, execute upstream programs or
publish a native graph. Byte and quote checks refer to the retained export's
explicit verification receipts. Workflow narratives remain separately accounted
context; only bounded technical fields enter repository records.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from .repository_layer import _digest, _identity_resolution, _repo_id
from .repository_layer_import import _pin


EXPORT_SCHEMA = "cite_refinery.repository_refresh_export.v1"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _source_repo(url: str) -> str | None:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if parsed.hostname in {"github.com", "www.github.com", "raw.githubusercontent.com"} and len(parts) >= 2:
        return _repo_id("/".join(parts[:2]))
    if parsed.hostname == "api.github.com" and len(parts) >= 3 and parts[0] == "repos":
        return _repo_id("/".join(parts[1:3]))
    return None


def refresh_snapshot(path: str | Path) -> dict:
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    if data.get("schema") != EXPORT_SCHEMA or not isinstance(data.get("records"), list):
        raise ValueError("a frozen repository refresh export is required")
    export_sha = hashlib.sha256(raw).hexdigest()
    observed_at = data.get("observed_at")
    records = data["records"]
    sources, rows, exclusions, resolutions = {}, {}, [], []
    checks, quotes = {}, {}
    for key in ("identity_reviews", "census_reviews", "handoff_documents"):
        for wrapper in data.get(key, []):
            if wrapper.get("exported_document_sha256") and _digest(wrapper.get("document")) != wrapper["exported_document_sha256"]:
                raise ValueError("review document changed after the frozen export")

    def add_check(check: dict) -> None:
        key = (check.get("path"), check.get("expected_sha256"))
        if key in checks and checks[key] != check:
            # A repeated successful byte check may carry extra attribution.
            if any(checks[key].get(k) != check.get(k) for k in ("state", "actual_sha256")):
                raise ValueError("conflicting retained-source checks")
        checks[key] = check

    def add_quote(check: dict) -> None:
        key = (check.get("source_path", check.get("path")), check.get("source_sha256"), check.get("quote_sha256"))
        if key in quotes and quotes[key].get("state") != check.get("state"):
            raise ValueError("conflicting literal quote checks")
        quotes[key] = check

    for check in data.get("source_checks", []):
        add_check(check)
    for check in data.get("quote_checks", []) + data.get("evidence_checks", []):
        add_quote(check)
    for record in records:
        if record.get("source_check"):
            add_check(record["source_check"])
        for check in record.get("quote_checks", []):
            add_quote(check)

    known_ids = {_repo_id(r["catalog_id"]) for r in records}
    if len(known_ids) != len(records):
        raise ValueError("mapping cohorts overlap or repeat listing IDs")
    for wrapper in data.get("identity_reviews", []):
        document = wrapper.get("document", {})
        for group in document.get("groups", []):
            canonical = group.get("canonical_id", group.get("canonical_repository_id"))
            ids = group.get("catalog_ids", group.get("observed_repository_ids", []))
            ids = sorted({_repo_id(r) for r in ids})
            if not canonical or not ids:
                continue
            resolution = _identity_resolution({
                "canonical_repository_id": canonical, "observed_repository_ids": ids,
                "decision": "same_repository", "authority": "reviewed_identity",
                "native_merge_performed": False,
                "reason": group.get("reason") or "Reviewed captured GitHub identity and preserved native bindings.",
                "evidence": [{"path": wrapper["path"], "sha256": wrapper["sha256"]}],
                "reviewed_at": document.get("reviewed_at"), "reviewed_by": document.get("reviewed_by"),
                "preserved_native_bindings": deepcopy(group.get("incumbent_bindings", {})),
                "preserved_contexts": deepcopy(group.get("preserved_contexts", {})),
            })
            if resolution not in resolutions:
                resolutions.append(resolution)
    identity_by_id = {}
    for resolution in resolutions:
        for rid in resolution["observed_repository_ids"]:
            canonical = resolution["canonical_repository_id"]
            if rid in identity_by_id and identity_by_id[rid] != canonical:
                raise ValueError("conflicting reviewed current identities")
            identity_by_id[rid] = canonical

    def source(original: dict, rid: str) -> str:
        url = original.get("source_url", "")
        capture = original.get("path", original.get("source_path"))
        content_sha = original.get("sha256", original.get("source_sha256"))
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("original source requires an HTTPS locator without credentials")
        if not re.fullmatch(r"[0-9a-f]{64}", str(content_sha or "")) or not capture:
            raise ValueError("original source requires its captured bytes and SHA256")
        owner = _source_repo(url)
        if owner and owner != rid and identity_by_id.get(rid) != owner:
            raise ValueError("cross-repository source lacks a reviewed identity resolution")
        check = checks.get((capture, content_sha), {})
        matched = check.get("state") == "match" and check.get("actual_sha256") == content_sha
        if not matched:
            raise ValueError("retained original source bytes were not verified")
        sid = "refresh_source:" + _digest([rid, url, capture, content_sha])[:24]
        receipt = {"id": sid, "repository_id": rid, "url": url,
                   "kind": "code" if original.get("kind") in {"code", "source"} else "documentation",
                   "content_sha256": content_sha, "original_capture_path": capture,
                   "capture_integrity": "match", "byte_integrity_checked": True,
                   "semantic_support_verified": False, "runtime_tested": False,
                   "verification_origin": "frozen_repository_refresh_export", **_pin(url)}
        if owner and owner != rid:
            receipt["original_source_repository_id"] = owner
            receipt["identity_resolution_ids"] = [r["id"] for r in resolutions if rid in r["observed_repository_ids"]]
        if sid in sources and sources[sid] != receipt:
            raise ValueError("conflicting retained source record")
        sources[sid] = receipt
        return sid

    def evidence(original: dict, rid: str, *, source_defaults: dict | None = None) -> dict:
        original = {**(source_defaults or {}), **original}
        quote = original.get("quote", original.get("excerpt"))
        if not isinstance(quote, str) or len(quote) < 12:
            raise ValueError("literal source excerpt is absent or too short")
        sid = source(original, rid)
        receipt = sources[sid]
        check = quotes.get((receipt["original_capture_path"], receipt["content_sha256"], _sha(quote)), {})
        if check.get("state") != "match":
            raise ValueError("literal source excerpt was not verified")
        start = original.get("start", original.get("character_start"))
        end = original.get("end", original.get("character_end"))
        proof = {"source_id": sid, "source_sha256": receipt["content_sha256"], "excerpt": quote,
                 "byte_integrity_checked": True, "quote_integrity": "exact_quote_present",
                 "semantic_support_verified": False, "runtime_tested": False}
        if start is not None or end is not None:
            if (type(start) is not int or type(end) is not int or start < 0 or end - start != len(quote)
                    or check.get("start_match") is not True or check.get("end_match") is not True):
                raise ValueError("retained source excerpt offsets are inconsistent")
            proof.update(excerpt_start=start, excerpt_end=end, offset_verification="retained_catalog_check")
        return proof

    def interpretation(result: dict, rid: str, provenance: dict, worker: str = "", status: str = "mapped") -> dict:
        proofs = [evidence(e, rid) for e in result.get("evidence", []) + result.get("additional_evidence", [])]
        if not proofs:
            raise ValueError("technical interpretation has no verified literal evidence")
        method = result.get("analysis_method", "")
        return {"purpose": result.get("purpose", ""),
                **{k: deepcopy(result.get(k, [])) for k in ("inputs", "outputs", "human_work", "custom_glue")},
                "limitations": deepcopy(result.get("limits", [])), "analysis_method": method,
                "worker": worker, "status": status,
                "authority": "source_bound_model_interpretation" if "model" in method or "llm" in method or result.get("explanation_state") == "source_bound_model_interpretation" else "source_bound_interpretation",
                "semantic_support_verified": False, "runtime_tested": False,
                "evidence": proofs, "evidence_ids": sorted({p["source_id"] for p in proofs}),
                "provenance": {**provenance, "catalog_id": rid, "export_sha256": export_sha,
                    "revision_of_sha256": result.get("revision_of_sha256"),
                    "review_method": result.get("review_method"), "review_reason": result.get("review_reason"),
                    "reviewed_by": result.get("reviewed_by")}}

    admitted = 0
    for record in records:
        rid = _repo_id(record["catalog_id"])
        project = record.get("project", {})
        row = {"id": rid, "full_name": rid[7:], "url": "https://github.com/" + rid[7:],
               "description": project.get("description", ""), "topics": deepcopy(project.get("topics", [])),
               "observed_at": observed_at, "source_interpretations": [],
               "source_mapping_states": [{"cohort": record["cohort"], "status": record["status"],
                    "reason": record.get("reason"), "source_status": (record.get("source") or {}).get("status"),
                    "record_sha256": _digest(record), "observed_at": observed_at}],
               "technical_context": {"mapping_updated_at": record.get("updated_at"),
                    "source_sha256": record.get("source_sha256"), "result_sha256": record.get("result_sha256"),
                    "excluded_fields": deepcopy(record.get("excluded_fields", {})),
                    "publication_observations": deepcopy(project.get("publication_observations", [])),
                    "source_ids": [], "source_interpretation_exclusions": []}}
        rows[rid] = row
        original = record.get("source") or {}
        if original.get("status") == "captured":
            try:
                row["technical_context"]["source_ids"].append(source(original, rid))
            except ValueError as exc:
                exclusions.append({"catalog_id": rid, "kind": "source_receipt", "reason": str(exc),
                                   "original_record_sha256": record.get("original_source_json_sha256")})
        if record["status"] != "mapped":
            continue
        result = record.get("result") or {}
        try:
            if result.get("source_sha256") != record.get("source_sha256"):
                raise ValueError("accepted interpretation source hash differs from queue source")
            if (record.get("original_result_json_sha256") and
                    record.get("result_sha256") != record["original_result_json_sha256"]):
                raise ValueError("accepted result JSON no longer matches its retained hash")
            item = interpretation(result, rid, {"cohort": record["cohort"],
                "raw_record_sha256": record.get("original_result_json_sha256"),
                "excluded_fields": record.get("excluded_fields", {})}, record.get("worker", ""))
            row["source_interpretations"].append(item)
            admitted += 1
        except ValueError as exc:
            exclusion = {"catalog_id": rid, "kind": "accepted_interpretation", "reason": str(exc),
                         "original_record_sha256": record.get("original_result_json_sha256")}
            row["technical_context"]["source_interpretation_exclusions"].append(exclusion)
            exclusions.append(exclusion)

    published_admitted = 0
    published = data.get("published_catalog", {})
    for record in published.get("records", []):
        raw_id = record.get("catalog_id", "")
        if not raw_id.startswith("github:"):
            continue
        rid = _repo_id(raw_id)
        row = rows.setdefault(rid, {"id": rid, "full_name": rid[7:], "url": "https://github.com/" + rid[7:],
                    "observed_at": observed_at, "source_interpretations": [], "technical_context": {"source_ids": []}})
        for original in record.get("source_receipts", []):
            try:
                sid = source(original, rid)
                refs = row["technical_context"].setdefault("source_ids", [])
                if sid not in refs:
                    refs.append(sid)
            except ValueError as exc:
                exclusions.append({"catalog_id": rid, "kind": "published_source_receipt", "reason": str(exc),
                                   "original_record_sha256": record.get("original_payload_sha256")})
    for record in data.get("published_records", []):
        raw_id = record.get("catalog_id", "")
        if not raw_id.startswith("github:"):
            exclusions.append({"catalog_id": raw_id, "kind": "published_interpretation", "reason": "not_a_repository_record",
                               "original_record_sha256": record.get("original_result_sha256")})
            continue
        rid = _repo_id(raw_id)
        project = record.get("project", {})
        row = rows.setdefault(rid, {"id": rid, "full_name": rid[7:], "url": "https://github.com/" + rid[7:],
                    "description": project.get("description", ""), "topics": project.get("topics", []),
                    "observed_at": observed_at, "source_interpretations": [], "technical_context": {}})
        try:
            item = interpretation(record["result"], rid, {
                "publication_state": record.get("status"), "published_index": record.get("published_index"),
                "raw_record_sha256": record.get("original_result_sha256"),
                "raw_payload_sha256": record.get("original_payload_sha256"), "publication_difference": record.get("reason"),
                "excluded_fields": record.get("excluded_fields", [])},
                record["result"].get("worker", ""), "published_source_bound")
            row["source_interpretations"].append(item)
            published_admitted += 1
        except ValueError as exc:
            exclusions.append({"catalog_id": rid, "kind": "published_interpretation", "reason": str(exc),
                               "original_record_sha256": record.get("original_result_sha256")})

    for resolution in resolutions:
        for rid in resolution["observed_repository_ids"]:
            rows.setdefault(rid, {"id": rid, "full_name": rid[7:], "url": "https://github.com/" + rid[7:],
                                  "observed_at": observed_at, "source_interpretations": [],
                                  "technical_context": {"identity_review_only": True,
                                      "reason": "Historical listing retained by the explicit identity review."}})

    census_counts = Counter()
    withheld_count = 0
    for wrapper in data.get("census_reviews", []):
        document = wrapper.get("document", wrapper)
        reviews = document.get("reviews", [document])
        for review in reviews:
            rid = _repo_id(review["catalog_id"])
            status = {"approve": "approved", "reject": "rejected", "restricted": "held"}.get(review["decision"], "unresolved")
            census_counts[status] += 1
            withheld_count += bool(review.get("content_withheld"))
            if rid not in rows or review.get("content_withheld"):
                exclusions.append({"kind": "technical_finding", "catalog_id": rid,
                                   "original_id": review.get("review_id"), "status": status,
                                   "reason": "withheld_content" if review.get("content_withheld") else "repository_not_in_export"})
                continue
            try:
                selected = review.get("approved_evidence") or review.get("census_evidence")
                proof = evidence(selected or {}, rid, source_defaults={
                    "source_path": review.get("source_path"), "source_sha256": review.get("source_sha256"),
                    "source_url": review.get("source_url")})
                finding = {"repository_id": rid, "title": str(review.get("artifact", "Operation")),
                           "kind": "input_output_interface" if review.get("interface_admission") == "admit_verified_interface" else "source_interface_candidate",
                           "direction": review.get("direction") if review.get("direction") in {"input", "output", "internal"} else "unknown",
                           "format": review.get("artifact", ""), "description": review.get("reason", ""),
                           "status": status, "authority": "source_reviewed_finding", "runtime_tested": False,
                           "evidence_ids": [proof["source_id"]], "evidence": [proof],
                           "limitations": ["Source review only; content and runtime compatibility remain untested."],
                           "provenance": {"review_id": review.get("review_id"), "review_file_sha256": wrapper.get("sha256"),
                                          "classification": review.get("classification"), "interface_admission": review.get("interface_admission"),
                                          "analysis_method": review.get("analysis_method"), "export_sha256": export_sha}}
                rows[rid].setdefault("technical_findings", []).append(finding)
            except ValueError as exc:
                exclusions.append({"kind": "technical_finding", "catalog_id": rid, "original_id": review.get("review_id"),
                                   "status": status, "reason": str(exc)})

    interface_admitted = 0
    for record in data.get("handoff_interfaces", []):
        rid = _repo_id(record["catalog_id"])
        try:
            if rid not in rows:
                raise ValueError("interface listing is not in the frozen inventory")
            proof = evidence(record["evidence"], rid)
            finding = {"repository_id": rid, "title": "Qualified " + record["format"] + " " + record["direction"] + " candidate",
                       "kind": "source_interface_candidate", "direction": record["direction"], "format": record["format"],
                       "description": record["evidence"].get("mapping_descriptor") or "Retained interface statement in the artifact handoff index.",
                       "status": "unresolved", "authority": "source_reviewed_finding", "runtime_tested": False,
                       "evidence": [proof], "evidence_ids": [proof["source_id"]],
                       "limitations": ["Interface qualification only; record content, version compatibility and execution remain unchecked."],
                       "provenance": {"origin": "artifact_handoff_index", "export_sha256": export_sha,
                                      "original_evidence_json_sha256": record.get("original_evidence_json_sha256"),
                                      "original_profile_json_sha256": record.get("original_profile_json_sha256"),
                                      "evidence_basis": record["evidence"].get("evidence_basis")}}
            rows[rid].setdefault("technical_findings", []).append(finding)
            interface_admitted += 1
        except ValueError as exc:
            exclusions.append({"kind": "qualified_interface", "catalog_id": rid, "format": record.get("format"),
                               "direction": record.get("direction"), "reason": str(exc)})

    proposed = []
    pair_count = 0
    for wrapper in data.get("handoff_documents", []):
        document = wrapper.get("document", wrapper)
        groups = document.get("format_groups", document.get("formats", document.get("groups", [])))
        if isinstance(groups, dict):
            groups = list(groups.values())
        pairs = document.get("representative_pairs", []) + [p for g in groups for p in g.get("representative_pairs", [])]
        for pair in pairs:
            pair_count += 1
            try:
                producer, consumer = pair["producer"], pair["consumer"]
                source_id, target_id = _repo_id(producer["catalog_id"]), _repo_id(consumer["catalog_id"])
                if source_id not in rows or target_id not in rows:
                    raise ValueError("technical candidate endpoint is not in the frozen inventory")
                pp, cp = evidence(producer["interface_evidence"], source_id), evidence(consumer["interface_evidence"], target_id)
                proposed.append({"original_id": pair["id"], "source_repository_id": source_id, "target_repository_id": target_id,
                    "type": "technical_handoff_candidate", "status": "unreviewed", "authority": "source_bound_candidate",
                    "runtime_tested": False, "description": pair.get("goal") or "Candidate transfer of " + pair.get("format_label", "documented artifact"),
                    "format": pair.get("format"), "match_basis": pair.get("match_basis"),
                    "format_match_only": pair.get("format_match_only"), "content_compatibility": pair.get("content_compatibility"),
                    "evidence_ids": sorted({pp["source_id"], cp["source_id"]}),
                    "producer_contract": {"name": "Produced artifact", "format": pair.get("format", "unspecified"), "description": producer["interface_evidence"].get("mapping_descriptor") or producer.get("purpose"), "evidence": pp, "evidence_ids": [pp["source_id"]], "limitations": producer.get("limits", [])},
                    "consumer_contract": {"name": "Accepted artifact", "format": pair.get("format", "unspecified"), "description": consumer["interface_evidence"].get("mapping_descriptor") or consumer.get("purpose"), "evidence": cp, "evidence_ids": [cp["source_id"]], "limitations": consumer.get("limits", [])},
                    "required_adapters": ["Determine and implement any content/schema conversion after inspecting versioned fixtures."],
                    "validation_gaps": pair.get("required_checks") or ["Content compatibility and end-to-end behavior remain untested."],
                    "provenance": {"handoff_document_sha256": wrapper.get("sha256"), "export_sha256": export_sha,
                                   "producer_result_sha256": producer.get("accepted_result_sha256"),
                                   "consumer_result_sha256": consumer.get("accepted_result_sha256")}})
            except (KeyError, ValueError) as exc:
                exclusions.append({"kind": "technical_handoff_candidate", "original_id": pair.get("id"), "reason": str(exc)})

    gallery = data.get("gallery_records", [])
    gallery_accounting = []
    for record in gallery:
        receipt = {k: deepcopy(record[k]) for k in ("id", "card_id", "origin", "kind", "original_payload_sha256", "payload_sha256") if k in record}
        receipt.update(disposition="workflow_context_retained_separately",
                       reason="Gallery narratives have no independent capability authority; repository readings and interface reviews are imported from their source records.")
        gallery_accounting.append(receipt)
    counts = Counter(r["status"] for r in records)
    summary = {"export_sha256": export_sha, "observed_at": observed_at, "mapping_records": len(records),
               "mapping_status_counts": dict(sorted(counts.items())), "accepted_mapping_records": counts["mapped"],
               "admitted_interpretations": admitted,
               "published_additional_interpretations_seen": len(data.get("published_records", [])),
               "published_additional_interpretations_admitted": published_admitted,
               "excluded_accepted_interpretations": sum(e["kind"] == "accepted_interpretation" for e in exclusions),
               "retained_source_records": len(sources), "identity_resolution_count": len(resolutions),
               "census_review_status_counts": dict(sorted(census_counts.items())),
               "census_withheld_content_count": withheld_count,
               "admitted_technical_findings": sum(len(r.get("technical_findings", [])) for r in rows.values()),
               "qualified_interfaces_seen": len(data.get("handoff_interfaces", [])),
               "qualified_interfaces_admitted": interface_admitted,
               "handoff_examples_seen": pair_count, "admitted_handoff_candidates": len(proposed),
               "gallery_records_accounted": len(gallery_accounting),
               "cohorts": deepcopy(data.get("cohorts", [])), "stop": deepcopy(data.get("stop", {})),
               "handoff_checkpoint": deepcopy(data.get("handoff_checkpoint", {})),
               "published_catalog": {k: deepcopy(v) for k, v in published.items() if k != "records"},
               "published_record_ledger_sha256": _digest(published.get("records", [])),
               "exclusions": sorted(exclusions, key=lambda e: json.dumps(e, sort_keys=True)),
               "gallery_accounting": gallery_accounting}
    if admitted + summary["excluded_accepted_interpretations"] != counts["mapped"]:
        raise ValueError("accepted interpretation reconciliation failed")
    return {"schema": "cite_refinery.repository_snapshot.refresh.v1", "observed_at": observed_at,
            "repositories": sorted(rows.values(), key=lambda r: r["id"]),
            "sources": sorted(sources.values(), key=lambda s: s["id"]), "relationships": [],
            "proposed_relationships": proposed, "identity_resolutions": resolutions,
            "import_summary": {k: v for k, v in summary.items() if k not in {"exclusions", "gallery_accounting"}},
            "refresh": summary}
