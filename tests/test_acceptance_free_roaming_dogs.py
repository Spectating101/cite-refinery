"""Second independent domain acceptance: source evidence and open gaps enforced."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.hosted_store import WorkspaceDB
from scripts.acceptance_free_roaming_dogs import (
    CASE,PILOT_SHA256,REVIEW_SHA256,case_packet,checked_sources,evaluate_case,run_case,
)

ROOT=Path(__file__).resolve().parents[1]
PILOT=ROOT/"examples/free_roaming_dog_semantic_pilot.json"
REVIEW=ROOT/"examples/acceptance_free_roaming_dog_source_review_v1.json"


class AnimalWelfareAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=WorkspaceDB(Path(self.tmp.name)/"test.sqlite3")
        account=self.db.create_tenant("Acceptance","reviewer")
        self.uid=account["owner_user_id"]
        self.project=self.db.create_project(self.uid,account["tenant_id"],
                 "Dog population","Research case with unverified interventions")

    def tearDown(self):
        self.tmp.cleanup()

    def seed(self):
        packet=case_packet(PILOT,REVIEW)
        pre=self.db.preview(self.uid,self.project,packet)
        self.db.enqueue(self.uid,self.project,packet,pre["project_revision"],pre["packet_digest"])
        self.assertEqual(self.db.run_one_job()["status"],"succeeded")
        return packet,self.db.project_state(self.uid,self.project)

    def mutate(self,state,key,update):
        node=next(n for n in state["semantic_nodes"].values()
                  if n.get("external_key")=="public_animal_welfare_case_review:"+key)
        update(node)
        return state

    def test_second_domain_real_sources_and_boundary_preserved(self):
        packet,state=self.seed()
        result=evaluate_case(state,self.project)
        self.assertEqual(result["outcome"],"ACCEPTED_WITH_OPEN_GAPS")
        self.assertEqual(result["module_count"],4)
        self.assertEqual(result["structurally_three_layer_modules"],3)
        self.assertEqual((result["practical_nodes"],result["academic_nodes"],result["program_nodes"]),(3,3,3))
        self.assertEqual(result["total_edges"],16)
        self.assertEqual(result["candidate_edges"],5)
        self.assertEqual(result["unresolved_edges"],2)
        self.assertEqual(result["qualified_edges"],9)
        self.assertFalse(result["verified_local_population_estimator"])
        self.assertFalse(result["verified_field_survey_run"])
        self.assertFalse(result["human_researcher_usability_tested"])
        self.assertEqual(len(result["machine_audited_researcher_tasks"]),4)
        self.assertEqual(result["violations"],[])
        self.assertTrue(self.db.preview(self.uid,self.project,packet)["already_imported"])
        all_edges=[e for e in state["semantic_edges"].values() if e["project_id"]==self.project]
        self.assertFalse(any(e["status"]=="asserted" for e in all_edges))

    def test_frozen_primary_sources_and_original_pilot_tampering_fail(self):
        self.assertEqual(len(checked_sources(REVIEW)),6)
        altered=Path(self.tmp.name)/"modified-pilot.json"
        obj=json.loads(PILOT.read_text())
        obj["nodes"][0]["statement"]="Government field program proven to solve everything."
        altered.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError,"original .* changed"):
            case_packet(altered,REVIEW)
        altered=Path(self.tmp.name)/"modified-review.json"
        obj=json.loads(REVIEW.read_text())
        obj["sources"][4]["scope"]="Talea has a photo ID estimator deployed everywhere."
        altered.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError,"source review mutated"):
            case_packet(PILOT,altered)

    def test_missing_non_significance_and_field_limit_rejected(self):
        _,state=self.seed()
        bad=copy.deepcopy(state)
        self.mutate(bad,"tw_periodic_estimate",
                    lambda n:[r.update(statistically_significant_decline=True)
                              for r in n["provenance_receipts"]])
        res=evaluate_case(bad,self.project)
        self.assertEqual(res["outcome"],"REJECTED")
        self.assertTrue(any("non-significant" in x for x in res["violations"]))
        bad=copy.deepcopy(state)
        self.mutate(bad,"talea",lambda n:[r.update(
            individual_photo_capture=True,field_execution_tested=True,
            population_estimator_executed=True) for r in n["provenance_receipts"]])
        res=evaluate_case(bad,self.project)
        self.assertEqual(res["outcome"],"REJECTED")
        self.assertTrue(any("Talea limitation" in x for x in res["violations"]))

    def test_policy_intent_not_turned_to_outcome_or_shoushan_national_causation(self):
        _,state=self.seed()
        bad=copy.deepcopy(state)
        self.mutate(bad,"tw_source_control_policy",
                    lambda n:[r.update(intervention_effectiveness_verified=True)
                              for r in n["provenance_receipts"]])
        res=evaluate_case(bad,self.project)
        self.assertEqual(res["outcome"],"REJECTED")
        self.assertTrue(any("program intent" in x.lower() for x in res["violations"]))
        bad=copy.deepcopy(state)
        self.mutate(bad,"shoushan_immigration",
                    lambda n:[r.update(causal_extrapolation_to_all_taiwan=True)
                              for r in n["provenance_receipts"]])
        res=evaluate_case(bad,self.project)
        self.assertEqual(res["outcome"],"REJECTED")
        self.assertTrue(any("Shoushan" in x for x in res["violations"]))

    def test_unresolved_links_and_unverified_claims_cannot_be_promoted(self):
        _,state=self.seed()
        bad=copy.deepcopy(state)
        edge=next(e for e in bad["semantic_edges"].values()
                  if e.get("relation")=="MISSING_LINK")
        edge["status"]="qualified"
        res=evaluate_case(bad,self.project)
        self.assertEqual(res["outcome"],"REJECTED")
        self.assertTrue(any("unresolved" in x for x in res["violations"]))
        bad=copy.deepcopy(state)
        edge=next(e for e in bad["semantic_edges"].values()
                  if e.get("relation")=="PARTIALLY_ADDRESSES")
        edge["status"]="asserted"
        res=evaluate_case(bad,self.project)
        self.assertEqual(res["outcome"],"REJECTED")
        self.assertTrue(any("asserted" in x for x in res["violations"]))

    def test_does_not_write_into_existing_database(self):
        with self.assertRaisesRegex(ValueError,"existing private database"):
            run_case(PILOT,REVIEW,Path(self.tmp.name)/"test.sqlite3")
        new=Path(self.tmp.name)/"new-acceptance.sqlite3"
        res=run_case(PILOT,REVIEW,new)
        self.assertEqual(res["outcome"],"ACCEPTED_WITH_OPEN_GAPS")
        self.assertTrue(new.exists())


if __name__=="__main__":
    unittest.main()
