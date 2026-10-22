"""Truthful semantic readiness: the browser is lexical; past LLMs are separate."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from cite_refinery.implementation_evidence_atlas import attach_original_lef_def_replay
from cite_refinery.standalone_workspace import build_pilot
from cite_refinery.semantic_integration_reality_audit import (
    SCHEMA,PAIRS,audit,frontend_match,check_recorded_semantic_diagnostic,main)
from test_standalone_workspace_pilot_v1 import OfflineStandalonePilotTests
from test_implementation_original_lef_def_trial_v1 import (
    OriginalLefDefTests,source_bound_map,synthetic_eda_receipt)

ROOT=Path(__file__).resolve().parents[1]
ATLAS=ROOT/"research_materials/opportunity_atlas"


def load(path):
    return json.loads(path.read_text("utf-8"))


class SemanticReadinessRealityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OfflineStandalonePilotTests.setUpClass()
        OriginalLefDefTests.setUpClass()
        impl=attach_original_lef_def_replay(source_bound_map(
            functional_trials=load(ATLAS/"functional_component_trials.json")),
            synthetic_eda_receipt())
        cls.pilot=build_pilot(OfflineStandalonePilotTests.foundation,
                              OfflineStandalonePilotTests.academic,impl)
        cls.archive=load(ATLAS/"semantic_entailment_diagnostic_results.json")
        cls.review=load(ATLAS/"academic_semantic_review_queue.json")
        cls.html=(ROOT/"src/cite_refinery/standalone_atlas_template.html").read_text("utf-8")
        cls.compiler=(ROOT/"src/cite_refinery/standalone_workspace.py").read_text("utf-8")

    def test_actual_1497_record_browser_literal_vs_paraphrased_queries(self):
        r=audit(self.pilot,self.archive,self.review,
                template=self.html,compiler_source=self.compiler)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["search"]["n_pairs"],10)
        self.assertEqual(r["search"]["literal_target_recall"],10)
        self.assertEqual(r["search"]["meaning_preserving_paraphrase_target_recall"],0)
        self.assertEqual(r["search"]["paraphrase_trials_by_layer"],
                         {"practical":3,"academic":4,"implementation":3})
        self.assertEqual(len(PAIRS),10)
        self.assertTrue(all(not row["source_answer_entailment_evaluated"]
                            for row in r["search"]["cases"]))
        self.assertFalse(r["readiness_gate_passed"])
        older=r["historic_model_diagnostic"]
        self.assertEqual(older["archived_unique_original_source_count"],8)
        self.assertEqual(older["archived_source_ids_aligning_with_legacy_abstract_cards"],8)
        self.assertEqual(older["archived_source_ids_aligning_with_new_103_development_cards"],0)
        self.assertEqual(older["archived_result_cards_actually_attached_to_workspace"],0)

    def test_earlier_separate_semantic_model_receipts_not_a_live_browser(self):
        r=check_recorded_semantic_diagnostic(self.archive,self.review)
        self.assertEqual(r["archived_model_casebook_size"],24)
        self.assertEqual(r["archived_agreement_with_investigator_labels"],23)
        self.assertEqual(r["archived_mechanism_review_questions"],8)
        self.assertEqual(r["archived_false_entailed_vs_investigator_labels"],0)
        self.assertFalse(r["diagnostic_auto_connected_to_live_atlas"])
        self.assertFalse(r["independent_human_reference_adjudication"])
        self.assertFalse(r["source_quote_verification_replayed_by_this_audit"])

    def test_same_original_source_cannot_be_counted_as_two_witnesses(self):
        r=audit(self.pilot,self.archive,self.review)
        self.assertEqual(r["source_integrity"]["exact_same_original_urls_occurring_across_layers"],6)
        self.assertTrue(r["source_integrity"][
            "repeated_same_URLs_are_not_independent_corroboration"])
        self.assertFalse(r["source_integrity"][
            "original_body_text_available_for_answer_entailment"])

    def test_model_available_as_separate_route_but_no_connected_semantic_frontend(self):
        r=audit(self.pilot,self.archive,self.review,
                template=self.html,compiler_source=self.compiler)
        caps=r["current_integration"]
        self.assertTrue(caps["semantic_engines_exist_in_separate_prior_experimental_routes"])
        self.assertFalse(caps["authenticated_llm_invoked_by_workspace"])
        self.assertFalse(caps["runtime_source_body_reading_for_questions"])
        self.assertFalse(caps["real_semantic_link_between_independent_map_records"])
        self.assertFalse(caps["live_multi_layer_semantic_integration_verified"])
        self.assertTrue(caps["implementation_narrow_function_tests_available"])
        self.assertTrue(caps["source_metadata_and_independent_provenance_visible"])

    def test_fails_closed_on_unsealed_holdout_fake_field_claim_or_model_promotion(self):
        changed=deepcopy(self.pilot)
        changed["original_data"]["academic_sealed_holdout_not_imported"]=0
        with self.assertRaisesRegex(ValueError,"sources or scientific authority"):
            audit(changed,self.archive,self.review)
        changed=deepcopy(self.pilot)
        changed["original_data"]["implementation_live_field_outcomes"]=1
        with self.assertRaisesRegex(ValueError,"sources or scientific authority"):
            audit(changed,self.archive,self.review)
        forged=deepcopy(self.archive)
        forged["cases"][0]["human_adjudication_complete"]=True
        with self.assertRaisesRegex(ValueError,"nonpromotion"):
            audit(self.pilot,forged,self.review)
        review=deepcopy(self.review)
        review["counts"]["validated_technical_fit"]=2
        with self.assertRaisesRegex(ValueError,"review-only"):
            audit(self.pilot,self.archive,review)
        with self.assertRaisesRegex(ValueError,"Frontend source changed"):
            audit(self.pilot,self.archive,self.review,template="<script>fake retrieval</script>")

    def test_cli_outputs_reproducible_nonpromoted_gap_report(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            p=root/"pilot.json"; p.write_text(json.dumps(self.pilot))
            dest=root/"report.json"
            result=main([
                "--pilot",str(p),
                "--archived-entailment",str(ATLAS/"semantic_entailment_diagnostic_results.json"),
                "--archived-semantic-queue",str(ATLAS/"academic_semantic_review_queue.json"),
                "--template",str(ROOT/"src/cite_refinery/standalone_atlas_template.html"),
                "--workspace-source",str(ROOT/"src/cite_refinery/standalone_workspace.py"),
                "--report-out",str(dest)])
            self.assertEqual(result,0)
            report=load(dest)
            self.assertEqual(report["search"]["literal_target_recall"],10)
            self.assertEqual(report["search"]["meaning_preserving_paraphrase_target_recall"],0)
            self.assertFalse(report["evaluation_promotes_scientific_or_commercial_authority"])
            with self.assertRaisesRegex(ValueError,"replace"):
                main([
                    "--pilot",str(p),
                    "--archived-entailment",str(ATLAS/"semantic_entailment_diagnostic_results.json"),
                    "--archived-semantic-queue",str(ATLAS/"academic_semantic_review_queue.json"),
                    "--report-out",str(dest)])


if __name__=="__main__":
    unittest.main()
