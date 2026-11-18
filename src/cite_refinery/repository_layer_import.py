"""Lossless repository-side adapters for existing Atlas evidence snapshots.

These adapters retain prior role/interface assignments as observations, never
as reviewed capabilities. They do not fetch or execute upstream software.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse, unquote

from .repository_layer import _repo_id


def _sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()


def _read(path: str | Path) -> tuple[dict, str]:
    raw = Path(path).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def _pin(url: str) -> dict:
    """Record a Git object identity without pretending a blob is a commit."""
    result = {}
    parts = urlparse(url).path.strip("/").split("/")
    if "blobs" in parts and re.fullmatch(r"[a-fA-F0-9]{40}", parts[-1]):
        result["blob_sha"] = parts[-1].lower()
    elif len(parts) >= 5 and parts[2] == "blob":
        if re.fullmatch(r"[a-fA-F0-9]{40}", parts[3]):
            result["revision"] = parts[3].lower()
        else:
            result["unresolved_ref"] = parts[3]
        result["path"] = unquote("/".join(parts[4:]))
    return result


def current_catalog_snapshot(path: str | Path) -> dict:
    """Read a frozen, audited export of the user's current discovery catalogue.

    Source-bound technical interpretations are retained separately from both
    reviewed capability contracts and legacy role guesses. Evidence checks are
    imported receipts from the frozen export, not a new local execution or a
    semantic verification of the interpretation.
    """
    data, export_sha = _read(path)
    if data.get("schema") != "cite_refinery.current_repository_catalog_export.v1":
        raise ValueError("unknown current catalogue export schema")
    database_sha = data.get("source_catalog_sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", str(database_sha or "")):
        raise ValueError("current catalogue export requires the frozen database hash")
    metadata = data.get("metadata", {})
    if metadata.get("schema") != "cite_refinery.software_discovery_catalog.v1":
        raise ValueError("current catalogue export does not identify the source schema")
    projects = data.get("projects")
    if not isinstance(projects, list):
        raise ValueError("current catalogue export requires a complete projects list")
    checks = {}
    for check in data.get("integrity", {}).get("source_checks", []):
        key = (check.get("path"), check.get("expected_sha256"))
        if key in checks and checks[key] != check:
            raise ValueError("conflicting retained-source integrity checks")
        if check.get("state") == "match" and check.get("actual_sha256") != check.get("expected_sha256"):
            raise ValueError("retained-source check reports a mismatched hash as a match")
        checks[key] = check
    rows, sources, excluded, seen = [], {}, [], set()
    rejected_interpretations = 0

    def retain_source(raw: dict, rid: str) -> tuple[str, bool]:
        url, content_sha, capture_path = raw.get("source_url"), raw.get("sha256"), raw.get("path")
        parsed = urlparse(str(url or ""))
        if parsed.scheme != "https" or parsed.username or parsed.password or not parsed.hostname:
            raise ValueError("retained original source requires its HTTPS locator")
        if not re.fullmatch(r"[0-9a-f]{64}", str(content_sha or "")) or not isinstance(capture_path, str) or not capture_path:
            raise ValueError("retained original source requires its path and content hash")
        parts = parsed.path.strip("/").split("/")
        source_repo = None
        if parsed.hostname in {"github.com", "www.github.com", "raw.githubusercontent.com"} and len(parts) >= 2:
            source_repo = _repo_id("/".join(parts[:2]))
        elif parsed.hostname == "api.github.com" and len(parts) >= 3 and parts[0] == "repos":
            source_repo = _repo_id("/".join(parts[1:3]))
        if source_repo is not None and source_repo != rid:
            raise ValueError("retained original source belongs to a different repository")
        check = checks.get((capture_path, content_sha), {})
        checked = (check.get("state") == "match" and check.get("actual_sha256") == content_sha
                   and raw.get("capture_integrity", "match") == "match")
        kind = "code" if raw.get("kind") in {"code", "source"} else "documentation"
        pin = _pin(url) if parsed.hostname in {"github.com", "www.github.com", "api.github.com"} else {}
        if parsed.hostname == "raw.githubusercontent.com" and len(parts) >= 4:
            pin["revision" if re.fullmatch(r"[0-9a-fA-F]{40}", parts[2]) else "unresolved_ref"] = parts[2]
            pin["path"] = unquote("/".join(parts[3:]))
        source = {"repository_id": rid, "url": url, "kind": kind, "content_sha256": content_sha,
                  "original_capture_path": capture_path, "capture_integrity": "match" if checked else "unavailable_or_mismatch",
                  "byte_integrity_checked": checked, "semantic_support_verified": False, "runtime_tested": False,
                  "verification_origin": "frozen_current_catalog_export",
                  "authority": "captured_original_source; semantic_support_and_runtime_unverified", **pin}
        # A changed capture, locator or audit result is another receipt, never an
        # overwrite of an earlier snapshot's source history.
        sid = "catalog_source:" + _sha(source)[:24]
        source["id"] = sid
        sources[sid] = source
        return sid, checked

    for project in projects:
        if not isinstance(project, dict):
            raise ValueError("current catalogue project rows must be objects")
        raw_id = project.get("catalog_id", "")
        if not isinstance(raw_id, str) or not raw_id.startswith("github:"):
            excluded.append({"id": raw_id, "reason": "not_an_explicit_repository_identity"})
            continue
        rid = _repo_id(raw_id)
        if rid in seen:
            raise ValueError("duplicate repository identity in frozen current catalogue")
        seen.add(rid)
        if _repo_id(str(project.get("url", ""))) != rid:
            raise ValueError("current catalogue repository URL differs from its identity")
        display = project.get("slug") or rid[7:]
        if _repo_id(display) != rid:
            raise ValueError("current catalogue slug differs from its repository identity")
        raw_payload_sha = project.get("raw_payload_sha256")
        if not re.fullmatch(r"[0-9a-f]{64}", str(raw_payload_sha or "")):
            raise ValueError("current catalogue project requires its original payload hash")
        source_ids = []
        for original in project.get("original_sources", []):
            sid, _ = retain_source(original, rid)
            source_ids.append(sid)
        interpretations, rejections = [], []
        for raw in project.get("source_interpretations", []):
            if not isinstance(raw, dict):
                raise ValueError("current catalogue interpretation must be an object")
            proofs, reasons = [], []
            raw_evidence = raw.get("evidence", []) + raw.get("additional_evidence", [])
            if not raw_evidence:
                reasons.append("no_literal_source_evidence")
            for original in raw_evidence:
                sid, checked = retain_source(original, rid)
                source_ids.append(sid)
                excerpt = original.get("quote", original.get("excerpt"))
                quote_checked = original.get("quote_integrity") == "exact_quote_present"
                if not checked or not quote_checked or not isinstance(excerpt, str) or len(excerpt) < 12:
                    reasons.append("source_hash_or_literal_excerpt_not_verified")
                    continue
                proof = {"source_id": sid, "source_sha256": original["sha256"], "excerpt": excerpt,
                         "byte_integrity_checked": True, "quote_integrity": "exact_quote_present",
                         "semantic_support_verified": False, "runtime_tested": False}
                start, end = original.get("start"), original.get("end")
                if start is not None or end is not None:
                    if type(start) is not int or type(end) is not int or start < 0 or end - start != len(excerpt):
                        reasons.append("retained_excerpt_offsets_inconsistent")
                        continue
                    proof.update(excerpt_start=start, excerpt_end=end, offset_verification="retained_catalog_check")
                proofs.append(proof)
            if reasons:
                rejected_interpretations += 1
                rejections.append({"raw_record_sha256": _sha(raw), "reasons": sorted(set(reasons)),
                                   "authority": "unreviewed; retained_in_frozen_export"})
                continue
            method = str(raw.get("analysis_method") or "")
            model = method == "llm_source_review" or raw.get("explanation_state") == "source_bound_model_interpretation"
            interpretation = {
                "purpose": raw.get("purpose", ""),
                **{key: deepcopy(raw.get(key, [])) for key in ("inputs", "outputs", "human_work", "custom_glue")},
                "limitations": deepcopy(raw.get("limits", [])),
                "evidence": proofs, "evidence_ids": sorted({proof["source_id"] for proof in proofs}),
                "authority": "source_bound_model_interpretation" if model else "source_bound_interpretation",
                "analysis_method": method, "worker": raw.get("worker") or project.get("mapping_worker") or "",
                "status": raw.get("status") or "source_bound", "semantic_support_verified": False, "runtime_tested": False,
                "provenance": {"catalog_id": rid, "raw_record_sha256": _sha(raw),
                               "raw_payload_sha256": raw_payload_sha, "source_catalog_sha256": database_sha,
                               "export_sha256": export_sha, "mapping_cohort_sha256": project.get("mapping_cohort_sha256"),
                               "original_explanation_state": raw.get("explanation_state"),
                               "excluded_workflow_fields": [k for k in ("contribution", "workflow_families", "workflow_roles") if k in raw]},
            }
            interpretations.append(interpretation)
        context = {key: deepcopy(project[key]) for key in (
            "keywords", "review_state", "provider", "announcement_url", "signals_page_url",
            "publication_observations", "mapping_state", "mapping_reason", "mapping_worker", "mapping_cohort_sha256", "gaps"
        ) if key in project}
        context.update(source_ids=sorted(set(source_ids)), raw_payload_sha256=raw_payload_sha,
                       source_catalog_sha256=database_sha, export_sha256=export_sha,
                       source_interpretation_exclusions=rejections,
                       authority="discovery_metadata_and_separately_labelled_source_interpretations")
        rows.append({"id": rid, "full_name": display, "url": project["url"],
                     "description": project.get("description", ""), "topics": deepcopy(project.get("topics", [])),
                     "source_interpretations": interpretations, "technical_context": context})
    coverage = metadata.get("coverage", {})
    if coverage.get("total_projects") is not None and coverage["total_projects"] != len(projects):
        raise ValueError("frozen current catalogue export omits project records")
    summary = {"project_records": len(projects), "repository_records": len(rows),
               "unique_repository_identities": len(seen), "nonrepository_records": len(excluded),
               "source_records": len(sources),
               "source_interpreted_repository_count": sum(bool(r["source_interpretations"]) for r in rows),
               "source_interpretation_count": sum(len(r["source_interpretations"]) for r in rows),
               "unbound_interpretation_count": rejected_interpretations,
               "export_sha256": export_sha, "source_catalog_sha256": database_sha,
               "source_dataset": deepcopy(metadata.get("source_dataset", {})),
               "input_receipts": deepcopy(metadata.get("input_receipts", {})),
               "original_catalog_review_states": deepcopy(coverage.get("review_states", {})),
               "source_check_counts": deepcopy(data.get("integrity", {}).get("source_check_counts", {})),
               "quote_check_counts": deepcopy(data.get("integrity", {}).get("quote_check_counts", {}))}
    return {"schema": "cite_refinery.repository_snapshot.current_catalog.v1",
            "observed_at": metadata.get("built_at"), "repositories": rows,
            "sources": sorted(sources.values(), key=lambda s: s["id"]), "relationships": [],
            "proposed_relationships": [], "import_summary": summary, "nonrepository_exclusions": excluded}


def connected_snapshot(profiles_path: str | Path, audit_path: str | Path | None = None,
                       *, observed_at: str | None = None) -> dict:
    """Import every explicit repository identity from the connected catalogue.

    Papers, news, registries and model assets are counted separately. A source
    link in their prose is not enough to invent another repository identity.
    """
    data, profile_sha = _read(profiles_path)
    profiles = data.get("profiles")
    if not isinstance(profiles, list):
        raise ValueError("connected snapshot requires a profiles list")
    audit, audit_sha = _read(audit_path) if audit_path else ({}, None)
    if audit and audit.get("profile_sha256") != profile_sha:
        raise ValueError("source-integrity audit belongs to a different profile snapshot")
    checks = {(c.get("path"), c.get("expected_sha256")): c
              for c in audit.get("source_integrity", {}).get("checks", [])}
    bad_quotes = {(r["profile_id"], r["role_index"]): r["state"]
                  for r in audit.get("unmatched_role_quotes", [])}
    rows, sources, excluded = [], {}, []
    source_lookup = {}
    for profile in profiles:
        raw_id = str(profile.get("id", ""))
        primary = str(profile.get("url", ""))
        if raw_id.startswith("github:"):
            rid = _repo_id(raw_id)
        elif urlparse(primary).hostname in {"github.com", "www.github.com"}:
            rid = _repo_id(primary)
        else:
            excluded.append({"id": raw_id, "kind": profile.get("kind"),
                             "reason": "not_an_explicit_repository_identity"})
            continue
        title = str(profile.get("title", ""))
        try:
            display = title if _repo_id(title) == rid else rid[7:]
        except ValueError:
            display = rid[7:]
        source_ids = []
        for receipt in profile.get("source_receipts", []):
            url = str(receipt.get("source_url", ""))
            if urlparse(url).scheme not in {"http", "https"}:
                continue
            sid = "captured:" + _sha([rid, url, receipt.get("sha256")])[:24]
            check = checks.get((receipt.get("path"), receipt.get("sha256")))
            sources[sid] = {
                "id": sid, "repository_id": rid, "url": url,
                "kind": "documentation" if receipt.get("kind") in {"readme", "documentation", "docs"} else "code",
                "content_sha256": receipt.get("sha256"),
                "original_capture_path": receipt.get("path"),
                "capture_integrity": check.get("state") if check else "not_rechecked",
                "authority": "captured_source_bytes_only; capability_semantics_unreviewed",
                "snapshot_sha256": profile_sha, **_pin(url),
            }
            source_lookup[(rid, url, receipt.get("sha256"))] = sid
            source_ids.append(sid)
        proposals = []
        for index, role in enumerate(profile.get("roles", [])):
            ev = role.get("evidence", {})
            sid = source_lookup.get((rid, ev.get("source_url"), ev.get("sha256")))
            proposals.append({
                "key": role.get("role") or "role_" + _sha(role)[:12],
                "name": role.get("title") or role.get("role") or "Unreviewed role",
                "status": "unreviewed", "evidence_ids": [sid] if sid else [],
                "mechanism": "Historical role assignment; source meaning and callable interface require review.",
                "proposed_inputs": deepcopy(role.get("inputs", [])),
                "proposed_outputs": deepcopy(role.get("outputs", [])),
                "source_evidence": deepcopy(ev),
                "exact_quote_state": bad_quotes.get((raw_id, index), "exact_quote_present" if audit else "not_rechecked"),
                "mapping_method": profile.get("mapping_method"),
                "interpretation": role.get("interpretation"),
                "contract_authority": role.get("contract_authority"),
            })
        rows.append({
            "id": rid, "full_name": display, "url": "https://github.com/" + display,
            "description": profile.get("description", ""), "domains": profile.get("domains", []),
            "topics": profile.get("prior_categories", []), "proposed_capabilities": proposals,
            "technical_context": {
                **{key: deepcopy(profile[key]) for key in (
                    "source_state", "acquisition_state", "source_errors", "known_functions",
                    "documented_interface_hints", "mapping_method", "gaps", "native_interface_schema_status"
                ) if key in profile},
                "source_ids": source_ids, "raw_profile_id": raw_id,
                "raw_record_sha256": _sha(profile), "snapshot_sha256": profile_sha,
                "authority": "retained_source_context; not_adjudicated_capabilities",
            },
        })
    ids = {r["id"] for r in rows}
    proposed = []
    omitted_edges = Counter()
    types = {"PROPOSED_ARTIFACT_HANDOFF": "legacy_handoff", "COMPARE_FOR_SAME_FUNCTION": "legacy_comparison",
             "SOURCE_DECLARES_DEPENDENCY": "legacy_dependency"}
    for edge in audit.get("legacy_relationships", []):
        source, target = str(edge.get("source", "")).lower(), str(edge.get("target", "")).lower()
        if source not in ids or target not in ids:
            omitted_edges[edge.get("relation", "unknown")] += 1
            continue
        item = deepcopy(edge)
        item.update(source_repository_id=source, target_repository_id=target,
                    type=types.get(edge.get("relation"), "legacy_association"),
                    original_relation=edge.get("relation"), original_id="legacy:" + _sha(edge),
                    status="unreviewed", snapshot_sha256=audit.get("relationship_sha256"),
                    description="Preserved rule-derived relationship; capability meaning, direction and interoperability have not been established.")
        proposed.append(item)
    summary = {
        "profile_records": len(profiles), "repository_records": len(rows),
        "unique_repository_identities": len(ids), "nonrepository_records": len(excluded),
        "source_records": len(sources), "legacy_role_records": sum(len(r["proposed_capabilities"]) for r in rows),
        "repository_relationship_proposals": len(proposed),
        "excluded_nonrepository_relationships": dict(sorted(omitted_edges.items())),
        "profile_sha256": profile_sha, "audit_sha256": audit_sha,
        "source_integrity": {k: v for k, v in audit.get("source_integrity", {}).items() if k != "checks"},
        "quote_integrity": audit.get("quote_integrity", {}),
        "unmatched_repository_quotes": sum(r["profile_id"] in ids for r in audit.get("unmatched_role_quotes", [])),
    }
    return {"schema": "cite_refinery.repository_snapshot.connected.v1", "observed_at": observed_at or data.get("observed_at"),
            "repositories": rows, "sources": sorted(sources.values(), key=lambda s: s["id"]),
            "relationships": [], "proposed_relationships": proposed,
            "import_summary": summary, "nonrepository_exclusions": excluded}


def source_lock_snapshot(path: str | Path) -> dict:
    data, sha = _read(path)
    rows, sources = [], []
    for item in data.get("sources", []):
        rid = _repo_id(item["repository"])
        rows.append({"id": rid, "full_name": item["repository"],
                     "description": "", "technical_context": {"source_lock_sha256": sha,
                     "original_source_key": item.get("id"), "source_file": item.get("file_path"),
                     "authority": "version_observation_only; no_workflow_role_promotion"}})
        blob = item.get("last_observed_blob_sha") or item.get("captured_blob_sha")
        if blob:
            sources.append({"id": "source_lock:" + _sha([rid, item.get("file_path"), blob])[:24],
                            "repository_id": rid, "url": "https://api.github.com/repos/" + rid[7:] + "/git/blobs/" + blob,
                            "kind": "metadata", "blob_sha": blob, "path": item.get("file_path"),
                            "authority": "source_version_observation; source_bytes_not_in_lockfile"})
    return {"schema": "cite_refinery.repository_snapshot.source_lock.v1", "repositories": rows,
            "sources": sources, "relationships": [], "import_summary": {"file_sha256": sha,
            "source_records": len(rows), "unique_repository_identities": len({r["id"] for r in rows})}}


def legacy_snapshot(root: str | Path, portfolio_path: str | Path | None = None) -> dict:
    """Retain prior repository evidence identities without copying problem briefs."""
    root = Path(root)
    rows = []
    checks_path = root / "repository_documentation_checks.json"
    if checks_path.exists():
        checks, sha = _read(checks_path)
        for review in checks.get("reviews", []):
            rows.append({"id": _repo_id(review["repo_id"]), "description": review.get("description", ""),
                         "technical_context": {"source_file": checks_path.name, "file_sha256": sha,
                         "prior_documentation_review": deepcopy(review)}})
    mechanism_path = root / "primary_mechanism_network.json"
    if mechanism_path.exists():
        data, sha = _read(mechanism_path)
        for brief in data.get("briefs", []):
            lead = brief.get("implementation_lead")
            if not lead or not str(lead.get("id", "")).startswith("github:"):
                continue
            safe = {k: deepcopy(lead[k]) for k in ("id", "url", "readme_url", "git_blob_sha", "readme_anchor", "status") if k in lead}
            rows.append({"id": _repo_id(lead["id"]), "technical_context": {
                "source_file": mechanism_path.name, "file_sha256": sha, "implementation_evidence": safe}})
    probes_path = root / "functional_component_trials.json"
    if probes_path.exists():
        probes, sha = _read(probes_path)
        for probe in probes.get("probes", []):
            rows.append({"id": _repo_id(probe["asset_id"]), "technical_context": {
                "source_file": probes_path.name, "file_sha256": sha,
                "source": probe.get("source"), "source_entry_point": probe.get("source_entry_point"),
                "execution": probe.get("execution"), "cases": deepcopy(probe.get("cases", [])),
                "authority": "historical_scoped_probe; preserve_failures_and_untested_cases"}})
    for path in sorted(root.glob("semantic_review_batch_*.json")):
        data, sha = _read(path)
        reviews = data.get("reviews", data.get("assessments", data.get("judgments", [])))
        for review in reviews:
            value = review.get("repo_id") or review.get("repository_id")
            if value:
                rows.append({"id": _repo_id(value), "technical_context": {
                    "source_file": path.name, "file_sha256": sha, "domain_scoped_review": deepcopy(review),
                    "authority": "domain_annotation_only; not_an_inventory_exclusion"}})
    if portfolio_path:
        portfolio, sha = _read(portfolio_path)
        for row in portfolio.get("repositories", []):
            full_name = row.get("repository") or row.get("full_name") or row.get("repo") or row.get("url")
            if isinstance(full_name, dict):
                full_name = full_name.get("full_name") or full_name.get("url")
            if full_name:
                rows.append({"id": _repo_id(full_name), "technical_context": {
                    "source_file": Path(portfolio_path).name, "file_sha256": sha,
                    "portfolio_entry": deepcopy(row), "authority": "retained_repository_history; no_capability_promotion"}})
    return {"schema": "cite_refinery.repository_snapshot.legacy.v1", "repositories": rows,
            "sources": [], "relationships": [], "import_summary": {"repository_observations": len(rows),
            "unique_repository_identities": len({r["id"] for r in rows})}}
