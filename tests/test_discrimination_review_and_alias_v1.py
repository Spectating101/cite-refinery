"""Source alias preservation, independent hypotheses and protocol review."""
from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch
import unittest

from cite_refinery.discriminating_tests import review_material
from cite_refinery.discriminating_test_review import critique_prompt,validate_critique,review_gate
from cite_refinery.synthetic_identifiability import demonstrations
from test_discriminating_tests_v1 import model_answer,sample_review
from cite_refinery.discriminating_tests import validate_design


class ProvenanceAndReviewTests(unittest.TestCase):
    def test_inter_round_source_alias_merges_without_fake_independent_family(self):
        one={"id":"DUP01","url":"https://example.org/a","text":"First excerpt concerns detectability assumptions.", "origin_type":"scholarly_abstract_lead"}
        two={**one,"text":"Second excerpt concerns household dog abandonment."}
        extra={"id":"UNIQUE","url":"https://example.org/b","text":"Another source supports individual resighting.", "origin_type":"scholarly_abstract_lead"}
        cls=type("Controller",(),{"load":lambda self,id:{
          "stage":"done","rounds":[
            {"number":1,"sources":[one]},
            {"number":2,"sources":[two,extra],"state":"staged_candidates",
             "critique":{"reviews":[]},"graph_receipt":{"id":"saved-stage"},
             "focus":"Which field measurements distinguish the mechanisms?",
             "inspected":{"propositions":[
                 {"id":"P2","statement":"Recent dog abandonment is relevant.",
                  "scope":"unknown population","limitation":"no specific local effect",
                  "support":[{"source_id":"DUP01","quote":"household dog abandonment."}]},
                 {"id":"P1","statement":"Detection has limitations.",
                  "scope":"unknown population","limitation":"no specific local effect",
                  "support":[{"source_id":"DUP01","quote":"detectability assumptions."}]}
                 ]}}]}})
        with patch("cite_refinery.discriminating_tests.InvestigationController",return_value=cls()):
            _,material=review_material("/tmp/fixture", "session")
        self.assertEqual(len(material["sources"]),2)
        dup=next(x for x in material["sources"] if x["id"]=="DUP01")
        self.assertEqual(len(dup["variant_sha256"]),2)
        self.assertIn("detectability assumptions",dup["text"])
        self.assertIn("household dog abandonment",dup["text"])

    def test_same_id_different_url_is_provenance_collision(self):
        one={"id":"DUP01","url":"https://example.org/a","text":"Data one"}
        two={"id":"DUP01","url":"https://example.org/b","text":"Data two"}
        cls=type("Controller",(),{"load":lambda self,id:{
          "stage":"done","rounds":[
            {"sources":[one]},
            {"sources":[two],"state":"staged_candidates","critique":True,
             "graph_receipt":True,"inspected":{"propositions":[{"id":"P1",
             "statement":"Statement","scope":"scope","limitation":"limitation","support":[]}]}}
          ]}})
        with patch("cite_refinery.discriminating_tests.InvestigationController",return_value=cls()):
            with self.assertRaisesRegex(ValueError,"collision"):
                review_material("/tmp/fixture","session")

    def test_second_pass_scope_and_fixed_test_coverage(self):
        design=validate_design(model_answer(),sample_review())
        self.assertIn("non executed",critique_prompt(design).lower().replace("-"," "))
        response={"reviews":[{"id":t["id"],"verdict":"conditionally_useful",
             "limitation":"Only source-bound analogies, absent original matched field measurements.",
             "required_revision":"Add individual identities with effort covariates and privacy-safe ownership data."}
            for t in design["tests"]],
            "design_decision":"protocol_only_unexecuted",
            "independence":"same_model_family_reviewer_not_external_truth"}
        checked=validate_critique(response,design)
        self.assertEqual(len(checked["reviews"]),3)
        self.assertEqual(checked["approved_scientific_effect_claims"],0)
        gate=review_gate(design,checked)
        self.assertEqual(gate["readiness"],"external_field_design_review_required")
        self.assertEqual(gate["approved_field_protocols"],0)
        reviewed=deepcopy(checked)
        reviewed["reviews"][1]["verdict"]="not_discriminating"
        gate=review_gate(design,reviewed)
        self.assertEqual(gate["readiness"],"revision_required")
        self.assertEqual(gate["required_revisions"][0]["id"],"T2")
        altered=deepcopy(response);altered["reviews"].pop()
        with self.assertRaisesRegex(ValueError,"Every test"):
            validate_critique(altered,design)
        altered=deepcopy(response);altered["design_decision"]="field_evidence_validated"
        with self.assertRaisesRegex(ValueError,"implemented"):
            validate_critique(altered,design)

    def test_identical_observed_counts_can_have_distinct_latent_mechanisms(self):
        result=demonstrations()
        self.assertFalse(result["empirical_data_used"])
        self.assertEqual(result["observations"],[80,100])
        self.assertEqual(len(result["scenarios"]),3)
        self.assertEqual({(s["expected_count_before"],s["expected_count_after"])
                         for s in result["scenarios"]},{(80,100)})
        self.assertGreater(len({(s["n_before"],s["n_after"]) for s in result["scenarios"]}),1)


if __name__=="__main__":unittest.main()
