"""Mechanism discriminator must decline causal identification from analogies alone."""
from __future__ import annotations
from copy import deepcopy
import unittest

from cite_refinery.discriminating_tests import design_prompt,validate_design,graph_packet


def sample_review():
    return {
        "schema":"cite_refinery.discriminating_test_input.v1",
        "target_investigation":"test-investigation",
        "source_digest":"b"*64,
        "target_question":"Why did dogs appear more frequently in CNVR street surveys?",
        "propositions":[],
        "sources":[
            {"id":"SCH-01","url":"https://doi.org/10.1234/dog-survey",
             "origin_type":"scholarly_abstract_lead","text":
             "Mark recapture estimates are sensitive to immigration, individual identification, and heterogeneity in capture probability."},
            {"id":"OFF-01","url":"https://www.who.int/dog-surveillance",
             "origin_type":"official_webpage_excerpt_unverified","text":
             "Policy guidance recommends monitoring vaccination coverage and population outcomes separately."}
        ],
    }


def model_answer():
    source={"source_id":"SCH-01","quote":"Mark recapture estimates are sensitive to immigration"}
    ms={
      "immigration_abandonment":"New arriving or abandoned animals can enter monitored street populations.",
      "survey_detectability":"The proportion visible in transect surveys can vary across time and sites.",
      "local_recruitment":"Local birth and puppy survival can increase total numbers even with stable immigration."
    }
    answer={"mechanisms":[],
            "tests":[],
            "current_identifiability":"not_identifiable_from_available_sources",
            "missing_input":["Animal-specific longitudinal resight history with individual marks",
                             "Matched controls and survey effort with observer/season covariates"],
            "next_decision":"Collect standardized repeat individual-detection observations and local recruitment records before fitting any causal model."}
    for id,meaning in ms.items():
        answer["mechanisms"].append({"id":id,"mechanism":meaning,
                                     "rationale":"The cited source identifies these assumptions as necessary to assess dog counts.",
                                     "source_receipts":[dict(source)]})
    pairs=[("immigration_abandonment","survey_detectability"),
           ("immigration_abandonment","local_recruitment"),
           ("survey_detectability","local_recruitment")]
    for i,(a,b) in enumerate(pairs,1):
        answer["tests"].append({"id":"T"+str(i),"title":"Matched longitudinal survey contrast "+str(i),
            "compares":[a,b],"observations":["capture_recapture","individual_tracking"],
            "unit_of_observation":"Individually identified dog sightings by district and survey visit",
            "timing":"Repeated short marking-resighting rounds with known fixed survey windows",
            "expected_if_first":"First rival predicts persistent newcomers with changing animal identity composition.",
            "expected_if_second":"Second rival predicts little individual turnover with altered repeat sighting fraction.",
            "nonidentifying_pattern":"More visible dogs with unknown detection probability remain compatible with either hypothesis.",
            "falsification_condition":"An unchanging tested arrival fraction under precise individual ID tracking would challenge the dominance assumption.",
            "confounders":"Visitor timing, sampling effort, GPS boundaries, dog ownership and weather.",
            "data_required":"Exact dog ID repeats, census effort, standardized individual classification and protocol.",
            "source_receipts":[dict(source)]})
    return answer


class MechanismDiscriminationTests(unittest.TestCase):
    def setUp(self):
        self.review=sample_review()
        self.raw=model_answer()
    def test_evidence_input_is_inference_ready(self):
        prompt=design_prompt(self.review)
        self.assertIn("population",prompt.lower())
        self.assertIn("mechanism",prompt.lower())
        self.assertNotIn('"current_identifiability":"identified"',prompt)
    def test_only_unidentified_three_mechanism_comparisons_accepted(self):
        assessed=validate_design(self.raw,self.review)
        self.assertEqual(len(assessed["mechanisms"]),3)
        self.assertEqual(len(assessed["tests"]),3)
        self.assertEqual({frozenset(t["compares"]) for t in assessed["tests"]},
                         {frozenset((a,b)) for i,a in enumerate(
                             ("immigration_abandonment","survey_detectability","local_recruitment"))
                          for b in ("immigration_abandonment","survey_detectability","local_recruitment")[i+1:]})
        self.assertEqual(assessed["authority"],"neutral_unexecuted_protocol_only")
        self.assertEqual(assessed["current_identifiability"],"not_identifiable_from_available_sources")
    def test_reject_fabricated_source_quote(self):
        raw=deepcopy(self.raw)
        raw["tests"][0]["source_receipts"][0]["quote"]="No immigration occurred; we measured zero new animals."
        with self.assertRaisesRegex(ValueError,"Unverified"):
            validate_design(raw,self.review)
    def test_reject_causal_verdict_without_primary_data(self):
        raw=deepcopy(self.raw)
        raw["current_identifiability"]="identified_immigration_as_cause"
        with self.assertRaisesRegex(ValueError,"automatically identified"):
            validate_design(raw,self.review)
    def test_reject_insufficient_alternative_comparisons(self):
        raw=deepcopy(self.raw)
        raw["tests"][-1]["compares"]=["immigration_abandonment","survey_detectability"]
        with self.assertRaisesRegex(ValueError,"three competing mechanism pairs"):
            validate_design(raw,self.review)
    def test_staged_packet_is_neutral_and_does_not_assert_causality(self):
        validated=validate_design(self.raw,self.review)
        packet=graph_packet(validated)
        self.assertEqual(len(packet["nodes"]),7)
        self.assertEqual(len(packet["edges"]),9)
        self.assertTrue(all(n["layer"]=="neutral" for n in packet["nodes"]))
        self.assertTrue(all(e["status"]=="unresolved" for e in packet["edges"]))
        self.assertNotIn("CAUSES",{e["relation"] for e in packet["edges"]})
        self.assertEqual(packet["conversion_metadata"]["accepted_effect_claims"],0)
    def test_duplicate_hypotheses_and_unknown_data_codes_blocked(self):
        raw=deepcopy(self.raw)
        raw["mechanisms"][2]["id"]="immigration_abandonment"
        with self.assertRaisesRegex(ValueError,"three explicit"):
            validate_design(raw,self.review)
        raw=deepcopy(self.raw)
        raw["tests"][0]["observations"]=["invisible_animal_welfare_signal","individual_tracking"]
        with self.assertRaisesRegex(ValueError,"concrete observation"):
            validate_design(raw,self.review)

if __name__=="__main__":
    unittest.main()
