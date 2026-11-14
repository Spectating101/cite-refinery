"""Milestone 014: distinguish month-to-month reports from old-data corrections."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.legal_codex_reporting_delta import evaluate, semantic_packet

SEED=Path(__file__).resolve().parents[1]/"examples/legal_codex_outcome_trace_013.json"


class ReportingDelta014Tests(unittest.TestCase):
    def setUp(self):
        self.bundle=json.loads(SEED.read_text(encoding="utf-8"))

    def row(self,collection,ident):
        return next(x for x in self.bundle[collection] if x["id"]==ident)

    def test_exactly_two_comparable_monthly_series(self):
        out=evaluate(self.bundle)
        self.assertEqual(out["real_time_series_pair_count"],2)
        self.assertEqual(out["retrospective_revision_count"],2)
        self.assertFalse(out["dutch_time_series_computed"])
        self.assertFalse(out["exact_disbursement_inferred"])

    def test_reported_total_1727_to_1756_is_rounded_period_change_not_exact_payments(self):
        row=next(x for x in evaluate(self.bundle)["period_comparisons"]
                 if x["id"]=="uk_total_sep_to_oct")
        self.assertEqual((row["earlier_official_reported"],
                          row["later_official_reported"],
                          row["rounded_reported_change"]),(1727,1756,29))
        self.assertEqual(row["change_type"],"newer_published_cumulative_observation")
        self.assertFalse(row["exact_cash_disbursed_from_difference_proven"])

    def test_hssa_18_to_18_has_zero_reported_rounding_delta(self):
        row=next(x for x in evaluate(self.bundle)["period_comparisons"]
                 if x["id"]=="uk_hssa_sep_to_oct")
        self.assertEqual(row["rounded_reported_change"],0)
        self.assertFalse(row["individual_remedy_verified"])

    def test_september_total_revision_is_not_negative_payments(self):
        out=evaluate(self.bundle)
        r=next(x for x in out["retroactive_corrections"]
               if x["id"]=="uk_sep_total_correction")
        self.assertEqual((r["superseded_reported"],
                          r["revised_reported"],r["revision_difference"]),(1731,1727,-4))
        self.assertTrue(r["not_an_incremental_payment"])
        self.assertEqual(r["revision_published_on"],"2026-11-13")
        self.assertFalse(r["original_pre_revision_bytes_captured"])

    def test_september_hssa_revision_is_second_separate_event(self):
        out=evaluate(self.bundle)
        r=next(x for x in out["retroactive_corrections"]
               if x["id"]=="uk_sep_hssa_correction")
        self.assertEqual((r["superseded_reported"],
                          r["revised_reported"],r["revision_difference"]),(22,18,-4))
        self.assertEqual(r["data_as_of"],"2026-09-30")
        self.assertTrue(r["not_an_incremental_payment"])

    def test_component_rounding_not_false_fraud_allegation(self):
        out=evaluate(self.bundle)
        self.assertEqual(out["october_component_rounded_total"],1755)
        self.assertEqual(out["october_reported_overall_rounded_total"],1756)
        self.assertEqual(out["rounded_component_gap"],1)
        self.assertFalse(out["rounded_gap_is_an_audited_accounting_error"])

    def test_later_observation_not_prior_period_restatement(self):
        for row in evaluate(self.bundle)["period_comparisons"]:
            self.assertLess(row["earlier_data_as_of"],row["later_data_as_of"])
            self.assertEqual(row["unit"],"GBP_million")
            self.assertEqual(row["change_type"],"newer_published_cumulative_observation")

    def test_cannot_graft_dutch_euro_metric_into_uk_series(self):
        self.row("money","uk_hssa_paid")["unit"]="EUR_million"
        with self.assertRaisesRegex(ValueError,"currency"):
            evaluate(self.bundle)

    def test_spoof_october_total_source_date_is_rejected(self):
        self.row("money","uk_all_redress_oct")["data_as_of"]="2026-09-30"
        with self.assertRaisesRegex(ValueError,"currency|time|amount"):
            evaluate(self.bundle)

    def test_cannot_remove_one_correction_to_hide_revision(self):
        self.bundle["corrections"]=[x for x in self.bundle["corrections"]
                                   if x["id"]!="uk_sep_hssa_correction"]
        with self.assertRaisesRegex(ValueError,"correction"):
            evaluate(self.bundle)

    def test_cannot_claim_superseded_value_is_current(self):
        self.row("money","uk_all_redress_sep_corrected")["reported_amount"]=1731
        with self.assertRaisesRegex(ValueError,"amount"):
            evaluate(self.bundle)

    def test_cross_country_effectiveness_never_estimated(self):
        out=evaluate(self.bundle)
        self.assertFalse(out["cross_country_effectiveness_ranked"])
        self.assertFalse(out["source_reporting_truth_independently_verified"])
        self.assertFalse(out["publication_authorized"])

    def test_no_forged_semantic_causal_or_money_edge(self):
        packet=semantic_packet(self.bundle,evaluate(self.bundle))
        self.assertEqual(packet["schema"],"cite_refinery.semantic_graph.v1")
        self.assertEqual(len(packet["nodes"]),6)
        self.assertEqual(len(packet["edges"]),4)
        self.assertTrue(all(x["status"]=="candidate" for x in packet["edges"]))
        self.assertFalse(any(e["relation"] in {
            "GUILTY","PAID","REMEDIED","CAUSES","LAW_APPLIES"
        } for e in packet["edges"]))

    def test_stale_delta_packet_not_accepted(self):
        out=evaluate(self.bundle)
        self.row("sources","s_uk_moj")["scope"]+=" An unsupported change."
        with self.assertRaisesRegex(ValueError,"stale"):
            semantic_packet(self.bundle,out)

    def test_actual_cite_semantic_preview_accepts_only_candidate_revisions(self):
        from cite_refinery.app import CiteRefinery
        from cite_refinery.semantic import SemanticGraph
        packet=semantic_packet(self.bundle,evaluate(self.bundle))
        with TemporaryDirectory() as tmp:
            app=CiteRefinery(tmp)
            p=app.init_project("Official reporting periods and revisions",
                               "Change tracking with no individual or cash causality")
            graph=SemanticGraph(app.store)
            preview=graph.preview_packet(p.id,packet)
            self.assertFalse(preview["authority_boundary_warnings"])
            receipt=graph.ingest_packet(
                p.id,packet,expected_state_digest=preview["state_digest"])
            self.assertEqual(len(receipt["edge_ids"]),4)
            self.assertTrue(all(app.store.load()["semantic_edges"][i]["status"]=="candidate"
                                for i in receipt["edge_ids"]))


if __name__=="__main__":
    unittest.main()
