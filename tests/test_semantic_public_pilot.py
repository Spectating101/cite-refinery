from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery import CiteRefinery, SemanticGraph


PILOT = Path(__file__).resolve().parents[1] / "examples" / "free_roaming_dog_semantic_pilot.json"


class PublicSemanticPilotTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.app = CiteRefinery(self.tmp.name)
        self.project = self.app.init_project(
            "Free-roaming dog semantic pilot",
            "Map specific management problems across practical, academic, and program evidence.",
        )
        self.graph = SemanticGraph(self.app.store)
        packet = json.loads(PILOT.read_text(encoding="utf-8"))
        self.receipt = self.graph.ingest_packet(
            self.project.id,
            packet,
            packet_ref=str(PILOT),
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _node(self, suffix: str) -> dict:
        state = self.app.store.load()
        return next(
            node
            for node in state["semantic_nodes"].values()
            if node.get("project_id") == self.project.id
            and str(node.get("external_key") or "").endswith(f":{suffix}")
        )

    def test_observability_problem_has_three_distinct_source_layers(self) -> None:
        problem = self._node("continuous_state_problem")
        report = self.graph.coverage(self.project.id, problem["id"], depth=1)
        self.assertEqual(
            report["layer_presence"],
            {"practical": True, "academic": True, "program": True},
        )
        self.assertEqual(report["intersection"], "practical_academic_program")
        self.assertNotIn("coverage_score", report)
        self.assertTrue(any(
            node["statement"].startswith("Taiwan estimates the national free-roaming dog population")
            for node in report["layers"]["practical"]
        ))
        self.assertTrue(any(node["statement"].startswith("Talea is a street-survey system") for node in report["layers"]["program"]))

    def test_replenishment_problem_is_semantically_covered_but_effectiveness_not_implied(self) -> None:
        problem = self._node("open_population_problem")
        report = self.graph.coverage(self.project.id, problem["id"], depth=1)
        self.assertEqual(report["intersection"], "practical_academic_program")
        program_edges = [
            edge
            for edge in report["relations"].get("ADDRESSES", [])
            if edge["target_id"] == problem["id"]
        ]
        self.assertEqual(len(program_edges), 1)
        self.assertEqual(program_edges[0]["status"], "qualified")
        self.assertIn("does not assert outcome effectiveness", program_edges[0]["provenance_receipts"][0]["boundary"])

    def test_missing_method_to_implementation_path_is_reported_exactly(self) -> None:
        problem = self._node("continuous_state_problem")
        result = self.graph.trace_pattern(
            self.project.id,
            problem["id"],
            [
                {"relation": "MEASURED_BY", "target_kind": "method"},
                {"relation": "IMPLEMENTED_BY", "target_kind": "repository"},
            ],
        )
        self.assertEqual(result["completed_paths"], [])
        self.assertEqual(len(result["breaks"]), 1)
        self.assertEqual(result["breaks"][0]["step_index"], 1)
        self.assertEqual(result["breaks"][0]["expected"]["relations"], ["IMPLEMENTED_BY"])
        self.assertIn("not represented", result["boundary"])

    def test_cluster_map_is_module_local_not_global_layer_scoring(self) -> None:
        atlas = self.graph.cluster_map(self.project.id)
        clusters = {cluster["title"]: cluster for cluster in atlas["clusters"]}
        self.assertEqual(
            clusters["Population observability"]["layer_presence"],
            {"practical": True, "academic": True, "program": True},
        )
        self.assertEqual(
            clusters["Population replenishment and source control"]["layer_presence"],
            {"practical": True, "academic": True, "program": True},
        )
        self.assertGreaterEqual(len(clusters["Intervention effectiveness and feedback"]["node_ids"]), 4)

    def test_sources_and_boundaries_survive_ingestion(self) -> None:
        survey = self._node("tw_periodic_estimate")
        self.assertIn(
            "https://animal.moa.gov.tw/Frontend/News/Detail/N0000000001599",
            survey["source_refs"],
        )
        state = self.app.store.load()
        qualified = next(
            edge
            for edge in state["semantic_edges"].values()
            if edge["project_id"] == self.project.id
            and edge["relation"] == "SUPPORTS"
            and edge["source_id"] == survey["id"]
        )
        self.assertEqual(qualified["status"], "qualified")
        self.assertIn("inference", qualified["provenance_receipts"][0]["boundary"])


if __name__ == "__main__":
    unittest.main()
