from __future__ import annotations

import tempfile
import unittest

from cite_refinery.app import CiteRefinery
from cite_refinery.cite_research import CiteResearchResult
from cite_refinery.semantic import SemanticGraph
from cite_refinery.semantic_projection import SemanticProjection
from cite_refinery.solution import RefinerySearchResult


class FakeDeepResearch:
    def deep(self, topic: str, *, target_count: int = 40, snowball_depth: int = 1) -> CiteResearchResult:
        return CiteResearchResult(
            engine="fake:deep",
            status="completed",
            raw="fixture",
            structured={
                "schema_version": 1,
                "tool": "deep_research",
                "status": "completed",
                "topic": topic,
                "paper_count": 1,
                "papers": [
                    {
                        "title": "Estimating hidden free-roaming animal populations",
                        "doi": "10.0000/hidden-population",
                        "year": 2025,
                    }
                ],
            },
        )


class FakeSupply:
    def search(self, query: str, limit: int = 20) -> RefinerySearchResult:
        return RefinerySearchResult(
            engine="fake:supply",
            status="completed",
            raw="fixture",
            structured={
                "commons": [
                    {
                        "kind": "reviewed_market_entity",
                        "authority": "reviewed_market_graph",
                        "entity_id": "repo:example/animal-sightings",
                        "name": "Animal Sightings",
                        "repository": "example/animal-sightings",
                    }
                ],
                "operational": [],
            },
        )


class SemanticProjectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.app = CiteRefinery(
            self.tmp.name,
            cite_research=FakeDeepResearch(),
            solution_refinery=FakeSupply(),
        )
        self.project = self.app.init_project(
            "Hidden animal population",
            "Free-roaming animals are not continuously enumerated.",
        )
        state = self.app.store.load()
        state["problem_observations"]["robs:fixture"] = {
            "id": "robs:fixture",
            "project_id": self.project.id,
            "source_system": "manual",
            "external_id": "field-1",
            "matter_id": None,
            "event_id": None,
            "text": "Field teams observe roaming animals but only at sampled places and times.",
            "observed_at": None,
            "status_stage": None,
            "frame": "field_observation",
            "sources": ["https://example.test/field"],
            "literature_queries": [
                {
                    "query": "methods for estimating hidden free-roaming animal populations",
                    "reason": "measurement",
                    "origin": "manual",
                }
            ],
            "provenance": {},
            "created_at": "2026-10-16T00:00:00+00:00",
        }
        self.app.store.save(state)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_projection_materializes_three_source_families_without_false_support(self) -> None:
        brief = self.app.prepare_research_brief(self.project.id)
        self.app.discover_research_brief(self.project.id, brief.id, max_questions=1)
        requirement = self.app.add_requirement(
            self.project.id,
            "Continuously reconcile sightings into a current local population estimate",
            source_brief_id=brief.id,
        )
        self.app.map_requirements(self.project.id, [requirement.id])

        graph = SemanticGraph(self.app.store)
        projection = SemanticProjection(graph)
        result = projection.project_all(self.project.id)
        self.assertEqual(result["bootstrap"]["materialized"]["observations"], 1)
        self.assertEqual(result["research"]["papers_projected"], 1)
        self.assertEqual(result["solution_supply"]["candidates_projected"], 1)

        exported = graph.export(self.project.id)
        nodes = list(exported["nodes"].values())
        edges = list(exported["edges"].values())

        observation = next(node for node in nodes if "problem_observation:robs:fixture" in node["source_refs"])
        paper = next(node for node in nodes if "10.0000/hidden-population" in node["source_refs"])
        candidate = next(node for node in nodes if "repository:example/animal-sightings" in node["source_refs"])
        question = next(node for node in nodes if "academic_agenda" in node["tags"])

        self.assertEqual(observation["layer"], "practical")
        self.assertEqual(paper["layer"], "academic")
        self.assertEqual(candidate["layer"], "program")
        self.assertEqual(question["layer"], "neutral")

        discovery = next(edge for edge in edges if edge["relation"] == "DISCOVERED_FOR")
        supply = next(edge for edge in edges if edge["relation"] == "CANDIDATE_FOR")
        self.assertEqual(discovery["status"], "candidate")
        self.assertEqual(supply["status"], "candidate")
        self.assertIn("does_not_establish_support", discovery["provenance_receipts"][0]["boundary"])
        self.assertEqual(supply["provenance_receipts"][0]["boundary"], "candidate_relation_only")

        # Projection must never turn paper discovery or supply discovery into a
        # semantic support/solution claim by itself.
        self.assertFalse(any(
            edge["source_id"] == paper["id"] and edge["relation"] == "SUPPORTS"
            for edge in edges
        ))
        self.assertFalse(any(
            edge["source_id"] == candidate["id"] and edge["relation"] in {"ADDRESSES", "IMPLEMENTS"}
            for edge in edges
        ))

    def test_projection_is_repeatable_without_duplicate_graph_growth(self) -> None:
        brief = self.app.prepare_research_brief(self.project.id)
        self.app.discover_research_brief(self.project.id, brief.id, max_questions=1)
        requirement = self.app.add_requirement(self.project.id, "Estimate the local hidden population")
        self.app.map_requirements(self.project.id, [requirement.id])

        graph = SemanticGraph(self.app.store)
        projection = SemanticProjection(graph)
        projection.project_all(self.project.id)
        first = graph.export(self.project.id)
        projection.project_all(self.project.id)
        second = graph.export(self.project.id)
        self.assertEqual(len(first["nodes"]), len(second["nodes"]))
        self.assertEqual(len(first["edges"]), len(second["edges"]))


if __name__ == "__main__":
    unittest.main()
