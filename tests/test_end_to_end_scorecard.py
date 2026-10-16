import sys
import tempfile
import unittest

from cite_refinery import CiteRefinery
from cite_refinery.cite import CiteAuditResult
from cite_refinery.cite_research import CiteResearchResult
from cite_refinery.scorecard import build_end_to_end_scorecard
from cite_refinery.solution import RefinerySearchResult


class FakeCite:
    def ground(self, text: str) -> CiteAuditResult:
        return CiteAuditResult(
            engine="fake:ground",
            status="completed",
            raw="grounded",
            structured={"grounded": True},
        )


class FakeDeep:
    def deep(self, topic: str, *, target_count: int = 40, snowball_depth: int = 1) -> CiteResearchResult:
        return CiteResearchResult(
            engine="fake:deep",
            status="completed",
            raw="papers",
            structured={
                "papers": [
                    {"title": "Mechanism evidence", "doi": "10.0000/mechanism"},
                    {"title": "Intervention evidence", "doi": "10.0000/intervention"},
                ]
            },
        )


class FakeSupply:
    def __init__(self, authority="commons"):
        self.authority = authority

    def search(self, query: str, limit: int = 20) -> RefinerySearchResult:
        if self.authority == "reviewed_market_graph":
            structured = {
                "results": [{
                    "kind": "reviewed_market_entity",
                    "authority": "reviewed_market_graph",
                    "entity_id": "repo:fixture/tool",
                    "name": "Fixture Tool",
                }]
            }
        else:
            structured = {
                "commons": [{
                    "kind": "capability",
                    "authority": "commons",
                    "subject_id": "capability:fixture",
                    "capability": "fixture",
                }],
                "operational": [],
            }
        return RefinerySearchResult(
            engine="fake:supply",
            status="completed",
            raw="supply",
            structured=structured,
        )


PACKET = {
    "schema": "nocturnal.trace5_empirical_case.v1",
    "candidate_id": "fixture-matter",
    "country": "Fixtureland",
    "domain": "public_administration_rights",
    "matter_id": "fixture-matter",
    "cohort": "development",
    "quality_state": "research_grade",
    "claims": [
        {
            "claim": "An institution published an initial record.",
            "matter_id": "fixture-matter",
            "event_id": "fixture:1",
            "status_stage": "reported",
            "sources": ["https://fixture.invalid/1"],
        },
        {
            "claim": "The institution later revised the record and documented remediation.",
            "matter_id": "fixture-matter",
            "event_id": "fixture:2",
            "status_stage": "implementation_followup",
            "sources": ["https://fixture.invalid/2"],
            "trace_edges": [{
                "source_event_id": "fixture:1",
                "target_event_id": "fixture:2",
                "relation_type": "mitigated_by",
            }],
        },
    ],
}


class EndToEndScorecardTests(unittest.TestCase):
    def test_scorecard_tracks_complete_chain_without_composite_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp, cite=FakeCite(), cite_research=FakeDeep(), solution_refinery=FakeSupply())
            project = app.init_project("Fixture chain", "Test every authority transition")
            app.ingest_nocturnal_packet(project.id, PACKET)
            brief = app.prepare_research_brief(project.id)
            discovery = app.discover_research_brief(project.id, brief.id, max_questions=2)
            grounding = app.ground_research_brief(project.id, brief.id)
            requirement = app.add_requirement(
                project.id,
                "Preserve revision provenance and verify remediation",
                tags=["provenance"],
                source_brief_id=brief.id,
                source_audit_id=grounding.id,
            )
            solution_map = app.map_requirements(project.id, [requirement.id])
            cap = app.adopt_capability(
                project.id,
                requirement.id,
                name="Revision verifier",
                description="Verify revision history and remediation",
                solution_map_id=solution_map.id,
                candidate_ref="capability:fixture",
            )
            impl = app.refinery.register_implementation(
                capability_id=cap.id,
                project_id=project.id,
                provider="subprocess",
                invocation={
                    "argv": [sys.executable, "-c", "import json,sys; print(json.dumps({'ok': True}))"],
                    "input_mode": "none",
                },
            )
            run = app.invoke(project.id, impl.id)
            experiment = app.add_experiment(
                project.id,
                name="fixture validation",
                method="fixture",
                result="passed",
                verdict="passed",
                run_ids=[run.id],
            )
            app.promote_capability(project.id, cap.id, experiment.id)

            scorecard = build_end_to_end_scorecard(app.store.load(), project.id)
            self.assertNotIn("score", scorecard)
            stages = scorecard["stages"]
            self.assertEqual(stages["empirical_problem_map"]["status"], "ready")
            self.assertEqual(stages["literature_discovery"]["status"], "ready")
            self.assertEqual(stages["literature_grounding"]["status"], "ready")
            self.assertEqual(stages["requirement_translation"]["lineage_coverage"], 1.0)
            self.assertEqual(stages["solution_mapping"]["candidate_coverage"], 1.0)
            self.assertEqual(stages["execution_validation"]["status"], "ready")
            self.assertEqual(stages["execution_validation"]["successful_runs"], 1)
            self.assertEqual(stages["execution_validation"]["promoted_global_capabilities"], 1)
            self.assertEqual(stages["nocturnal_feedback_loop"]["status"], "not_started")
            self.assertTrue(any("validated intervention exists" in item for item in scorecard["bottlenecks"]))
            self.assertEqual(discovery.purpose, "literature_discovery")

    def test_market_only_supply_is_reported_as_descriptive_bottleneck(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp, solution_refinery=FakeSupply(authority="reviewed_market_graph"))
            project = app.init_project("Market only", "Find but do not overclaim program supply")
            app.ingest_nocturnal_packet(project.id, PACKET)
            brief = app.prepare_research_brief(project.id)
            requirement = app.add_requirement(
                project.id,
                "Find revision provenance tooling",
                source_brief_id=brief.id,
            )
            app.map_requirements(project.id, [requirement.id])

            scorecard = build_end_to_end_scorecard(app.store.load(), project.id)
            solution = scorecard["stages"]["solution_mapping"]
            self.assertEqual(solution["candidate_coverage"], 1.0)
            self.assertEqual(solution["candidate_authorities"], {"reviewed_market_graph": 1})
            self.assertTrue(any("descriptive reviewed-market" in item for item in scorecard["bottlenecks"]))
            self.assertEqual(scorecard["stages"]["literature_discovery"]["status"], "not_started")
            self.assertEqual(scorecard["stages"]["literature_grounding"]["status"], "not_started")
            self.assertEqual(scorecard["stages"]["execution_validation"]["status"], "not_started")

    def test_unknown_project_fails(self):
        with self.assertRaisesRegex(KeyError, "unknown project"):
            build_end_to_end_scorecard({"projects": {}}, "rproject:missing")


if __name__ == "__main__":
    unittest.main()
