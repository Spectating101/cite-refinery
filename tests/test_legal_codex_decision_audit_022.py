"""022: adversarial checks against original Dutch court snapshots + attributed Indonesia ledger."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import unittest

from cite_refinery.legal_codex_decision_audit_022 import (
    BOUNDARIES, NL_CHECKPOINTS, ID_CHECKPOINTS, EXPECTED_SYNTHETIC,
    run, semantic_packet, digest,
)

INDO = Path(__file__).resolve().parents[1] / "examples/legal_codex_signature_chain_008.json"

class OfflineContract022(unittest.TestCase):
    def test_no_boundary_can_be_true(self):
        self.assertEqual(len(BOUNDARIES), 8)
        self.assertTrue(all(v is False for v in BOUNDARIES.values()))

    def test_fixed_scope_of_decision_points(self):
        ids = [r[0] for r in NL_CHECKPOINTS + ID_CHECKPOINTS]
        self.assertEqual(len(ids), 7)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(EXPECTED_SYNTHETIC), {
            "valid_purchase", "missing_appointment", "revocation_after_approval",
            "changed_package", "late_evidence_no_hindsight",
            "agency_record_missing", "waiver_after_reasoned_review",
            "recovery_after_reasoned_review", "missingness_not_considered",
        })

    def test_nocturnal_and_cite_review_schemas_are_distinct(self):
        self.assertNotIn("nocturnal_handoff", "legal_codex.decision_checkpoint_audit_022.v1")


@unittest.skipUnless(os.environ.get("LEGAL_CODEX_022_EVIDENCE"),
                     "source-dependent checks run unskipped in dedicated official-source CI")
class SourceBound022(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = Path(os.environ["LEGAL_CODEX_022_EVIDENCE"])
        cls.indonesia = json.loads(INDO.read_text(encoding="utf-8"))

    def report(self, source=None, fixture=None):
        return run(source or self.folder, fixture or self.indonesia)

    def test_three_real_originals_twelve_attributed_reports(self):
        p = self.report()
        self.assertEqual(p["source_corpus"]["dutch_verified_originals"], 3)
        self.assertEqual(p["source_corpus"]["dutch_court_anchored_facts"], 24)
        self.assertEqual(p["source_corpus"]["indonesian_source_reports"], 12)
        self.assertEqual(p["source_corpus"]["indonesian_signed_originals"], 0)

    def test_seven_provenance_anchored_checkpoints(self):
        r = self.report()
        self.assertEqual(len(r["checkpoints"]), 7)
        self.assertEqual({c["id"] for c in r["checkpoints"]}, {
            "nl_application", "nl_recovery", "nl_objection", "nl_district",
            "nl_appeal", "id_appointment", "id_order"})
        self.assertTrue(all(c["historical_actor_first_known_at"] is None for c in r["checkpoints"]))
        self.assertTrue(all(c["historical_control_deployed"] is None for c in r["checkpoints"]))

    def test_judicial_recollection_not_promoted_to_contemporaneous_fact(self):
        by = {c["id"]: c for c in self.report()["checkpoints"]}
        self.assertEqual(by["nl_recovery"]["reported_event_day"], "2024-01-05")
        self.assertEqual(by["nl_recovery"]["report_date"], "2026-03-25")
        self.assertNotEqual(by["nl_recovery"]["reported_event_day"], by["nl_recovery"]["report_date"])
        self.assertIsNone(by["nl_recovery"]["historical_actor_first_known_at"])

    def test_indonesian_allegation_is_not_original_2020_order(self):
        by = {c["id"]: c for c in self.report()["checkpoints"]}
        self.assertEqual(by["id_order"]["historical_event_evidence_tier"], "prosecution_allegation")
        self.assertFalse(by["id_order"]["assertion_adjudicated"])
        self.assertFalse(by["id_order"]["original_procurement_transaction_obtained"])
        self.assertEqual(by["id_order"]["report_date"], "2025-07-15")

    def test_reported_trial_reasoning_not_certified_original_court_pdf(self):
        by = {c["id"]: c for c in self.report()["checkpoints"]}
        self.assertEqual(by["id_appointment"]["historical_event_evidence_tier"], "court_reasoning_reported")
        self.assertFalse(by["id_appointment"]["assertion_adjudicated"])

    def test_two_disputed_2020_accounts_not_silently_reconciled(self):
        findings = self.report()["disconfirming_outcomes"]
        self.assertTrue(any(x["kind"] == "competing_2020_ppk_replacement_accounts" for x in findings))
        people = {a["id"]: a for a in self.report()["actors"]}
        self.assertIn("Bambang Hadi Waluyo", people["id_bambang"]["name"])
        self.assertIn("Wahyu Haryadi", people["id_wahyu"]["name"])
        self.assertEqual(people["nl_claimant"]["identity_status"], "anonymity_preserved_do_not_resolve")

    def test_all_actor_relations_labeled_as_reports_only(self):
        r = self.report()
        self.assertEqual(len(r["actors"]), 5)
        self.assertEqual(len(r["actor_relationships"]), 3)
        self.assertTrue(all(not x["verified_original"] for x in r["actor_relationships"]))
        self.assertTrue(any(x["competing_accounts"] for x in r["actor_relationships"]))

    def test_hearing_violation_is_not_appellate_waiver_ground(self):
        r = self.report()
        self.assertIn("hearing_breach_did_not_produce_waiver",
                      [x["kind"] for x in r["disconfirming_outcomes"]])
        self.assertIn("separate_agency_assessment_otherwise_upheld",
                      [x["kind"] for x in r["disconfirming_outcomes"]])

    def test_2021_recovery_upheld_is_disconfirming_comparator(self):
        p = self.report()
        self.assertIn("proportionality_did_not_always_waive_recovery",
                      [r["kind"] for r in p["disconfirming_outcomes"]])
        self.assertFalse(any(c["case_id"] == "child_budget_2014" for c in p["checkpoints"]))

    def test_nine_real_engine_counterfactuals_no_historical_success_rate(self):
        p = self.report()
        self.assertEqual(len(p["synthetic_control_outcomes"]), 9)
        self.assertTrue(all(x["synthetic_only"] and not x["historical_prevention_established"]
                            for x in p["synthetic_control_outcomes"]))
        self.assertIsNone(p["historical_prevention_effect"])
        self.assertEqual(p["historical_trigger_observability"], "unknown")

    def test_false_automatic_waiver_rejected_by_synthetic_outcomes(self):
        s = {x["scenario"]: x["synthetic_final_state"] for x in self.report()["synthetic_control_outcomes"]}
        self.assertEqual(s["agency_record_missing"], "HOLD_ADVERSE_COLLECTION")
        self.assertEqual(s["waiver_after_reasoned_review"], "NO_COLLECTION_SIMULATED")
        self.assertEqual(s["recovery_after_reasoned_review"], "SIMULATED_COLLECTION")

    def test_authority_must_be_revalidated_at_commit(self):
        s = {x["scenario"]: x["synthetic_final_state"] for x in self.report()["synthetic_control_outcomes"]}
        self.assertEqual(s["revocation_after_approval"], "HOLD_PURCHASE")
        self.assertEqual(s["changed_package"], "HOLD_PURCHASE")
        self.assertEqual(s["valid_purchase"], "SIMULATED_COMMIT")

    def test_late_evidence_does_not_rewrite_previous_hold(self):
        s = {x["scenario"]: x["synthetic_final_state"] for x in self.report()["synthetic_control_outcomes"]}
        self.assertEqual(s["late_evidence_no_hindsight"], "SIMULATED_COMMIT")
        self.assertEqual(s["missing_appointment"], "HOLD_PURCHASE")

    def test_five_very_specific_unsent_requests(self):
        p = self.report()
        self.assertEqual(len(p["next_original_record_targets"]), 5)
        self.assertTrue(all(x["status"] == "NOT_OBTAINED" and x["request_sent"] is False
                            for x in p["next_original_record_targets"]))
        self.assertTrue(all(not x["proof_of_who_knew_what_when"] for x in p["next_original_record_targets"]))

    def test_dutch_subject_access_mandate_remains_needed(self):
        p = self.report()
        for x in p["next_original_record_targets"]:
            if x["case_id"] == "nl_benefits_2023":
                self.assertEqual(x["required_access"], "data_subject_or_verified_representative")

    def test_originals_missing_is_not_historical_destruction(self):
        gaps = self.report()["missing_originals"]
        self.assertEqual(len(gaps), 2)
        self.assertTrue(all(x["first_known_time"] is None for x in gaps))
        self.assertTrue(all(x["historical_record_status"] == "unverified" for x in gaps))

    def test_output_declares_no_legal_guilt_or_payment(self):
        p = self.report()
        self.assertEqual(p["boundaries"], BOUNDARIES)
        self.assertTrue(all(x is False for x in BOUNDARIES.values()))
        self.assertIsNone(p["historical_prevention_effect"])

    def test_indonesia_fake_signed_original_is_rejected(self):
        f = deepcopy(self.indonesia)
        next(x for x in f["documents"] if x["id"] == "d_wahyu_replacement")["signed_document_verified"] = True
        with self.assertRaises(ValueError):
            self.report(fixture=f)

    def test_indonesia_fake_e_order_id_is_rejected(self):
        f = deepcopy(self.indonesia)
        next(x for x in f["documents"] if x["id"] == "d_sd_june30_purchase")["procurement_package_id_verified"] = True
        with self.assertRaises(ValueError):
            self.report(fixture=f)

    def test_report_conflict_removed_is_refused(self):
        f = deepcopy(self.indonesia)
        f["conflicts"] = [x for x in f["conflicts"] if x["id"] != "c_replacement_reason"]
        with self.assertRaises(ValueError):
            self.report(fixture=f)

    def test_cross_docket_document_substitution_refused(self):
        f = deepcopy(self.indonesia)
        next(x for x in f["reports"] if x["id"] == "r_prosecution_sd_click")["document_id"] = "d_smp_2020_addendum_one"
        with self.assertRaises(ValueError):
            self.report(fixture=f)

    def test_verification_refuses_forged_legal_effect_even_with_rehashed_report(self):
        r = self.report()
        r["historical_prevention_effect"] = 1.0
        r["result_sha256"] = digest({k: v for k, v in r.items() if k != "result_sha256"})
        with self.assertRaisesRegex(ValueError, "source-bound audit differs"):
            semantic_packet(r, evidence_folder=self.folder, indonesia_fixture=self.indonesia)

    def test_actor_role_tampering_refused_even_with_recomputed_hash(self):
        r = self.report()
        r["actors"][0]["role"] = "proven criminal mastermind"
        r["result_sha256"] = digest({k: v for k, v in r.items() if k != "result_sha256"})
        with self.assertRaises(ValueError):
            semantic_packet(r, evidence_folder=self.folder, indonesia_fixture=self.indonesia)

    def test_no_native_graph_promotion_for_candidate_edges(self):
        r = self.report()
        p = semantic_packet(r, evidence_folder=self.folder, indonesia_fixture=self.indonesia)
        self.assertEqual(len(p["nodes"]), 24)
        self.assertEqual(len(p["edges"]), 15)
        self.assertTrue(all(x["status"] == "candidate" for x in p["edges"]))
        self.assertFalse(any(x["relation"] in {"GUILTY", "PREVENTED", "ORIGINAL_SIGNED", "CAUSED"}
                             for x in p["edges"]))

    def test_actual_cite_graph_ingestion(self):
        from cite_refinery.app import CiteRefinery
        from cite_refinery.semantic import SemanticGraph
        r = self.report()
        packet = semantic_packet(r, evidence_folder=self.folder, indonesia_fixture=self.indonesia)
        with TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project = app.init_project("022 cross-case audit", "Candidate-only judicial reconstruction")
            graph = SemanticGraph(app.store)
            preview = graph.preview_packet(project.id, packet)
            self.assertFalse(preview["authority_boundary_warnings"])
            receipt = graph.ingest_packet(project.id, packet, expected_state_digest=preview["state_digest"])
            self.assertEqual(len(receipt["edge_ids"]), len(packet["edges"]))
            self.assertTrue(all(app.store.load()["semantic_edges"][e]["status"] == "candidate"
                                for e in receipt["edge_ids"]))

    def test_verified_original_xml_mutation_rejected(self):
        with TemporaryDirectory() as tmp:
            from shutil import copytree
            root = Path(tmp) / "source"
            copytree(self.folder, root)
            path = root / "appeal_2026.xml"
            path.write_bytes(path.read_bytes() + b" x ")
            with self.assertRaises(ValueError):
                self.report(source=root)

    def test_no_skips_in_live_run(self):
        self.assertTrue(self.folder.joinpath("district_2025.xml").exists())
        self.assertTrue(self.folder.joinpath("appeal_2026.xml").exists())
        self.assertTrue(self.folder.joinpath("comparator_2021.xml").exists())


if __name__ == "__main__":
    unittest.main()
