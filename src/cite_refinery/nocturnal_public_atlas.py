"""Read-only Nocturnal public snapshot -> independent Practical Atlas projection.

The exporter, not Cite–Refinery, decides what can be made public. No
private ledger, local operator API, or investigation journal is read.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "cite_refinery.nocturnal_practical_atlas.v1"
UPSTREAM = "nocturnal.public_snapshot.v1"
FILES = ("modules.jsonl", "matters.jsonl", "entities.jsonl",
         "sources.jsonl", "corrections.jsonl", "stewardship.json")
MAX_BYTES = 64_000_000
MAX_ROWS = 100_000


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(path):
    result = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError("Nocturnal JSONL row must be an object")
                result.append(item)
                if len(result) > MAX_ROWS:
                    raise ValueError("Nocturnal snapshot exceeds row limit")
    return result


def _unique(rows, field):
    indexed = {}
    for row in rows:
        key = row.get(field)
        if not isinstance(key, str) or not key or key in indexed:
            raise ValueError("Nocturnal duplicate or missing " + field)
        indexed[key] = row
    return indexed


def _https(url):
    parsed = urlsplit(url) if isinstance(url, str) else None
    if not parsed or parsed.scheme != "https" or not parsed.hostname or parsed.username:
        raise ValueError("Nocturnal snapshot contains invalid public HTTPS source URL")
    return url



def _resolve_public_reference(reference, modules, by_event, *, matter_id):
    """Resolve an upstream pointer only against this approved public release.

    A missing or ambiguous pointer remains *unresolved*, never a verified
    correction of an inaccessible or differently scoped original.
    """
    if not isinstance(reference, str) or not reference:
        return {"reference": reference, "state": "invalid", "module_id": None,
                "matched_by": None}
    candidates = set(by_event.get(reference, ()))
    if reference in modules:
        candidates.add(reference)
    if not candidates:
        return {"reference": reference, "state": "not_in_public_snapshot",
                "module_id": None, "matched_by": None}
    if len(candidates) != 1:
        return {"reference": reference, "state": "ambiguous",
                "module_id": None, "matched_by": None}
    target_id = next(iter(candidates))
    if modules[target_id].get("matter_id") != matter_id:
        return {"reference": reference, "state": "different_matter",
                "module_id": None, "matched_by": None}
    return {
        "reference": reference,
        "state": "resolved_same_matter",
        "module_id": target_id,
        "matched_by": "module_id" if reference == target_id else "event_id",
    }


def _bounded_iso_day(day):
    if day is None:
        return None
    if not isinstance(day, str) or len(day) != 10:
        raise ValueError("Practical chronology filter requires YYYY-MM-DD")
    try:
        return date.fromisoformat(day).isoformat()
    except ValueError as exc:
        raise ValueError("Invalid Practical chronology filter") from exc

def load_public_snapshot(directory, *, expected_manifest_sha256=None):
    """Check release authority, manifest fingerprint, byte hashes and references."""
    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Nocturnal release must be a real local directory")
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file() or manifest_path.stat().st_size > 1_000_000:
        raise ValueError("Missing or oversized Nocturnal manifest")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    pilot = manifest.get("pilot_gate") or {}
    if pilot.get("fictional") is not True:
        if expected_manifest_sha256 is None:
            raise ValueError("Real Nocturnal public snapshot requires an out-of-band approved manifest SHA-256")
    if expected_manifest_sha256 is not None:
        actual = sha256(manifest_bytes).hexdigest()
        if (not isinstance(expected_manifest_sha256, str) or len(expected_manifest_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in expected_manifest_sha256)
            or expected_manifest_sha256 != actual):
            raise ValueError("Trusted Nocturnal manifest SHA-256 pin mismatch")
    integrity = manifest.get("integrity") or {}
    if (manifest.get("schema") != UPSTREAM or
        manifest.get("publishable") is not True or
        manifest.get("source_rights_reviewed") is not True or
        pilot.get("publication_allowed") is not True or
        not pilot.get("pilot_id") or
        integrity.get("ok") is not True or
        not integrity.get("chains") or
        not all(c.get("ok") is True for c in integrity["chains"]) or
        manifest.get("publication_blockers") != [] or
        str(manifest.get("dataset_license") or "").strip().lower() in
        {"", "unspecified", "unspecified-not-for-publication", "noassertion"}):
        raise ValueError("Nocturnal snapshot has not cleared its publication gate")
    descriptors = manifest.get("files")
    if not isinstance(descriptors, dict) or set(descriptors) != set(FILES):
        raise ValueError("Unexpected Nocturnal public snapshot file manifest")
    hashes = {}
    for name in FILES:
        file = root / name
        if file.is_symlink() or not file.is_file():
            raise ValueError("Missing/symlinked Nocturnal public snapshot file")
        length = file.stat().st_size
        digest = sha256(file.read_bytes()).hexdigest() if length <= MAX_BYTES else None
        declared = descriptors[name]
        if (digest is None or declared.get("bytes") != length or
            declared.get("sha256") != digest):
            raise ValueError("Nocturnal public snapshot file hash/size mismatch: " + name)
        hashes[name] = digest
    payloads = {name[:-6]: _rows(root / name) for name in FILES if name.endswith(".jsonl")}
    counts = manifest.get("counts") or {}
    if any(counts.get(name) != len(payloads[name]) for name in payloads):
        raise ValueError("Nocturnal manifest count mismatch")
    fingerprint = sha256(_canonical({
        "schema": UPSTREAM, "files": hashes, "counts": {name: counts[name] for name in payloads},
        "pilot_id": pilot["pilot_id"]
    }).encode("utf-8")).hexdigest()
    if manifest.get("snapshot_id") != "nocturnal-" + fingerprint[:20]:
        raise ValueError("Nocturnal snapshot ID does not bind its files and counts")
    return manifest, payloads, hashes


def build_practical_atlas(directory, *, previous=None, expected_manifest_sha256=None):
    manifest, rows, hashes = load_public_snapshot(
        directory, expected_manifest_sha256=expected_manifest_sha256)
    modules = _unique(rows["modules"], "module_id")
    matters = _unique(rows["matters"], "matter_id")
    entities = _unique(rows["entities"], "entity_id")
    sources = _unique(rows["sources"], "url")
    corrections = _unique(rows["corrections"], "module_id")
    if any(set((m.get("module_ids") or [])) != {
        key for key, v in modules.items() if v.get("matter_id") == mid
    } or len(m.get("module_ids") or []) != m.get("module_count")
           for mid, m in matters.items()):
        raise ValueError("Nocturnal matter membership/count mismatch")
    if set(matters) != {m["matter_id"] for m in modules.values() if m.get("matter_id")}:
        raise ValueError("Nocturnal matter index omits modules")
    if any(row.get("matter_id") not in matters for row in modules.values()
           if row.get("matter_id")):
        raise ValueError("Nocturnal invalid matter reference")
    for sid, row in sources.items():
        _https(sid)
        ids = row.get("module_ids")
        if not isinstance(ids, list) or not ids or len(set(ids)) != len(ids):
            raise ValueError("Nocturnal source has invalid module references")
        if set(ids) != {key for key, module in modules.items()
                        if sid in (module.get("source_urls") or [])}:
            raise ValueError("Nocturnal source/module provenance mismatch")
    source_urls = set(sources)
    if {url for m in modules.values() for url in (m.get("source_urls") or [])} != source_urls:
        raise ValueError("Nocturnal module sources not exhausted by source index")
    for row in modules.values():
        if not isinstance(row.get("text"), str):
            raise ValueError("Missing original public observation text")
        if not isinstance(row.get("source_urls"), list):
            raise ValueError("Missing original source URLs")
        if len(set(row["source_urls"])) != len(row["source_urls"]):
            raise ValueError("Repeated source URL is not corroboration")
        for url in row["source_urls"]:
            _https(url)
        for linked in row.get("entities") or []:
            if linked.get("entity_id") not in entities:
                raise ValueError("Entity not anchored in public entity index")
    for item in entities.values():
        ids = item.get("module_ids") or []
        if not ids or not set(ids) <= set(modules):
            raise ValueError("Public entity references missing modules")
        if any(item["entity_id"] not in {
            e.get("entity_id") for e in modules[mid].get("entities") or []
        } for mid in ids):
            raise ValueError("Public entity/module mismatch")
    if set(corrections) != {mid for mid, row in modules.items() if row.get("correction_of")}:
        raise ValueError("Nocturnal correction index is not append-only consistent")
    for mid, row in corrections.items():
        if row.get("correction_of") != modules[mid].get("correction_of"):
            raise ValueError("Nocturnal correction link mismatch")
    # Event identifiers can differ from module identifiers in native Nocturnal
    # releases. Collisions deliberately remain unresolved rather than guessing.
    event_ids = defaultdict(set)
    for module_id, module in modules.items():
        event_id = module.get("event_id")
        if isinstance(event_id, str) and event_id:
            event_ids[event_id].add(module_id)
    projected_modules = {}
    for idx, original in enumerate(rows["modules"], 1):
        mid = original["module_id"]
        projected_modules[mid] = {
            "module_id": mid, "content_hash": original.get("content_hash"),
            "text_sha256": sha256(original["text"].encode("utf-8")).hexdigest(),
            "original_snapshot_locator": "modules.jsonl#L" + str(idx),
            "matter_id": original.get("matter_id"), "event_id": original.get("event_id"),
            "observed_at": original.get("observed_at"), "title": original.get("article_title"),
            "status": original.get("status"), "status_stage": original.get("status_stage"),
            "evidence_grade_reported": original.get("evidence_grade"),
            "editorial_review_state": original.get("editorial_review_state"),
            "dispute_state": original.get("dispute_state"),
            "correction_of": original.get("correction_of"),
            "correction_target": (
                _resolve_public_reference(
                    original["correction_of"], modules, event_ids,
                    matter_id=original.get("matter_id"))
                if original.get("correction_of") else None),
            "supersedes": original.get("supersedes") or [],
            "supersession_targets": [
                _resolve_public_reference(
                    ref, modules, event_ids, matter_id=original.get("matter_id"))
                for ref in (original.get("supersedes") or [])
            ] if isinstance(original.get("supersedes") or [], list) else [
                {"reference": None, "state": "invalid", "module_id": None,
                 "matched_by": None}
            ],
            "source_urls": original["source_urls"],
            "canonical_url": original.get("canonical_url"),
            "entity_ids": [e["entity_id"] for e in original.get("entities") or []],
            "classification_reviewed_by_atlas": False,
            "fact_truth_independently_verified_by_atlas": False,
        }
    projected_matters = {}
    for mid, item in matters.items():
        event_ids = item["module_ids"]
        ordered = sorted(event_ids, key=lambda key:
                         (str(modules[key].get("observed_at") or ""), key))
        projected_matters[mid] = {
            "matter_id": mid, "module_ids": ordered,
            "timeline": [{
                "module_id": key, "observed_at": modules[key].get("observed_at"),
                "event_id": modules[key].get("event_id"),
                "stage": modules[key].get("status_stage"),
                "correction_of": modules[key].get("correction_of"),
                "correction_target": projected_modules[key]["correction_target"],
                "dispute_state": modules[key].get("dispute_state"),
            } for key in ordered],
            "source_urls": sorted({url for key in event_ids
                                   for url in modules[key].get("source_urls") or []}),
            "source_domains_not_independent_witnesses": sorted({
                urlsplit(url).hostname for key in event_ids
                for url in modules[key].get("source_urls") or []}),
            "entity_ids": sorted({e.get("entity_id") for key in event_ids
                                  for e in modules[key].get("entities") or []}),
            "current_stage_reported_by_nocturnal": item.get("current_stage"),
            "unresolved_dispute_reported": any(
                modules[key].get("dispute_state") not in ("none", None, "", "resolved")
                for key in event_ids),
            "substantive_outcome_independently_verified": False,
        }
    prior_modules = {}
    prior_snapshot = None
    if previous is not None:
        if (not isinstance(previous, dict) or previous.get("schema") != SCHEMA or
            previous.get("provenance", {}).get("exporter_schema") != UPSTREAM):
            raise ValueError("Prior atlas schema/authority mismatch")
        prior_snapshot = previous["provenance"]["snapshot_id"]
        prior_modules = previous["modules"]
        if not isinstance(prior_modules, dict):
            raise ValueError("Invalid previous Nocturnal module index")
        for mid in set(prior_modules) & set(projected_modules):
            earlier, current = prior_modules[mid], projected_modules[mid]
            if (earlier.get("content_hash") != current["content_hash"] or
                earlier.get("text_sha256") != current["text_sha256"]):
                raise ValueError("Existing published module mutated; require new correction record")
        if prior_snapshot == manifest["snapshot_id"] and set(prior_modules) != set(projected_modules):
            raise ValueError("Reused snapshot ID with changed contents")
    added = sorted(set(projected_modules) - set(prior_modules))
    no_longer_public = sorted(set(prior_modules) - set(projected_modules))
    return {
        "schema": SCHEMA,
        "provenance": {
            "exporter_schema": UPSTREAM,
            "snapshot_id": manifest["snapshot_id"],
            "generated_at": manifest.get("generated_at"),
            "nocturnal_commit_sha": manifest.get("commit_sha"),
            "dataset_license": manifest["dataset_license"],
            "pilot_id": (manifest["pilot_gate"] or {})["pilot_id"],
            "fictional": manifest["pilot_gate"].get("fictional") is True,
            "approved_public_release_only": True,
            "trusted_manifest_sha256_pinned": expected_manifest_sha256 is not None,
            "file_sha256": hashes,
        },
        "coverage": {
            "scope_domain_from_pilot": (manifest["pilot_gate"].get("scope") or {}).get("domain"),
            "matter_count": len(matters), "module_count": len(modules),
            "source_url_count": len(sources), "source_domain_count": len({
                urlsplit(url).hostname for url in sources}),
            "entity_count": len(entities), "correction_count": len(corrections),
            "correction_targets_resolved_in_public_snapshot": sum(
                p["correction_target"]["state"] == "resolved_same_matter"
                for p in projected_modules.values() if p["correction_target"]),
            "correction_targets_unresolved_in_public_snapshot": sum(
                p["correction_target"]["state"] != "resolved_same_matter"
                for p in projected_modules.values() if p["correction_target"]),
            "matters_without_original_source_links": sum(
                not case["source_urls"] for case in projected_matters.values()),
            "matters_with_open_dispute_flags": sum(
                case["unresolved_dispute_reported"] for case in projected_matters.values()),
            "untagged_cross_domain_subjects": len(matters),
            "world_or_field_completeness_measured": False,
        },
        "modules": projected_modules,
        "matters": projected_matters,
        "entities": {key: {
            "entity_id": key, "name": item.get("name"),
            "identity_state": item.get("identity_state"),
            "review_state": item.get("review_state"),
            "module_ids": item.get("module_ids"),
        } for key, item in entities.items()},
        "sources": {url: {
            "url": url, "domain": row.get("domain"), "module_ids": row["module_ids"],
            "archive_refs": row.get("archive_refs") or []
        } for url, row in sources.items()},
        "sync": {
            "previous_snapshot_id": prior_snapshot, "new_snapshot_id": manifest["snapshot_id"],
            "added_module_ids": added, "no_longer_public_module_ids": no_longer_public,
            "unchanged_module_count": len(set(projected_modules) & set(prior_modules)),
            "no_longer_public_records_retained": False,
        },
        "interpretation": {
            "source_url_count_is_not_independent_corroboration": True,
            "dispute_flag_is_not_adjudicated_source_contradiction": True,
            "resolved_public_correction_pointer_is_not_adjudicated_truth": True,
            "unresolved_correction_pointer_does_not_prove_original_deleted": True,
            "case_or_actor_listing_is_not_a_guilt_or_risk_score": True,
            "snapshot_does_not_supply_reviewed_field_taxonomy": True,
            "cross_layer_edges_created": 0,
        },
    }


def browse_practical(atlas, *, terms=None, matter_id=None, limit=25,
                     stage=None, source_domain=None, evidence_grade=None,
                     unresolved_dispute=None, after=None, before=None):
    """Literal, within-Practical exploration of published source attributes.

    Temporal filters match individual event dates, not inferred case duration.
    Nothing in these filters upgrades original claims into verified outcomes.
    """
    if atlas.get("schema") != SCHEMA or not 1 <= limit <= 100:
        raise ValueError("Invalid Practical Atlas or browse limit")
    if terms is not None and (not isinstance(terms, str) or len(terms) > 160):
        raise ValueError("Malformed search")
    if matter_id is not None and matter_id not in atlas["matters"]:
        raise ValueError("Unknown matter")
    for value in (stage, source_domain, evidence_grade):
        if value is not None and (not isinstance(value, str) or
                                  not value.strip() or len(value) > 160):
            raise ValueError("Invalid Practical source facet")
    if unresolved_dispute is not None and not isinstance(unresolved_dispute, bool):
        raise ValueError("Invalid unresolved-dispute filter")
    after, before = _bounded_iso_day(after), _bounded_iso_day(before)
    if after and before and after > before:
        raise ValueError("Practical chronology range is reversed")
    needles = (terms or "").casefold().split()
    hits = []
    for mid, matter in sorted(atlas["matters"].items()):
        if matter_id and mid != matter_id:
            continue
        evidence = [atlas["modules"][rid] for rid in matter["module_ids"]]
        if stage is not None and not any(
            (row.get("status_stage") or "").casefold() == stage.casefold()
            for row in evidence):
            continue
        if source_domain is not None and not any(
            domain.casefold() == source_domain.casefold()
            for domain in matter["source_domains_not_independent_witnesses"]):
            continue
        if evidence_grade is not None and not any(
            str(row.get("evidence_grade_reported") or "").casefold()
            == evidence_grade.casefold() for row in evidence):
            continue
        if unresolved_dispute is not None and (
            bool(matter["unresolved_dispute_reported"]) != unresolved_dispute):
            continue
        if after is not None or before is not None:
            days = [str(row.get("observed_at") or "")[:10] for row in evidence]
            if not any(len(d) == 10 and (after is None or d >= after) and
                       (before is None or d <= before) for d in days):
                continue
        indexed = [mid, str(matter.get("current_stage_reported_by_nocturnal") or "")]
        indexed += matter["source_urls"]
        indexed += [str(atlas["entities"][eid].get("name") or "")
                    for eid in matter["entity_ids"]]
        indexed += [str(row.get("title") or "") for row in evidence]
        indexed += [str(row.get("status_stage") or "") for row in evidence]
        haystack = " ".join(indexed).casefold()
        if all(needle in haystack for needle in needles):
            hits.append(matter)
    return {
        "schema": "cite_refinery.nocturnal_practical_browse.v1",
        "snapshot_id": atlas["provenance"]["snapshot_id"],
        "matching_count": len(hits), "results": hits[:limit],
        "filters": {
            "stage": stage, "source_domain": source_domain,
            "evidence_grade": evidence_grade,
            "unresolved_dispute": unresolved_dispute,
            "after": after, "before": before,
        },
        "lexical_only": True, "searches_original_body_text": False,
        "source_url_count_is_not_independent_corroboration": True,
        "cross_layer_join_performed": False,
    }
