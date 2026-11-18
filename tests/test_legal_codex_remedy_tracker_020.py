"""Synthetic adversarial behavior tests; counts are not legal accuracy estimates."""
from copy import deepcopy
import hashlib
import unittest

from cite_refinery.legal_codex_remedy_tracker import evaluate, semantic_packet, SCHEMA


class SyntheticRemedy020Tests(unittest.TestCase):
    def setUp(self):
        self.sources = {}
        self.ledger = {"schema": SCHEMA, "sources": {}, "obligations": [
            {"id": "logs", "case_id": "ECLI:TEST:2026:1", "label": "Synthetic log explanation", "scope": "log_explanation"}], "events": []}
        self.add_source("s1", "2026-10-10", "2026-10-01")

    def add_source(self, sid, available, source_date, identity="ECLI:TEST:2026:1"):
        text = "Synthetic public evidence; original case ECLI:TEST:2026:1. No real person or event."
        digest = hashlib.sha256(text.encode()).hexdigest()
        self.sources[sid] = {"identity": identity, "date": source_date,
            "source_url": "https://example.invalid/" + sid, "raw_sha256": digest,
            "captured_at": "2026-11-18T10:00:00+00:00", "metadata": {"publication_values": [available]},
            "blocks": [{"id": "p1", "text": text, "sha256": digest}]}
        self.ledger["sources"][sid] = {"available_on": available, "publication_basis": "Synthetic fixture publication date."}

    def event(self, kind, occurred="2026-09-30", role="court_finding", sid="s1", oid="logs", **extra):
        row = {"id": f"e{len(self.ledger['events']) + 1}", "obligation_id": oid, "kind": kind,
            "source_id": sid, "block_id": "p1", "block_sha256": self.sources[sid]["blocks"][0]["sha256"],
            "occurred_on": occurred, "role": role, "label": "Synthetic " + kind, **extra}
        self.ledger["events"].append(row)
        return row

    def report(self, when="2026-11-18"):
        return evaluate(self.ledger, self.sources, when)

    def state(self, when="2026-11-18"):
        return self.report(when)["obligations"][0]

    def test_request_fulfilled_as_reported_without_original_record_custody(self):
        self.event("request_reported", "2026-08-01")
        self.event("receipt_reported", "2026-09-07", role="court_records_claimant_confirmation")
        self.event("fulfillment_confirmed", "2026-09-30")
        self.assertEqual(self.state()["fulfillment"], "confirmed_by_public_source")
        self.assertFalse(self.report()["original_record_custody"])
        self.assertFalse(self.report()["operational_replay_allowed"])

    def test_prior_receipt_does_not_fulfill_later_explanation_order(self):
        receipt = self.event("receipt_reported", "2026-09-07")
        self.event("fulfillment_confirmed", "2026-09-07")
        self.event("order_reported", "2026-09-30", role="operative_order")
        state = self.state()
        self.assertEqual(state["pre_order_receipt_ids"], [receipt["id"]])
        self.assertEqual(state["fulfillment"], "unverified")
        self.assertEqual(state["historical_confirmation_ids"], ["e2"])

    def test_later_receipt_alone_is_not_post_order_confirmation(self):
        self.event("order_reported", "2026-09-20")
        self.event("receipt_reported", "2026-09-30")
        self.assertEqual(self.state()["post_order_receipt_ids"], ["e2"])
        self.assertEqual(self.state()["fulfillment"], "unverified")

    def test_later_confirmation_requires_exact_order_reference(self):
        order = self.event("order_reported", "2026-09-20")
        confirmation = self.event("fulfillment_confirmed", "2026-09-30")
        self.assertEqual(self.state()["fulfillment"], "unverified")
        confirmation["fulfills_order_id"] = order["id"]
        self.assertEqual(self.state()["fulfillment"], "confirmed_by_public_source")

    def test_latest_order_confirmation_cannot_close_older_active_order(self):
        older = self.event("order_reported", "2026-09-10")
        latest = self.event("order_reported", "2026-09-20")
        self.event("fulfillment_confirmed", "2026-09-30", fulfills_order_id=latest["id"])
        self.assertEqual(self.state()["active_order_count"], 2)
        self.assertEqual(self.state()["fulfillment"], "unverified")
        latest["supersedes"] = [older["id"]]
        self.assertEqual(self.state()["active_order_count"], 1)
        self.assertEqual(self.state()["fulfillment"], "confirmed_by_public_source")

    def test_explicit_reference_cannot_make_pre_order_confirmation_valid(self):
        order = self.event("order_reported", "2026-09-30")
        self.event("fulfillment_confirmed", "2026-09-07", fulfills_order_id=order["id"])
        with self.assertRaisesRegex(ValueError, "predate"):
            self.report()

    def test_confirmation_does_not_cross_obligation_scope(self):
        self.ledger["obligations"].append({"id": "copy", "case_id": "ECLI:TEST:2026:1", "label": "Synthetic copy", "scope": "medical_copy"})
        order = self.event("order_reported")
        self.event("fulfillment_confirmed", oid="copy")
        result = self.report()
        self.assertEqual(result["confirmed_obligation_count"], 1)
        self.assertEqual(result["obligations"][0]["fulfillment"], "unverified")
        self.ledger["events"][1]["fulfills_order_id"] = order["id"]
        with self.assertRaisesRegex(ValueError, "exact obligation"):
            self.report()

    def test_late_publication_does_not_rewrite_earlier_public_view(self):
        self.event("receipt_reported", "2026-09-07")
        self.event("fulfillment_confirmed", "2026-09-30")
        self.assertEqual(self.report("2026-10-09")["events"], [])
        self.assertEqual(self.report("2026-10-09")["confirmed_obligation_count"], 0)
        self.assertEqual(self.report("2026-10-10")["confirmed_obligation_count"], 1)

    def test_remedial_decision_and_assurance_do_not_prove_delivery(self):
        self.event("remedial_decision_reported")
        self.event("assurance_of_compliance", role="controller_statement")
        state = self.state()
        self.assertTrue(state["remedial_decision_reported"])
        self.assertTrue(state["assurance_reported"])
        self.assertEqual(state["delivery"], "unverified")
        self.assertEqual(state["fulfillment"], "unverified")

    def test_case_citation_does_not_move_evidence_between_proceedings(self):
        self.add_source("other", "2026-10-10", "2026-10-01", "ECLI:TEST:2026:2")
        self.event("fulfillment_confirmed", sid="other")
        with self.assertRaisesRegex(ValueError, "different proceeding"):
            self.report()

    def test_explicit_proceeding_review_is_a_curated_link_not_semantic_verification(self):
        self.add_source("other", "2026-10-10", "2026-10-01", "ECLI:TEST:2026:2")
        event = self.event("fulfillment_confirmed", sid="other")
        self.ledger["case_links"] = [{"source_id": "other", "block_id": "p1", "block_sha256": event["block_sha256"],
            "case_id": "ECLI:TEST:2026:1", "relationship": "reviewed_same_proceeding", "review_note": "Synthetic explicitly reviewed proceeding link."}]
        self.assertEqual(self.state()["fulfillment"], "confirmed_by_public_source")
        self.assertFalse(self.report()["independent_legal_interpretation_reviewed"])
        self.ledger["case_links"][0]["relationship"] = "citation"
        with self.assertRaisesRegex(ValueError, "citation alone"):
            self.report()

    def test_source_or_evidence_hash_tampering_is_rejected(self):
        event = self.event("receipt_reported")
        event["block_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.report()
        event["block_sha256"] = self.sources["s1"]["blocks"][0]["sha256"]
        self.sources["s1"]["blocks"][0]["text"] = "Changed evidence"
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.report()

    def test_controller_assertion_cannot_be_authoritative_fulfillment(self):
        self.event("fulfillment_confirmed", role="controller_statement")
        with self.assertRaisesRegex(ValueError, "party assertion"):
            self.report()

    def test_duplicate_event_ids_are_rejected(self):
        event = self.event("receipt_reported")
        self.ledger["events"].append(deepcopy(event))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.report()

    def test_conflicting_delivery_assertions_do_not_resolve_by_majority(self):
        self.event("receipt_reported")
        self.event("receipt_reported")
        self.event("nonreceipt_reported", role="claimant_statement")
        self.event("fulfillment_confirmed")
        self.assertEqual(self.state()["delivery"], "contested")
        self.assertEqual(self.state()["fulfillment"], "contested")

    def test_explicit_later_resolution_preserves_old_public_view(self):
        old = self.event("nonreceipt_reported", role="claimant_statement")
        self.add_source("later", "2026-11-10", "2026-11-01")
        self.event("receipt_reported", "2026-10-20", sid="later", supersedes=[old["id"]])
        self.assertEqual(self.state("2026-10-31")["delivery"], "nonreceipt_reported")
        self.assertEqual(self.state()["delivery"], "receipt_reported")
        self.assertEqual(self.state()["superseded_event_ids"], [old["id"]])

    def test_party_statement_cannot_erase_authoritative_finding(self):
        old = self.event("inadequacy_found", "2026-09-20")
        self.event("adequacy_confirmed", "2026-09-30", role="controller_statement", supersedes=[old["id"]])
        with self.assertRaisesRegex(ValueError, "party assertion"):
            self.report()

    def test_supersedes_cannot_cross_dimensions_or_reverse_time(self):
        old = self.event("nonreceipt_reported", "2026-09-20")
        newer = self.event("receipt_reported", "2026-09-10", supersedes=[old["id"]])
        with self.assertRaisesRegex(ValueError, "strictly later"):
            self.report()
        newer["occurred_on"] = "2026-09-30"
        newer["kind"] = "fulfillment_confirmed"
        with self.assertRaisesRegex(ValueError, "same obligation and dimension"):
            self.report()

    def test_elapsed_review_date_does_not_infer_breach_or_penalty_accrual(self):
        order = self.event("order_reported")
        self.event("penalty_ordered")
        self.ledger["obligations"][0]["deadline"] = {"literal": "Synthetic one-month order", "due_on": "2026-10-30",
            "basis": {k: order[k] for k in ("source_id", "block_id", "block_sha256")},
            "review_note": "Synthetic manually reviewed calendar checkpoint; no legal default calculation."}
        state = self.state()
        self.assertEqual(state["deadline_status"], "review_due")
        self.assertEqual(state["fulfillment"], "unverified")
        self.assertFalse(state["breach_inferred_from_elapsed_time"])
        self.assertEqual(state["penalty_accrual"], "unverified")
        self.assertEqual(state["penalty_payment"], "unverified")

    def test_literal_month_deadline_without_reviewed_anchor_is_not_30_days(self):
        order = self.event("order_reported")
        self.ledger["obligations"][0]["deadline"] = {"literal": "Within one month of service",
            "basis": {k: order[k] for k in ("source_id", "block_id", "block_sha256")}}
        self.assertEqual(self.state()["deadline_status"], "not_calculated")
        self.assertIsNone(self.state()["deadline"].get("due_on"))

    def test_literal_deadline_requires_source_provenance(self):
        self.event("order_reported")
        self.ledger["obligations"][0]["deadline"] = {"literal": "Within one month of service"}
        with self.assertRaisesRegex(ValueError, "unconfigured evidence source"):
            self.report()

    def test_later_deadline_details_stay_hidden_despite_visible_earlier_request(self):
        self.event("request_reported", "2026-09-01")
        self.add_source("later", "2026-11-10", "2026-11-01")
        order = self.event("order_reported", "2026-11-01", sid="later")
        deadline = {"literal": "Synthetic deadline first stated in the later decision", "due_on": "2026-12-01",
            "basis": {k: order[k] for k in ("source_id", "block_id", "block_sha256")},
            "review_note": "Synthetic explicitly reviewed checkpoint."}
        self.ledger["obligations"][0]["deadline"] = deadline
        before = self.state("2026-10-31")
        self.assertEqual(before["event_ids"], ["e1"])
        self.assertIsNone(before["deadline"])
        self.assertEqual(before["deadline_status"], "not_yet_publicly_evidenced")
        self.assertEqual(self.state()["deadline"], deadline)
        del deadline["due_on"]
        self.assertIsNone(self.state("2026-10-31")["deadline"])
        self.assertEqual(self.state()["deadline"]["literal"], deadline["literal"])

    def test_source_publication_delay_cannot_supply_post_decision_facts(self):
        self.event("receipt_reported", "2026-10-05")
        # Source decision is October 1 and publication is October 10.
        with self.assertRaisesRegex(ValueError, "after the source decision date"):
            self.report()

    def test_missing_records_and_no_further_order_are_not_fulfillment_or_right_denial(self):
        self.event("record_unavailable_reported", role="regulator_records_controller_submission")
        self.event("nonfulfillment_confirmed", role="regulator_finding")
        self.event("further_order_not_issued", role="regulator_finding")
        state = self.state()
        self.assertEqual(state["disposition"], "further_order_not_issued")
        self.assertEqual(state["fulfillment"], "nonfulfillment_confirmed_by_public_source")
        self.assertTrue(state["record_unavailable_reported"])
        self.assertFalse(state["intentional_deletion_inferred"])

    def test_capture_visibility_requires_actual_capture_date(self):
        self.ledger["sources"]["s1"].update(available_on="2026-11-18", availability_basis="first_verified_capture")
        self.event("receipt_reported")
        self.assertEqual(self.report("2026-11-17")["events"], [])
        self.assertEqual(len(self.report()["events"]), 1)
        self.ledger["sources"]["s1"]["available_on"] = "2026-11-10"
        with self.assertRaisesRegex(ValueError, "capture"):
            self.report()

    def test_source_finality_and_conflicting_dates_are_preserved(self):
        self.sources["s1"]["decision_finality"] = "explicitly_not_final"
        self.ledger["obligations"][0]["data_quality_flags"] = ["Two published end dates differ; unresolved."]
        self.event("partial_receipt_reported", data_quality_flags=["Do not repair the source date silently."])
        result = self.report()
        self.assertEqual(result["sources"][0]["decision_finality"], "explicitly_not_final")
        self.assertEqual(len(result["obligations"][0]["data_quality_flags"]), 2)
        self.assertEqual(result["obligations"][0]["delivery"], "partial_receipt_reported")
        self.assertEqual(self.report("2026-10-09")["obligations"][0]["data_quality_flags"], [])
        self.assertFalse(result["sources"][0]["historical_version_verified"])
        self.assertIn("Publication-date filter", result["sources"][0]["visibility_note"])

    def test_candidate_graph_preserves_scope_without_claiming_actual_execution(self):
        self.event("receipt_reported")
        self.event("order_reported")
        packet = semantic_packet(self.ledger, self.sources, "2026-11-18")
        self.assertEqual(len(packet["edges"]), 4)
        self.assertTrue(all(e["status"] == "candidate" for e in packet["edges"]))
        self.assertEqual({e["relation"] for e in packet["edges"]}, {"REPORTS_SCOPED_REMEDY_EVENT", "CONCERNS_EXACT_OBLIGATION"})
        self.assertEqual(semantic_packet(self.ledger, self.sources, "2026-10-09")["nodes"], [])


if __name__ == "__main__":
    unittest.main()
