"""Real-source Chromebook authority chronology: adversarial safety checks.

Exact source authenticity and source meaning are not decided by these tests.
The two live-capture SHA receipts are historical CI metadata, not a public
permanent archive of the source HTML.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.legal_codex_authority import validate, evaluate, semantic_packet
from cite_refinery.app import CiteRefinery
from cite_refinery.semantic import SemanticGraph

DATA = Path(__file__).resolve().parents[1] / "examples/legal_codex_chromebook_source_audit_v1.json"


class ChromebookAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(DATA.read_text(encoding="utf-8"))

    def observe(self, ident):
        return next(o for o in self.fixture["observations"] if o["id"] == ident)

    def test_full_reconstruction_keeps_unresolved_sides_separate(self):
        result = evaluate(self.fixture)
        self.assertEqual(result["source_count"], 11)
        self.assertEqual(result["actor_count"], 14)
        self.assertEqual(result["observation_count"], 22)
        self.assertEqual(len(result["disputes"]), 8)
        self.assertFalse(result["personal_guilt_assessed_by_system"])
        self.assertFalse(result["actor_decision_authority_verified"])
        self.assertFalse(result["publication_authorized"])
        self.assertIn("external_witness_as_reported", result["stance_counts"])
        self.assertIn("prosecution_allegation", result["stance_counts"])

    def test_two_real_nocturnal_source_capture_receipts_are_narrow(self):
        captured = [x["capture_receipt"] for x in self.fixture["sources"]
                    if x.get("capture_receipt")]
        self.assertEqual(len(captured), 2)
        self.assertEqual({x["workflow_run"] for x in captured}, {42820272488})
        self.assertTrue(all(len(x["raw_sha256"]) == 64 for x in captured))
        self.assertTrue(all(s["original_document_bytes_archived"] is False
                            and s["claim_truth_authenticated"] is False
                            for s in self.fixture["sources"]))

    def test_admin_mapping_is_not_usage_rate(self):
        result = evaluate(self.fixture)
        mapped = [x["metric"] for x in result["timeline"] if x["metric"]]
        self.assertEqual({(m["population"], m["value"]) for m in mapped},
                         {("APBN_Pusat", 98.82), ("DAK_Fisik", 61.27)})
        self.assertFalse(result["actual_use_rate_measured"])
        self.assertFalse(result["mapping_counts_are_use_rates"])

    def test_false_usage_rate_label_rejected(self):
        self.observe("mapped_apbn")["metric"]["name"] = "device_utilization_rate"
        with self.assertRaisesRegex(ValueError, "mapping coverage"):
            validate(self.fixture)

    def test_wrong_date_or_source_publication_rejected(self):
        self.observe("may2020_instruction")["reported_at"] = "2020-05-06"
        with self.assertRaisesRegex(ValueError, "reported-at"):
            validate(self.fixture)

    def test_prosecutor_claim_cannot_become_court_finding(self):
        self.observe("may2020_instruction")["stance"] = "court_disposition_as_indexed"
        with self.assertRaisesRegex(ValueError, "court disposition"):
            validate(self.fixture)

    def test_defense_claim_cannot_masquerade_as_prosecutor(self):
        self.observe("nadiem_defense")["stance"] = "prosecution_allegation"
        with self.assertRaisesRegex(ValueError, "prosecution claim"):
            validate(self.fixture)

    def test_factual_truth_upgrade_rejected(self):
        self.observe("fiona_messages")["factual_truth_established"] = True
        with self.assertRaisesRegex(ValueError, "may not upgrade"):
            validate(self.fixture)

    def test_fabricated_source_authentication_rejected(self):
        self.fixture["sources"][0]["claim_truth_authenticated"] = True
        with self.assertRaisesRegex(ValueError, "auto-certified"):
            validate(self.fixture)

    def test_fabricated_capture_digest_rejected(self):
        self.fixture["sources"][0]["capture_receipt"]["raw_sha256"] = "malformed"
        with self.assertRaisesRegex(ValueError, "capture receipt"):
            validate(self.fixture)

    def test_unresolved_dispute_cannot_be_declared_proven(self):
        self.fixture["issues"][0]["verdict"] = "fraud_proven"
        with self.assertRaisesRegex(ValueError, "unsupported dispute resolution"):
            validate(self.fixture)

    def test_2021_regulation_does_not_claim_all_funding_streams(self):
        result = evaluate(self.fixture)
        self.assertEqual(result["regulatory_applicability_to_all_funding_streams"], "not_established")
        rule = self.observe("reg_rule_scope")
        self.assertEqual(rule["effective_from"], "2021-02-11")
        self.assertIn("not automatically", rule["statement"])

    def test_original_2020_ministry_manual_is_month_precise_and_not_outcome_proof(self):
        result = evaluate(self.fixture)
        manual = next(x for x in self.fixture["sources"]
                      if x["id"] == "ministry_manual_2020")
        self.assertEqual(manual["published_at"], "2020-08")
        self.assertEqual(manual["date_precision"], "month")
        self.assertFalse(manual["original_document_bytes_archived"])
        self.assertFalse(result["actual_use_rate_measured"])
        offline = self.observe("original_manual_offline")
        self.assertIn("offline", offline["statement"].lower())
        self.assertEqual(offline["human_review"], "pending")

    def test_month_only_document_does_not_automatically_verify_2020_event_day(self):
        self.observe("original_manual_muly")["event_at"] = "2020-09-01"
        with self.assertRaisesRegex(ValueError, "future event"):
            validate(self.fixture)

    def test_statutory_roles_are_not_named_person_appointments(self):
        result = evaluate(self.fixture)
        for item in result["timeline"]:
            if item["id"].startswith("role_"):
                self.assertEqual(item["actors_named"], [])
                self.assertFalse(item["factual_truth_established"])
        self.assertFalse(result["actor_decision_authority_verified"])
        self.assertTrue(all(issue["verdict"] == "unresolved_requires_original_records"
                            for issue in result["disputes"]))

    def test_2018_versus_2021_statute_keeps_distinct_effective_dates(self):
        old = self.observe("role_ppk_2018")
        new = self.observe("role_ppk_2021")
        self.assertEqual(old["effective_from"], "2018-03-22")
        self.assertEqual(new["effective_from"], "2021-02-02")
        self.assertEqual(new["actor_ids"], [])
        self.assertIn("not automatically applicable", new["statement"])

    def test_source_first_graph_imports_without_asserting_guilt(self):
        packet = semantic_packet(self.fixture)
        self.assertTrue(all(n["layer"] == "neutral" for n in packet["nodes"]))
        self.assertTrue(all(e["status"] == "candidate" for e in packet["edges"]))
        self.assertTrue(all(e["relation"] == "REPORTS" for e in packet["edges"]))
        self.assertFalse(any("GUILT" in e["relation"] or e["relation"] == "CAUSES"
                             for e in packet["edges"]))
        with tempfile.TemporaryDirectory() as temp:
            app = CiteRefinery(temp)
            project = app.init_project("Chromebook audit", "Who had authority and what evidence supports it?")
            graph = SemanticGraph(app.store)
            preview = graph.preview_packet(project.id, packet)
            receipt = graph.ingest_packet(
                project.id, packet, expected_state_digest=preview["state_digest"])
            self.assertEqual(len(receipt["edge_ids"]), 22)
            stored = app.store.load()
            self.assertTrue(all(stored["semantic_edges"][eid]["status"] == "candidate"
                                for eid in receipt["edge_ids"]))

    def test_reverse_observation_order_is_stable(self):
        initial = evaluate(self.fixture)
        self.fixture["observations"].reverse()
        result = evaluate(self.fixture)
        self.assertEqual(initial["timeline"], result["timeline"])


if __name__ == "__main__":
    unittest.main()
