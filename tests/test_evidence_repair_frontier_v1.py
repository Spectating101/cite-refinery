"""Offline contracts: source-audit issues become neutral, idempotent research frontier."""
from __future__ import annotations
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.investigation_controller import InvestigationController,planning_prompt
from cite_refinery.evidence_repair_frontier import build_repair_cases,stage_frontier,new_repair_investigation,repair_packet
from cite_refinery.external_llm_packets import _key

DATA=Path(__file__).resolve().parents[1]/"research_materials/runtime_trials/fulltext_dog_20261020"
DOI="https://doi.org/10.14202/vetworld.2026.2816-2849"

def loaded(name):return json.loads((DATA/name).read_text(encoding="utf-8"))

def create_source_backed_investigation(root):
    ctrl=InvestigationController(root,reasoner=None)
    state=ctrl.start("Do dog-population intervention monitoring results support health impact?",
                     [{"id":"AW-01","title":"Free roaming dog population estimates",
                       "summary":"Methodological limits and independent intervention validation."}],
                     max_rounds=2)
    known={
       "P4":"The reported number of free-roaming dogs requiring sterilization declined from 1,368 in 2021 to 484 in 2025.",
       "P6":"The abstract reports significant buffer-intervention effects on male populations in zone 1.",
       "P7":"The abstract reports significant buffer-intervention effects on female populations in zone 3.",
    }
    claims=[{"id":pid,"statement":statement,"support":[{"source_url":DOI,
                 "source_id":"EPMC-TEST","quote":"test original source text"}]}
             for pid,statement in known.items()]
    state["rounds"]=[{"number":2,"state":"staged_candidates",
                      "inspected":{"propositions":claims},"sources":[]}]
    state["stage"]="ready_next";ctrl.save(state)
    source_packet={
         "schema":"cite_refinery.semantic_graph.v1",
         "source_system":"external_llm_reasoner_v1",
         "clusters":[],
         "nodes":[{"key":_key("proposition",p["id"]+p["statement"]),
                   "statement":p["statement"],"kind":"concept","layer":"neutral",
                   "source_refs":[DOI],"provenance":{"source":"frozen original"}} for p in claims],
         "edges":[],
    }
    ctrl.graph.ingest_packet(state["project_id"],source_packet)
    return ctrl,state


class EvidenceRepairContracts(unittest.TestCase):
    def test_prepare_integrity_and_five_distinct_neutral_questions(self):
        with TemporaryDirectory() as folder:
            _,session=create_source_backed_investigation(folder)
            cases=build_repair_cases(loaded("published_program_table_quality.json"),
                                     loaded("replication_assessment.json"),session,loaded("fulltext_audit.json"))
            self.assertEqual(len(cases["cases"]),5)
            self.assertEqual([x["priority"] for x in cases["cases"]].count("P0"),2)
            self.assertTrue(all(x["question"].endswith("?") for x in cases["cases"]))
            by_key={x["key"]:x for x in cases["cases"]}
            self.assertEqual(by_key["table2-sex-total-2023-3-2"]["claim_ids"],[])
            self.assertEqual(by_key["table6-buffer-exposure-design-gap"]["claim_ids"],
                             ["R2:P6","R2:P7"])
            self.assertEqual(by_key["external-population-outcome-gap"]["claim_ids"],
                             ["R2:P4","R2:P6","R2:P7"])
            self.assertIn("unverified",cases["authority"].replace("needs_primary_data","unverified"))

    def test_complete_staging_idempotent_and_original_graph_immutable(self):
        with TemporaryDirectory() as folder:
            ctrl,session=create_source_backed_investigation(folder)
            frontier=build_repair_cases(loaded("published_program_table_quality.json"),
                                       loaded("replication_assessment.json"),session,loaded("fulltext_audit.json"))
            before=copy.deepcopy(ctrl.app.store.load())
            staged=stage_frontier(folder,session["id"],frontier)
            packet=staged["packet"]
            self.assertEqual(len(packet["nodes"]),11)
            self.assertTrue(all(node["layer"]=="neutral" for node in packet["nodes"]))
            self.assertTrue(all(edge["status"] in {"candidate","unresolved"} for edge in packet["edges"]))
            self.assertFalse(staged["preview"]["changed_existing_edge_statuses"])
            self.assertEqual([q["kind"] for q in packet["nodes"]].count("research_question"),5)
            after=copy.deepcopy(ctrl.app.store.load())
            self.assertEqual({eid:x["status"] for eid,x in before["semantic_edges"].items()},
                             {eid:after["semantic_edges"][eid]["status"] for eid in before["semantic_edges"]})
            repeated=stage_frontier(folder,session["id"],frontier)
            self.assertEqual(repeated["receipt"]["id"],staged["receipt"]["id"])
            self.assertEqual(after,ctrl.app.store.load())
            self.assertEqual(ctrl.load(session["id"])["stage"],"ready_next")

    def test_repair_is_new_lineaged_session_not_rewrite_of_finished_investigation(self):
        with TemporaryDirectory() as folder:
            ctrl,session=create_source_backed_investigation(folder)
            frontier=build_repair_cases(loaded("published_program_table_quality.json"),
                                       loaded("replication_assessment.json"),session,loaded("fulltext_audit.json"))
            original=copy.deepcopy(ctrl.load(session["id"]))
            child=new_repair_investigation(folder,session["id"],frontier,max_rounds=2)
            self.assertNotEqual(child["project_id"],session["project_id"])
            self.assertNotEqual(child["id"],session["id"])
            self.assertEqual(child["stage"],"plan")
            self.assertTrue(child["fulltext_enrichment"])
            self.assertIn("dog-abundance survey",child["question"])
            self.assertEqual(len(child["frontier"]),0)
            self.assertEqual(len(child["dependency_queue"]),4)
            self.assertEqual(len(child["lineage"]["requires_external_author_data"]),4)
            self.assertEqual(original,ctrl.load(session["id"]))
            prompt=planning_prompt(child)
            self.assertIn("upon request",prompt)
            self.assertIn("evidence_repair_lineage",prompt)
            self.assertIn(session["id"],prompt)

    def test_tamper_detection(self):
        with TemporaryDirectory() as folder:
            _,session=create_source_backed_investigation(folder)
            table=loaded("published_program_table_quality.json")
            assessment=loaded("replication_assessment.json")
            fake=dict(table,source_doi="10.1234/fake")
            with self.assertRaises(ValueError):build_repair_cases(fake,assessment,session,loaded("fulltext_audit.json"))
            fake2=dict(assessment,program_rows=100000)
            with self.assertRaises(ValueError):build_repair_cases(table,fake2,session,loaded("fulltext_audit.json"))
            fake3=copy.deepcopy(assessment)
            fake3["within_row_sex_total_mismatches"][0]["sex_sum"]=62
            fake3["within_row_sex_total_mismatches"][0]["female"]=51
            with self.assertRaises(ValueError):build_repair_cases(table,fake3,session,loaded("fulltext_audit.json"))
            valid=build_repair_cases(table,assessment,session,loaded("fulltext_audit.json"))
            valid["cases"][0]["claim_ids"]=["R9:P999"]
            with self.assertRaises(ValueError):stage_frontier(folder,session["id"],valid)

if __name__=="__main__":unittest.main()
