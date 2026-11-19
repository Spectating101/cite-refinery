"""Milestone 010: case procedural chronology cannot overclaim court finality."""
import copy
import json
from pathlib import Path
import unittest
from cite_refinery.legal_codex_case_posture import evaluate, validate, semantic_packet

SEED = Path(__file__).resolve().parents[1] / "examples/legal_codex_case_posture_010.json"


class CasePostureTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SEED.read_text(encoding="utf-8"))

    def case(self, name):
        return next(c for c in self.data["cases"] if c["id"] == name)

    def test_three_separate_trajectories(self):
        result = evaluate(self.data)
        self.assertEqual(result["case_count"], 3)
        self.assertEqual(result["event_count"], 7)
        self.assertEqual(result["official_trial_case_pages_indexed"], 2)
        self.assertEqual(result["official_appeal_index_entries"], 2)
        self.assertEqual(result["original_court_pdf_count"], 0)
        self.assertEqual(result["source_page_captures_rechecked"], 2)
        self.assertTrue(result["source_page_capture_does_not_verify_judgment"])
        self.assertEqual(result["certified_finality_count"], 0)
        stages = {x["id"]: x["posture"] for x in result["case_trajectories"]}
        self.assertEqual(stages["case_nadiem"], "cassation_reported_pending_official_verification")
        self.assertEqual(stages["case_sri"], "finality_reported_without_official_certificate")
        self.assertEqual(stages["case_ibam"], "appeal_judgment_indexed_no_cassation_status_established")

    def test_trial_official_page_cannot_be_swapped_between_people(self):
        self.case("case_nadiem")["events"][0]["source_id"] = "s_ibam_trial_official"
        with self.assertRaisesRegex(ValueError, "trial directory metadata mismatch"):
            validate(self.data)

    def test_spoofed_page_receipt_rejected(self):
        rec = next(s for s in self.data["sources"] if s["id"] == "s_nadiem_cassation")["capture_receipt"]
        rec["raw_sha256"] = "forged"
        with self.assertRaisesRegex(ValueError, "capture receipt"):
            validate(self.data)

    def test_captured_article_does_not_become_original_judgment(self):
        rec = next(s for s in self.data["sources"] if s["id"] == "s_academic_examination")["capture_receipt"]
        rec["original_judgment_verified"] = True
        with self.assertRaisesRegex(ValueError, "capture receipt"):
            validate(self.data)

    def test_reported_finality_is_not_certified(self):
        self.case("case_sri")["finality_certificate_verified"] = True
        with self.assertRaisesRegex(ValueError, "unverified original or finality"):
            validate(self.data)

    def test_cassation_report_does_not_become_official_judgment(self):
        ev = self.case("case_nadiem")["events"][-1]
        ev["source_id"] = "s_official_appeal_index"
        with self.assertRaisesRegex(ValueError, "impersonate official directory"):
            validate(self.data)

    def test_reported_cassation_has_no_guessed_docket(self):
        self.case("case_nadiem")["events"][-1]["docket"] = "Invented/MA"
        with self.assertRaisesRegex(ValueError, "invented"):
            validate(self.data)

    def test_wrong_appeal_docket_rejected(self):
        self.case("case_nadiem")["events"][1]["docket"] = "31/PID.SUS-TPK/2026/PT DKI"
        with self.assertRaisesRegex(ValueError, "appeal docket/provenance mismatch"):
            validate(self.data)

    def test_appeal_date_cannot_precede_trial(self):
        self.case("case_ibam")["events"][1]["date"] = "2026-02-01"
        with self.assertRaisesRegex(ValueError, "strictly ascending"):
            validate(self.data)

    def test_trial_and_appeal_not_same_document(self):
        self.case("case_nadiem")["events"][1]["original_court_document_acquired"] = True
        with self.assertRaisesRegex(ValueError, "event overclaims"):
            validate(self.data)

    def test_expert_criticism_not_judicial_holding(self):
        self.data["external_opinions"][0]["not_court_holding"] = False
        with self.assertRaisesRegex(ValueError, "academic commentary"):
            validate(self.data)

    def test_fake_official_source_domain_rejected(self):
        self.data["sources"][3]["url"] = "https://invalid.example/direktori/index/pengadilan/pt-jakarta/kategori/korupsi-1/tahunjenis/putus/tahun/2026.html"
        with self.assertRaisesRegex(ValueError, "official index provenance"):
            validate(self.data)

    def test_no_appeal_report_cannot_apply_to_other_case(self):
        self.case("case_nadiem")["events"][-1]["kind"] = "no_appeal_reported"
        with self.assertRaisesRegex(ValueError, "wrong defendant"):
            validate(self.data)

    def test_pdf_custody_cannot_be_invented(self):
        self.data["original_judgment_pdfs_in_hand"] = ["fake.pdf"]
        with self.assertRaisesRegex(ValueError, "promoted"):
            validate(self.data)

    def test_graph_is_candidate_only_and_case_local(self):
        packet = semantic_packet(self.data)
        self.assertEqual(len(packet["nodes"]), 7)
        self.assertEqual(len(packet["edges"]), 4)
        self.assertTrue(all(e["status"] == "candidate" for e in packet["edges"]))
        self.assertTrue(all(e["source"].split("-event-")[0] == e["target"].split("-event-")[0]
                            for e in packet["edges"]))
        self.assertFalse(any(e["relation"] in ("SIGNED", "PAID", "CONVICTED", "CORRUPTED")
                             for e in packet["edges"]))


if __name__ == "__main__":
    unittest.main()
