"""Module-local temporal diffs and private browser shell authorization."""
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from cite_refinery.hosted_api import create_private_app
from cite_refinery.hosted_store import WorkspaceDB
from test_capability_evolution import packet_one, packet_two


class PrivateEvolutionUITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "private.sqlite3"
        self.db = WorkspaceDB(self.path)
        tenant = self.db.create_tenant("Research", "owner")
        self.uid = tenant["owner_user_id"]
        self.token = self.db.issue_token(self.uid)
        self.other = self.db.create_tenant("Other", "separate-owner")["owner_user_id"]
        self.foreign = self.db.issue_token(self.other)
        self.project = self.db.create_project(
            self.uid, tenant["tenant_id"], "Privacy cases", "One semantic module")
        self.api = TestClient(create_private_app(str(self.path)))
        self.auth = {"Authorization": "Bearer " + self.token}

    def tearDown(self):
        self.tmp.cleanup()

    def ingest(self, p):
        r=self.db.preview(self.uid, self.project, p)
        self.db.enqueue(
            self.uid, self.project, p, r["project_revision"], r["packet_digest"],
            approved_status_changes=r["changed_existing_edge_statuses"] or None,
            approval_reason=("Owner reviewed the exact source changes and approved this status transition."
                             if r["changed_existing_edge_statuses"] else None),
        )
        self.assertEqual(self.db.run_one_job()["status"],"succeeded")

    def test_private_shell_no_embedded_research_token_or_unprotected_api(self):
        response=self.api.get("/private/evolution")
        self.assertEqual(response.status_code,200)
        self.assertIn("text/html",response.headers["content-type"])
        self.assertIn("connect-src 'self'",response.headers["content-security-policy"])
        self.assertIn("script-src 'self'",response.headers["content-security-policy"])
        self.assertEqual(response.headers["cache-control"],"no-store")
        self.assertNotIn(self.token,response.text)
        self.assertNotIn(self.project,response.text)
        self.assertNotIn("localStorage",response.text)
        js=self.api.get("/private/evolution/app.js")
        self.assertEqual(js.status_code,200)
        self.assertIn("text/javascript",js.headers["content-type"])
        self.assertIn("app.token",js.text)
        self.assertNotIn("localStorage",js.text)
        self.assertNotIn("sessionStorage",js.text)
        self.assertNotIn("Authorization': 'Bearer",js.text)
        css=self.api.get("/private/evolution/app.css")
        self.assertEqual(css.status_code,200)
        self.assertIn("text/css",css.headers["content-type"])
        self.assertEqual(self.api.get("/api/projects").status_code,401)
        self.assertEqual(self.api.get(f"/api/projects/{self.project}/evolution/snapshots").status_code,401)

    def test_module_local_evidence_and_candidate_transition(self):
        old=self.db.capture_snapshot(self.uid,self.project,"Empty baseline graph",0)
        self.ingest(packet_one())
        middle=self.db.capture_snapshot(self.uid,self.project,"Initial evidence version",1)
        self.ingest(packet_two())
        last=self.db.capture_snapshot(self.uid,self.project,"New source evidence version",2)
        outcome=self.api.get(
            f"/api/projects/{self.project}/evolution/compare",
            headers=self.auth,
            params={"from_snapshot":middle["id"],"to_snapshot":last["id"]})
        self.assertEqual(outcome.status_code,200)
        result=outcome.json()
        self.assertEqual(result["module_changes"]["count"],1)
        module=result["module_changes"]["items"][0]
        self.assertEqual(module["title"],"Sensitive data in LLM pipelines")
        self.assertEqual(module["changed_node_counts"],{"program":4})
        self.assertEqual(module["new_nodes_total"],2)
        self.assertEqual(module["revised_nodes_total"],2)
        self.assertEqual(module["changed_relations_total"],1)
        self.assertEqual(module["changed_relations_qualified_or_asserted"],1)
        self.assertEqual(module["changed_relations_candidate_or_unresolved"],0)
        self.assertEqual(module["relations"][0]["status"],"qualified")
        self.assertEqual(module["relations"][0]["change"],"revised")
        self.assertEqual(len([n for n in module["nodes"] if n["kind"]=="limitation"]),1)
        limitation=next(n for n in module["nodes"] if n["kind"]=="limitation")
        self.assertIn("https://example.org/refinery/limitations",limitation["source_refs"])
        self.assertIsNone(result["interpretation"]["performance_improvement_estimate"])
        self.assertIsNone(result["interpretation"]["market_adoption_estimate"])
        first=self.api.get(
            f"/api/projects/{self.project}/evolution/compare",
            headers=self.auth,
            params={"from_snapshot":old["id"],"to_snapshot":middle["id"]})
        self.assertEqual(first.status_code,200)
        self.assertEqual(first.json()["module_changes"]["items"][0]["changed_relations_candidate_or_unresolved"],1)
        outsider=self.api.get(
            f"/api/projects/{self.project}/evolution/compare",
            headers={"Authorization":"Bearer "+self.foreign},
            params={"from_snapshot":middle["id"],"to_snapshot":last["id"]})
        self.assertEqual(outsider.status_code,403)


if __name__=="__main__":
    unittest.main()
