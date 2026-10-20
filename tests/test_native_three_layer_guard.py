"""Status-transition safety and native bidirectional three-layer read path."""
from __future__ import annotations
import copy
import json
import tempfile
import unittest
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from pathlib import Path

from cite_refinery.app import CiteRefinery
from cite_refinery.semantic import SemanticGraph
from cite_refinery.layered_cli import main
from cite_refinery.three_layer_native_ingest import as_packet

ROOT=Path(__file__).resolve().parents[1] / "research_materials/opportunity_atlas"

def atlas():
    return json.loads((ROOT/"three_layer_unified_atlas.json").read_text(encoding="utf-8"))

class NativeGuardAndTraversalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=CiteRefinery(self.tmp.name)
        self.project=self.app.init_project("Source-mapping review","Research candidate mapping, no product validation")
        self.graph=SemanticGraph(self.app.store)

    def tearDown(self):
        self.tmp.cleanup()

    def nodes_and_candidate(self):
        a=self.graph.add_node(self.project.id,"A documented implementation candidate.",
                              kind="repository",layer="program")
        b=self.graph.add_node(self.project.id,"A practical field requirement.",
                              kind="problem_claim",layer="practical")
        e=self.graph.add_edge(self.project.id,a["id"],"PARTIALLY_ADDRESSES",b["id"],
                              status="candidate",evidence_refs=["https://example.org/candidate"])
        return a,b,e

    def test_direct_repeated_write_cannot_promote_existing_edge(self):
        a,b,e=self.nodes_and_candidate()
        before=copy.deepcopy(self.app.store.load())
        with self.assertRaisesRegex(ValueError,"requires a reviewed packet"):
            self.graph.add_edge(self.project.id,a["id"],"PARTIALLY_ADDRESSES",
                                b["id"],status="qualified")
        self.assertEqual(before,self.app.store.load())
        same=self.graph.add_edge(self.project.id,a["id"],"PARTIALLY_ADDRESSES",
                                 b["id"],status="candidate")
        self.assertEqual(same["id"],e["id"])
        with self.assertRaisesRegex(ValueError,"requires a reviewed packet"):
            self.graph.add_edge(self.project.id,a["id"],"PARTIALLY_ADDRESSES",
                                b["id"],status="asserted")

    def test_packet_transition_requires_exact_preview_and_rationale(self):
        a,b,e=self.nodes_and_candidate()
        packet={
            "schema":"cite_refinery.semantic_graph.v1",
            "source_system":"explicit_manual_review",
            "clusters":[],
            "nodes":[],
            "edges":[{"source":a["id"],"target":b["id"],
                      "relation":"PARTIALLY_ADDRESSES","status":"qualified",
                      "evidence_refs":["https://example.org/manual-report"]}],
        }
        before=copy.deepcopy(self.app.store.load())
        preview=self.graph.preview_packet(self.project.id,packet)
        self.assertTrue(preview["status_change_requires_explicit_approval"])
        changes=preview["changed_existing_edge_statuses"]
        self.assertEqual(changes,[{"edge_id":e["id"],"from":"candidate","to":"qualified"}])
        self.assertEqual(self.app.store.load(),before)
        with self.assertRaisesRegex(ValueError,"exact approved_status_changes"):
            self.graph.ingest_packet(self.project.id,packet,
                expected_state_digest=preview["state_digest"])
        with self.assertRaisesRegex(ValueError,"exact approved_status_changes"):
            self.graph.ingest_packet(self.project.id,packet,
                expected_state_digest=preview["state_digest"],
                approved_status_changes=changes,approval_reason="short")
        self.assertEqual(self.app.store.load(),before)
        receipt=self.graph.ingest_packet(self.project.id,packet,
            expected_state_digest=preview["state_digest"],
            approved_status_changes=changes,
            approval_reason="I inspected the original source and approve changing this exact relation.")
        self.assertEqual(receipt["status_transition_review"]["changes"],changes)
        self.assertEqual(receipt["status_transition_review"]["reviewed_state_digest"],
                         preview["state_digest"])
        updated=self.app.store.load()["semantic_edges"][e["id"]]
        self.assertEqual(updated["status"],"qualified")
        self.assertEqual(updated["evidence_refs"],
                         ["https://example.org/candidate","https://example.org/manual-report"])
        self.assertTrue(receipt["status_transition_review"]["rationale"])

    def test_stale_preview_cannot_approve_transition(self):
        a,b,e=self.nodes_and_candidate()
        packet={"schema":"cite_refinery.semantic_graph.v1","source_system":"manual",
                "clusters":[],"nodes":[],"edges":[{"source":a["id"],"target":b["id"],
                "relation":"PARTIALLY_ADDRESSES","status":"qualified"}]}
        preview=self.graph.preview_packet(self.project.id,packet)
        self.graph.add_node(self.project.id,"Another unrelated field note",
                            layer="practical",kind="observation")
        before=self.app.store.load()
        with self.assertRaisesRegex(ValueError,"changed after review"):
            self.graph.ingest_packet(self.project.id,packet,
                expected_state_digest=preview["state_digest"],
                approved_status_changes=preview["changed_existing_edge_statuses"],
                approval_reason="Previously approved but workspace advanced after preview.")
        self.assertEqual(self.app.store.load(),before)

    def test_packet_converter_only_candidates_and_precise_layers(self):
        source=atlas()
        packet=as_packet(source,self.project.id)
        self.assertEqual(packet["schema"],"cite_refinery.semantic_graph.v1")
        self.assertEqual(len(packet["nodes"]),50)
        self.assertEqual(len(packet["edges"]),len(source["edges"]))
        self.assertEqual({n["layer"] for n in packet["nodes"]},
                         {"practical","academic","program"})
        self.assertTrue(all("source_lead_only" in n["tags"] for n in packet["nodes"]))
        self.assertTrue(all(e["status"] in {"candidate","not_established"}
                            for e in packet["edges"]))
        self.assertEqual(packet["conversion_metadata"]["commercial_revenue_verified"],0)
        fake=copy.deepcopy(source)
        fake["nodes"][0]["verified_commercial_value"]=True
        with self.assertRaisesRegex(ValueError,"promoted"):
            as_packet(fake,self.project.id)

    def test_native_review_apply_and_reverse_navigation(self):
        packet=as_packet(atlas(),self.project.id)
        empty=copy.deepcopy(self.app.store.load())
        preview=self.graph.preview_packet(self.project.id,packet)
        self.assertEqual(self.app.store.load(),empty)
        self.assertEqual(preview["projected_new_records"]["semantic_nodes"],50)
        self.assertEqual(preview["projected_new_records"]["semantic_edges"],len(packet["edges"]))
        receipt=self.graph.ingest_packet(self.project.id,packet,
                                         expected_state_digest=preview["state_digest"])
        self.assertEqual(len(receipt["node_ids"]),50)
        self.assertEqual(receipt["id"],self.graph.ingest_packet(self.project.id,packet)["id"])
        state=self.app.store.load()
        by_key={n["external_key"].split(":",1)[1]:n["id"]
                for n in state["semantic_nodes"].values() if
                n["project_id"]==self.project.id and
                n.get("external_key","").startswith("three_layer_atlas_candidate_import_v1:")}
        root=by_key["problem:battery_recycling_economics"]
        repo=by_key["github:lingrany/EverBatt-LFP-Recycling-Analysis"]
        forward=self.graph.investigate_three_layers(self.project.id,root,max_depth=2)
        backward=self.graph.investigate_three_layers(self.project.id,repo,max_depth=2)
        self.assertEqual(set(forward["three_layers"]),{"practical","academic","implementation"})
        self.assertTrue(all(forward["coverage"].values()))
        self.assertIn(root,{n["id"] for n in backward["three_layers"]["practical"]})
        self.assertIn(repo,{n["id"] for n in forward["three_layers"]["implementation"]})
        self.assertTrue(all(e["status"]=="candidate" for e in forward["edges"]))
        self.assertFalse(forward["truncated"])
        self.assertIn("NOT inferred",forward["boundary"])

        # Project isolation: nothing about another project is leaked.
        other=self.app.init_project("Other project","No related evidence")
        with self.assertRaisesRegex(ValueError,"does not belong"):
            self.graph.investigate_three_layers(other.id,root)

    def test_assessment_excludes_unreviewed_and_non_established_paths(self):
        a,b,e=self.nodes_and_candidate()
        c=self.graph.add_node(self.project.id,"Independent research method",
                              kind="mechanism",layer="academic")
        self.graph.add_edge(self.project.id,b["id"],"EXPLAINED_BY_CANDIDATE",
                            c["id"],status="asserted")
        extra=self.graph.add_node(self.project.id,"Not applicable implementation",
                                  kind="repository",layer="program")
        self.graph.add_edge(self.project.id,extra["id"],"LIKELY_WRONG_FIT",
                            b["id"],status="not_established")
        x=self.graph.investigate_three_layers(self.project.id,a["id"],max_depth=3)
        self.assertEqual(x["coverage"],{"practical":True,"academic":False,
                                        "implementation":True})
        self.assertTrue(any(e["status"]=="asserted" for e in x["blocked_unreviewed_edges"]))
        self.assertTrue(any(e["status"]=="not_established" for e in x["blocked_unreviewed_edges"]))
        self.assertNotIn(extra["id"],{n["id"] for n in x["three_layers"]["implementation"]})
        with self.assertRaisesRegex(ValueError,"depth"):
            self.graph.investigate_three_layers(self.project.id,a["id"],max_depth=9)

    def test_graph_review_cli_requires_explicit_transition_acknowledgment(self):
        a,b,e=self.nodes_and_candidate()
        packet={"schema":"cite_refinery.semantic_graph.v1",
                "source_system":"human_reviewed_manual_change",
                "clusters":[],"nodes":[],
                "edges":[{"source":a["id"],"target":b["id"],
                          "relation":"PARTIALLY_ADDRESSES","status":"qualified"}]}
        path=Path(self.tmp.name)/"change_packet.json"
        path.write_text(json.dumps(packet),encoding="utf-8")
        args=["graph-review","--workspace",self.tmp.name,
              self.project.id,"--input",str(path)]
        preview_out=StringIO()
        with redirect_stdout(preview_out):
            self.assertEqual(main(args),0)
        review=json.loads(preview_out.getvalue())
        self.assertTrue(review["status_change_requires_explicit_approval"])
        approval=["--apply","--expected-state-digest",review["state_digest"],
                  "--expected-packet-digest",review["packet_digest"]]
        err=StringIO()
        with redirect_stderr(err):
            self.assertEqual(main(args+approval),2)
        self.assertIn("approval",err.getvalue())
        self.assertEqual(self.app.store.load()["semantic_edges"][e["id"]]["status"],"candidate")
        applied=StringIO()
        with redirect_stdout(applied):
            self.assertEqual(main(args+approval+["--approve-status-changes",
                "--approval-reason","Read original source and explicitly authorize the exact status transition."]),0)
        self.assertEqual(json.loads(applied.getvalue())["action"],"applied")
        self.assertEqual(self.app.store.load()["semantic_edges"][e["id"]]["status"],"qualified")

    def test_cli_investigate_reads_same_native_graph(self):
        packet=as_packet(atlas(),self.project.id)
        self.graph.ingest_packet(self.project.id,packet)
        one=next(n for n in self.app.store.load()["semantic_nodes"].values()
                 if n.get("external_key")=="three_layer_atlas_candidate_import_v1:problem:battery_recycling_economics")
        out=StringIO()
        with redirect_stdout(out):
            code=main(["graph-investigate","--workspace",self.tmp.name,
                       self.project.id,one["id"],"--depth","2"])
        self.assertEqual(code,0)
        doc=json.loads(out.getvalue())
        self.assertTrue(doc["coverage"]["academic"])
        self.assertTrue(doc["coverage"]["implementation"])
        self.assertEqual(doc["root_id"],one["id"])

    def test_native_packet_attaches_semantic_and_functional_diagnostics_without_promotion(self):
        sem_review=json.loads((ROOT/"academic_semantic_review_queue.json").read_text(encoding="utf-8"))
        func_overlay=json.loads((ROOT/"functional_three_layer_overlay.json").read_text(encoding="utf-8"))
        packet=as_packet(atlas(),self.project.id,semantic_review=sem_review,functional_overlay=func_overlay)
        self.assertEqual(packet["conversion_metadata"]["semantic_reviews_attached"],8)
        self.assertEqual(packet["conversion_metadata"]["functional_trials_attached"],3)
        self.assertEqual(packet["conversion_metadata"]["reproduced_component_defects"],3)
        self.assertTrue(all(e["status"] in {"candidate","not_established"} for e in packet["edges"]))
        preview=self.graph.preview_packet(self.project.id,packet)
        self.graph.ingest_packet(self.project.id,packet,expected_state_digest=preview["state_digest"])
        state=self.app.store.load()
        by_key={n["external_key"].split(":",1)[1]:n["id"]
                for n in state["semantic_nodes"].values()
                if n["project_id"]==self.project.id and
                n.get("external_key","").startswith("three_layer_atlas_candidate_import_v1:")}
        root=by_key["problem:battery_recycling_economics"]
        inv=self.graph.investigate_three_layers(self.project.id,root,max_depth=2)
        self.assertEqual(inv["evidence_diagnostics"]["semantic_reviews_in_subgraph"],1)
        self.assertEqual(inv["evidence_diagnostics"]["functional_trials_in_subgraph"],1)
        self.assertEqual(inv["evidence_diagnostics"]["reproduced_component_defects_in_subgraph"],1)
        acad_node=inv["three_layers"]["academic"][0]
        impl_node=inv["three_layers"]["implementation"][0]
        self.assertIn("semantic_entailment_review",acad_node)
        self.assertIn("functional_component_trial",impl_node)
        self.assertTrue(impl_node["functional_component_trial"]["reproducible_component_defect_detected"])

    def test_three_layer_ingest_cli_previews_and_applies_with_digests(self):
        atlas_path=ROOT/"three_layer_unified_atlas.json"
        sem_path=ROOT/"academic_semantic_review_queue.json"
        func_path=ROOT/"functional_three_layer_overlay.json"
        preview_out=StringIO()
        with redirect_stdout(preview_out):
            rc=main(["three-layer-ingest","--workspace",self.tmp.name,self.project.id,
                     "--atlas",str(atlas_path),"--semantic-review",str(sem_path),
                     "--functional-overlay",str(func_path)])
        self.assertEqual(rc,0)
        preview=json.loads(preview_out.getvalue())
        self.assertEqual(preview["action"],"preview_only")
        apply_out=StringIO()
        with redirect_stdout(apply_out):
            rc2=main(["three-layer-ingest","--workspace",self.tmp.name,self.project.id,
                      "--atlas",str(atlas_path),"--semantic-review",str(sem_path),
                      "--functional-overlay",str(func_path),"--apply",
                      "--expected-state-digest",preview["state_digest"],
                      "--expected-packet-digest",preview["packet_digest"]])
        self.assertEqual(rc2,0)
        applied=json.loads(apply_out.getvalue())
        self.assertEqual(applied["action"],"applied")
        self.assertEqual(len(applied["receipt"]["node_ids"]),50)

if __name__=="__main__":
    unittest.main()
