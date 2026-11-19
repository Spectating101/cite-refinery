"""Legal Codex multi-domain acceptance and adversarial checks."""
import copy
import json
import unittest
from pathlib import Path

from cite_refinery.legal_codex_benchmark import checked, evaluate, semantic_packet

DATA = Path(__file__).resolve().parents[1] / "examples/legal_codex_benchmark_001.json"


class LegalCodexBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads(DATA.read_text(encoding="utf-8"))

    def test_three_unreviewed_cases_and_candidates(self):
        result = evaluate(self.bundle)
        self.assertEqual(len(result["cases"]), 3)
        self.assertFalse(result["publication_authorized"])
        cases = {x["case_id"]: x for x in result["cases"]}
        self.assertIn("m_uk_animal_offence",
                      [x["mechanism_id"] for x in cases["wangwang"]["candidate_alternatives"]])
        self.assertIn("m_ccrc_independent_review",
                      [x["mechanism_id"] for x in cases["horizon"]["candidate_alternatives"]])
        self.assertIn("m_dpa_institutional_scrutiny",
                      [x["mechanism_id"] for x in cases["dutch_benefits"]["later_alternatives"]])
        for case in result["cases"]:
            self.assertIsNone(case["causal_effect"])
            self.assertEqual(case["personal_culpability"], "not_established")

    def test_foreign_law_is_not_chinese_law(self):
        china = next(x for x in evaluate(self.bundle)["cases"] if x["case_id"] == "wangwang")
        self.assertNotIn("c_uk_animal_law", china["applicable_rule_candidates"])

    def test_source_excerpt_tampering(self):
        self.bundle["sources"][0]["excerpt"] = "A wholly different alleged source"
        with self.assertRaisesRegex(ValueError, "altered excerpt"):
            checked(self.bundle)

    def test_quote_fabrication(self):
        self.bundle["claims"][0]["support"][0]["quote"] = "It prevented all harm"
        with self.assertRaisesRegex(ValueError, "quoted passage"):
            checked(self.bundle)

    def test_fabricated_editorial_approval(self):
        self.bundle["claims"][0]["review"] = "accepted"
        with self.assertRaisesRegex(ValueError, "editorial approval"):
            checked(self.bundle)

    def test_personal_blame_is_not_allowed(self):
        self.bundle["claims"][0]["kind"] = "personal_culpability"
        with self.assertRaisesRegex(ValueError, "personal blame"):
            checked(self.bundle)

    def test_fabricated_causal_effect_is_not_allowed(self):
        self.bundle["mechanisms"][0]["effect_estimate"] = .8
        with self.assertRaisesRegex(ValueError, "invented policy impact"):
            checked(self.bundle)

    def test_no_fabricated_full_document_custody(self):
        self.bundle["sources"][0]["custody"] = "original_fully_authenticated"
        with self.assertRaisesRegex(ValueError, "authenticated-source"):
            checked(self.bundle)

    def test_duplicate_references(self):
        self.bundle["sources"].append(copy.deepcopy(self.bundle["sources"][0]))
        with self.assertRaisesRegex(ValueError, "repeated source"):
            checked(self.bundle)

    def test_semantic_packet_neutral_and_candidate_only(self):
        result = evaluate(self.bundle)
        packet = semantic_packet(self.bundle, result)
        self.assertEqual(packet["schema"], "cite_refinery.semantic_graph.v1")
        self.assertTrue(all(n["layer"] == "neutral" for n in packet["nodes"]))
        self.assertTrue(all(e["status"] == "candidate" for e in packet["edges"]))

    def test_existing_semantic_graph_preview_and_import(self):
        from tempfile import TemporaryDirectory
        from cite_refinery.app import CiteRefinery
        from cite_refinery.semantic import SemanticGraph
        packet = semantic_packet(self.bundle, evaluate(self.bundle))
        with TemporaryDirectory() as folder:
            app = CiteRefinery(folder)
            project = app.init_project("Legal Codex three-case pilot", "Compare evidence and institutional outcomes")
            graph = SemanticGraph(app.store)
            preview = graph.preview_packet(project.id, packet)
            self.assertEqual(preview["declared_node_layers"].get("neutral"), len(packet["nodes"]))
            self.assertFalse(preview["authority_boundary_warnings"])
            receipt = graph.ingest_packet(project.id, packet,
                                          expected_state_digest=preview["state_digest"])
            self.assertTrue(receipt["edge_ids"])
            state = app.store.load()
            self.assertTrue(all(state["semantic_edges"][edge_id]["status"] == "candidate"
                                for edge_id in receipt["edge_ids"]))

    def test_stale_graph_result_rejected(self):
        result = evaluate(self.bundle)
        self.bundle["cases"][0]["title"] = "Different evidence case"
        with self.assertRaisesRegex(ValueError, "stale result"):
            semantic_packet(self.bundle, result)


if __name__ == "__main__":
    unittest.main()
