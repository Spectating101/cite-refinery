"""Snapshot-and-compare: access controls, immutability, provenance and no false uplift."""
import copy
import io
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cite_refinery.capability_evolution import compare_states
from cite_refinery.capability_evolution_cli import main
from cite_refinery.hosted_store import (
    WorkspaceDB, PermissionDenied, NotFound, StateConflict,
)
from cite_refinery.hosted_api import create_private_app
from fastapi.testclient import TestClient


def packet_one():
    return {
        "schema": "cite_refinery.semantic_graph.v1",
        "source_system": "refinery",
        "clusters": [{"key": "security", "title": "Sensitive data in LLM pipelines"}],
        "nodes": [
            {"key": "capability", "layer": "program", "kind": "capability",
             "statement": "Redact narrow recognized patterns",
             "clusters": ["security"],
             "provenance": {"capability_key": "cap:redact-patterns",
                            "execution_ready": False}},
            {"key": "implementation", "layer": "program", "kind": "implementation",
             "statement": "Versioned basic redaction implementation",
             "clusters": ["security"],
             "provenance": {"upstream_repository": "owner/redactor",
                            "upstream_revision": "a"*40,
                            "implementation_key": "impl:patterns"}},
        ],
        "edges": [{
            "source": "implementation", "target": "capability",
            "relation": "IMPLEMENTS", "status": "candidate",
            "provenance": {"review_state": "unreviewed"},
        }],
    }


def packet_two():
    return {
        "schema": "cite_refinery.semantic_graph.v1",
        "source_system": "refinery",
        "clusters": [{"key": "security", "title": "Sensitive data in LLM pipelines"}],
        "nodes": [
            {"key": "capability", "layer": "program", "kind": "capability",
             "statement": "Redact narrow recognized patterns",
             "clusters": ["security"],
             "source_refs": ["https://example.org/refinery/verified"],
             "provenance": {"capability_key": "cap:redact-patterns",
                            "execution_ready": False,
                            "source_note": "Version 2 source receipt"}},
            {"key": "implementation", "layer": "program", "kind": "implementation",
             "statement": "Versioned basic redaction implementation",
             "clusters": ["security"],
             "provenance": {"upstream_repository": "owner/redactor",
                            "upstream_revision": "a"*40,
                            "implementation_key": "impl:patterns"}},
            {"key": "new_version", "layer": "program", "kind": "implementation",
             "statement": "Another version of basic redaction implementation",
             "clusters": ["security"],
             "provenance": {"upstream_repository": "owner/redactor",
                            "upstream_revision": "a"*40,
                            "implementation_key": "impl:patterns"}},
            {"key": "limitations", "layer": "program", "kind": "limitation",
             "statement": "Names and split secrets remain outside documented scope",
             "clusters": ["security"],
             "source_refs": ["https://example.org/refinery/limitations"],
             "provenance": {"limitation_probe_leaks": 4, "execution_ready": False}},
        ],
        "edges": [{
            "source": "implementation", "target": "capability",
            "relation": "IMPLEMENTS", "status": "qualified",
            "provenance": {"review_state": "source_record_qualified"},
        }],
    }


class CapabilityEvolutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dbpath = Path(self.tmp.name) / "private.sqlite3"
        self.db = WorkspaceDB(self.dbpath)
        tenant = self.db.create_tenant("North Lab", "owner")
        self.user = tenant["owner_user_id"]
        self.tenant = tenant["tenant_id"]
        self.token = self.db.issue_token(self.user)
        self.viewer = self.db.add_user("reader")
        self.db.grant_membership(self.user, self.tenant, self.viewer, "viewer")
        self.viewer_token = self.db.issue_token(self.viewer)
        self.project = self.db.create_project(
            self.user, self.tenant, "Privacy project", "A specific practical problem")
        other = self.db.create_tenant("South Lab", "other-owner")
        self.other_user = other["owner_user_id"]
        self.other_token = self.db.issue_token(self.other_user)
        self.other_project = self.db.create_project(
            self.other_user, other["tenant_id"], "Other", "No shared rights")

    def tearDown(self):
        self.tmp.cleanup()

    def ingest(self, packet, project=None, user=None):
        user = user or self.user
        project = project or self.project
        review = self.db.preview(user, project, packet)
        self.db.enqueue(user, project, packet,
                        review["project_revision"], review["packet_digest"])
        result = self.db.run_one_job()
        self.assertEqual(result["status"], "succeeded")
        return review

    def test_snapshot_history_reports_evidence_not_performance(self):
        first = self.db.capture_snapshot(
            self.user, self.project, "Empty problem baseline", 0)
        self.ingest(packet_one())
        middle = self.db.capture_snapshot(
            self.user, self.project, "Recorded initial program evidence", 1)
        self.ingest(packet_two())
        last = self.db.capture_snapshot(
            self.user, self.project, "Additional qualified source evidence", 2)
        report = self.db.compare_snapshots(
            self.user, self.project, middle["id"], last["id"])
        self.assertEqual(report["record_delta"]["semantic_nodes"]["added"], 2)
        self.assertGreaterEqual(report["record_delta"]["semantic_nodes"]["revised_existing"], 1)
        self.assertEqual(report["new_node_layers"], {"program": 2})
        self.assertEqual(report["new_node_kinds"], {"implementation": 1, "limitation": 1})
        self.assertEqual(len(report["edge_status_transitions"]), 1)
        self.assertEqual(report["edge_status_transitions"][0]["old_status"], "candidate")
        self.assertEqual(report["edge_status_transitions"][0]["new_status"], "qualified")
        self.assertEqual(report["new_candidate_or_unresolved_edges"], 0)
        self.assertIsNone(report["interpretation"]["performance_improvement_estimate"])
        self.assertIsNone(report["interpretation"]["production_readiness_estimate"])
        self.assertEqual(report["interpretation"]["comparability"], "not_established")
        self.assertTrue(any(group["source_identity"] == "refinery-implementation:impl:patterns"
                            for group in report["same_source_identity_groups"]))
        early = self.db.compare_snapshots(self.user,self.project, first["id"],middle["id"])
        self.assertEqual(early["record_delta"]["semantic_nodes"]["added"], 2)
        self.assertTrue(
            self.db.list_snapshots(self.viewer, self.project)[2]["id"] == last["id"])

    def test_access_revision_and_same_project_boundaries(self):
        with self.assertRaises(PermissionDenied):
            self.db.capture_snapshot(self.viewer, self.project, "Viewer may not snapshot", 0)
        with self.assertRaises(PermissionDenied):
            self.db.capture_snapshot(self.other_user, self.project, "Other tenant snapshot", 0)
        with self.assertRaises(PermissionDenied):
            self.db.list_snapshots(self.other_user, self.project)
        snap = self.db.capture_snapshot(self.user,self.project,"First baseline capture",0)
        with self.assertRaises(StateConflict):
            self.db.capture_snapshot(self.user,self.project,"Duplicate revision",0)
        with self.assertRaises(StateConflict):
            self.db.capture_snapshot(self.user,self.project,"Stale revision now",1)
        foreign = self.db.capture_snapshot(
            self.other_user,self.other_project,"Other research baseline",0)
        with self.assertRaises(NotFound):
            self.db.compare_snapshots(self.user,self.project,snap["id"],foreign["id"])
        with self.assertRaises(NotFound):
            self.db.compare_snapshots(self.user,self.project,snap["id"],snap["id"])
        self.assertEqual(len(self.db.list_snapshots(self.user,self.project)),1)

    def test_tampering_is_detected_without_overwriting(self):
        original = self.db.capture_snapshot(self.user,self.project,"Baseline state v0",0)
        self.ingest(packet_one())
        newer = self.db.capture_snapshot(self.user,self.project,"Program state v1",1)
        with sqlite3.connect(self.dbpath) as db:
            db.execute("UPDATE project_snapshots SET state_json='{}' WHERE id=?",
                       (original["id"],))
            db.commit()
        with self.assertRaises(StateConflict):
            self.db.compare_snapshots(self.user,self.project, original["id"],newer["id"])
        self.assertEqual(len(self.db.project_state(self.user,self.project)["semantic_nodes"]),2)

    def test_manual_retractions_are_not_silent_quality_decline(self):
        source={"projects":{"p":{"id":"p"}},
                "semantic_nodes":{"n":{"id":"n","project_id":"p","layer":"program"}},
                "semantic_clusters":{},"semantic_edges":{},"semantic_packets":{}}
        target=copy.deepcopy(source)
        target["semantic_nodes"].clear()
        with self.assertRaisesRegex(ValueError,"retraction"):
            compare_states(source,target,"p",
                           old_revision=1,new_revision=2,
                           old_capture="s:1",new_capture="s:2")

    def test_private_api_and_cli_auth(self):
        api = TestClient(create_private_app(str(self.dbpath)))
        a={"Authorization":"Bearer "+self.token}
        viewer={"Authorization":"Bearer "+self.viewer_token}
        outsider={"Authorization":"Bearer "+self.other_token}
        url=f"/api/projects/{self.project}/evolution/snapshots"
        self.assertEqual(api.post(url,json={"label":"Not authorized snapshot","expected_revision":0},
                                  headers=viewer).status_code,403)
        first=api.post(url,json={"label":"Initial saved checkpoint","expected_revision":0},
                       headers=a)
        self.assertEqual(first.status_code,201)
        sid=first.json()["id"]
        self.assertEqual(api.get(url,headers=outsider).status_code,403)
        self.ingest(packet_one())
        second=api.post(url,json={"label":"After source-backed ingestion","expected_revision":1},
                        headers=a)
        self.assertEqual(second.status_code,201)
        to=second.json()["id"]
        response=api.get(f"/api/projects/{self.project}/evolution/compare",
                         params={"from_snapshot":sid,"to_snapshot":to},headers=viewer)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()["record_delta"]["semantic_nodes"]["added"],2)
        self.assertEqual(api.get(
            f"/api/projects/{self.project}/evolution/compare",
            params={"from_snapshot":to,"to_snapshot":sid},headers=a).status_code,422)
        with patch.dict(os.environ,{"CITE_REFINERY_TOKEN":self.token}):
            out=io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["--db",str(self.dbpath),"--project",self.project,"list"]),0)
            self.assertEqual(len(json.loads(out.getvalue())),2)
            out=io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["--db",str(self.dbpath),"--project",self.project,
                                       "compare","--from-snapshot",sid,"--to-snapshot",to]),0)
            self.assertIn("not_established",out.getvalue())
        with patch.dict(os.environ,{"CITE_REFINERY_TOKEN":"invalid"}):
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(["--db",str(self.dbpath),"--project",self.project,"list"]),2)


if __name__=="__main__":
    unittest.main()
