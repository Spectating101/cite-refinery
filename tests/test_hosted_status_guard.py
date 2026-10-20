"""SQLite hosted evidence-status changes are owner-approved and durable."""
from __future__ import annotations
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cite_refinery.hosted_store import WorkspaceDB, PermissionDenied, StateConflict
from test_capability_evolution import packet_one,packet_two

class HostedStatusReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"native_status.sqlite3"
        self.db=WorkspaceDB(self.path)
        team=self.db.create_tenant("Owner-reviewed graph","owner1")
        self.owner=team["owner_user_id"]
        self.tenant=team["tenant_id"]
        self.editor=self.db.add_user("graph-editor")
        self.db.grant_membership(self.owner,self.tenant,self.editor,"editor")
        self.project=self.db.create_project(self.owner,self.tenant,"Evidence project",
                                            "No verified intervention or commercial use")
        p=packet_one()
        preview=self.db.preview(self.owner,self.project,p)
        self.db.enqueue(self.owner,self.project,p,
                        preview["project_revision"],preview["packet_digest"])
        self.assertEqual(self.db.run_one_job()["status"],"succeeded")

    def tearDown(self):
        self.tmp.cleanup()

    def test_owner_approval_requires_exact_changes_and_reason(self):
        p=packet_two()
        reviewed=self.db.preview(self.owner,self.project,p)
        changes=reviewed["changed_existing_edge_statuses"]
        self.assertEqual(len(changes),1)
        self.assertEqual(changes[0]["from"],"candidate")
        self.assertEqual(changes[0]["to"],"qualified")
        before=self.db.project_state(self.owner,self.project)
        with self.assertRaisesRegex(StateConflict,"explicit exact"):
            self.db.enqueue(self.owner,self.project,p,
                            reviewed["project_revision"],reviewed["packet_digest"])
        with self.assertRaisesRegex(StateConflict,"explicit exact"):
            self.db.enqueue(self.owner,self.project,p,
                            reviewed["project_revision"],reviewed["packet_digest"],
                            approved_status_changes=changes,approval_reason="short")
        with self.assertRaises(PermissionDenied):
            self.db.enqueue(self.editor,self.project,p,
                            reviewed["project_revision"],reviewed["packet_digest"],
                            approved_status_changes=changes,
                            approval_reason="Detailed review of the exact original source transition.")
        self.assertEqual(self.db.project_state(self.owner,self.project),before)
        job=self.db.enqueue(
            self.owner,self.project,p,reviewed["project_revision"],reviewed["packet_digest"],
            approved_status_changes=changes,
            approval_reason="Owner verified the revised evidence receipt and explicitly approves transition.",
        )
        self.assertEqual(self.db.run_one_job()["status"],"succeeded")
        state=self.db.project_state(self.owner,self.project)
        edge=next(iter(state["semantic_edges"].values()))
        self.assertEqual(edge["status"],"qualified")
        receipt=next(iter(state["semantic_packets"].values()))
        approved=[r for r in state["semantic_packets"].values() if "status_transition_review" in r]
        self.assertEqual(len(approved),1)
        self.assertEqual(approved[0]["status_transition_review"]["changes"],changes)
        audit=self.db.audit_events(self.owner,self.project)
        self.assertTrue(any(ev["action"]=="ingest_committed" for ev in audit))
        self.assertTrue(any(
            ev["action"]=="existing_evidence_status_transition_approved" and
            ev["details"]["reviewer_id"]==self.owner
            for ev in audit))


    def test_worker_rejects_tampered_status_approval(self):
        p=packet_two()
        review=self.db.preview(self.owner,self.project,p)
        job=self.db.enqueue(
            self.owner,self.project,p,review["project_revision"],review["packet_digest"],
            approved_status_changes=review["changed_existing_edge_statuses"],
            approval_reason="Owner has compared original source evidence and requests status change.",
        )
        with sqlite3.connect(self.path) as con:
            con.execute("UPDATE ingest_jobs SET approval_json=? WHERE id=?",
                        (json.dumps({"changes":[],"reviewed_by":self.owner}),job))
            con.commit()
        before=self.db.project_state(self.owner,self.project)
        result=self.db.run_one_job()
        self.assertEqual(result["status"],"failed")
        self.assertEqual(self.db.project_state(self.owner,self.project),before)

    def test_owner_does_not_need_special_approval_for_new_candidates(self):
        own=self.db.project_state(self.owner,self.project)
        p=packet_one()
        duplicate=self.db.preview(self.owner,self.project,p)
        self.assertTrue(duplicate["already_imported"])
        # A fresh initial candidate packet in another project is ordinary.
        p2=self.db.create_project(self.owner,self.tenant,"Second project",
                                  "Independent project scope")
        reviewed=self.db.preview(self.editor,p2,p)
        self.assertEqual(reviewed["changed_existing_edge_statuses"],[])
        self.db.enqueue(self.editor,p2,p,
                        reviewed["project_revision"],reviewed["packet_digest"])
        self.assertEqual(self.db.run_one_job()["status"],"succeeded")

if __name__=="__main__":
    unittest.main()
