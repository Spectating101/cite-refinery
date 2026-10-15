import json
import tempfile
import unittest

from cite_refinery.cite import CiteAuditResult
from cite_refinery.pipeline import CiteRefinery
from cite_refinery.solution import RefinerySearchResult


class FakeCite:
    def __init__(self):
        self.inputs = []

    def ground(self, text: str) -> CiteAuditResult:
        self.inputs.append(text)
        return CiteAuditResult(
            engine="fake:cite",
            status="completed",
            raw="grounded literature",
            structured={"literature_claims": [{"claim": "Intervention evidence exists", "citation": "doi:test"}]},
        )


class FakeCanonicalRefinery:
    def __init__(self):
        self.queries = []

    def search(self, query: str, limit: int = 20) -> RefinerySearchResult:
        self.queries.append((query, limit))
        structured = [{"capability": "record.version.diff", "implementation": "repo:example/history"}]
        return RefinerySearchResult(
            engine="fake:refinery-search",
            status="completed",
            raw=json.dumps(structured),
            structured=structured,
        )


PACKET = {
    "artifact_kind": "research companion assembled from Nocturnal outputs",
    "engine_diagnostics": {
        "claims": [
            {
                "matter_id": "agency-record-change",
                "event_id": "agency-record-change:2026-01-01:first",
                "claim": "An agency published an initial status notice.",
                "observed_at": "2026-01-01",
                "status_stage": "initial_notice",
                "sources": ["https://example.invalid/one"],
                "source_tier": "official_primary",
                "literature_queries": [
                    {
                        "domain": "information systems",
                        "query": "versioned public records provenance correction transparency",
                        "reason": "record_changed_over_time",
                    }
                ],
            },
            {
                "matter_id": "agency-record-change",
                "event_id": "agency-record-change:2026-01-05:revision",
                "public_claim": "The agency later revised the status notice.",
                "observed_at": "2026-01-05",
                "status_stage": "revision",
                "sources": ["https://example.invalid/two"],
                "epistemic_posture": {
                    "literature_queries": [
                        {
                            "domain": "information systems",
                            "query": "versioned public records provenance correction transparency",
                            "reason": "record_changed_over_time",
                        }
                    ]
                },
            },
        ]
    },
}


class ProblemPipelineTests(unittest.TestCase):
    def test_nocturnal_ingest_is_idempotent_and_brief_deduplicates_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp, cite=FakeCite(), solution_refinery=FakeCanonicalRefinery())
            project = app.init_project("Public record revisions", "Understand and address silent changes in public records")
            first = app.ingest_nocturnal_packet(project.id, PACKET, packet_ref="fixture:nocturnal")
            second = app.ingest_nocturnal_packet(project.id, PACKET, packet_ref="fixture:nocturnal")
            self.assertEqual(len(first), 2)
            self.assertEqual([item.id for item in first], [item.id for item in second])
            state = app.store.load()
            self.assertEqual(len(state["problem_observations"]), 2)

            brief = app.prepare_research_brief(project.id)
            self.assertEqual(len(brief.questions), 1)
            self.assertEqual(set(brief.questions[0]["source_observation_ids"]), {item.id for item in first})

    def test_cite_research_grounding_keeps_empirical_objects_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            cite = FakeCite()
            app = CiteRefinery(tmp, cite=cite, solution_refinery=FakeCanonicalRefinery())
            project = app.init_project("Public record revisions", "Understand and address silent changes in public records")
            observations = app.ingest_nocturnal_packet(project.id, PACKET)
            brief = app.prepare_research_brief(project.id)
            audit = app.ground_research_brief(project.id, brief.id)
            state = app.store.load()

            self.assertEqual(audit.purpose, "research_brief")
            self.assertEqual(audit.target_ids, [brief.id])
            self.assertEqual(state["research_briefs"][brief.id]["status"], "grounded")
            self.assertEqual(state["claims"], {})
            self.assertEqual(len(state["problem_observations"]), len(observations))
            self.assertIn("Treat the observations as empirical context, not as academic evidence.", cite.inputs[0])
            self.assertIn("RESEARCH QUESTIONS", cite.inputs[0])

    def test_requirement_maps_to_canonical_refinery_and_adopts_with_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            cite = FakeCite()
            canonical = FakeCanonicalRefinery()
            app = CiteRefinery(tmp, cite=cite, solution_refinery=canonical)
            project = app.init_project("Public record revisions", "Understand and address silent changes in public records")
            app.ingest_nocturnal_packet(project.id, PACKET)
            brief = app.prepare_research_brief(project.id)
            audit = app.ground_research_brief(project.id, brief.id)
            requirement = app.add_requirement(
                project.id,
                "Preserve and compare revisions to public records with source provenance",
                tags=["provenance", "versioning"],
                source_brief_id=brief.id,
                source_audit_id=audit.id,
            )
            solution_map = app.map_requirements(project.id, [requirement.id], limit=7)
            self.assertEqual(solution_map.status, "completed")
            self.assertEqual(canonical.queries, [(requirement.text, 7)])
            mapped = solution_map.results[requirement.id]["canonical_refinery"]
            self.assertEqual(mapped["structured"][0]["capability"], "record.version.diff")

            cap = app.adopt_capability(
                project.id,
                requirement.id,
                name="Versioned public-record diff",
                description="Preserve source history and compare successive revisions",
                tags=["provenance", "diff"],
                solution_map_id=solution_map.id,
                candidate_ref="record.version.diff",
            )
            self.assertEqual(cap.provenance["requirement_id"], requirement.id)
            self.assertEqual(cap.provenance["source_brief_id"], brief.id)
            self.assertEqual(cap.provenance["source_audit_id"], audit.id)
            self.assertEqual(cap.provenance["solution_map_id"], solution_map.id)
            self.assertEqual(cap.provenance["candidate_ref"], "record.version.diff")
            dossier = app.dossier(project.id)
            self.assertEqual(len(dossier["problem_observations"]), 2)
            self.assertEqual(len(dossier["research_briefs"]), 1)
            self.assertEqual(len(dossier["requirements"]), 1)
            self.assertEqual(len(dossier["solution_maps"]), 1)
            self.assertEqual(len(dossier["capabilities"]), 1)


if __name__ == "__main__":
    unittest.main()
