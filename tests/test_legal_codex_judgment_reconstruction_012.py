"""Milestone 012: original-source reference, outcome, and adverse-case gates."""
import copy
import json
from pathlib import Path
import unittest

from cite_refinery.legal_codex_judgment_reconstruction import (
    evaluate, validate, semantic_packet,
)

SEED = Path(__file__).resolve().parents[1] / "examples/legal_codex_judgment_reconstruction_012.json"


class JudgmentReconstruction012Tests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SEED.read_text(encoding="utf-8"))

    def item(self, part, ident):
        return next(x for x in self.data[part] if x["id"] == ident)

    def test_judgments_and_anchored_holdings(self):
        result = evaluate(self.data)
        self.assertEqual(result["judgment_count"], 3)
        self.assertEqual(result["jurisdiction_count"], 2)
        self.assertEqual(result["holding_count"], 12)
        self.assertEqual(result["comparison_count"], 3)
        self.assertEqual([x["docket"] for x in result["judgments"]],
                         ["ECLI:NL:RVS:2019:3535", "ECLI:NL:RVS:2019:3536", "[2021] EWCA Crim 577"])
        self.assertFalse(result["document_bytes_authenticated"])
        self.assertFalse(result["legal_source_entailment_verified"])
        self.assertFalse(result["publication_authorized"])

    def test_hamilton_denominator_and_three_failed_appeals(self):
        result = evaluate(self.data)
        u = next(x for x in result["judgments"] if x["judgment_id"] == "hamilton_2021")
        self.assertEqual((u["outcome"]["appellants"], u["outcome"]["appeals_allowed"],
                          u["outcome"]["appeals_dismissed"]), (42, 39, 3))
        self.assertFalse(u["outcome"]["automatic_restitution_awarded"])

    def test_dutch_3535_entitlement_not_recovery(self):
        result = evaluate(self.data)
        d = next(x for x in result["judgments"] if x["judgment_id"] == "dutch_3535")
        self.assertEqual(d["outcome"]["status"], "remittal_for_new_entitlement_decision")
        self.assertEqual(d["outcome"]["new_decision_deadline_weeks"], 26)
        self.assertIn("proportionate_entitlement", [h["kind"] for h in d["paragraph_holdings"]])
        self.assertNotIn("proportionate_recovery", [h["kind"] for h in d["paragraph_holdings"]])

    def test_dutch_3536_recovery_not_entitlement(self):
        result = evaluate(self.data)
        d = next(x for x in result["judgments"] if x["judgment_id"] == "dutch_3536")
        self.assertEqual(d["outcome"]["status"], "remittal_for_new_recovery_decision")
        self.assertEqual(d["outcome"]["new_decision_deadline_weeks"], 26)
        self.assertIn("third_party_liability_nonretroactive", [h["kind"] for h in d["paragraph_holdings"]])
        self.assertNotIn("proportionate_entitlement", [h["kind"] for h in d["paragraph_holdings"]])

    def test_court_url_cannot_be_changed_to_news_or_another_docket(self):
        self.item("judgments", "dutch_3535")["source_url"] = "https://www.hukumonline.com/example"
        with self.assertRaisesRegex(ValueError, "court identity"):
            validate(self.data)

    def test_docket_mismatch_cannot_transfer_judicial_holding(self):
        self.item("judgments", "dutch_3535")["docket"] = "ECLI:NL:RVS:2019:3536"
        with self.assertRaisesRegex(ValueError, "court identity"):
            validate(self.data)

    def test_source_cannot_claim_captured_signed_original(self):
        self.item("judgments", "hamilton_2021")["source_bytes_archived"] = True
        with self.assertRaisesRegex(ValueError, "custody"):
            validate(self.data)

    def test_hash_cannot_be_fabricated_from_web_citation(self):
        self.item("judgments", "hamilton_2021")["original_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "custody"):
            validate(self.data)

    def test_cannot_claim_independent_legal_review(self):
        self.data["independent_legal_review_completed"] = True
        with self.assertRaisesRegex(ValueError, "promoted"):
            validate(self.data)

    def test_no_public_legal_conclusion_from_unreviewed_paraphrase(self):
        self.data["publication_authorized"] = True
        with self.assertRaisesRegex(ValueError, "promoted"):
            validate(self.data)

    def test_no_independently_proven_causal_impact(self):
        self.data["causal_policy_effect_measured"] = True
        with self.assertRaisesRegex(ValueError, "promoted"):
            validate(self.data)

    def test_no_uk_2024_statute_projected_backward_into_2021(self):
        self.item("holdings", "uk_horizon_reliability")["domestic_legal_bases"].append("post_office_2024_act")
        with self.assertRaisesRegex(ValueError, "foreign or later"):
            validate(self.data)

    def test_uk_evidence_standard_not_dutch_entitlement_law(self):
        self.item("holdings", "uk_horizon_reliability")["domestic_legal_bases"] = ["wko_1_7"]
        with self.assertRaisesRegex(ValueError, "foreign or later"):
            validate(self.data)

    def test_dutch_entitlement_disposition_not_dpa_fine(self):
        self.item("judgments", "dutch_3535")["outcome"]["status"] = "regulator_fine_imposed"
        with self.assertRaisesRegex(ValueError, "disposition"):
            validate(self.data)

    def test_uk_39_of_42_not_42_of_42(self):
        self.item("judgments", "hamilton_2021")["outcome"]["appeals_allowed"] = 42
        with self.assertRaisesRegex(ValueError, "disposition"):
            validate(self.data)

    def test_uk_nonessential_horizon_exception_is_preserved(self):
        self.data["holdings"] = [
            h for h in self.data["holdings"] if h["id"] != "uk_specific_exception"]
        with self.assertRaisesRegex(ValueError, "holding types"):
            validate(self.data)

    def test_no_reclassification_of_neelam_appeal_as_allowed(self):
        self.item("holdings", "uk_specific_exception")["kind"] = "mixed_appeal_disposition"
        with self.assertRaisesRegex(ValueError, "holding types"):
            validate(self.data)

    def test_3535_and_3536_paragraphs_cannot_swap(self):
        self.item("holdings", "nl_3535_entitlement")["judgment_id"] = "dutch_3536"
        with self.assertRaisesRegex(ValueError, "moved between"):
            validate(self.data)

    def test_dutch_remittal_is_not_direct_final_cash_award(self):
        self.item("judgments", "dutch_3536")["outcome"]["automatic_restitution_awarded"] = True
        with self.assertRaisesRegex(ValueError, "cash restitution"):
            validate(self.data)

    def test_dutch_remittal_has_redecision_deadline(self):
        self.item("judgments", "dutch_3535")["outcome"]["new_decision_deadline_weeks"] = 0
        with self.assertRaisesRegex(ValueError, "remitted"):
            validate(self.data)

    def test_dutch_same_day_changes_do_not_form_one_holding(self):
        self.item("comparisons", "cmp_dutch_split")["left_holding"] = "nl_3536_discretion"
        with self.assertRaisesRegex(ValueError, "distinct judicial decisions"):
            validate(self.data)

    def test_foreign_law_not_imported_to_other_jurisdiction(self):
        self.item("comparisons", "cmp_documented_evidence")["foreign_rule_applied"] = True
        with self.assertRaisesRegex(ValueError, "equivalence"):
            validate(self.data)

    def test_comparative_causal_effect_must_be_null(self):
        self.item("comparisons", "cmp_remedy_boundary")["measured_effect_difference"] = 0.75
        with self.assertRaisesRegex(ValueError, "equivalence"):
            validate(self.data)

    def test_dutch_nationality_profiling_is_outside_these_rulings(self):
        self.data["expressly_not_adjudicated"].remove("dutch_nationality_profiling_adjudicated")
        with self.assertRaisesRegex(ValueError, "exclusion"):
            validate(self.data)

    def test_indonesian_ppk_not_inferred_from_unrelated_judgments(self):
        self.data["expressly_not_adjudicated"].remove("indonesia_ppk_signature_established")
        with self.assertRaisesRegex(ValueError, "exclusion"):
            validate(self.data)

    def test_graph_does_not_publish_court_rulings_as_universal_laws(self):
        out = evaluate(self.data)
        packet = semantic_packet(self.data, out)
        self.assertEqual(packet["schema"], "cite_refinery.semantic_graph.v1")
        self.assertEqual(len(packet["nodes"]), 15)
        self.assertEqual(len(packet["edges"]), 15)
        self.assertTrue(all(e["status"] == "candidate" for e in packet["edges"]))
        self.assertFalse(any(e["relation"] in {"CAUSES", "GUILTY", "LAW_APPLIES", "PAID", "SIGNED"}
                             for e in packet["edges"]))
        self.assertEqual(sum(e["relation"] == "COMPARABLE_LEGAL_MECHANISM_CANDIDATE"
                             for e in packet["edges"]), 3)

    def test_stale_result_cannot_move_unchecked_graph(self):
        out = evaluate(self.data)
        self.item("holdings", "nl_3536_discretion")["summary"] += " New unsupported text."
        with self.assertRaisesRegex(ValueError, "changed"):
            semantic_packet(self.data, out)

    def test_actual_cite_preview_and_ingest_keep_candidate_review_state(self):
        from tempfile import TemporaryDirectory
        from cite_refinery.app import CiteRefinery
        from cite_refinery.semantic import SemanticGraph

        packet = semantic_packet(self.data, evaluate(self.data))
        with TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project = app.init_project("Cross-border legal reconstruction", "Three selected judicial opinions only")
            graph = SemanticGraph(app.store)
            preview = graph.preview_packet(project.id, packet)
            self.assertFalse(preview["authority_boundary_warnings"])
            receipt = graph.ingest_packet(
                project.id, packet, expected_state_digest=preview["state_digest"])
            self.assertEqual(len(receipt["edge_ids"]), 15)
            self.assertTrue(all(
                app.store.load()["semantic_edges"][i]["status"] == "candidate"
                for i in receipt["edge_ids"]))


if __name__ == "__main__":
    unittest.main()
