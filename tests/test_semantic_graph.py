from __future__ import annotations

import json
import tempfile
import unittest

from cite_refinery.app import CiteRefinery
from cite_refinery.semantic import SEMANTIC_PACKET_SCHEMA, SemanticGraph


class SemanticGraphTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.app = CiteRefinery(self.tmp.name)
        self.project = self.app.init_project(
            "Free-roaming dog management",
            "Local authorities cannot continuously observe and manage free-roaming dog populations.",
        )
        self.graph = SemanticGraph(self.app.store)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _pilot_packet(self) -> dict:
        return {
            "schema": SEMANTIC_PACKET_SCHEMA,
            "source_system": "manual-public-research",
            "clusters": [
                {"key": "obs", "title": "Population observability"},
                {"key": "control", "title": "Intervention feedback"},
            ],
            "nodes": [
                {
                    "key": "problem",
                    "statement": "Current local free-roaming dog population is not continuously known.",
                    "kind": "problem_claim",
                    "layer": "neutral",
                    "clusters": ["obs"],
                },
                {
                    "key": "field",
                    "statement": "Periodic field surveys observe only sampled places and times.",
                    "kind": "observation",
                    "layer": "practical",
                    "clusters": ["obs"],
                    "source_refs": ["https://example.test/practical"],
                },
                {
                    "key": "paper",
                    "statement": "Detection probability and individual recognition affect free-ranging dog estimates.",
                    "kind": "academic_claim",
                    "layer": "academic",
                    "clusters": ["obs"],
                    "source_refs": ["doi:10.example/test"],
                },
                {
                    "key": "method",
                    "statement": "Repeated individually reconciled sightings can feed capture-recapture estimation.",
                    "kind": "method",
                    "layer": "academic",
                    "clusters": ["obs"],
                },
                {
                    "key": "app",
                    "statement": "A street survey application records geolocated dog sightings.",
                    "kind": "program",
                    "layer": "program",
                    "clusters": ["obs"],
                    "source_refs": ["repo:street-survey"],
                },
                {
                    "key": "source_gap",
                    "statement": "Owned or abandoned dogs transition into the free-roaming population.",
                    "kind": "problem_claim",
                    "layer": "neutral",
                    "clusters": ["control"],
                },
                {
                    "key": "source_obs",
                    "statement": "Incoming dogs are observed after sterilization campaigns.",
                    "kind": "observation",
                    "layer": "practical",
                    "clusters": ["control"],
                },
                {
                    "key": "source_paper",
                    "statement": "Open-population immigration can undermine fertility-control effects.",
                    "kind": "academic_claim",
                    "layer": "academic",
                    "clusters": ["control"],
                },
            ],
            "edges": [
                {"source": "field", "relation": "SUPPORTS", "target": "problem"},
                {"source": "paper", "relation": "SUPPORTS", "target": "problem"},
                {"source": "problem", "relation": "MEASURED_BY", "target": "method"},
                {"source": "app", "relation": "PARTIALLY_ADDRESSES", "target": "problem"},
                {"source": "source_obs", "relation": "SUPPORTS", "target": "source_gap"},
                {"source": "source_paper", "relation": "SUPPORTS", "target": "source_gap"},
                {
                    "source": "source_paper",
                    "relation": "QUALIFIES",
                    "target": "source_gap",
                    "status": "qualified",
                },
            ],
        }

    def test_packet_ingest_is_idempotent_and_preserves_provenance(self) -> None:
        packet = self._pilot_packet()
        first = self.graph.ingest_packet(self.project.id, packet, packet_ref="pilot.json")
        second = self.graph.ingest_packet(self.project.id, packet, packet_ref="pilot.json")
        self.assertEqual(first["id"], second["id"])

        state = self.app.store.load()
        self.assertEqual(len(state["semantic_packets"]), 1)
        self.assertEqual(len(state["semantic_nodes"]), 8)
        self.assertEqual(len(state["semantic_edges"]), 7)
        practical = next(node for node in state["semantic_nodes"].values() if node["external_key"].endswith(":field"))
        self.assertEqual(practical["layer"], "practical")
        self.assertEqual(practical["provenance_receipts"][0]["source_system"], "manual-public-research")
        self.assertEqual(practical["provenance_receipts"][0]["packet_ref"], "pilot.json")

    def test_coverage_is_structural_not_numeric(self) -> None:
        receipt = self.graph.ingest_packet(self.project.id, self._pilot_packet())
        state = self.app.store.load()
        problem_id = next(
            node_id for node_id in receipt["node_ids"]
            if state["semantic_nodes"][node_id]["external_key"].endswith(":problem")
        )
        report = self.graph.coverage(self.project.id, problem_id)
        self.assertEqual(
            report["layer_presence"],
            {"practical": True, "academic": True, "program": True},
        )
        self.assertEqual(report["intersection"], "practical_academic_program")
        serialized = json.dumps(report)
        self.assertNotIn('"score"', serialized)
        self.assertNotIn('"coverage_score"', serialized)

    def test_query_finds_practical_academic_node_without_program_connection(self) -> None:
        self.graph.ingest_packet(self.project.id, self._pilot_packet())
        result = self.graph.query_coverage(
            self.project.id,
            present=["practical", "academic"],
            absent=["program"],
            kind="problem_claim",
        )
        statements = [item["node"]["statement"] for item in result["matches"]]
        self.assertIn(
            "Owned or abandoned dogs transition into the free-roaming population.",
            statements,
        )
        self.assertNotIn(
            "Current local free-roaming dog population is not continuously known.",
            statements,
        )

    def test_trace_reports_specific_missing_semantic_edge(self) -> None:
        receipt = self.graph.ingest_packet(self.project.id, self._pilot_packet())
        state = self.app.store.load()
        problem_id = next(
            node_id for node_id in receipt["node_ids"]
            if state["semantic_nodes"][node_id]["external_key"].endswith(":problem")
        )
        result = self.graph.trace_pattern(
            self.project.id,
            problem_id,
            [
                {"relation": "MEASURED_BY", "target_kind": "method"},
                {"relation": "IMPLEMENTED_BY", "target_kind": "repository"},
            ],
        )
        self.assertEqual(result["completed_paths"], [])
        self.assertEqual(len(result["breaks"]), 1)
        self.assertEqual(result["breaks"][0]["step_index"], 1)
        self.assertEqual(result["breaks"][0]["expected"]["relations"], ["IMPLEMENTED_BY"])

    def test_custom_semantic_relation_and_contradiction_are_preserved(self) -> None:
        a = self.graph.add_node(
            self.project.id,
            "Sterilization reduces reproductive output.",
            kind="academic_claim",
            layer="academic",
        )
        b = self.graph.add_node(
            self.project.id,
            "Adult roaming-dog counts did not fall over the observed period.",
            kind="academic_claim",
            layer="academic",
        )
        edge = self.graph.add_edge(
            self.project.id,
            b["id"],
            "CONTRADICTS",
            a["id"],
            evidence_refs=["doi:example"],
        )
        self.assertEqual(edge["relation"], "CONTRADICTS")
        report = self.graph.coverage(self.project.id, a["id"])
        self.assertEqual(len(report["contradictions"]), 1)

        custom = self.graph.add_edge(
            self.project.id,
            a["id"],
            "EFFECT_MODIFIED_BY",
            b["id"],
        )
        self.assertEqual(custom["relation"], "EFFECT_MODIFIED_BY")

    def test_bootstrap_exposes_existing_records_without_claim_upgrading(self) -> None:
        state = self.app.store.load()
        observation_id = "robs:test"
        state["problem_observations"][observation_id] = {
            "id": observation_id,
            "project_id": self.project.id,
            "source_system": "nocturnal",
            "external_id": "case-1",
            "matter_id": None,
            "event_id": None,
            "text": "Street dogs repeatedly observed near a school.",
            "observed_at": None,
            "status_stage": None,
            "frame": "field_observation",
            "sources": ["https://example.test/case"],
            "literature_queries": [],
            "provenance": {},
            "created_at": "2026-10-16T00:00:00+00:00",
        }
        self.app.store.save(state)
        result = self.graph.bootstrap_project_records(self.project.id)
        self.assertEqual(result["materialized"]["observations"], 1)
        exported = self.graph.export(self.project.id)
        context_edges = [edge for edge in exported["edges"].values() if edge["relation"] == "CONTEXT_FOR"]
        self.assertEqual(len(context_edges), 1)
        self.assertEqual(
            context_edges[0]["provenance_receipts"][0]["boundary"],
            "context_only_not_support",
        )

    def test_cluster_map_keeps_layer_presence_local_to_cluster(self) -> None:
        self.graph.ingest_packet(self.project.id, self._pilot_packet())
        result = self.graph.cluster_map(self.project.id)
        by_title = {cluster["title"]: cluster for cluster in result["clusters"]}
        self.assertEqual(
            by_title["Population observability"]["layer_presence"],
            {"practical": True, "academic": True, "program": True},
        )
        self.assertEqual(
            by_title["Intervention feedback"]["layer_presence"],
            {"practical": True, "academic": True, "program": False},
        )


if __name__ == "__main__":
    unittest.main()
