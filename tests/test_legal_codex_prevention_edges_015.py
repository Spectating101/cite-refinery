"""Milestone 015: test conditional regulatory prevention, failures and false transfers."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.legal_codex_prevention_edges import (
    evaluate, semantic_packet, simulate_authority_gate, validate,
)

SEED = Path(__file__).resolve().parents[1] / "examples/legal_codex_prevention_edges_015.json"


class PreventionEdge015Tests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SEED.read_text(encoding="utf-8"))

    def item(self, part, ident):
        return next(x for x in self.data[part] if x["id"] == ident)

    def edge(self, ident):
        return next(x for x in evaluate(self.data)["paths"] if x["proposal_id"] == ident)

    def test_result_is_still_proposal_not_historical_proof(self):
        result = evaluate(self.data)
        self.assertEqual(result["case_count"], 6)
        self.assertEqual(result["instrument_count"], 7)
        self.assertEqual(result["examined_edge_count"], 13)
        self.assertFalse(result["historical_prevention_proven"])
        self.assertFalse(result["individual_guilt_proven"])
        self.assertIsNone(result["regulation_success_rate"])
        self.assertIsNone(result["intervention_effect_size"])
        self.assertFalse(result["legal_publication_authorized"])

    def test_uk_disclosure_duty_existed_but_did_not_prevent(self):
        row = self.edge("p_uk_duty_horizon")
        self.assertEqual(row["temporal_relation"], "rule_preexisted_failure")
        self.assertEqual(row["country_scope"], "domestic_candidate")
        self.assertEqual(row["edge_determination"], "preexisting_duty_failed_to_prevent")
        self.assertIn("withheld_undermining_material", row["matched_risk_mechanisms"])
        self.assertFalse(row["historical_prevention_proven"])

    def test_dutch_historical_norm_vs_later_interpretation(self):
        row = self.edge("p_dutch_norm_2017")
        self.assertEqual(row["temporal_relation"], "rule_preexisted_failure")
        self.assertTrue(row["court_clarified_only_after_target"])
        self.assertEqual(row["edge_determination"], "preexisting_norm_later_reattributed_by_court")

    def test_2019_dutch_ruling_did_not_prevent_2017_decision(self):
        row = self.edge("p_dutch_2019_backwards")
        self.assertEqual(row["temporal_relation"], "introduced_after_failure")
        self.assertEqual(row["edge_determination"], "postevent_remedy_not_historical_prevention")

    def test_2019_dutch_rule_used_in_2021_without_relief(self):
        row = self.edge("p_dutch_reused_in_2021")
        self.assertEqual(row["temporal_relation"], "rule_preexisted_failure")
        self.assertEqual(row["edge_determination"], "documented_rule_considered_no_relief")
        self.assertEqual(row["intervention_path"]["implementation_evidence"],
                         "judicially_considered_no_relief")
        self.assertFalse(row["historical_prevention_proven"])

    def test_indonesia_existing_document_duty_cannot_verify_missing_2020_signed_order(self):
        row = self.edge("p_indonesia_ppk_2020")
        self.assertEqual(row["edge_determination"], "potential_domestic_safeguard_implementation_unverified")
        self.assertEqual(row["country_scope"], "domestic_candidate")
        self.assertGreaterEqual(len(row["missing_required_evidence"]), 3)
        self.assertFalse(row["legally_applicable_to_individual_proven"])

    def test_indonesia_hps_not_equated_to_state_losses(self):
        row = self.edge("p_id_loss_guard")
        self.assertEqual(row["edge_determination"], "potential_domestic_safeguard_implementation_unverified")
        self.assertEqual(row["intervention_path"]["known_target_outcome"],
                         "hypothetical_inference_risk_only")
        self.assertFalse(row["historical_prevention_proven"])

    def test_proposed_authority_gate_never_masquerades_as_existing_law(self):
        row = self.edge("p_id_proposed_authority_gate")
        self.assertEqual(row["instrument_kind"], "proposed_workflow")
        self.assertEqual(row["temporal_relation"], "not_enacted_historical_counterfactual")
        self.assertEqual(row["edge_determination"], "future_design_candidate_not_historical_law")

    def test_horizon_provenance_design_reuses_general_control_in_indonesian_case(self):
        row = self.edge("p_transfer_system_provenance_to_id")
        self.assertEqual(row["edge_determination"], "future_design_candidate_not_historical_law")
        self.assertEqual(row["country_scope"], "foreign_only")
        self.assertIn("unverifiable_record_provenance", row["matched_risk_mechanisms"])
        self.assertTrue(row["checkpoint_match"])
        self.assertFalse(row["cross_border_rule_applied"])

    def test_same_horizon_record_provenance_design_remains_proposed(self):
        row = self.edge("p_uk_digital_provenance")
        self.assertEqual(row["edge_determination"], "future_design_candidate_not_historical_law")
        self.assertFalse(row["historical_prevention_proven"])

    def test_foreign_procedure_same_stage_is_research_analogy_not_law(self):
        row = self.edge("p_foreign_uk_trial_disclosure")
        self.assertEqual(row["country_scope"], "foreign_only")
        self.assertTrue(row["arena_match"])
        self.assertTrue(row["checkpoint_match"])
        self.assertEqual(row["edge_determination"], "foreign_analogy_not_binding_law")
        self.assertFalse(row["cross_border_rule_applied"])
        self.assertFalse(row["historical_prevention_proven"])

    def test_foreign_uk_to_indonesia_is_rejected_by_stage(self):
        row = self.edge("p_foreign_uk_into_id")
        self.assertEqual(row["edge_determination"], "failure_path_or_operational_stage_mismatch")
        self.assertFalse(row["checkpoint_match"])

    def test_foreign_dutch_to_uk_rejected(self):
        row = self.edge("p_foreign_dutch_into_uk")
        self.assertEqual(row["edge_determination"], "failure_path_or_operational_stage_mismatch")
        self.assertFalse(row["arena_match"])

    def test_foreign_dutch_into_procurement_is_not_binding(self):
        row = self.edge("p_foreign_nl_into_id")
        self.assertEqual(row["country_scope"], "foreign_only")
        self.assertEqual(row["edge_determination"], "failure_path_or_operational_stage_mismatch")

    def test_false_future_regulation_can_not_be_backdated(self):
        self.item("instruments", "nl_2019_recovery_interpretation")["effective_from"] = "2029-01-01"
        with self.assertRaisesRegex(ValueError, "instrument legal scope"):
            validate(self.data)

    def test_rewrite_2019_judgment_into_1994_source_blocked(self):
        self.item("instruments", "nl_2019_recovery_interpretation")["effective_from"] = "1993-01-01"
        with self.assertRaisesRegex(ValueError, "instrument legal scope"):
            validate(self.data)

    def test_wrong_country_cannot_impersonate_domestic_law(self):
        self.item("instruments", "uk_cpia_disclosure")["jurisdiction"] = "Indonesia"
        with self.assertRaisesRegex(ValueError, "instrument legal scope"):
            evaluate(self.data)

    def test_spoof_source_host_rejected(self):
        self.item("instruments", "id_ppk_2018_record_integrity")["source_url"] = "https://example.org/fake"
        with self.assertRaisesRegex(ValueError, "source provenance"):
            validate(self.data)

    def test_allegation_of_missing_decree_is_not_adjudicated_crime(self):
        self.item("cases", "indonesia_2020_ppk_authority")["individual_culpability"] = True
        with self.assertRaisesRegex(ValueError, "liability"):
            validate(self.data)

    def test_hps_hypothetical_not_mislabelled_actual_violation(self):
        self.item("cases", "indonesia_2020_hps_inference_scenario")["hypothetical"] = False
        with self.assertRaisesRegex(ValueError, "analytical hazard"):
            validate(self.data)

    def test_uk_duty_not_claimed_successful_enforcement(self):
        self.item("proposals", "p_uk_duty_horizon")["outcome_prevented"] = True
        with self.assertRaisesRegex(ValueError, "prevention claim"):
            validate(self.data)

    def test_all_impacts_and_foreign_law_application_remain_false(self):
        for r in evaluate(self.data)["paths"]:
            self.assertIsNone(r["causal_effect_estimated"])
            self.assertFalse(r["cross_border_rule_applied"])
            self.assertFalse(r["historical_prevention_proven"])

    def test_no_fabricated_probability(self):
        self.item("proposals", "p_uk_duty_horizon")["counterfactual_probability"] = 0.9
        with self.assertRaisesRegex(ValueError, "prevention claim"):
            validate(self.data)

    def test_candidate_graph_has_no_effect_proof_and_skips_mismatches(self):
        result = evaluate(self.data)
        packet = semantic_packet(self.data, result)
        self.assertEqual(packet["schema"], "cite_refinery.semantic_graph.v1")
        candidate_proposals = [p for p in result["paths"]
                               if p["edge_determination"] != "failure_path_or_operational_stage_mismatch"]
        self.assertEqual(len(packet["nodes"]), 6 + 7 + len(candidate_proposals))
        self.assertEqual(len(packet["edges"]), 2 * len(candidate_proposals))
        self.assertTrue(all(x["status"] == "candidate" for x in packet["edges"]))
        self.assertFalse(any(x["relation"] in (
            "CAUSES", "PREVENTED", "ENFORCED", "GUILTY", "PAID", "LAW_APPLIES")
            for x in packet["edges"]))

    def test_synthetic_unverified_appointment_holds_order(self):
        response = simulate_authority_gate(
            appointment_original_verified=False,
            effective_date_covers_order=False,
            role_scope_covers_order=False,
            original_purchase_order_verified=False)
        self.assertEqual(response["result"], "hold_for_documentary_review")
        self.assertEqual(len(response["missing_verifications"]), 4)
        self.assertTrue(response["synthetic_only"])
        self.assertFalse(response["real_2020_legality_determined"])

    def test_synthetic_validated_authority_permits_only_simulated_order(self):
        response = simulate_authority_gate(
            appointment_original_verified=True,
            effective_date_covers_order=True,
            role_scope_covers_order=True,
            original_purchase_order_verified=True)
        self.assertEqual(response["result"], "permit_simulated_authorization")
        self.assertFalse(response["actual_person_identity_proven"])

    def test_one_wrong_date_blocks_even_when_other_docs_present(self):
        response = simulate_authority_gate(
            appointment_original_verified=True,
            effective_date_covers_order=False,
            role_scope_covers_order=True,
            original_purchase_order_verified=True)
        self.assertEqual(response["missing_verifications"], ["date_window_matches"])
        self.assertEqual(response["result"], "hold_for_documentary_review")

    def test_invalid_synthetic_flag_refused(self):
        with self.assertRaisesRegex(ValueError, "explicit boolean"):
            simulate_authority_gate(
                appointment_original_verified="probably",
                effective_date_covers_order=True,
                role_scope_covers_order=True,
                original_purchase_order_verified=True)

    def test_real_cite_graph_preview_candidate_only(self):
        from cite_refinery.app import CiteRefinery
        from cite_refinery.semantic import SemanticGraph
        packet = semantic_packet(self.data, evaluate(self.data))
        with TemporaryDirectory() as root:
            app = CiteRefinery(root)
            p = app.init_project("Regulation-to-case prevention candidates",
                                 "No statutory transplantation or unreviewed causal findings")
            g = SemanticGraph(app.store)
            preview = g.preview_packet(p.id, packet)
            self.assertFalse(preview["authority_boundary_warnings"])
            receipt = g.ingest_packet(p.id, packet,
                                      expected_state_digest=preview["state_digest"])
            self.assertEqual(len(receipt["edge_ids"]), len(packet["edges"]))
            self.assertTrue(all(app.store.load()["semantic_edges"][x]["status"] == "candidate"
                                for x in receipt["edge_ids"]))

    def test_stale_counterfactual_packet_rejected(self):
        result = evaluate(self.data)
        self.item("proposals", "p_uk_duty_horizon")["interruption_path"] += " Unverified addition."
        with self.assertRaisesRegex(ValueError, "stale"):
            semantic_packet(self.data, result)


if __name__ == "__main__":
    unittest.main()
