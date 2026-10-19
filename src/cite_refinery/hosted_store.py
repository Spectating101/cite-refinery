"""Transactional, tenant-isolated private workspace control plane (SQLite milestone).

Projects store the existing v6 semantic state as JSON inside a SQLite transaction.
Users, tenant memberships, hashed credentials, jobs and audit records are separate
tables. This is a first executable backend, NOT a production Postgres migration.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from .semantic import SemanticGraph
from .store import _EMPTY_STATE


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}:{uuid4().hex}"


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class PermissionDenied(Exception):
    pass


class StateConflict(Exception):
    pass


class NotFound(Exception):
    pass


class _MemoryStore:
    def __init__(self, state: dict[str, Any]):
        self.state = deepcopy(state)

    def load(self) -> dict[str, Any]:
        return deepcopy(self.state)

    def save(self, state: dict[str, Any]) -> None:
        self.state = deepcopy(state)


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS tenants (
  id TEXT PRIMARY KEY, name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS memberships (
  tenant_id TEXT NOT NULL REFERENCES tenants(id),
  user_id TEXT NOT NULL REFERENCES users(id),
  role TEXT NOT NULL CHECK(role IN ('owner','editor','viewer')),
  PRIMARY KEY (tenant_id,user_id)
);
CREATE TABLE IF NOT EXISTS access_tokens (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
  token_hash TEXT NOT NULL UNIQUE,
  expires_at TEXT NOT NULL, revoked_at TEXT
);
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES tenants(id),
  title TEXT NOT NULL, problem TEXT NOT NULL,
  revision INTEGER NOT NULL DEFAULT 0, state_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ingest_jobs (
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES tenants(id),
  project_id TEXT NOT NULL REFERENCES projects(id),
  submitted_by TEXT NOT NULL REFERENCES users(id),
  packet_json TEXT NOT NULL,
  packet_hash TEXT NOT NULL,
  expected_revision INTEGER NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','failed')),
  result_json TEXT, error TEXT, created_at TEXT NOT NULL,
  started_at TEXT, finished_at TEXT
);
CREATE INDEX IF NOT EXISTS jobs_pending_idx ON ingest_jobs(status, created_at);
CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL REFERENCES tenants(id),
  project_id TEXT, actor TEXT, action TEXT NOT NULL,
  details_json TEXT NOT NULL, created_at TEXT NOT NULL
);
"""


class WorkspaceDB:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with self._connection() as db:
            db.executescript(SCHEMA)
        # SQLite may create a file with the caller's permissive default umask.
        os.chmod(self.path, 0o600)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=15000")
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    @staticmethod
    def _audit(db: sqlite3.Connection, tenant_id: str, project_id: str | None,
               actor: str | None, action: str, details: dict[str, Any]) -> None:
        db.execute(
            "INSERT INTO audit_events VALUES(?,?,?,?,?,?,?)",
            (_id("audit"), tenant_id, project_id, actor, action,
             json.dumps(details, sort_keys=True), _now()),
        )

    def create_tenant(self, name: str, owner_username: str) -> dict[str, str]:
        if not name.strip() or not owner_username.strip():
            raise ValueError("nonempty tenant name and owner username required")
        tenant_id, user_id = _id("tenant"), _id("user")
        with self._write() as db:
            db.execute("INSERT INTO tenants VALUES(?,?)", (tenant_id, name.strip()))
            db.execute("INSERT INTO users VALUES(?,?)", (user_id, owner_username.strip()))
            db.execute("INSERT INTO memberships VALUES(?,?,?)", (tenant_id, user_id, "owner"))
        return {"tenant_id": tenant_id, "owner_user_id": user_id}

    def add_user(self, username: str) -> str:
        if not username.strip():
            raise ValueError("username required")
        user_id = _id("user")
        with self._write() as db:
            db.execute("INSERT INTO users VALUES(?,?)", (user_id, username.strip()))
        return user_id

    def grant_membership(self, owner_id: str, tenant_id: str,
                         target_id: str, role: str) -> None:
        if role not in {"owner", "editor", "viewer"}:
            raise ValueError("invalid role")
        with self._write() as db:
            self._require(db, owner_id, tenant_id, {"owner"})
            db.execute(
                "INSERT INTO memberships(tenant_id,user_id,role) VALUES(?,?,?) "
                "ON CONFLICT(tenant_id,user_id) DO UPDATE SET role=excluded.role",
                (tenant_id, target_id, role),
            )
            self._audit(db, tenant_id, None, owner_id, "membership_granted",
                        {"user_id": target_id, "role": role})

    def issue_token(self, user_id: str, ttl_hours: int = 24) -> str:
        if not 1 <= ttl_hours <= 720:
            raise ValueError("token TTL must be 1..720 hours")
        raw = secrets.token_urlsafe(40)
        expires = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()
        with self._write() as db:
            db.execute("INSERT INTO access_tokens VALUES(?,?,?,?,?)",
                       (_id("token"), user_id, _hash_token(raw), expires, None))
        return raw

    def revoke_token(self, raw: str) -> None:
        with self._write() as db:
            db.execute("UPDATE access_tokens SET revoked_at=? WHERE token_hash=?",
                       (_now(), _hash_token(raw)))

    def authenticate(self, raw: str) -> str:
        if not raw or len(raw) > 256:
            raise PermissionDenied("invalid credentials")
        candidate = _hash_token(raw)
        with self._connection() as db:
            row = db.execute("SELECT user_id,token_hash,expires_at,revoked_at FROM access_tokens "
                             "WHERE token_hash=?", (candidate,)).fetchone()
        if (row is None or not hmac.compare_digest(row["token_hash"], candidate)
                or row["revoked_at"] is not None
                or datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc)):
            raise PermissionDenied("invalid credentials")
        return str(row["user_id"])

    @staticmethod
    def _require(db: sqlite3.Connection, user_id: str,
                 tenant_id: str, roles: set[str] | None = None) -> str:
        row = db.execute("SELECT role FROM memberships WHERE tenant_id=? AND user_id=?",
                         (tenant_id, user_id)).fetchone()
        if not row or (roles is not None and row["role"] not in roles):
            raise PermissionDenied("insufficient project permissions")
        return str(row["role"])

    @staticmethod
    def _project(db: sqlite3.Connection, project_id: str) -> sqlite3.Row:
        row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise NotFound("unknown project")
        return row

    def create_project(self, user_id: str, tenant_id: str, title: str, problem: str) -> str:
        if not title.strip() or not problem.strip():
            raise ValueError("project title and problem required")
        project_id = _id("rproject")
        state = deepcopy(_EMPTY_STATE)
        state["projects"][project_id] = {
            "id": project_id, "title": title.strip(), "problem": problem.strip(),
            "branch": "main", "status": "active",
            "created_at": _now(), "updated_at": _now(),
        }
        with self._write() as db:
            self._require(db, user_id, tenant_id, {"owner", "editor"})
            db.execute("INSERT INTO projects VALUES(?,?,?,?,?,?)",
                       (project_id, tenant_id, title.strip(), problem.strip(),
                        0, json.dumps(state)))
            self._audit(db, tenant_id, project_id, user_id, "project_created",
                        {"title": title.strip()})
        return project_id

    def list_projects(self, user_id: str) -> list[dict[str, Any]]:
        with self._connection() as db:
            rows = db.execute(
                "SELECT p.id,p.tenant_id,p.title,p.problem,p.revision,m.role "
                "FROM projects p JOIN memberships m ON m.tenant_id=p.tenant_id "
                "WHERE m.user_id=? ORDER BY p.title,p.id", (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def project_state(self, user_id: str, project_id: str) -> dict[str, Any]:
        with self._connection() as db:
            row = self._project(db, project_id)
            self._require(db, user_id, row["tenant_id"])
            return json.loads(row["state_json"])

    def project_projection(self, user_id: str, project_id: str):
        from .workspace import ProductWorkspace
        state = self.project_state(user_id, project_id)
        ws = ProductWorkspace(_MemoryStore(state))
        return ws.project_view(project_id)

    def preview(self, user_id: str, project_id: str, packet: dict[str, Any]) -> dict[str, Any]:
        with self._connection() as db:
            row = self._project(db, project_id)
            self._require(db, user_id, row["tenant_id"], {"owner", "editor"})
            state = json.loads(row["state_json"])
            revision = int(row["revision"])
        graph = SemanticGraph(_MemoryStore(state))
        data = graph.preview_packet(project_id, packet)
        return {**data, "project_revision": revision}

    def enqueue(self, user_id: str, project_id: str, packet: dict[str, Any],
                expected_revision: int, expected_packet_digest: str) -> str:
        if not isinstance(packet, dict):
            raise ValueError("packet must be an object")
        raw = json.dumps(packet, sort_keys=True, ensure_ascii=False)
        if len(raw.encode("utf-8")) > 8 * 1024 * 1024:
            raise ValueError("packet exceeds 8 MiB")
        with self._write() as db:
            row = self._project(db, project_id)
            self._require(db, user_id, row["tenant_id"], {"owner", "editor"})
            if row["revision"] != expected_revision:
                raise StateConflict("project changed since preview")
            review = SemanticGraph(_MemoryStore(json.loads(row["state_json"]))).preview_packet(
                project_id, packet)
            if review["packet_digest"] != expected_packet_digest:
                raise StateConflict("packet differs from reviewed content")
            if review["already_imported"]:
                raise StateConflict("packet already imported")
            job_id = _id("job")
            db.execute(
                "INSERT INTO ingest_jobs(id,tenant_id,project_id,submitted_by,packet_json,"
                "packet_hash,expected_revision,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (job_id, row["tenant_id"], project_id, user_id, raw,
                 expected_packet_digest, expected_revision, "queued", _now()),
            )
            self._audit(db, row["tenant_id"], project_id, user_id, "ingest_queued",
                        {"job_id": job_id, "revision": expected_revision})
        return job_id

    def get_job(self, user_id: str, job_id: str) -> dict[str, Any]:
        with self._connection() as db:
            row = db.execute("SELECT * FROM ingest_jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise NotFound("unknown job")
            self._require(db, user_id, row["tenant_id"])
        # Never expose the full submitted packet to readers via job metadata.
        return {key: row[key] for key in
                ("id", "project_id", "status", "created_at", "started_at",
                 "finished_at", "error", "result_json")}

    def run_one_job(self) -> dict[str, Any] | None:
        """Process one bounded packet within a *single* SQLite transaction.

        A worker crash rolls the transaction back to a still-queued job.
        BEGIN IMMEDIATE serializes workers and the project revision update.
        This deliberately limits concurrency: production needs a separate queue,
        transactional project store and lease-based distributed workers.
        """
        with self._write() as db:
            row = db.execute("SELECT * FROM ingest_jobs WHERE status='queued' "
                             "ORDER BY created_at,id LIMIT 1").fetchone()
            if row is None:
                return None
            db.execute("UPDATE ingest_jobs SET status='running',started_at=? WHERE id=?",
                       (_now(), row["id"]))
            project = self._project(db, row["project_id"])
            try:
                if project["tenant_id"] != row["tenant_id"]:
                    raise StateConflict("tenant boundary changed")
                if project["revision"] != row["expected_revision"]:
                    raise StateConflict("project changed since ingest was queued")
                state = json.loads(project["state_json"])
                packet = json.loads(row["packet_json"])
                graph = SemanticGraph(_MemoryStore(state))
                review = graph.preview_packet(row["project_id"], packet)
                if review["packet_digest"] != row["packet_hash"]:
                    raise StateConflict("queued packet digest mismatch")
                receipt = graph.ingest_packet(row["project_id"], packet)
                committed = graph.store.load()
                db.execute("UPDATE projects SET state_json=?,revision=revision+1 WHERE id=?",
                           (json.dumps(committed, ensure_ascii=False), row["project_id"]))
                db.execute(
                    "UPDATE ingest_jobs SET status='succeeded',result_json=?,finished_at=? WHERE id=?",
                    (json.dumps({"receipt_id": receipt["id"], "revision": project["revision"]+1}),
                     _now(), row["id"]),
                )
                self._audit(db, row["tenant_id"], row["project_id"], row["submitted_by"],
                            "ingest_committed", {"job_id": row["id"], "receipt_id": receipt["id"]})
                status = "succeeded"
            except (ValueError, KeyError, StateConflict) as exc:
                db.execute("UPDATE ingest_jobs SET status='failed',error=?,finished_at=? WHERE id=?",
                           (str(exc)[:500], _now(), row["id"]))
                self._audit(db, row["tenant_id"], row["project_id"], row["submitted_by"],
                            "ingest_failed", {"job_id": row["id"], "reason": str(exc)[:200]})
                status = "failed"
        return {"job_id": row["id"], "status": status}

    def audit_events(self, user_id: str, project_id: str) -> list[dict[str, Any]]:
        with self._connection() as db:
            row = self._project(db, project_id)
            self._require(db, user_id, row["tenant_id"], {"owner", "editor"})
            records = db.execute("SELECT action,details_json,created_at FROM audit_events "
                                 "WHERE project_id=? ORDER BY created_at,id", (project_id,)).fetchall()
        return [{"action": r["action"], "details": json.loads(r["details_json"]),
                 "created_at": r["created_at"]} for r in records]
