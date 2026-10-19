"""Authenticated SQLite backend and queue security integration tests."""
import copy
import os
from contextlib import closing
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from cite_refinery.hosted_api import create_private_app
from cite_refinery.hosted_store import PermissionDenied, WorkspaceDB


def packet():
    return {
        "schema": "cite_refinery.semantic_graph.v1",
        "source_system": "nocturnal",
        "clusters": [{"key": "root", "title": "Population observability"}],
        "nodes": [
            {"key": "p", "statement": "Periodical sightings", "layer": "practical", "clusters": ["root"]},
            {"key": "a", "statement": "Capture-recapture limits", "layer": "academic", "clusters": ["root"]},
            {"key": "s", "statement": "Candidate monitoring tool", "layer": "program", "clusters": ["root"]},
        ],
        "edges": [
            {"source": "p", "relation": "RELATED_TO", "target": "a", "status": "qualified"},
            {"source": "a", "relation": "IMPLEMENTED_BY", "target": "s", "status": "candidate"},
        ],
    }


class PrivateBackendTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / "workspaces.sqlite3")
        self.db = WorkspaceDB(self.path)
        self.tenant = self.db.create_tenant("Applied research", "owner")
        self.tenant2 = self.db.create_tenant("Independent NGO", "independent-owner")
        self.owner = self.tenant["owner_user_id"]
        self.outsider = self.tenant2["owner_user_id"]
        self.viewer = self.db.add_user("viewer")
        self.editor = self.db.add_user("editor")
        self.db.grant_membership(self.owner, self.tenant["tenant_id"], self.viewer, "viewer")
        self.db.grant_membership(self.owner, self.tenant["tenant_id"], self.editor, "editor")
        self.tokens = {
            label: self.db.issue_token(uid)
            for label, uid in [
                ("owner", self.owner), ("viewer", self.viewer),
                ("editor", self.editor), ("outsider", self.outsider)
            ]
        }
        self.project = self.db.create_project(
            self.owner, self.tenant["tenant_id"], "Taiwan free-roaming dog problem",
            "Population observation to intervention")
        self.client = TestClient(create_private_app(self.path))

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def auth(self, name):
        return {"Authorization": "Bearer " + self.tokens[name]}

    def test_token_hashing_revocation_and_expiry(self):
        with closing(sqlite3.connect(self.path)) as conn:
            row = conn.execute("SELECT token_hash FROM access_tokens LIMIT 1").fetchone()
        self.assertNotIn(row[0], self.tokens.values())
        self.assertEqual(len(row[0]), 64)
        self.assertEqual(self.db.authenticate(self.tokens["owner"]), self.owner)
        self.db.revoke_token(self.tokens["viewer"])
        self.assertEqual(self.client.get("/api/projects", headers=self.auth("viewer")).status_code, 401)
        self.assertEqual(self.client.get("/api/projects", headers=self.auth("owner")).status_code, 200)

    def test_no_anonymous_or_cross_tenant_access(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/api/projects").status_code, 401)
        self.assertEqual(self.client.get("/api/projects", headers={"Authorization": "Bearer made-up"}).status_code, 401)
        self.assertEqual(self.client.get("/api/projects/" + self.project, headers=self.auth("outsider")).status_code, 403)
        self.assertEqual(self.client.get("/api/projects/" + self.project + "/atlas", headers=self.auth("outsider")).status_code, 403)
        self.assertEqual(self.client.post("/api/projects/" + self.project + "/ingest/preview", headers=self.auth("outsider"), json={"packet":packet()}).status_code, 403)
        self.assertEqual(self.client.get("/api/projects", headers=self.auth("outsider")).json(), [])

    def test_viewer_can_read_atlas_but_cannot_import(self):
        self.assertEqual(self.client.get("/api/projects/" + self.project + "/atlas", headers=self.auth("viewer")).status_code, 200)
        self.assertEqual(self.client.post("/api/projects/" + self.project + "/ingest/preview", headers=self.auth("viewer"), json={"packet":packet()}).status_code, 403)
        self.assertEqual(self.client.post("/api/projects", headers=self.auth("viewer"), json={"tenant_id":self.tenant["tenant_id"], "title":"X", "problem":"Y"}).status_code, 403)
        self.assertEqual(self.client.get("/api/projects/" + self.project + "/audit", headers=self.auth("viewer")).status_code, 403)

    def test_editor_preview_queue_worker_and_atlas(self):
        headers = self.auth("editor")
        before = copy.deepcopy(self.db.project_state(self.editor, self.project))
        res = self.client.post("/api/projects/" + self.project + "/ingest/preview", headers=headers, json={"packet":packet()})
        self.assertEqual(res.status_code, 200, res.text)
        preview = res.json()
        self.assertEqual(preview["project_revision"], 0)
        self.assertEqual(preview["projected_new_records"]["semantic_nodes"], 3)
        self.assertEqual(preview["projected_new_records"]["semantic_edges"], 2)
        self.assertTrue(preview["authority_boundary_warnings"])
        self.assertEqual(self.db.project_state(self.editor, self.project), before)
        res = self.client.post("/api/projects/" + self.project + "/ingest", headers=headers,
                 json={"packet":packet(), "expected_revision":preview["project_revision"],
                       "expected_packet_digest":preview["packet_digest"]})
        self.assertEqual(res.status_code, 202, res.text)
        job_id = res.json()["job_id"]
        self.assertEqual(self.client.get("/api/jobs/" + job_id, headers=self.auth("outsider")).status_code, 403)
        self.assertEqual(self.client.get("/api/jobs/" + job_id, headers=self.auth("viewer")).status_code, 200)
        self.assertEqual(self.db.run_one_job()["status"], "succeeded")
        self.assertIsNone(self.db.run_one_job())
        self.assertEqual(self.client.get("/api/jobs/" + job_id, headers=headers).json()["status"], "succeeded")
        project = self.client.get("/api/projects/" + self.project, headers=headers).json()
        self.assertEqual(project["atlas"]["summary"]["cluster_count"], 1)
        self.assertEqual(project["atlas"]["layers"], ["practical", "academic", "program"])
        self.assertEqual(len(project["graph_export"]["nodes"]), 3)
        node = next(iter(project["graph_export"]["nodes"]))
        trace = self.client.get(f"/api/projects/{self.project}/nodes/{node}/coverage", headers=headers)
        self.assertEqual(trace.status_code, 200)
        self.assertEqual(trace.json()["trace"]["schema"], "cite_refinery.node_layer_trace.v1")
        self.assertTrue(any(r["action"] == "ingest_committed" for r in self.client.get("/api/projects/" + self.project + "/audit", headers=headers).json()))

    def test_stale_revision_causes_failed_job_without_mutation(self):
        headers = self.auth("owner")
        pre = self.client.post("/api/projects/" + self.project + "/ingest/preview", headers=headers,json={"packet":packet()}).json()
        body = {"packet":packet(), "expected_revision":0, "expected_packet_digest":pre["packet_digest"]}
        first = self.client.post("/api/projects/" + self.project + "/ingest", headers=headers,json=body).json()["job_id"]
        stale = self.client.post("/api/projects/" + self.project + "/ingest", headers=headers,json=body).json()["job_id"]
        self.assertEqual(self.db.run_one_job()["status"], "succeeded")
        self.assertEqual(self.db.run_one_job()["status"], "failed")
        self.assertEqual(self.client.get("/api/jobs/" + stale, headers=headers).json()["status"], "failed")
        self.assertEqual(len(self.db.project_state(self.owner, self.project)["semantic_nodes"]), 3)
        self.assertEqual(self.client.post("/api/projects/" + self.project + "/ingest", headers=headers,json=body).status_code, 409)

    def test_corrupted_late_edge_never_queues_or_commits(self):
        invalid = packet()
        invalid["edges"].append({"source":"missing","target":"p","relation":"SUPPORTS"})
        before = self.db.project_state(self.owner, self.project)
        resp = self.client.post("/api/projects/" + self.project + "/ingest/preview", headers=self.auth("owner"),json={"packet":invalid})
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(self.db.project_state(self.owner, self.project), before)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM ingest_jobs").fetchone()[0], 0)

    def test_absent_user_cannot_create_project_inside_another_tenant(self):
        out = self.client.post("/api/projects", headers=self.auth("outsider"),
             json={"tenant_id":self.tenant["tenant_id"], "title":"Intrusion", "problem":"Unauthorized"})
        self.assertEqual(out.status_code,403)
        self.assertEqual(len(self.db.list_projects(self.outsider)),0)

    def test_database_files_are_private_and_proxy_headers_not_trusted(self):
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)
        res = self.client.get("/api/projects", headers={"X-Forwarded-User":self.owner})
        self.assertEqual(res.status_code, 401)
        body = {"packet":packet()}
        over = self.client.post("/api/projects/" + self.project + "/ingest/preview",
             headers={**self.auth("owner"),"content-length":str(9*1024*1024)},json=body)
        self.assertEqual(over.status_code, 413)

    def test_worker_unexpected_crash_does_not_strand_running_job(self):
        from unittest.mock import patch
        from cite_refinery.semantic import SemanticGraph
        pre=self.db.preview(self.owner,self.project,packet())
        job=self.db.enqueue(self.owner,self.project,packet(),0,pre["packet_digest"])
        with patch.object(SemanticGraph,"ingest_packet",side_effect=RuntimeError("worker aborted")):
            with self.assertRaises(RuntimeError):
                self.db.run_one_job()
        self.assertEqual(self.db.get_job(self.owner,job)["status"],"queued")
        self.assertEqual(self.db.run_one_job()["status"],"succeeded")

    def test_created_project_visibility_is_tenant_scoped(self):
        res = self.client.post("/api/projects",headers=self.auth("editor"),json={"tenant_id":self.tenant["tenant_id"],"title":"Research cluster","problem":"Map a problem"})
        self.assertEqual(res.status_code, 201,res.text)
        new_id = res.json()["id"]
        self.assertIn(new_id,[row["id"] for row in self.client.get("/api/projects",headers=self.auth("viewer")).json()])
        self.assertNotIn(new_id,[row["id"] for row in self.client.get("/api/projects",headers=self.auth("outsider")).json()])

if __name__=="__main__":
    unittest.main()
