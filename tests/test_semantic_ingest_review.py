"""Local semantic import must be full-packet atomic and reviewable."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

from cite_refinery import CiteRefinery, SemanticGraph
from cite_refinery.layered_cli import main

def packet():
    return {
        "schema":"cite_refinery.semantic_graph.v1",
        "source_system":"nocturnal",
        "clusters":[{"key":"root","title":"Auditable module"}],
        "nodes":[
            {"key":"p","statement":"Observed environmental change","layer":"practical","kind":"observation","clusters":["root"]},
            {"key":"a","statement":"Measurement method","layer":"academic","kind":"method","clusters":["root"]}
        ],
        "edges":[{"source":"p","target":"a","relation":"MEASURED_BY","status":"qualified"}]
    }

class SemanticIngestReviewTests(unittest.TestCase):
    def test_failing_late_edge_does_not_mutate_persistent_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=CiteRefinery(tmp)
            project=app.init_project("Test","Atomic import")
            graph=SemanticGraph(app.store)
            before=copy.deepcopy(app.store.load())
            bad=packet()
            bad["edges"].append({"source":"p","target":"nonexistent","relation":"IMPLEMENTS"})
            with self.assertRaisesRegex(ValueError,"unknown semantic"):
                graph.ingest_packet(project.id,bad)
            self.assertEqual(app.store.load(),before)
            with self.assertRaisesRegex(ValueError,"unknown semantic"):
                graph.preview_packet(project.id,bad)
            self.assertEqual(app.store.load(),before)

    def test_preview_commit_idempotence_and_stale_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=CiteRefinery(tmp)
            project=app.init_project("Test","Review import")
            graph=SemanticGraph(app.store)
            before=copy.deepcopy(app.store.load())
            report=graph.preview_packet(project.id,packet(),packet_ref="nocturnal/output.json")
            self.assertEqual(report["projected_new_records"]["semantic_nodes"],2)
            self.assertEqual(report["projected_new_records"]["semantic_edges"],1)
            self.assertFalse(report["already_imported"])
            self.assertEqual(app.store.load(),before)
            receipt=graph.ingest_packet(project.id,packet(),packet_ref="nocturnal/output.json",expected_state_digest=report["state_digest"])
            self.assertTrue(receipt["id"].startswith("sgpacket:"))
            state=copy.deepcopy(app.store.load())
            report2=graph.preview_packet(project.id,packet(),packet_ref="nocturnal/output.json")
            self.assertTrue(report2["already_imported"])
            self.assertEqual(report2["projected_new_records"]["semantic_edges"],0)
            self.assertEqual(graph.ingest_packet(project.id,packet())["id"],receipt["id"])
            self.assertEqual(app.store.load(),state)
            with self.assertRaisesRegex(ValueError,"changed after review"):
                graph.ingest_packet(project.id,packet(),expected_state_digest=report["state_digest"])
            self.assertEqual(app.store.load(),state)

    def test_receipts_are_scoped_by_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=CiteRefinery(tmp)
            first=app.init_project("First","One")
            second=app.init_project("Second","Two")
            graph=SemanticGraph(app.store)
            a=graph.ingest_packet(first.id,packet())
            b=graph.ingest_packet(second.id,packet())
            self.assertNotEqual(a["id"],b["id"])
            self.assertEqual(b["project_id"],second.id)
            self.assertEqual(len(app.store.load()["semantic_packets"]),2)

    def test_cli_review_requires_both_digests_for_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=CiteRefinery(tmp)
            project=app.init_project("CLI","Review")
            path=Path(tmp)/"packet.json"
            path.write_text(json.dumps(packet()),encoding="utf-8")
            args=["graph-review","--workspace",tmp,project.id,"--input",str(path)]
            output=StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(args),0)
            preview=json.loads(output.getvalue())
            self.assertEqual(preview["action"],"preview_only")
            self.assertEqual(len(app.store.load()["semantic_nodes"]),0)
            err=StringIO()
            with redirect_stderr(err):
                self.assertEqual(main(args+["--apply"]),2)
            self.assertIn("requires both",err.getvalue())
            with redirect_stdout(StringIO()):
                self.assertEqual(main(args+["--apply","--expected-state-digest",preview["state_digest"],"--expected-packet-digest",preview["packet_digest"]]),0)
            self.assertEqual(len(app.store.load()["semantic_nodes"]),2)

    def test_source_authority_mismatch_is_visible_before_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=CiteRefinery(tmp)
            project=app.init_project("Authority","Review")
            graph=SemanticGraph(app.store)
            report=graph.preview_packet(project.id,packet())
            self.assertEqual(report["declared_node_layers"], {"academic":1, "practical":1})
            self.assertEqual(len(report["authority_boundary_warnings"]),1)
            self.assertIn("academic",report["authority_boundary_warnings"][0])
            self.assertEqual(len(app.store.load()["semantic_nodes"]),0)

    def test_status_upgrade_is_disclosed_before_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=CiteRefinery(tmp)
            project=app.init_project("Authority","Review")
            graph=SemanticGraph(app.store)
            first=packet()
            graph.ingest_packet(project.id,first)
            second=packet()
            second["edges"][0]["status"]="asserted"
            preview=graph.preview_packet(project.id,second)
            self.assertEqual(len(preview["changed_existing_edge_statuses"]),1)
            self.assertEqual(preview["changed_existing_edge_statuses"][0]["from"],"qualified")
            self.assertEqual(preview["changed_existing_edge_statuses"][0]["to"],"asserted")
            self.assertTrue(any("status" in text for text in preview["authority_boundary_warnings"]))
            self.assertEqual(next(iter(app.store.load()["semantic_edges"].values()))["status"],"qualified")

    def test_changed_packet_rejected_by_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            app=CiteRefinery(tmp)
            project=app.init_project("CLI","Review")
            path=Path(tmp)/"packet.json"
            path.write_text(json.dumps(packet()),encoding="utf-8")
            args=["graph-review","--workspace",tmp,project.id,"--input",str(path)]
            output=StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(args),0)
            preview=json.loads(output.getvalue())
            changed=packet()
            changed["edges"][0]["status"]="asserted"
            path.write_text(json.dumps(changed),encoding="utf-8")
            with redirect_stderr(StringIO()):
                self.assertEqual(main(args+["--apply","--expected-state-digest",preview["state_digest"],"--expected-packet-digest",preview["packet_digest"]]),2)
            self.assertEqual(len(app.store.load()["semantic_edges"]),0)

if __name__=="__main__":
    unittest.main()
