"""Real critique + synthetic observation dataset, never released as field evidence."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
import unittest

from cite_refinery.field_observation_repair import proposed_repair
from cite_refinery.field_observation_synthetic import synthetic_pilot,incomplete_pilot

ROOT=Path(__file__).resolve().parents[1]/"research_materials/runtime_trials/discrimination_20261020"

def load(name): return json.loads((ROOT/name).read_text(encoding="utf-8"))

class RepairedProtocolTests(unittest.TestCase):
    def setUp(self):
        self.source=load("protocol_candidate.json")
        self.critique=load("critic_review.json")
    def test_revised_protocol_links_to_actual_critical_reviews(self):
        result=proposed_repair(self.source,self.critique,synthetic_pilot())
        self.assertEqual(result["status"],"data_dictionary_and_pilot_quality_checks_only")
        self.assertEqual(result["revised_tests"]["T2"]["prior_verdict"],"not_discriminating")
        self.assertEqual(result["revised_tests"]["T3"]["prior_verdict"],"uncertain")
        self.assertFalse(result["approved_for_field_deployment"])
        self.assertEqual(result["causal_identification"],"not_identified")
        self.assertTrue(all(not t["ready_for_field_use"] for t in result["revised_tests"].values()))
        self.assertTrue(result["synthetic"])
        self.assertIn("consent",result["revised_tests"]["T2"]["candidate_revision"].lower())
        self.assertIn("g(0)",result["revised_tests"]["T3"]["candidate_revision"])
    def test_incomplete_data_keeps_tests_blocked(self):
        result=proposed_repair(self.source,self.critique,incomplete_pilot())
        self.assertEqual(result["revised_tests"]["T2"]["data_format_readiness"],"unresolved_data_gap")
        self.assertEqual(result["revised_tests"]["T3"]["data_format_readiness"],"not_ready_for_detection_model")
        self.assertFalse(result["observed_field_outcome_validated"])
    def test_tampered_critic_or_wrong_field_contract_not_accepted(self):
        x=deepcopy(self.critique)
        x["original_plan_digest"]="faked_source_hash"
        with self.assertRaisesRegex(ValueError,"source-digest"):
            proposed_repair(self.source,x,synthetic_pilot())
        x=deepcopy(self.critique)
        x["reviews"][1]["verdict"]="conditionally_useful"
        with self.assertRaisesRegex(ValueError,"Unexpected input critique"):
            proposed_repair(self.source,x,synthetic_pilot())
        data=deepcopy(synthetic_pilot())
        data["visits"][0]["household_id"]="SECRET"
        with self.assertRaises(ValueError):
            proposed_repair(self.source,self.critique,data)

if __name__=="__main__":unittest.main()
