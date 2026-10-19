"""Product acceptance oracle for full three-layer prompt-privacy problem case.

Synthetic records test the acceptance gates. The actual source-backed run is
verified separately against the pinned Refinery Git object on Optiplex.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.hosted_store import WorkspaceDB
from scripts.acceptance_prompt_privacy import (
    academic_packet, evaluate_acceptance, REFINERY_PIN, BASELINE,
    CASE_CLUSTER, CASE_TITLE,
)


def synthesized_case():
    receipts = {
        "practical": {
            "refinery_commit": REFINERY_PIN,
            "review_state": "accepted_as_source_statement",
            "boundary": "Synthetic public report, not independently verified",
        },
        "limitation": {
            "refinery_commit": REFINERY_PIN,
            "limitation_probes": 4, "limitation_probe_leaks": 4,
            "boundary": "Four synthetic broad limitations",
        },
        "decision": {
            "refinery_commit": REFINERY_PIN,
            "decision_code": "REUSE_CANDIDATE",
            "execution_ready": False,
            "boundary": "Synthetic reuse review, execution not authorized",
        },
    }
    base = [
        ("problem-source-statement","practical","observation","An attributed source report of sensitive input handling concerns", receipts["practical"]),
        ("program-capability","program","capability","Narrow pattern matching on selected inputs",{"bounded":True}),
        ("program-implementation","program","implementation","Synthetic pinned implementation record",{}),
        ("program-predeclared-contract","program","requirement","Declared bounded contract with exclusions",{}),
        ("program-bounded-run","program","outcome","Synthetic bounded 27/27 required pass",{}),
        ("program-limitation-probes","program","limitation","Broader probes: all four fail",receipts["limitation"]),
        ("program-reuse-review","program","outcome","Reuse candidate is not execution ready",receipts["decision"]),
    ]
    nodes = [
        {
            "key":key,"statement":statement,"layer":layer,"kind":kind,
            "clusters":[CASE_CLUSTER],"source_refs":["https://example.org/synthetic-evidence"],
            "provenance":prov,
        } for key,layer,kind,statement,prov in base
    ]
    return {
        "schema":"cite_refinery.semantic_graph.v1",
        "source_system":"refinery",
        "clusters":[{"key":CASE_CLUSTER,"title":CASE_TITLE,"provenance":{
            "case_id":"cloakpipe-core-20261016","refinery_commit":REFINERY_PIN}}],
        "nodes":nodes,
        "edges":[{"source":"program-capability","target":"problem-source-statement",
                  "relation":"PARTIALLY_ADDRESSES","status":"candidate",
                  "evidence_refs":["https://example.org/synthetic-evidence"]}],
    }


class PrivacyAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=WorkspaceDB(Path(self.tmp.name)/"research.sqlite3")
        account=self.db.create_tenant("Synthetic Acceptance","operator")
        self.user=account["owner_user_id"]
        self.tenant=account["tenant_id"]
        self.project=self.db.create_project(self.user,account["tenant_id"],
            "Synthetic privacy acceptance","No efficacy assumption")
        self.seed(synthesized_case())
        self.review=json.loads(Path("examples/acceptance_prompt_privacy_academic_v1.json").read_text())

    def tearDown(self):
        self.tmp.cleanup()

    def seed(self,packet):
        preview=self.db.preview(self.user,self.project,packet)
        self.db.enqueue(self.user,self.project,packet,
            preview["project_revision"],preview["packet_digest"])
        result=self.db.run_one_job()
        self.assertEqual(result["status"],"succeeded")

    def combined(self):
        packet=academic_packet(self.review,
            self.db.project_state(self.user,self.project),self.project)
        self.seed(packet)
        return self.db.project_state(self.user,self.project)

    def test_three_layers_not_automatically_solved(self):
        state=self.combined()
        report=evaluate_acceptance(state,self.project)
        self.assertEqual(report["outcome"],"ACCEPTED_WITH_OPEN_GAPS")
        self.assertEqual(report["infrastructure_baseline"],BASELINE)
        self.assertEqual(report["layer_counts"],{
            "practical":1,"academic":4,"program":6})
        self.assertEqual(report["cluster_node_count"],11)
        self.assertEqual(report["cross_layer_links"],5)
        self.assertEqual(report["cross_layer_candidate_links"],4)
        self.assertEqual(report["cross_layer_qualified_scope_links"],1)
        self.assertFalse(report["production_ready"])
        self.assertFalse(report["user_report_independently_verified"])
        self.assertFalse(report["fulltext_academic_replication"])
        self.assertEqual(report["violations"],[])
        # Same packet re-import is idempotent.
        pkt=academic_packet(self.review,state,self.project)
        self.assertTrue(self.db.preview(self.user,self.project,pkt)["already_imported"])

    def test_exact_source_identity_and_quote_tampering_fails(self):
        for key,new in (
            ("citation_quote","This quotation is entirely fabricated."),
            ("source_url","https://not-original.example/articles"),
            ("title","A fabricated study"),
            ("publication_status","journal_confirmed"),
            ("year",2026),
        ):
            forged=copy.deepcopy(self.review)
            forged["papers"][0][key]=new
            with self.assertRaisesRegex(ValueError,"mismatch"):
                academic_packet(forged,self.db.project_state(self.user,self.project),self.project)
        forged=copy.deepcopy(self.review)
        forged["papers"].pop()
        with self.assertRaisesRegex(ValueError,"two manually reviewed"):
            academic_packet(forged,self.db.project_state(self.user,self.project),self.project)

    def test_unreviewed_reinterpretation_of_papers_is_refused(self):
        for field in ("claim", "source_boundary"):
            altered=copy.deepcopy(self.review)
            altered["papers"][1][field] = (
                "This article experimentally proves that CloakPipe solves all input privacy leakage problems."
            )
            with self.assertRaisesRegex(ValueError,"digest mismatch"):
                academic_packet(altered,self.db.project_state(self.user,self.project),self.project)

    def test_wrong_case_and_source_identity_rejected(self):
        wrong=copy.deepcopy(self.review)
        wrong["case"]="totally-unrelated-case"
        with self.assertRaisesRegex(ValueError,"case-specific"):
            academic_packet(wrong,self.db.project_state(self.user,self.project),self.project)
        another=self.db.create_project(self.user,self.tenant,"Other case","Different scope")
        with self.assertRaises(ValueError):
            academic_packet(self.review,self.db.project_state(self.user,another),another)

    def test_four_failed_probes_and_non_ready_verdict_are_mandatory(self):
        for kind in ("program-limitation-probes","program-reuse-review"):
            state=self.db.project_state(self.user,self.project)
            n=next(n for n in state["semantic_nodes"].values()
                   if n.get("external_key")=="refinery:"+kind)
            for receipt in n["provenance_receipts"]:
                if kind=="program-limitation-probes":
                    receipt["limitation_probe_leaks"]=0
                else:
                    receipt["execution_ready"]=True
            with self.assertRaises(ValueError):
                academic_packet(self.review,state,self.project)

    def test_acceptance_rejects_misleading_cross_layer_truth(self):
        state=self.combined()
        source=next(n for n in state["semantic_nodes"].values()
            if n.get("external_key")=="academic_acceptance:reviewed-finding-casper-arxiv-2408-07004")
        practical=next(n for n in state["semantic_nodes"].values()
            if n.get("external_key")=="refinery:problem-source-statement")
        edge=next(e for e in state["semantic_edges"].values()
            if e["source_id"]==source["id"] and e["target_id"]==practical["id"])
        edge["status"]="asserted"
        outcome=evaluate_acceptance(state,self.project)
        self.assertEqual(outcome["outcome"],"REJECTED")
        self.assertTrue(any("Cross-layer" in v for v in outcome["violations"]))
        self.assertFalse(outcome["production_ready"])

    def test_missing_primary_sources_fails_acceptance(self):
        state=self.combined()
        citation=next(n for n in state["semantic_nodes"].values()
            if n.get("external_key")=="academic_acceptance:primary-source-alsa-kdd-2025")
        citation["source_refs"]=[]
        result=evaluate_acceptance(state,self.project)
        self.assertEqual(result["outcome"],"REJECTED")
        self.assertTrue(any("linkable" in x for x in result["violations"]))


if __name__=="__main__":
    unittest.main()
