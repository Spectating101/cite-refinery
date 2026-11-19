"""Immutable, paged technical projection of a complete repository catalogue.

The index does not modify the active software-discovery or mapping databases.
It retains canonical records while searching only explicitly selected technical
fields. Captured text, source interpretations and curated capabilities keep their
separate authority and counts.
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any

from .repository_layer import validate_repository_layer


SCHEMA = "cite_refinery.repository_layer_index.v1"
PAGE_SCHEMA = "cite_refinery.repository_layer_page.v1"
ENV = "CITE_REFINERY_REPOSITORY_LAYER_DB"
_ARRAYS = ("repositories", "sources", "relationships", "proposed_relationships")
_CAPTURE_FIELDS = ("excerpt", "revision", "sha256", "blob_sha", "content_sha256", "source_sha256", "content_path")
_STATES = {"", "all", "metadata_only", "source_captured", "source_interpreted",
           "documented", "code_inspected", "executed", "unreviewed", "partially_reviewed"}
_MAPPING_STATES = {"mapping_" + value: value for value in
                   ("ready", "mapped", "needs_review", "insufficient_source", "source_unavailable")}
_STATES.update(_MAPPING_STATES)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _search_text(repository: dict) -> str:
    values = [repository.get(key, "") for key in ("id", "full_name", "description")]
    for field in ("aliases", "languages", "topics", "domains"):
        values.extend(repository.get(field, []))
    identity = repository.get("reviewed_identity") or {}
    values.append(identity.get("canonical_repository_id", ""))
    values.extend(identity.get("observed_repository_ids", []))
    for capability in repository.get("capabilities", []):
        values.extend(capability.get(key, "") for key in ("key", "name", "mechanism"))
        for field in ("inputs", "outputs", "requirements", "limitations"):
            for item in capability.get(field, []):
                if isinstance(item, str):
                    values.append(item)
                else:
                    values.extend(item.get(key, "") for key in ("kind", "name", "format", "description", "constraint", "text"))
    for interpretation in repository.get("source_interpretations", []):
        values.append(interpretation.get("purpose", ""))
        for field in ("inputs", "outputs", "human_work", "custom_glue", "limitations"):
            values.extend(interpretation.get(field, []))
    for finding in repository.get("technical_findings", []):
        if finding.get("status") == "approved":
            values.extend(finding.get(key, "") for key in ("title", "kind", "direction", "format", "description"))
            values.extend(finding.get("limitations", []))
    return " ".join(str(value) for value in values if value).casefold()


def _receipt(path: Path, catalog: dict) -> dict:
    return {"schema": SCHEMA, "path": str(path), "sha256": _sha_file(path),
            "bytes": path.stat().st_size, "catalog_digest": catalog["catalog_digest"],
            "coverage": catalog["coverage"]}


@contextmanager
def _open_index(path: str | Path):
    source = Path(path)
    if not source.is_file() or source.is_symlink():
        raise ValueError("Repository layer index is unavailable")
    db = None
    try:
        db = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        metadata = {key: json.loads(value) for key, value in db.execute("SELECT key,value FROM metadata")}
        if metadata.get("schema") != SCHEMA or db.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise ValueError("Unknown repository layer index schema")
        if not isinstance(metadata.get("catalog_metadata"), dict) or not isinstance(metadata.get("domains"), list):
            raise ValueError("Malformed repository layer index metadata")
        yield db, metadata
    except (sqlite3.DatabaseError, json.JSONDecodeError) as exc:
        raise ValueError("Repository layer index is unreadable") from exc
    finally:
        if db is not None:
            db.close()


def _read_catalog(path: Path) -> dict:
    with _open_index(path) as (db, metadata):
        catalog = metadata["catalog_metadata"]
        for table in _ARRAYS:
            catalog[table] = [json.loads(row[0]) for row in db.execute(f"SELECT payload FROM {table} ORDER BY ordinal")]
        return catalog


def build_repository_layer_index(catalog: dict, path: str | Path) -> dict:
    """Publish an immutable index; identical retries verify and reuse its content."""
    validate_repository_layer(catalog)
    target = Path(path)
    if target.is_symlink():
        raise ValueError("Repository layer index must not be a symbolic link")
    if target.exists():
        existing = _read_catalog(target)
        validate_repository_layer(existing)
        if existing != catalog:
            raise ValueError("Immutable repository layer index already contains a different catalogue")
        return _receipt(target, catalog)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix="repository-index-", suffix=".sqlite3", dir=target.parent)
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with sqlite3.connect(temporary) as db:
            db.executescript("""
                CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE repositories(
                    id TEXT PRIMARY KEY, ordinal INTEGER NOT NULL, sort_name TEXT NOT NULL,
                    search_text TEXT NOT NULL, has_source INTEGER NOT NULL,
                    interpretation_count INTEGER NOT NULL, capability_count INTEGER NOT NULL,
                    documented_count INTEGER NOT NULL, code_inspected_count INTEGER NOT NULL,
                    executed_count INTEGER NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE domains(repository_id TEXT NOT NULL, domain TEXT NOT NULL,
                                     PRIMARY KEY(repository_id,domain));
                CREATE INDEX domain_lookup ON domains(domain,repository_id);
                CREATE INDEX repository_order ON repositories(sort_name,id);
                CREATE TABLE source_mapping_states(repository_id TEXT NOT NULL, status TEXT NOT NULL,
                    PRIMARY KEY(repository_id,status));
                CREATE INDEX mapping_state_lookup ON source_mapping_states(status,repository_id);
                CREATE TABLE sources(id TEXT PRIMARY KEY, ordinal INTEGER NOT NULL,
                                     repository_id TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE INDEX source_owner ON sources(repository_id);
                CREATE TABLE relationships(id TEXT PRIMARY KEY, ordinal INTEGER NOT NULL,
                    source_repository_id TEXT NOT NULL, target_repository_id TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE INDEX relationship_source ON relationships(source_repository_id);
                CREATE INDEX relationship_target ON relationships(target_repository_id);
                CREATE TABLE proposed_relationships(id TEXT PRIMARY KEY, ordinal INTEGER NOT NULL,
                    source_repository_id TEXT NOT NULL, target_repository_id TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE INDEX proposed_relationship_source ON proposed_relationships(source_repository_id);
                CREATE INDEX proposed_relationship_target ON proposed_relationships(target_repository_id);
            """)
            captured = {source["repository_id"] for source in catalog["sources"]
                        if source["kind"] != "metadata"
                        and source.get("capture_integrity") not in {"mismatch", "unavailable", "unavailable_or_mismatch", "missing"}
                        and any(source.get(key) for key in _CAPTURE_FIELDS)}
            domain_counts = Counter()
            for ordinal, repository in enumerate(catalog["repositories"]):
                levels = Counter(item["evidence_level"] for item in repository["capabilities"])
                db.execute("INSERT INTO repositories VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                    repository["id"], ordinal, repository["full_name"].casefold(), _search_text(repository),
                    int(repository["id"] in captured), len(repository.get("source_interpretations", [])),
                    len(repository["capabilities"]), levels["documented"], levels["code_inspected"], levels["executed"],
                    _json(repository)))
                domains = set(repository["domains"])
                domain_counts.update(domains)
                db.executemany("INSERT INTO domains VALUES(?,?)", ((repository["id"], domain) for domain in domains))
                states = {item["status"] for item in repository.get("source_mapping_states", [])
                          if isinstance(item, dict) and isinstance(item.get("status"), str)}
                db.executemany("INSERT INTO source_mapping_states VALUES(?,?)",
                               ((repository["id"], status) for status in sorted(states)))
            for ordinal, source in enumerate(catalog["sources"]):
                db.execute("INSERT INTO sources VALUES(?,?,?,?)", (source["id"], ordinal, source["repository_id"], _json(source)))
            for table in ("relationships", "proposed_relationships"):
                for ordinal, relation in enumerate(catalog.get(table, [])):
                    db.execute(f"INSERT INTO {table} VALUES(?,?,?,?,?)", (relation["id"], ordinal,
                               relation["source_repository_id"], relation["target_repository_id"], _json(relation)))
            metadata = {
                "schema": SCHEMA, "catalog_digest": catalog["catalog_digest"], "coverage": catalog["coverage"],
                "index_features": ["source_mapping_states", "reviewed_identity_search"],
                "catalog_metadata": {key: value for key, value in catalog.items() if key not in _ARRAYS},
                "domains": [{"id": key, "title": key.replace("_", " "), "count": count}
                            for key, count in sorted(domain_counts.items())],
            }
            db.executemany("INSERT INTO metadata VALUES(?,?)", ((key, _json(value)) for key, value in metadata.items()))
            db.execute("PRAGMA user_version=1")
        db.close()
        # Publish the completed file without replacing an existing release.
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError:
            existing = _read_catalog(target)
            validate_repository_layer(existing)
            if existing != catalog:
                raise ValueError("Immutable repository layer index already contains a different catalogue")
        return _receipt(target, catalog)
    finally:
        temporary.unlink(missing_ok=True)


def configured_repository_layer_path() -> Path | None:
    value = os.environ.get(ENV, "").strip()
    return Path(value).expanduser() if value else None


def _evidence_ids(value: Any) -> set[str]:
    result = set()
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, dict):
            result.update(ref for ref in item.get("evidence_ids", []) if isinstance(ref, str))
            pending.extend(child for key, child in item.items() if key != "evidence_ids")
    return result


def _by_ids(db: sqlite3.Connection, table: str, identities: set[str]) -> list[dict]:
    found = []
    ordered = sorted(identities)
    for start in range(0, len(ordered), 500):
        batch = ordered[start:start + 500]
        marks = ",".join("?" for _ in batch)
        found.extend((ordinal, json.loads(payload)) for ordinal, payload in
                     db.execute(f"SELECT ordinal,payload FROM {table} WHERE id IN ({marks})", batch))
    return [record for _, record in sorted(found, key=lambda row: row[0])]


def _page_refresh(refresh: dict, repository_ids: set[str]) -> dict:
    """Keep complete accounting in the catalogue, not every paged response."""
    if not refresh:
        return {}
    result = {key: value for key, value in refresh.items() if key != "snapshots"}
    result["snapshots"] = []
    for snapshot in refresh.get("snapshots", []):
        summary = {key: value for key, value in snapshot.items() if key not in {"exclusions", "gallery_accounting"}}
        if "exclusions" in snapshot:
            exclusions = snapshot["exclusions"]
            summary["exclusion_count"] = len(exclusions)
            summary["page_exclusions"] = [value for value in exclusions if isinstance(value, dict)
                                           and any(value.get(key) in repository_ids
                                                   for key in ("repository_id", "catalog_id", "record_id"))]
        if "gallery_accounting" in snapshot:
            summary["gallery_accounting_count"] = len(snapshot["gallery_accounting"])
        result["snapshots"].append(summary)
    return result


def query_repository_layer(path: str | Path, query: str = "", domain: str = "", review_state: str = "",
                           limit: int = 30, offset: int = 0) -> dict:
    """Return one page plus its explicit evidence and incident technical edges."""
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or not 0 <= offset <= 1_000_000:
        raise ValueError("Use a page limit from one to one hundred and a bounded offset")
    if not isinstance(query, str) or len(query) > 250 or len(query.split()) > 12:
        raise ValueError("Search query exceeds its budget")
    if not isinstance(domain, str) or len(domain) > 200:
        raise ValueError("Invalid repository domain filter")
    if not isinstance(review_state, str) or review_state not in _STATES:
        raise ValueError("Unknown repository evidence filter")
    if path is None:
        raise ValueError("Repository layer index is not configured")
    clauses, parameters = [], []
    for token in query.casefold().split():
        escaped = token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append("r.search_text LIKE ? ESCAPE '\\'")
        parameters.append("%" + escaped + "%")
    if domain:
        clauses.append("EXISTS(SELECT 1 FROM domains d WHERE d.repository_id=r.id AND d.domain=?)")
        parameters.append(domain)
    filters = {
        "metadata_only": "r.has_source=0 AND r.interpretation_count=0 AND r.capability_count=0",
        "unreviewed": "r.capability_count=0",
        "partially_reviewed": "r.capability_count>0", "source_captured": "r.has_source=1",
        "source_interpreted": "r.interpretation_count>0", "documented": "r.documented_count>0",
        "code_inspected": "r.code_inspected_count>0", "executed": "r.executed_count>0",
    }
    if review_state in filters:
        clauses.append(filters[review_state])
    with _open_index(path) as (db, metadata):
        if review_state in _MAPPING_STATES:
            if "source_mapping_states" in metadata.get("index_features", []):
                clauses.append("EXISTS(SELECT 1 FROM source_mapping_states m WHERE m.repository_id=r.id AND m.status=?)")
                parameters.append(_MAPPING_STATES[review_state])
            else:
                # Older immutable snapshots have no mapping-status observations.
                clauses.append("0")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        total = db.execute("SELECT COUNT(*) FROM repositories r" + where, parameters).fetchone()[0]
        items = [json.loads(row[0]) for row in db.execute("SELECT r.payload FROM repositories r" + where +
                 " ORDER BY r.sort_name,r.id LIMIT ? OFFSET ?", [*parameters, limit, offset])]
        ids = {item["id"] for item in items}
        relations = {"relationships": [], "proposed_relationships": []}
        source_ids = _evidence_ids(items)
        neighbors = set()
        if ids:
            marks = ",".join("?" for _ in ids)
            for table in relations:
                relations[table] = [json.loads(row[0]) for row in db.execute(
                    f"SELECT payload FROM {table} WHERE source_repository_id IN ({marks}) "
                    f"OR target_repository_id IN ({marks}) ORDER BY ordinal", [*sorted(ids), *sorted(ids)])]
                for relation in relations[table]:
                    neighbors.update((relation["source_repository_id"], relation["target_repository_id"]))
                source_ids.update(_evidence_ids(relations[table]))
            source_ids.update(row[0] for row in db.execute(f"SELECT id FROM sources WHERE repository_id IN ({marks})", sorted(ids)))
        neighbor_records = [{key: item[key] for key in ("id", "full_name", "url")} for item in _by_ids(db, "repositories", neighbors - ids)]
        catalog_metadata = metadata["catalog_metadata"]
        resolution_ids = {value for item in items for value in
                          item.get("reviewed_identity", {}).get("resolution_ids", [])}
        identity_resolutions = [value for value in catalog_metadata.get("identity_resolutions", [])
                                if value.get("id") in resolution_ids]
        return {"schema": PAGE_SCHEMA, "scope": "repository_only", "catalog_digest": metadata["catalog_digest"],
                "total": total, "coverage": metadata["coverage"], "items": items,
                "refresh": _page_refresh(catalog_metadata.get("refresh", {}), ids), "identity_resolutions": identity_resolutions,
                "sources": _by_ids(db, "sources", source_ids), "neighbors": neighbor_records, **relations,
                "domains": metadata["domains"], "query": query, "domain": domain, "review_state": review_state,
                "limit": limit, "offset": offset}
