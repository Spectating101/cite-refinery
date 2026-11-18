"""Repository inventory and reviewed technical contracts, independent of demand.

Discovery metadata and captured README text do not establish capabilities. Only
the separately supplied curated evidence file creates reviewed capability
records. Source-bound technical interpretations retain their own authority,
apart from historical role assignments and reviewed capability contracts.
This module records source authority; it does not execute third-party software
or authenticate the people who supplied an evidence review.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable
from urllib.parse import urlparse


SCHEMA = "cite_refinery.repository_layer.v1"
EVIDENCE_SCHEMA = "cite_refinery.repository_layer_evidence.v1"
LEVELS = {"documented", "code_inspected", "executed"}
RELATION_KINDS = {"declared_dependency", "proposed_handoff", "tested_handoff"}
SOURCE_KINDS = {"metadata", "documentation", "code", "execution"}
FORBIDDEN_FIELDS = {
    "buyer_demand", "market_demand", "commercial_status", "commercial_fit",
    "commercial_underconversion", "demand_nodes", "problem_nodes", "problem_links",
    "market_nodes", "buyer_nodes", "buyers", "needs", "problems", "opportunities",
    "opportunity_scores", "conversion_modes", "published_procurement_context",
}
SLUG = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
KEY = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _strings(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set)):
        raise ValueError("expected a list of strings")
    return sorted({_text(v) for v in values if _text(v)})


def _stable(prefix: str, *parts: Any) -> str:
    return prefix + ":" + _digest(parts)[:24]


def _repo_id(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("repository identity must be text")
    slug = value.strip()
    if slug.startswith("github:"):
        slug = slug[7:]
    elif slug.startswith(("https://", "http://")):
        parsed = urlparse(slug)
        if parsed.hostname not in {"github.com", "www.github.com"}:
            raise ValueError("repository identity must name a GitHub repository")
        slug = "/".join(parsed.path.strip("/").split("/")[:2])
    slug = slug.rstrip("/")
    if slug.endswith(".git"):
        slug = slug[:-4]
    if not SLUG.fullmatch(slug) or any(p in {".", ".."} for p in slug.split("/")):
        raise ValueError("invalid GitHub owner/repository identity")
    return "github:" + slug.casefold()


def _identity(row: dict[str, Any]) -> str | None:
    for key in ("repository_id", "full_name", "repository"):
        if row.get(key):
            return _repo_id(row[key])
    if isinstance(row.get("id"), str) and row["id"].startswith("github:"):
        return _repo_id(row["id"])
    if isinstance(row.get("url"), str) and urlparse(row["url"]).hostname in {"github.com", "www.github.com"}:
        return _repo_id(row["url"])
    return None


def _clean(value: Any) -> Any:
    """Preserve supplied provenance while excluding unrelated layer fields."""
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items() if k not in FORBIDDEN_FIELDS}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return deepcopy(value)


def _reject_demand(value: Any) -> None:
    if isinstance(value, dict):
        if FORBIDDEN_FIELDS.intersection(value):
            raise ValueError("demand-layer fields are not allowed in a repository catalog")
        for item in value.values():
            _reject_demand(item)
    elif isinstance(value, list):
        for item in value:
            _reject_demand(item)


def _read(path: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(path)
    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("repository input must be a JSON object")
    sha = hashlib.sha256(raw).hexdigest()
    return data, {
        "id": "input:" + sha,
        "file_name": path.name,
        "sha256": sha,
        "schema": data.get("schema", "normalized_supplemental_snapshot"),
        "observed_at": data.get("observed_at", data.get("captured_at")),
    }


def _paths(values: Iterable[str | Path] | str | Path) -> list[str | Path]:
    return [values] if isinstance(values, (str, Path)) else list(values)


def _new_repo(rid: str) -> dict[str, Any]:
    return {
        "id": rid, "full_name": rid[7:], "url": "https://github.com/" + rid[7:],
        "aliases": [], "description": "", "languages": [], "topics": [], "domains": [],
        "domain_judgments": [],
        "observations": [], "review_state": "unreviewed", "capabilities": [],
        "source_interpretations": [],
        "proposed_capabilities": [], "rejected_assignments": [], "unknowns": [],
    }


def _source(raw: dict[str, Any]) -> dict[str, Any]:
    source = _clean(raw)
    if not isinstance(source.get("id"), str) or not source["id"].strip():
        raise ValueError("source requires a stable id")
    rid = _identity(source)
    if rid is None:
        raise ValueError("source requires a repository identity")
    source["repository_id"] = rid
    aliases = {"readme": "documentation", "docs": "documentation", "source": "code", "execution_receipt": "execution"}
    source["kind"] = aliases.get(source.get("kind"), source.get("kind", "metadata"))
    if source["kind"] not in SOURCE_KINDS:
        raise ValueError("unknown source kind")
    if urlparse(str(source.get("url", ""))).scheme not in {"http", "https"}:
        raise ValueError("source requires an HTTP(S) locator")
    return source


def _proposal(raw: Any, rid: str, input_id: str) -> dict[str, Any]:
    original = {"name": raw} if isinstance(raw, str) else _clean(raw)
    if not isinstance(original, dict):
        raise ValueError("legacy capability proposal must be text or an object")
    name = _text(original.get("name") or original.get("label") or original.get("role") or original.get("title") or original.get("capability"))
    key = _text(original.get("key") or original.get("role_id") or original.get("id"))
    if not name:
        name = key
    if not name:
        raise ValueError("legacy proposal has no name or role identity")
    key = key or _stable("legacy", name.casefold())
    status = "rejected" if original.get("status") == "rejected" else "unreviewed"
    return {
        "id": _stable("proposal", rid, key), "key": key, "name": name,
        "mechanism": _text(original.get("mechanism") or original.get("rationale") or original.get("description")),
        "status": status, "evidence_ids": _strings(original.get("evidence_ids", [])),
        "provenance": {"input_source_id": input_id, "legacy_record": original},
    }


def _source_interpretation(raw: dict, rid: str) -> dict:
    """Retain source-bound technical reading without a semantic/runtime pass."""
    if not isinstance(raw, dict):
        raise ValueError("source interpretation must be an object")
    authority = raw.get("authority")
    if authority not in {"source_bound_model_interpretation", "source_bound_interpretation"}:
        raise ValueError("source interpretation must retain its limited authority")
    if raw.get("semantic_support_verified") is not False or raw.get("runtime_tested") is not False:
        raise ValueError("source interpretation cannot assert semantic or runtime verification")
    item = {"repository_id": rid, "purpose": _text(raw.get("purpose")), "authority": authority,
            "analysis_method": _text(raw.get("analysis_method")), "worker": _text(raw.get("worker")),
            "status": _text(raw.get("status")), "semantic_support_verified": False, "runtime_tested": False}
    for field in ("inputs", "outputs", "human_work", "custom_glue", "limitations"):
        rows = raw.get(field, [])
        if not isinstance(rows, list) or any(not isinstance(v, str) for v in rows):
            raise ValueError("source interpretation technical fields must be string lists")
        item[field] = list(dict.fromkeys(_text(v) for v in rows if _text(v)))
    evidence = raw.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("source interpretation requires literal source evidence")
    item["evidence"] = []
    for raw_proof in evidence:
        if not isinstance(raw_proof, dict):
            raise ValueError("source interpretation evidence must be an object")
        proof = {k: deepcopy(raw_proof[k]) for k in (
            "source_id", "source_sha256", "excerpt", "excerpt_start", "excerpt_end", "offset_verification",
            "byte_integrity_checked", "quote_integrity", "semantic_support_verified", "runtime_tested"
        ) if k in raw_proof}
        if (not isinstance(proof.get("excerpt"), str) or len(proof["excerpt"]) < 12
                or proof.get("byte_integrity_checked") is not True
                or proof.get("quote_integrity") != "exact_quote_present"
                or proof.get("semantic_support_verified") is not False
                or proof.get("runtime_tested") is not False):
            raise ValueError("source interpretation requires hash-bound literal evidence without semantic promotion")
        start, end = proof.get("excerpt_start"), proof.get("excerpt_end")
        if start is not None or end is not None:
            if (type(start) is not int or type(end) is not int or start < 0
                    or end - start != len(proof["excerpt"])
                    or proof.get("offset_verification") != "retained_catalog_check"):
                raise ValueError("retained excerpt offsets are inconsistent")
        if proof not in item["evidence"]:
            item["evidence"].append(proof)
    item["evidence"].sort(key=_json)
    item["evidence_ids"] = sorted({proof.get("source_id", "") for proof in item["evidence"]})
    if "evidence_ids" in raw and _strings(raw["evidence_ids"]) != item["evidence_ids"]:
        raise ValueError("source interpretation evidence references do not reconcile")
    item["id"] = _stable("source_interpretation", rid, item)
    provenance = raw.get("provenance", {})
    if not isinstance(provenance, dict):
        raise ValueError("source interpretation provenance must be an object")
    item["provenance"] = _clean(provenance)
    return item


def _check_source_interpretation(item: dict, rid: str, sources: dict[str, dict]) -> None:
    _refs(item["evidence_ids"], sources)
    for proof in item["evidence"]:
        source = sources[proof["source_id"]]
        if (source["repository_id"] != rid or source["kind"] not in {"documentation", "code"}
                or source.get("capture_integrity") != "match"
                or proof.get("source_sha256") != source.get("content_sha256")
                or not re.fullmatch(r"[0-9a-f]{64}", str(proof.get("source_sha256", "")))):
            raise ValueError("source interpretation must bind its own repository and checked source bytes")


def _merge_row(registry: dict[str, dict], row: dict[str, Any], receipt: dict) -> bool:
    rid = _identity(row)
    if rid is None:
        return False
    repo = registry.setdefault(rid, _new_repo(rid))
    domains = _strings(row.get("domains", row.get("found_in", row.get("domain_ids", []))))
    topics = _strings(row.get("topics", []))
    languages = _strings(row.get("languages", row.get("language", [])))
    display = _text(row.get("full_name") or row.get("repository") or rid[7:])
    if display.startswith("github:"):
        display = display[7:]
    if not SLUG.fullmatch(display):
        display = rid[7:]
    observation = {
        "source_id": receipt["id"], "observed_at": row.get("observed_at", receipt.get("observed_at")),
        "full_name": display, "description": _text(row.get("description")),
        "language": _text(row.get("language")), "languages": languages,
        "topics": topics, "domains": domains,
        "license_api_label": row.get("license_api_label", "unknown"),
        "evidence_level": "metadata_only", "record_sha256": _digest(row),
    }
    if "technical_context" in row:
        if not isinstance(row["technical_context"], dict):
            raise ValueError("technical context must be an object")
        observation["technical_context"] = _clean(row["technical_context"])
    for key in ("stars", "forks", "archived", "last_push", "created_at", "sample_segments"):
        if key in row:
            observation[key] = deepcopy(row[key])
    if observation not in repo["observations"]:
        repo["observations"].append(observation)
    for judgment in row.get("domain_judgments", []):
        if not isinstance(judgment, dict) or not judgment.get("domain_id"):
            raise ValueError("domain judgment requires an explicit domain identity")
        recorded = {**_clean(judgment), "source_id": receipt["id"], "authority": "metadata_only"}
        if recorded not in repo["domain_judgments"]:
            repo["domain_judgments"].append(recorded)
    for key, values in (("aliases", [display]), ("domains", domains), ("topics", topics), ("languages", languages)):
        repo[key] = sorted(set(repo[key]) | set(values))
    for raw in row.get("source_interpretations", []):
        item = _source_interpretation(raw, rid)
        provenance = {**item.pop("provenance"), "input_source_id": receipt["id"]}
        existing = next((i for i in repo["source_interpretations"] if i["id"] == item["id"]), None)
        if existing is None:
            item["provenance"] = {"observations": [provenance]}
            repo["source_interpretations"].append(item)
        elif provenance not in existing["provenance"]["observations"]:
            existing["provenance"]["observations"].append(provenance)
    proposals = row.get("proposed_capabilities", row.get("roles", row.get("capabilities", [])))
    if isinstance(proposals, dict):
        proposals = [{"key": key, **(value if isinstance(value, dict) else {"name": value})} for key, value in proposals.items()]
    if not isinstance(proposals, list):
        raise ValueError("legacy proposals must be a list or mapping")
    for raw in proposals:
        item = _proposal(raw, rid, receipt["id"])
        existing = next((p for p in repo["proposed_capabilities"] if p["id"] == item["id"]), None)
        if existing is None:
            item["observations"] = [item.pop("provenance")]
            repo["proposed_capabilities"].append(item)
        else:
            evidence = item["provenance"]
            if evidence not in existing["observations"]:
                existing["observations"].append(evidence)
            existing["evidence_ids"] = sorted(set(existing["evidence_ids"]) | set(item["evidence_ids"]))
            if item["status"] == "rejected":
                existing["status"] = "rejected"
    return True


def _refs(values: Any, sources: dict[str, dict], *, required: bool = True) -> list[str]:
    refs = _strings(values)
    if (required and not refs) or any(ref not in sources for ref in refs):
        raise ValueError("claim references missing or unknown source evidence")
    return refs


def _capability(raw: dict, rid: str, sources: dict[str, dict]) -> dict:
    cap = _clean(raw)
    key = cap.get("key")
    if not isinstance(key, str) or not KEY.fullmatch(key):
        raise ValueError("capability requires a stable lowercase key")
    cap["id"] = _stable("capability", rid, key)
    cap["name"] = _text(cap.get("name"))
    cap["mechanism"] = _text(cap.get("mechanism"))
    if not cap["name"] or not cap["mechanism"]:
        raise ValueError("reviewed capability requires its name and actual mechanism")
    cap["evidence_level"] = {"source_documented": "documented"}.get(cap.get("evidence_level"), cap.get("evidence_level"))
    if cap["evidence_level"] not in LEVELS:
        raise ValueError("unknown capability evidence level")
    cap["evidence_ids"] = _refs(cap.get("evidence_ids", []), sources)
    cap["review_origin"] = "curated_evidence"
    for field in ("inputs", "outputs", "requirements", "limitations"):
        rows = cap.setdefault(field, [])
        if not isinstance(rows, list):
            raise ValueError("technical contract fields must be lists")
        for item in rows:
            if not isinstance(item, dict):
                raise ValueError("technical contract entries must be objects")
            item["evidence_ids"] = _refs(item.get("evidence_ids", cap["evidence_ids"]), sources)
            if field in {"inputs", "outputs"}:
                if not _text(item.get("name")) or not _text(item.get("format")) or not _text(item.get("description")):
                    raise ValueError("I/O contracts require name, format and description")
            elif field == "requirements":
                if not all(_text(item.get(k)) for k in ("kind", "name", "constraint")):
                    raise ValueError("technical requirement requires kind, name and constraint")
            elif not _text(item.get("text")):
                raise ValueError("limitation requires a scoped statement")
    _check_capability_authority(cap, rid, sources)
    return cap


def _check_capability_authority(cap: dict, rid: str, sources: dict[str, dict]) -> None:
    refs = _refs(cap.get("evidence_ids", []), sources)
    kinds = {sources[ref]["kind"] for ref in refs}
    level = cap.get("evidence_level")
    if level not in LEVELS or cap.get("review_origin") != "curated_evidence":
        raise ValueError("metadata or legacy proposals cannot become reviewed capabilities")
    if kinds <= {"metadata"}:
        raise ValueError("metadata alone does not support a reviewed capability")
    if level == "code_inspected" and not kinds.intersection({"code", "execution"}):
        raise ValueError("code-inspected capability requires code evidence")
    if level == "executed" and ("execution" not in kinds or not isinstance(cap.get("scope"), dict) or not cap["scope"]):
        raise ValueError("executed capability requires an execution receipt and bounded scope")
    if not any(sources[ref]["repository_id"] == rid for ref in refs) and not cap.get("scope"):
        raise ValueError("cross-repository capability evidence requires explicit scope")


def _relationship(raw: dict, sources: dict[str, dict]) -> dict:
    item = _clean(raw)
    kind = item.get("kind")
    if kind not in RELATION_KINDS:
        raise ValueError("unknown repository relationship kind")
    item["source_repository_id"] = _repo_id(item.get("source_repository_id", item.get("source")))
    item["target_repository_id"] = _repo_id(item.get("target_repository_id", item.get("target")))
    if item.get("basis") in {"format_only", "shared_format", "shared_json", "shared_topic", "topic_only"}:
        raise ValueError("a shared format or topic does not establish a technical relationship")
    item["description"] = _text(item.get("description"))
    if not item["description"]:
        raise ValueError("technical relationship requires an explicit explanation")
    item["evidence_ids"] = _refs(item.get("evidence_ids", []), sources)
    if kind == "tested_handoff":
        scope = item.get("scope", {})
        if (not isinstance(scope, dict) or not all(scope.get(k) for k in ("source_revision", "target_revision", "case"))
                or scope.get("result") not in {"pass", "succeeded"}
                or not any(sources[ref]["kind"] == "execution" for ref in item["evidence_ids"])):
            raise ValueError("tested handoff requires versioned, successful execution evidence")
    item["id"] = _stable("relationship", kind, item["source_repository_id"], item["target_repository_id"],
                         item.get("source_capability_key"), item.get("target_capability_key"), item.get("scope", {}))
    return item


def _proposed_relationship(raw: dict) -> dict:
    item = _clean(raw)
    source = _repo_id(item.get("source_repository_id", item.get("source")))
    target = _repo_id(item.get("target_repository_id", item.get("target")))
    kind = item.get("type", item.get("kind"))
    if kind not in {"legacy_handoff", "legacy_comparison", "legacy_dependency", "legacy_association"}:
        raise ValueError("unknown legacy relationship proposal type")
    item.update(source_repository_id=source, target_repository_id=target, type=kind, kind=kind,
                status="rejected" if item.get("status") == "rejected" else "unreviewed")
    item["description"] = _text(item.get("description", item.get("rationale", "")))
    original_id = item["original_id"] if "original_id" in item else item.get("id")
    item["original_id"] = original_id
    item["id"] = _stable("proposed_relationship", source, target, kind, original_id, item.get("original_relation"))
    return item


def _coverage(catalog: dict) -> dict:
    repos = catalog["repositories"]
    source_repos = {s["repository_id"] for s in catalog["sources"] if s["kind"] != "metadata" and
                    s.get("capture_integrity") not in {"mismatch", "unavailable", "unavailable_or_mismatch", "missing"} and
                    any(s.get(k) for k in ("excerpt", "revision", "sha256", "blob_sha", "content_sha256", "source_sha256", "content_path"))}
    levels = Counter(c["evidence_level"] for r in repos for c in r["capabilities"])
    reviewed = sum(bool(r["capabilities"]) for r in repos)
    return {
        "repository_count": len(repos), "capability_count": sum(levels.values()),
        "reviewed_repository_count": reviewed, "unreviewed_repository_count": len(repos) - reviewed,
        "source_captured_repository_count": len(source_repos),
        "source_interpreted_repository_count": sum(bool(r.get("source_interpretations")) for r in repos),
        "source_interpretation_count": sum(len(r.get("source_interpretations", [])) for r in repos),
        "source_count": len(catalog["sources"]), "relationship_count": len(catalog["relationships"]),
        "proposed_capability_count": sum(len(r["proposed_capabilities"]) for r in repos),
        "rejected_proposal_count": sum(p["status"] == "rejected" for r in repos for p in r["proposed_capabilities"]),
        "rejected_assignment_count": sum(len(r["rejected_assignments"]) for r in repos),
        "proposed_relationship_count": len(catalog.get("proposed_relationships", [])),
        "rejected_relationship_proposal_count": sum(r["status"] == "rejected" for r in catalog.get("proposed_relationships", [])),
        "evidence_levels": {level: levels[level] for level in sorted(LEVELS)},
    }


def build_repository_layer(survey_paths: Iterable[str | Path], *,
                           supplemental_paths: Iterable[str | Path] = (),
                           evidence_path: str | Path | None = None) -> dict:
    """Reconcile the complete known inventory, then apply reviewed evidence."""
    registry: dict[str, dict] = {}
    sources: dict[str, dict] = {}
    receipts: dict[str, dict] = {}
    relationships = []
    proposed_relationships = []
    for path in [*_paths(survey_paths), *_paths(supplemental_paths)]:
        data, receipt = _read(path)
        rows = data.get("repositories")
        if not isinstance(rows, list):
            raise ValueError("repository snapshot requires a repositories list")
        excluded = 0
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("repository snapshot rows must be objects")
            excluded += not _merge_row(registry, row, receipt)
        receipt.update(repository_records=len(rows) - excluded, nonrepository_records_excluded=excluded)
        if isinstance(data.get("import_summary"), dict):
            receipt["import_summary"] = _clean(data["import_summary"])
        receipts[receipt["id"]] = receipt
        for raw in data.get("sources", []):
            source = _source(raw)
            if source["id"] in sources and sources[source["id"]] != source:
                raise ValueError("conflicting records for the same source id")
            sources[source["id"]] = source
            registry.setdefault(source["repository_id"], _new_repo(source["repository_id"]))
        relationships.extend(data.get("relationships", []))
        proposed_relationships.extend(data.get("proposed_relationships", []))
    if evidence_path is not None:
        evidence, receipt = _read(evidence_path)
        if evidence.get("schema") != EVIDENCE_SCHEMA:
            raise ValueError("unknown curated repository evidence schema")
        receipts[receipt["id"]] = receipt
        for raw in evidence.get("sources", []):
            source = _source(raw)
            if source["id"] in sources and sources[source["id"]] != source:
                raise ValueError("conflicting records for the same source id")
            sources[source["id"]] = source
            registry.setdefault(source["repository_id"], _new_repo(source["repository_id"]))
        seen = set()
        for raw in evidence.get("repositories", []):
            rid = _identity(raw)
            if rid is None or rid in seen:
                raise ValueError("duplicate or missing repository in curated evidence")
            seen.add(rid)
            repo = registry.setdefault(rid, _new_repo(rid))
            repo["capabilities"] = [_capability(cap, rid, sources) for cap in raw.get("capabilities", [])]
            repo["unknowns"] = _strings(raw.get("unknowns", []))
            for rejection in raw.get("rejected_assignments", []):
                rejection = _clean(rejection)
                if not _text(rejection.get("name")) or not _text(rejection.get("reason")):
                    raise ValueError("rejected assignment requires its name and evidence-based reason")
                rejection["evidence_ids"] = _refs(rejection.get("evidence_ids", []), sources)
                repo["rejected_assignments"].append(rejection)
            for proposal in repo["proposed_capabilities"]:
                for rejected in repo["rejected_assignments"]:
                    if (_text(proposal["name"]).casefold() == _text(rejected["name"]).casefold()
                            or (rejected.get("key") and proposal["key"] == rejected["key"])):
                        proposal["status"] = "rejected"
                        proposal["rejection_reason"] = rejected["reason"]
                        proposal["evidence_ids"] = sorted(set(proposal["evidence_ids"]) | set(rejected["evidence_ids"]))
        relationships.extend(evidence.get("relationships", []))
        proposed_relationships.extend(evidence.get("proposed_relationships", []))
    if not registry:
        raise ValueError("no repository identities found")
    for repo in registry.values():
        repo["aliases"] = _strings(repo["aliases"] or [repo["id"][7:]])
        repo["full_name"] = sorted(repo["aliases"], key=lambda v: (v.casefold(), v))[0]
        repo["url"] = "https://github.com/" + repo["full_name"]
        repo["observations"].sort(key=_json)
        repo["domain_judgments"].sort(key=_json)
        descriptions = [o for o in repo["observations"] if o["description"]]
        if descriptions:
            repo["description"] = max(descriptions, key=lambda o: (str(o["observed_at"] or ""), o["record_sha256"]))["description"]
        repo["capabilities"].sort(key=lambda c: c["key"])
        repo["source_interpretations"].sort(key=lambda i: i["id"])
        for interpretation in repo["source_interpretations"]:
            interpretation["provenance"]["observations"].sort(key=_json)
            _check_source_interpretation(interpretation, repo["id"], sources)
        repo["proposed_capabilities"].sort(key=lambda p: p["id"])
        for proposal in repo["proposed_capabilities"]:
            proposal["observations"].sort(key=_json)
            proposal["provenance"] = {"observations": proposal.pop("observations")}
        repo["rejected_assignments"].sort(key=_json)
        repo["review_state"] = "partially_reviewed" if repo["capabilities"] else "unreviewed"
        unknowns = set(repo["unknowns"])
        if not repo["capabilities"]:
            unknowns.update({"capabilities", "mechanisms", "inputs", "outputs", "requirements", "limitations"})
        for cap in repo["capabilities"]:
            for field in ("inputs", "outputs", "requirements", "limitations"):
                if not cap[field]:
                    unknowns.add(cap["key"] + "." + field)
        repo["unknowns"] = sorted(unknowns)
    normalized_relations = {}
    for raw in relationships:
        item = _relationship(raw, sources)
        if item["id"] in normalized_relations and normalized_relations[item["id"]] != item:
            raise ValueError("conflicting relationship identity")
        normalized_relations[item["id"]] = item
    proposed = {}
    for raw in proposed_relationships:
        item = _proposed_relationship(raw)
        reasons = []
        for end, role_field in (("source", "producer_role"), ("target", "consumer_role")):
            endpoint = registry.get(item[end + "_repository_id"])
            role = item.get(role_field, item.get(end + "_role"))
            if endpoint and role:
                for rejection in endpoint["rejected_assignments"]:
                    rejected_keys = {_text(rejection.get("key")).casefold(), _text(rejection["name"]).casefold()}
                    if _text(role).casefold() in rejected_keys:
                        reasons.append(f"{end} role {role} rejected: {rejection['reason']}")
        if reasons:
            item["status"] = "rejected"
            item["rejection_reason"] = "; ".join(reasons)
        if item["id"] in proposed and proposed[item["id"]] != item:
            raise ValueError("conflicting legacy relationship proposal")
        proposed[item["id"]] = item
    catalog = {
        "schema": SCHEMA, "scope": "repository_only",
        "repositories": sorted(registry.values(), key=lambda r: r["id"]),
        "sources": sorted(sources.values(), key=lambda s: s["id"]),
        "relationships": sorted(normalized_relations.values(), key=lambda r: r["id"]),
        "proposed_relationships": sorted(proposed.values(), key=lambda r: r["id"]),
        "input_sources": sorted(receipts.values(), key=lambda r: r["id"]),
        "boundaries": [
            "Inventory scope is the supplied known repository snapshots; it is not a census of all GitHub.",
            "Captured source text and historical role proposals do not establish reviewed capabilities.",
            "Source-bound technical interpretations preserve literal evidence and model or analyst provenance; semantic support and execution remain unverified.",
            "Documented, inspected and executed evidence applies only to the recorded capability and scope.",
            "Empty technical contract fields are unknown, not a declaration that no constraints exist.",
            "No technical relationship is inferred merely from a shared topic or file format.",
        ],
    }
    catalog["coverage"] = _coverage(catalog)
    catalog["catalog_digest"] = _digest(catalog)
    validate_repository_layer(catalog)
    return catalog


def validate_repository_layer(catalog: dict) -> dict:
    if catalog.get("schema") != SCHEMA or catalog.get("scope") != "repository_only":
        raise ValueError("repository-only catalog required")
    _reject_demand(catalog)
    repos = catalog.get("repositories")
    if not isinstance(repos, list) or not repos:
        raise ValueError("repository catalog must retain its inventory")
    ids = [r.get("id") for r in repos]
    if len(ids) != len(set(ids)) or any(_repo_id(rid) != rid for rid in ids):
        raise ValueError("repository identities must be unique and canonical")
    by_repo = {r["id"]: r for r in repos}
    sources = {s["id"]: s for s in catalog.get("sources", [])}
    if len(sources) != len(catalog.get("sources", [])):
        raise ValueError("duplicate source id")
    for source in sources.values():
        if _source(source) != source or source["repository_id"] not in by_repo:
            raise ValueError("source identity or repository reference is inconsistent")
    all_ids = set(ids)
    input_ids = [s["id"] for s in catalog.get("input_sources", [])]
    if len(input_ids) != len(set(input_ids)):
        raise ValueError("duplicate input source receipt")
    for source_id in sources:
        if source_id in all_ids:
            raise ValueError("source identity collides with another record")
        all_ids.add(source_id)
    for repo in repos:
        if _repo_id(repo["full_name"]) != repo["id"]:
            raise ValueError("repository display identity differs from its canonical id")
        if repo["review_state"] != ("partially_reviewed" if repo["capabilities"] else "unreviewed"):
            raise ValueError("repository review status overstates capability review")
        for observation in repo["observations"]:
            if observation.get("evidence_level") != "metadata_only":
                raise ValueError("discovery observations cannot be promoted to capabilities")
            if observation.get("source_id") not in input_ids:
                raise ValueError("observation references an unknown input snapshot")
        for judgment in repo.get("domain_judgments", []):
            if judgment.get("authority") != "metadata_only" or judgment.get("source_id") not in input_ids:
                raise ValueError("domain judgment authority or provenance is invalid")
        keys = set()
        for interpretation in repo.get("source_interpretations", []):
            if interpretation != _source_interpretation(interpretation, repo["id"]) or interpretation["id"] in all_ids:
                raise ValueError("duplicate or inconsistent source interpretation")
            _check_source_interpretation(interpretation, repo["id"], sources)
            all_ids.add(interpretation["id"])
            observations = interpretation["provenance"].get("observations", [])
            if not observations or any(o.get("input_source_id") not in input_ids for o in observations):
                raise ValueError("source interpretation references an unknown input snapshot")
        for cap in repo["capabilities"]:
            normalized = _capability(cap, repo["id"], sources)
            if cap != normalized or cap["key"] in keys or cap["id"] in all_ids:
                raise ValueError("duplicate or inconsistent capability identity")
            keys.add(cap["key"])
            all_ids.add(cap["id"])
        for proposal in repo["proposed_capabilities"]:
            if proposal.get("status") not in {"unreviewed", "rejected"}:
                raise ValueError("legacy proposal cannot assert reviewed or verified status")
            if proposal["id"] != _stable("proposal", repo["id"], proposal["key"]) or proposal["id"] in all_ids:
                raise ValueError("duplicate or inconsistent proposal identity")
            all_ids.add(proposal["id"])
            _refs(proposal.get("evidence_ids", []), sources, required=False)
        for rejection in repo["rejected_assignments"]:
            if not _text(rejection.get("name")) or not _text(rejection.get("reason")):
                raise ValueError("invalid rejected assignment")
            _refs(rejection.get("evidence_ids", []), sources)
            if any(cap["name"].casefold() == _text(rejection["name"]).casefold()
                   or (rejection.get("key") and cap["key"] == rejection["key"])
                   for cap in repo["capabilities"]):
                raise ValueError("a rejected assignment remains an active capability")
    for relation in catalog.get("relationships", []):
        if relation != _relationship(relation, sources) or relation["id"] in all_ids:
            raise ValueError("duplicate or inconsistent relationship")
        all_ids.add(relation["id"])
        for end in ("source", "target"):
            rid = relation[end + "_repository_id"]
            if rid not in by_repo:
                raise ValueError("relationship references an unknown repository")
            key = relation.get(end + "_capability_key")
            if key is not None and key not in {c["key"] for c in by_repo[rid]["capabilities"]}:
                raise ValueError("relationship references an unreviewed or unknown capability")
    for proposal in catalog.get("proposed_relationships", []):
        if proposal != _proposed_relationship(proposal) or proposal["id"] in all_ids:
            raise ValueError("duplicate or inconsistent legacy relationship proposal")
        all_ids.add(proposal["id"])
        if proposal["source_repository_id"] not in by_repo or proposal["target_repository_id"] not in by_repo:
            raise ValueError("legacy relationship proposal references an unknown repository")
    coverage = _coverage(catalog)
    if catalog.get("coverage") != coverage:
        raise ValueError("catalog coverage counts do not reconcile")
    unhashed = {k: v for k, v in catalog.items() if k != "catalog_digest"}
    if catalog.get("catalog_digest") != _digest(unhashed):
        raise ValueError("catalog content digest mismatch")
    return {"schema": "cite_refinery.repository_layer_validation.v1", "valid": True,
            "scope": "repository_only", **coverage}


def repository_layer_packet(catalog: dict, project_id: str | None = None) -> dict:
    """Project technical records directly; never bootstrap a problem root."""
    validate_repository_layer(catalog)
    sources = {s["id"]: s for s in catalog["sources"]}
    source_ids_by_repo: dict[str, list[str]] = {}
    for source in sources.values():
        source_ids_by_repo.setdefault(source["repository_id"], []).append(source["id"])
    nodes, edges = [], []
    cluster = "repository_inventory"

    def refs(ids: list[str]) -> list[str]:
        return sorted({sources[sid]["url"] for sid in ids})

    def node(key: str, statement: str, kind: str, provenance: dict, evidence: list[str] | None = None) -> None:
        nodes.append({"key": key, "statement": statement, "kind": kind, "layer": "program",
                      "clusters": [cluster], "source_refs": refs(evidence or []), "provenance": provenance})

    def edge(source: str, target: str, relation: str, evidence: list[str], *, status: str = "qualified", **provenance: Any) -> None:
        edges.append({"source": source, "target": target, "relation": relation,
                      "status": status, "evidence_refs": refs(evidence), "provenance": provenance})

    for repo in catalog["repositories"]:
        evidence = source_ids_by_repo.get(repo["id"], [])
        node(repo["id"], "Source repository: " + repo["id"][7:], "repository", {
            "repository_id": repo["id"], "catalog_digest": catalog["catalog_digest"],
            "review_state": repo["review_state"], "domains": repo["domains"], "unknowns": repo["unknowns"],
            "domain_judgments": deepcopy(repo.get("domain_judgments", [])),
            "observation_sources": sorted({o["source_id"] for o in repo["observations"]}),
            "legacy_role_proposals": [{k: p[k] for k in ("id", "key", "name", "status")} for p in repo["proposed_capabilities"]],
        }, evidence)
        for interpretation in repo.get("source_interpretations", []):
            statement = interpretation["purpose"] or "Source-bound technical interpretation of " + repo["id"][7:]
            node(interpretation["id"], statement, "source_interpretation", deepcopy(interpretation), interpretation["evidence_ids"])
            edge(repo["id"], interpretation["id"], "HAS_SOURCE_INTERPRETATION", interpretation["evidence_ids"],
                 status="candidate", semantic_support_verified=False, runtime_tested=False)
            for source_id in interpretation["evidence_ids"]:
                edge(interpretation["id"], source_id, "DERIVED_FROM", [source_id],
                     status="candidate", scope="literal source binding; semantic support remains unverified")
        for cap in repo["capabilities"]:
            node(cap["id"], cap["name"], "capability", deepcopy(cap), cap["evidence_ids"])
            edge(repo["id"], cap["id"], "DECLARES_CAPABILITY", cap["evidence_ids"], evidence_level=cap["evidence_level"], scope=cap.get("scope", {}))
            mechanism = cap["id"] + ":mechanism"
            node(mechanism, cap["mechanism"], "mechanism", {"capability_id": cap["id"], "evidence_level": cap["evidence_level"]}, cap["evidence_ids"])
            edge(cap["id"], mechanism, "USES_MECHANISM", cap["evidence_ids"], evidence_level=cap["evidence_level"])
            for field, kind, relation in (("inputs", "input_contract", "ACCEPTS"), ("outputs", "output_contract", "PRODUCES"),
                                           ("requirements", "technical_requirement", "REQUIRES"), ("limitations", "limitation", "LIMITED_BY")):
                for item in cap[field]:
                    key = _stable(kind, cap["id"], item)
                    statement = item.get("text") or " — ".join(str(item[k]) for k in ("name", "format", "constraint", "description") if item.get(k))
                    node(key, statement, kind, {"capability_id": cap["id"], **deepcopy(item)}, item["evidence_ids"])
                    edge(cap["id"], key, relation, item["evidence_ids"], evidence_level=cap["evidence_level"])
            for source_id in cap["evidence_ids"]:
                edge(cap["id"], source_id, "DERIVED_FROM", [source_id], evidence_level=cap["evidence_level"])
        for item in repo["rejected_assignments"]:
            key = _stable("rejected_assignment", repo["id"], item)
            node(key, "Rejected assignment " + item["name"] + ": " + item["reason"], "limitation", deepcopy(item), item["evidence_ids"])
            edge(repo["id"], key, "LIMITED_BY", item["evidence_ids"], scope="specific rejected assignment, not proof of all absent functionality")
    for source in catalog["sources"]:
        summary = "Source evidence: " + source["repository_id"][7:] + " / " + str(source.get("path") or source.get("title") or source["kind"])
        node(source["id"], summary, "source", deepcopy(source), [source["id"]])
        edge(source["id"], source["repository_id"], "DERIVED_FROM", [source["id"]], scope="source provenance only")
    kinds = {"declared_dependency": "DEPENDS_ON", "proposed_handoff": "PROPOSED_HANDOFF", "tested_handoff": "TESTED_HANDOFF"}
    for relation in catalog["relationships"]:
        endpoints = []
        for end in ("source", "target"):
            rid, key = relation[end + "_repository_id"], relation.get(end + "_capability_key")
            endpoints.append(_stable("capability", rid, key) if key else rid)
        edge(*endpoints, kinds[relation["kind"]], relation["evidence_ids"],
             status="candidate" if relation["kind"] == "proposed_handoff" else "qualified", technical_relationship=deepcopy(relation))
    packet = {
        "schema": "cite_refinery.semantic_graph.v1", "source_system": "refinery",
        "clusters": [{"key": cluster, "title": "Repository capabilities and technical contracts", "tags": ["repository_only"]}],
        "nodes": sorted(nodes, key=lambda n: n["key"]), "edges": sorted(edges, key=_json),
        "conversion_metadata": {"source_schema": SCHEMA, "catalog_digest": catalog["catalog_digest"],
                                "scope": "repository_only", "coverage": deepcopy(catalog["coverage"]),
                                "boundary": "Source interpretations and legacy roles retain their distinct proposal authority; capability nodes require separate reviewed evidence."},
    }
    if project_id is not None:
        packet["project_id"] = project_id
    return packet
