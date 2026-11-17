"""Independent expected states for 016; the replay never sees these expectations."""
from copy import deepcopy
from itertools import product
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.legal_codex_control_replay import digest, replay, semantic_packet
from cite_refinery.legal_codex_control_scenarios import (
    appointment, at, bundle, check, commit, event, human_review, obj,
    package, procurement, recovery, scenarios,
)

# A behavioral oracle for this curated challenge set, NOT measured real-world harm.
EXPECTED = {
    "valid_purchase": "SIMULATED_COMMIT",
    "missing_appointment": "HOLD_PURCHASE",
    "future_appointment": "HOLD_PURCHASE",
    "wrong_officer": "HOLD_PURCHASE",
    "wrong_scope": "HOLD_PURCHASE",
    "excess_amount": "HOLD_PURCHASE",
    "expiry_between_check_and_commit": "HOLD_PURCHASE",
    "revocation_after_approval": "HOLD_PURCHASE",
    "changed_package": "HOLD_PURCHASE",
    "actor_swap": "HOLD_PURCHASE",
    "reused_approval": "HOLD_PURCHASE",
    "direct_execution_bypass": "HOLD_PURCHASE",
    "unsupported_override": "HOLD_PURCHASE",
    "late_evidence_no_hindsight": "SIMULATED_COMMIT",
    "agency_record_missing": "HOLD_ADVERSE_COLLECTION",
    "waiver_after_reasoned_review": "NO_COLLECTION_SIMULATED",
    "recovery_after_reasoned_review": "SIMULATED_COLLECTION",
    "claimant_document_missing": "HOLD_ADVERSE_COLLECTION",
    "reviewer_conflict": "HOLD_ADVERSE_COLLECTION",
    "stale_review_after_new_record": "HOLD_ADVERSE_COLLECTION",
    "missingness_not_considered": "HOLD_ADVERSE_COLLECTION",
    "overdue_review": "ESCALATE_UNRESOLVED_REVIEW",
    "collection_replay": "HOLD_ADVERSE_COLLECTION",
    "wrong_case_review": "HOLD_ADVERSE_COLLECTION",
}


class DecisionReplay016Tests(unittest.TestCase):
    def scenario(self, ident):
        return next(x for x in scenarios() if x["scenario_id"] == ident)

    def test_all_curated_outcomes_without_passing_oracle_into_engine(self):
        cases = scenarios()
        self.assertEqual(set(EXPECTED), {b["scenario_id"] for b in cases})
        for case in cases:
            with self.subTest(case=case["scenario_id"]):
                result = replay(case)
                self.assertEqual(result["trace"][-1]["status"], EXPECTED[case["scenario_id"]])
                self.assertFalse(result["historical_prevention_established"])
                self.assertFalse(result["real_transaction_executed"])
                self.assertFalse(result["real_collection_executed"])
                self.assertFalse(result["publication_authorized"])

    def test_late_evidence_does_not_rewrite_failed_earlier_attempt(self):
        b = self.scenario("late_evidence_no_hindsight")
        full = replay(b)
        prefix = deepcopy(b); prefix["events"] = prefix["events"][:3]
        earlier = replay(prefix)
        self.assertEqual(full["trace"][:3], earlier["trace"])
        self.assertEqual(full["trace"][2]["status"], "HOLD_PURCHASE")
        self.assertEqual(full["trace"][-1]["status"], "SIMULATED_COMMIT")

    def test_evidence_unobserved_in_object_bag_cannot_be_used_early(self):
        b = procurement("hidden_evidence", evidence=False)
        check(b);commit(b)
        result = replay(b)
        self.assertIn("appointment_not_available_at_decision", result["trace"][-2]["reasons"])
        self.assertEqual(result["trace"][-1]["status"],"HOLD_PURCHASE")

    def test_expiry_checked_at_commit_not_only_at_prior_approval(self):
        rows = replay(self.scenario("expiry_between_check_and_commit"))["trace"]
        self.assertEqual(rows[-2]["status"], "READY_FOR_SIMULATED_COMMIT")
        self.assertIn("outside_appointment_validity", rows[-1]["reasons"])

    def test_revocation_invalidates_prior_approval(self):
        rows = replay(self.scenario("revocation_after_approval"))["trace"]
        self.assertIn("appointment_revoked", rows[-1]["reasons"])
        self.assertEqual(rows[-3]["status"], "READY_FOR_SIMULATED_COMMIT")

    def test_updated_package_invalidates_prior_approval_even_within_budget(self):
        rows = replay(self.scenario("changed_package"))["trace"]
        self.assertIn("proposal_changed_after_approval", rows[-1]["reasons"])
        self.assertNotIn("delegation_amount_exceeded",rows[-1]["reasons"])

    def test_scope_date_identity_currency_limit_combinations(self):
        # 32 synthetic combinations: all predicates must hold at actual decision time.
        for future, wrong_subject, wrong_scope, too_much, wrong_currency in product((False,True),repeat=5):
            with self.subTest(flags=(future,wrong_subject,wrong_scope,too_much,wrong_currency)):
                b=procurement("matrix", effective_from=at(10 if future else -10),
                    subject="other" if wrong_subject else "test-officer",
                    package_ids=["different" if wrong_scope else "fictional-package"],
                    limit_minor=9999 if too_much else 20000,
                    currency="EUR" if wrong_currency else "IDR")
                check(b);commit(b)
                self.assertEqual(replay(b)["trace"][-1]["status"],
                    "HOLD_PURCHASE" if any((future,wrong_subject,wrong_scope,too_much,wrong_currency))
                    else "SIMULATED_COMMIT")

    def test_digest_tampering_rejected_before_any_replay(self):
        b=self.scenario("valid_purchase")
        b["objects"][0]["body"]["amount_minor"]=1
        with self.assertRaisesRegex(ValueError,"digest mismatch"):
            replay(b)

    def test_recomputed_hash_is_not_a_signature(self):
        b=self.scenario("valid_purchase")
        b["objects"][0]["body"]["amount_minor"]=100
        b["objects"][0]["sha256"]=digest(b["objects"][0]["body"])
        result=replay(b)
        self.assertFalse(result["source_authenticity_established"])
        self.assertFalse(result["historical_legality_decided"])

    def test_reject_real_operational_label(self):
        b=self.scenario("valid_purchase");b["mode"]="real_case_log"
        with self.assertRaisesRegex(ValueError,"synthetic"):
            replay(b)

    def test_unknown_payload_fields_cannot_hide_historical_prevention_claim(self):
        b=self.scenario("valid_purchase");b["historical_prevention_proven"]=True
        with self.assertRaisesRegex(ValueError,"unsupported replay fields"):
            replay(b)

    def test_reject_out_of_order_recorded_events(self):
        b=self.scenario("valid_purchase");b["events"][-1]["at"]=at(-1)
        with self.assertRaisesRegex(ValueError,"backdated"):
            replay(b)

    def test_reject_naive_timestamps(self):
        b=self.scenario("valid_purchase");b["events"][0]["at"]="2020-07-01T08:00:00"
        with self.assertRaisesRegex(ValueError,"timezone"):
            replay(b)

    def test_duplicate_event_identity_rejected(self):
        b=self.scenario("valid_purchase");b["events"].append(deepcopy(b["events"][-1]))
        with self.assertRaisesRegex(ValueError,"duplicate event"):
            replay(b)

    def test_negative_or_boolean_money_rejected(self):
        for amount in (-1, True, 3.5):
            b=self.scenario("valid_purchase")
            b["objects"][0]["body"]["amount_minor"]=amount
            b["objects"][0]["sha256"]=digest(b["objects"][0]["body"])
            with self.assertRaisesRegex(ValueError,"integer minor"):
                replay(b)

    def test_foreign_policy_cannot_be_applied(self):
        b=self.scenario("valid_purchase");b["jurisdiction"]="Netherlands"
        with self.assertRaisesRegex(ValueError,"jurisdiction mismatch"):
            replay(b)

    def test_wrong_case_package_not_accepted(self):
        b=procurement("wrong_case")
        b["objects"][0]["body"]["case_id"]="other-case"
        b["objects"][0]["sha256"]=digest(b["objects"][0]["body"])
        check(b);commit(b)
        self.assertEqual(replay(b)["trace"][-1]["status"],"HOLD_PURCHASE")

    def test_missing_agency_record_is_not_claimant_fault_or_automatic_debt(self):
        rows=replay(self.scenario("agency_record_missing"))["trace"]
        self.assertEqual(rows[-2]["status"],"PROTECTIVE_REVIEW")
        self.assertEqual(rows[-1]["status"],"HOLD_ADVERSE_COLLECTION")
        self.assertFalse(any(r["status"] in {"CLAIMANT_AT_FAULT","ENTITLEMENT_DENIED"} for r in rows))

    def test_missing_claimant_record_is_not_automatic_waiver(self):
        rows=replay(self.scenario("claimant_document_missing"))["trace"]
        self.assertEqual(rows[-2]["status"],"HUMAN_REVIEW_REQUIRED")
        self.assertFalse(any(r["status"]=="NO_COLLECTION_SIMULATED" for r in rows))

    def test_same_review_gate_can_preserve_opposite_human_outcomes(self):
        waive=replay(self.scenario("waiver_after_reasoned_review"))
        uphold=replay(self.scenario("recovery_after_reasoned_review"))
        self.assertEqual(waive["trace"][-1]["status"],"NO_COLLECTION_SIMULATED")
        self.assertEqual(uphold["trace"][-1]["status"],"SIMULATED_COLLECTION")
        self.assertFalse(waive["real_collection_executed"])
        self.assertFalse(uphold["historical_legality_decided"])

    def test_review_records_missingness_explicitly(self):
        rows=replay(self.scenario("missingness_not_considered"))["trace"]
        self.assertIn("missing_records_not_addressed", rows[-2]["reasons"])

    def test_new_record_invalidates_previously_accepted_review(self):
        rows=replay(self.scenario("stale_review_after_new_record"))["trace"]
        self.assertIn("evidence_changed_after_review",rows[-1]["reasons"])

    def test_deadline_escalates_without_automatically_waiving_or_collecting(self):
        rows=replay(self.scenario("overdue_review"))["trace"]
        self.assertEqual(rows[-1]["status"],"ESCALATE_UNRESOLVED_REVIEW")
        self.assertFalse(any(r["status"] in {"SIMULATED_COLLECTION","NO_COLLECTION_SIMULATED"} for r in rows))

    def test_future_dated_review_rejected(self):
        b=recovery("future_review")
        human_review(b,decided=50,record_at=4)
        event(b,"collection",5,"collect",review_event="review")
        rows=replay(b)["trace"]
        self.assertIn("review_not_yet_decided",rows[-2]["reasons"])
        self.assertEqual(rows[-1]["status"],"HOLD_ADVERSE_COLLECTION")

    def test_review_amount_cannot_exceed_proposal_or_conflict_with_waiver(self):
        b=recovery("bad_amount");human_review(b,remaining=12000)
        event(b,"collection",5,"collect",review_event="review")
        self.assertIn("review_disposition_amount_conflict",replay(b)["trace"][-2]["reasons"])

    def test_reasoned_mitigation_not_only_all_or_nothing(self):
        b=recovery("partial_remedy");human_review(b,disposition="mitigate",remaining=5000)
        event(b,"collection",5,"collect",review_event="review")
        self.assertEqual(replay(b)["trace"][-1]["status"],"SIMULATED_COLLECTION")

    def test_stale_or_modified_report_graph_is_refused(self):
        b=self.scenario("valid_purchase");r=replay(b)
        r["trace"][-1]["status"]="PREVENTED_CORRUPTION"
        with self.assertRaisesRegex(ValueError,"fabricated"):
            semantic_packet(b,r)

    def test_graph_is_explicitly_synthetic_candidate_only(self):
        b=self.scenario("valid_purchase");p=semantic_packet(b,replay(b))
        self.assertTrue(all(n["provenance"]["synthetic"] for n in p["nodes"]))
        self.assertTrue(all(e["status"]=="candidate" for e in p["edges"]))
        self.assertFalse(any(e["relation"] in {"PREVENTED","GUILTY","PAID","LAW_APPLIES"} for e in p["edges"]))

    def test_replay_is_deterministic_and_does_not_mutate_input(self):
        b=self.scenario("late_evidence_no_hindsight");before=deepcopy(b)
        self.assertEqual(replay(b),replay(b))
        self.assertEqual(b,before)

    def test_event_chain_links_exact_predecessors(self):
        rows=replay(self.scenario("valid_purchase"))["trace"]
        self.assertIsNone(rows[0]["previous_event_sha256"])
        for old,new in zip(rows,rows[1:]):
            self.assertEqual(old["event_sha256"],new["previous_event_sha256"])
            self.assertEqual(new["event_sha256"],digest({k:v for k,v in new.items() if k!="event_sha256"}))

    def test_new_approval_cannot_execute_same_purchase_twice(self):
        b=self.scenario("valid_purchase")
        check(b,4,"approval_again");commit(b,5,"second_commit","approval_again")
        rows=replay(b)["trace"]
        self.assertEqual(sum(x["status"]=="SIMULATED_COMMIT" for x in rows),1)
        self.assertEqual(rows[-1]["status"],"HOLD_PURCHASE")

    def test_changing_package_back_does_not_resurrect_old_approval(self):
        b=procurement("package_rollback");check(b)
        package(b,"p2",amount_minor=15000)
        event(b,"change",3,"propose",object_id="p2")
        event(b,"restore",4,"propose",object_id="p1")
        commit(b,5)
        self.assertEqual(replay(b)["trace"][-1]["status"],"HOLD_PURCHASE")

    def test_backdated_review_cannot_claim_to_consider_later_evidence(self):
        b=recovery("backdated_review")
        human_review(b,disposition="uphold",remaining=10000,decided=0,record_at=4)
        event(b,"collection",5,"collect",review_event="review")
        self.assertEqual(replay(b)["trace"][-1]["status"],"HOLD_ADVERSE_COLLECTION")

    def test_new_review_cannot_collect_same_one_shot_debt_twice(self):
        b=recovery("double_debt")
        human_review(b,disposition="uphold",remaining=10000)
        event(b,"collection",5,"collect",review_event="review")
        second=deepcopy(next(o for o in b["objects"] if o["id"]=="r1"))
        second["id"]="r2";second["body"]["decided_at"]=at(6)
        second["sha256"]=digest(second["body"]);b["objects"].append(second)
        event(b,"second_review",6,"review",object_id="r2")
        event(b,"second_collection",7,"collect",review_event="second_review")
        rows=replay(b)["trace"]
        self.assertEqual(sum(x["status"]=="SIMULATED_COLLECTION" for x in rows),1)

    def test_native_cite_graph_ingestion(self):
        try:
            from cite_refinery.app import CiteRefinery
            from cite_refinery.semantic import SemanticGraph
        except ModuleNotFoundError:
            self.skipTest("full repository unavailable in isolated assistant module workspace; required in repository CI")
        b=self.scenario("agency_record_missing")
        packet=semantic_packet(b,replay(b))
        with TemporaryDirectory() as path:
            app=CiteRefinery(path);project=app.init_project("Synthetic decision replay","No observed prevention claims")
            graph=SemanticGraph(app.store);preview=graph.preview_packet(project.id,packet)
            self.assertFalse(preview["authority_boundary_warnings"])
            receipt=graph.ingest_packet(project.id,packet,expected_state_digest=preview["state_digest"])
            self.assertEqual(len(receipt["edge_ids"]),len(packet["edges"]))
            self.assertTrue(all(app.store.load()["semantic_edges"][i]["status"]=="candidate"
                                for i in receipt["edge_ids"]))

    def test_015_boolean_gate_is_not_a_live_authorization_adapter(self):
        try:
            from cite_refinery.legal_codex_prevention_edges import simulate_precommit_gate
        except ModuleNotFoundError:
            self.skipTest("015 module available only in full repository CI")
        baseline=simulate_precommit_gate(appointment_original_verified=True,effective_date_covers_order=True,
                    role_scope_covers_order=True,proposed_package_identity_verified=True)
        self.assertEqual(baseline["result"],"proposed_order_may_enter_approval_flow")
        self.assertFalse(baseline["actual_purchase_executed"])
        self.assertEqual(replay(self.scenario("expiry_between_check_and_commit"))["trace"][-1]["status"],"HOLD_PURCHASE")


if __name__=="__main__":
    unittest.main()
