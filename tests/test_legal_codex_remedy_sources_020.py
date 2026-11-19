"""Real public-source integration checks; source reading is curated, not an accuracy benchmark."""
from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.legal_codex_remedy_sources import load_inputs, load_dutch
from cite_refinery.legal_codex_remedy_tracker import evaluate, semantic_packet


@unittest.skipUnless(os.environ.get("LEGAL_CODEX_020_DUTCH") and os.environ.get("LEGAL_CODEX_020_FINLEX"),
                     "Actual Dutch and Finnish sources required in the dedicated 020 job")
class RealRemedy020Tests(unittest.TestCase):
    def setUp(self):
        ledger_path = Path(__file__).resolve().parents[1] / "examples/legal_codex_remedy_020.json"
        self.ledger, self.sources = load_inputs(os.environ["LEGAL_CODEX_020_DUTCH"],
                                               os.environ["LEGAL_CODEX_020_FINLEX"], ledger_path)
        self.as_of = max(x["available_on"] for x in self.ledger["sources"].values())
        self.report = evaluate(self.ledger, self.sources, self.as_of)
        self.rows = {r["id"]: r for r in self.report["obligations"]}

    def test_four_decisions_twelve_components_and_three_source_confirmations(self):
        self.assertEqual(len(self.report["sources"]), 4)
        self.assertEqual(len(self.rows), 12)
        self.assertEqual(len(self.report["events"]), 27)
        self.assertEqual(self.report["confirmed_obligation_count"], 3)
        self.assertFalse(self.report["original_record_custody"])
        self.assertFalse(self.report["operational_replay_allowed"])

    def test_hospital_receipt_does_not_close_later_explanation_order(self):
        row = self.rows["h26_log_explanation"]
        self.assertEqual(row["pre_order_receipt_ids"], ["h26_prior_logs"])
        self.assertEqual(row["fulfillment"], "unverified")
        self.assertTrue(row["assurance_reported"])
        self.assertEqual(row["penalty_authority"], "declined")
        self.assertEqual(row["penalty_accrual"], "unverified")
        self.assertEqual(self.rows["h26_medical_copy"]["fulfillment"], "confirmed_by_public_source")
        self.assertEqual(self.rows["h24_log_overviews"]["fulfillment"], "unverified")

    def test_ministry_remedial_decision_is_not_receipt(self):
        self.assertTrue(self.rows["ministry_delivery"]["remedial_decision_reported"])
        self.assertEqual(self.rows["ministry_delivery"]["delivery"], "unverified")
        self.assertEqual(self.rows["ministry_employee_names"]["disposition"], "requirement_reversed")

    def test_finnish_missing_period_has_no_further_order_but_remains_unfulfilled(self):
        row = self.rows["finland_older_logs"]
        self.assertEqual(row["disposition"], "further_order_not_issued")
        self.assertEqual(row["fulfillment"], "nonfulfillment_confirmed_by_public_source")
        self.assertTrue(row["record_unavailable_reported"])
        self.assertFalse(row["intentional_deletion_inferred"])
        self.assertEqual(self.rows["finland_later_logs"]["fulfillment"], "confirmed_by_public_source")
        delay = self.rows["finland_remittal_delay"]
        self.assertEqual(delay["fulfillment"], "nonfulfillment_confirmed_by_public_source")
        self.assertEqual(delay["historical_confirmation_ids"], [])
        finding = next(e for e in self.report["events"] if e["id"] == "fi_delay_finding")
        self.assertEqual(finding["fulfills_order_id"], "fi_remittal_report")

    def test_finnish_nonfinality_and_discrepancies_are_retained(self):
        source = next(s for s in self.report["sources"] if s["source_id"] == "finnish_tax_2026")
        self.assertEqual(source["decision_finality"], "not_final_as_published")
        self.assertEqual(self.sources["finnish_tax_2026"]["metadata"]["produced_dates"], ["2026-11-10"])
        self.assertEqual(self.sources["finnish_tax_2026"]["metadata"]["publication_values"], [])
        flags = " ".join(self.rows["finland_later_logs"]["data_quality_flags"])
        self.assertIn("31 December 2021", flags)
        self.assertIn("28 November 2021", flags)
        older = " ".join(self.rows["finland_older_logs"]["data_quality_flags"])
        self.assertIn("13 April 2019", older)
        self.assertIn("13 May 2019", older)

    def test_before_capture_has_no_historical_version_or_fulfillment_claim(self):
        report = evaluate(self.ledger, self.sources, "2026-11-01")
        self.assertEqual(report["events"], [])
        self.assertEqual(report["confirmed_obligation_count"], 0)
        self.assertTrue(all(not r["data_quality_flags"] and r["deadline"] is None for r in report["obligations"]))
        self.assertTrue(all(s["historical_version_verified"] is False for s in self.report["sources"]))

    def test_real_source_tampering_and_wrong_case_binding_are_refused(self):
        ledger = deepcopy(self.ledger)
        event = next(e for e in ledger["events"] if e["id"] == "h26_prior_logs")
        event["obligation_id"] = "h24_log_overviews"
        with self.assertRaisesRegex(ValueError, "different proceeding"):
            evaluate(ledger, self.sources, self.as_of)
        import shutil
        with TemporaryDirectory() as folder:
            root = Path(folder) / "evidence"
            shutil.copytree(os.environ["LEGAL_CODEX_020_DUTCH"], root)
            path = root / "hospital_2026.xml"
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "changed"):
                load_dutch(root)

    def test_native_graph_accepts_candidate_obligation_links(self):
        from cite_refinery.app import CiteRefinery
        from cite_refinery.semantic import SemanticGraph
        packet = semantic_packet(self.ledger, self.sources, self.as_of)
        self.assertTrue(packet["edges"])
        self.assertTrue(all(e["status"] == "candidate" for e in packet["edges"]))
        self.assertFalse(any(e["relation"] in {"CAUSES", "PREVENTED", "GUILTY", "PAID"} for e in packet["edges"]))
        with TemporaryDirectory() as folder:
            app = CiteRefinery(folder)
            project = app.init_project("020 scoped remedies", "Published findings and actual source custody")
            graph = SemanticGraph(app.store)
            preview = graph.preview_packet(project.id, packet)
            self.assertFalse(preview["authority_boundary_warnings"])
            result = graph.ingest_packet(project.id, packet, expected_state_digest=preview["state_digest"])
            self.assertEqual(len(result["edge_ids"]), len(packet["edges"]))


if __name__ == "__main__":
    unittest.main()
