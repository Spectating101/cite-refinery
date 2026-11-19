"""Milestone 013: official outcome statistics are not individual judicial remedies."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.legal_codex_outcome_trace import (
    evaluate, validate, semantic_packet,
)

SEED = Path(__file__).resolve().parents[1] / "examples/legal_codex_outcome_trace_013.json"


class OutcomeTrace013Tests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SEED.read_text(encoding="utf-8"))

    def row(self, collection, ident):
        return next(x for x in self.data[collection] if x["id"] == ident)

    def test_two_regions_source_and_cohort_counts(self):
        out = evaluate(self.data)
        self.assertEqual(out["source_count"], 5)
        self.assertEqual(out["cohort_count"], 11)
        self.assertEqual(out["monetary_category_count"], 11)
        self.assertEqual(out["correction_count"], 2)
        self.assertEqual(out["context_only_court_link_count"], 3)
        self.assertEqual(out["unresolved_individual_record_count"], 4)
        self.assertEqual(out["individual_case_outcomes_authenticated"], 0)
        self.assertFalse(out["global_remedy_effectiveness_proven"])
        self.assertFalse(out["document_bytes_authenticated"])
        self.assertFalse(out["publication_authorized"])

    def test_uk_moj_person_count_not_2021_hamilton_denominator(self):
        cases=self.row("cohorts","uk_moj_casework")
        people=self.row("cohorts","uk_quashed_people")
        self.assertEqual((cases["reported_total"],cases["stages"]["assessed"]), (1011,1011))
        self.assertEqual((people["reported_total"],people["stages"]["notified"]), (620,584))
        self.assertNotEqual(cases["unit"],people["unit"])
        self.assertFalse(people["court_appellants_matched"])

    def test_hcrs_stages_reconcile_within_same_claims_scheme(self):
        out=evaluate(self.data)
        c=next(r for r in out["cohorts"] if r["cohort_id"]=="uk_hcrs_claims")
        self.assertEqual(c["reported_total"],545)
        self.assertEqual(sum(c["stages"].values()),545)
        self.assertEqual(c["stages"]["settled"],515)
        self.assertAlmostEqual(c["stage_fraction_within_same_cohort_only"]["settled"],515/545,places=5)
        self.assertIsNone(c["global_remedy_success_rate"])

    def test_other_uk_schemes_not_same_claimant_pool(self):
        records={c["id"]:c for c in self.data["cohorts"]}
        self.assertEqual(records["uk_hss_claims"]["reported_total"],14901)
        self.assertEqual(records["uk_glo_claims"]["reported_total"],492)
        self.assertEqual(records["uk_hssa_claims"]["reported_total"],173)
        self.assertTrue(all(not records[k]["same_persons_as_other_cohort"]
                            for k in ("uk_hss_claims","uk_glo_claims","uk_hssa_claims")))

    def test_dutch_objections_decided_does_not_mean_compensated(self):
        c=self.row("cohorts","nl_objections")
        self.assertEqual(c["reported_total"],18886)
        self.assertEqual(c["stages"]["pending"],5316)
        self.assertEqual(c["stages"]["decision_issued"],13570)
        self.assertFalse(c["all_fully_compensated"])

    def test_dutch_recognized_total_is_not_completed_integral_assessments(self):
        recognized=self.row("cohorts","nl_parent_classification")
        completed=self.row("cohorts","nl_integral_assessments")
        self.assertEqual(recognized["stages"]["recognized"],44131)
        self.assertEqual(recognized["reported_total"],69738)
        self.assertEqual(completed["reported_total"],69517)
        self.assertFalse(completed["is_exhaustive_partition"])

    def test_dutch_damage_commission_not_in_review_not_settled(self):
        c=self.row("cohorts","nl_cws_cases")
        self.assertEqual(c["reported_total"],12377)
        self.assertEqual(c["stages"]["no_longer_in_review"],8726)
        self.assertNotIn("settled",c["stages"])
        self.assertNotIn("paid",c["stages"])

    def test_approximate_sep_dutch_completion_not_exact_oct_cohort(self):
        c=self.row("cohorts","nl_additional_damages_approx")
        self.assertEqual(c["reported_total"],4500)
        self.assertTrue(c["approximate"])
        self.assertEqual(c["data_as_of"],"2026-09-18")
        self.assertNotEqual(c["data_as_of"],self.row("cohorts","nl_objections")["data_as_of"])

    def test_dutch_dashboard_publication_timestamp_not_invented(self):
        s=self.row("sources","s_nl_dashboard")
        self.assertIsNone(s["published_or_corrected_on"])
        self.assertEqual(s["data_as_of"],"2026-10-16")

    def test_superseded_uk_september_number_preserved_as_correction_not_payment(self):
        result=evaluate(self.data)
        by_id={c["id"]:c for c in result["corrected_official_figures"]}
        correction=by_id["uk_sep_total_correction"]
        self.assertEqual((correction["superseded"],correction["current"]),(1731,1727))
        self.assertTrue(correction["not_new_disbursement"])
        self.assertEqual(correction["revision_date"],"2026-11-13")
        hssa=by_id["uk_sep_hssa_correction"]
        self.assertEqual((hssa["superseded"],hssa["current"]),(22,18))
        self.assertTrue(hssa["not_new_disbursement"])

    def test_reporting_total_not_component_sum_due_to_rounding_overlap(self):
        amounts={m["id"]:m for m in self.data["money"]}
        self.assertEqual(amounts["uk_all_redress_oct"]["reported_amount"],1756)
        subids=("uk_hss_paid","uk_hssa_paid","uk_glo_paid","uk_hcrs_paid","uk_oc_closed_paid")
        self.assertEqual(sum(amounts[k]["reported_amount"] for k in subids),1755)
        self.assertTrue(all(not amounts[k]["additive_to_other_categories"] for k in subids))

    def test_currency_cross_country_mixing_blocked(self):
        self.row("money","nl_integral_assessment_disbursed")["unit"]="GBP_million"
        with self.assertRaisesRegex(ValueError,"currency"):
            validate(self.data)

    def test_amount_cannot_be_inflated_or_rounded_into_another_cohort(self):
        self.row("money","uk_hcrs_paid")["reported_amount"]=1756
        with self.assertRaisesRegex(ValueError,"amount"):
            validate(self.data)

    def test_corrected_september_not_previously_discredited_value(self):
        self.row("money","uk_all_redress_sep_corrected")["reported_amount"]=1731
        with self.assertRaisesRegex(ValueError,"amount"):
            validate(self.data)

    def test_official_revision_is_not_new_money_disbursed(self):
        self.data["corrections"][0]["change_is_new_payment"]=True
        with self.assertRaisesRegex(ValueError,"revision"):
            validate(self.data)

    def test_uk_moj_quashed_people_not_larger_from_other_scheme(self):
        self.row("cohorts","uk_quashed_people")["reported_total"]=545
        with self.assertRaisesRegex(ValueError,"cohort report"):
            validate(self.data)

    def test_hcrs_settled_must_not_be_money_paid(self):
        self.row("cohorts","uk_hcrs_claims")["stages"]["settled"]=529
        with self.assertRaisesRegex(ValueError,"cohort report"):
            validate(self.data)

    def test_synthetic_unsettled_claims_break_partition(self):
        self.row("cohorts","uk_glo_claims")["stages"]["under_assessment"]=30
        with self.assertRaisesRegex(ValueError,"cohort report"):
            validate(self.data)

    def test_conflation_of_uk_claims_and_people_rejected(self):
        self.row("cohorts","uk_hcrs_claims")["unit"]="individuals"
        with self.assertRaisesRegex(ValueError,"unit"):
            validate(self.data)

    def test_source_date_cannot_be_backdated(self):
        self.row("sources","s_uk_redress_oct")["data_as_of"]="2021-04-23"
        with self.assertRaisesRegex(ValueError,"source or dated snapshot"):
            validate(self.data)

    def test_source_host_cannot_impersonate_ministry(self):
        self.row("sources","s_uk_redress_oct")["url"]="https://fake.example/2026/statistics"
        with self.assertRaisesRegex(ValueError,"source or dated snapshot"):
            validate(self.data)

    def test_source_original_custody_must_not_be_faked(self):
        self.row("sources","s_nl_dashboard")["original_bytes_captured"]=True
        with self.assertRaisesRegex(ValueError,"authenticated original custody"):
            validate(self.data)

    def test_no_unapproved_publication_or_causal_claim(self):
        self.data["publication_authorized"]=True
        with self.assertRaisesRegex(ValueError,"archive, independent audit"):
            validate(self.data)
        self.data["publication_authorized"]=False
        self.data["causal_effect_estimated"]=True
        with self.assertRaisesRegex(ValueError,"archive, independent audit"):
            validate(self.data)

    def test_no_judgment_specific_payout_from_scheme_aggregate(self):
        self.row("court_context_links","link_hamilton_hcrs")["case_specific_payment_verified"]=True
        with self.assertRaisesRegex(ValueError,"particular litigant"):
            validate(self.data)

    def test_no_dutch_3535_to_3536_claimant_merge(self):
        self.row("court_context_links","link_3535_programme")["cohort_id"]="nl_objections"
        with self.assertRaisesRegex(ValueError,"statistics cannot"):
            validate(self.data)

    def test_individual_followup_still_unverified(self):
        self.row("unresolved_gaps","g_nl3536_followup")["individual_outcome_proven"]=True
        with self.assertRaisesRegex(ValueError,"presumed resolved"):
            validate(self.data)

    def test_no_population_wide_success_from_stages(self):
        result=evaluate(self.data)
        self.assertTrue(all(x["global_remedy_success_rate"] is None
                            for x in result["cohorts"]))
        self.assertTrue(all(x["individual_recipient_verification"] is False
                            for x in result["cohorts"]))

    def test_graph_is_candidate_only_without_named_litigant_edges(self):
        packet=semantic_packet(self.data,evaluate(self.data))
        self.assertEqual(packet["schema"],"cite_refinery.semantic_graph.v1")
        self.assertTrue(packet["nodes"])
        self.assertTrue(packet["edges"])
        self.assertTrue(all(e["status"]=="candidate" for e in packet["edges"]))
        self.assertFalse(any(e["relation"] in (
            "PAID", "REMEDIED", "GUILTY", "CAUSES", "LEGAL_RULE_APPLIES",
        ) for e in packet["edges"]))
        self.assertFalse(any(x["key"].startswith("judgment-") for x in packet["nodes"]))

    def test_changed_input_rejects_old_receipt(self):
        result=evaluate(self.data)
        self.row("sources","s_uk_moj")["scope"]+=" Unverified edit."
        with self.assertRaisesRegex(ValueError,"changed ledger"):
            semantic_packet(self.data,result)

    def test_real_cite_preview_and_ingest_keeps_all_edges_candidate(self):
        from cite_refinery.app import CiteRefinery
        from cite_refinery.semantic import SemanticGraph
        packet=semantic_packet(self.data,evaluate(self.data))
        with TemporaryDirectory() as workdir:
            app=CiteRefinery(workdir)
            project=app.init_project("Administrative outcome trace",
                                     "Official reporting, no individual judicial links")
            graph=SemanticGraph(app.store)
            preview=graph.preview_packet(project.id,packet)
            self.assertFalse(preview["authority_boundary_warnings"])
            receipt=graph.ingest_packet(
                project.id,packet,expected_state_digest=preview["state_digest"])
            self.assertEqual(len(receipt["edge_ids"]),len(packet["edges"]))
            self.assertTrue(all(app.store.load()["semantic_edges"][eid]["status"]=="candidate"
                                for eid in receipt["edge_ids"]))


if __name__=="__main__":
    unittest.main()
