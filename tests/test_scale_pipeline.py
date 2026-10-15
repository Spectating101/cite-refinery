import json
import tempfile
import unittest

from cite_refinery.cite import CiteAuditResult
from cite_refinery.pipeline import CiteRefinery
from cite_refinery.solution import RefinerySearchResult


DOMAINS = [
    "judicial_legal",
    "public_safety_infrastructure",
    "corporate_financial",
    "health_environment",
    "public_administration_rights",
]


class RecordingCite:
    def __init__(self):
        self.inputs = []

    def ground(self, text: str) -> CiteAuditResult:
        self.inputs.append(text)
        return CiteAuditResult(
            engine="fake:cite-scale",
            status="completed",
            raw="grounded",
            structured={"status": "bounded-scale-fixture"},
        )


class LiteralRefinery:
    """Behave like canonical Refinery's current literal substring discovery boundary."""

    def __init__(self):
        self.queries = []

    def search(self, query: str, limit: int = 20) -> RefinerySearchResult:
        self.queries.append((query, limit))
        if query.casefold() == "provenance":
            structured = {
                "query": query,
                "commons": [
                    {
                        "kind": "capability",
                        "subject_id": "capability:provenance-history",
                        "capability": "provenance-history",
                        "title": "Provenance History",
                    }
                ],
                "operational": [],
            }
        else:
            structured = {"query": query, "commons": [], "operational": []}
        return RefinerySearchResult(
            engine="fake:literal-refinery",
            status="completed",
            raw=json.dumps(structured),
            structured=structured,
        )


def build_trace_packets():
    """50 matters / 203 observations, matching the current China+India development scale."""

    packets = []
    matter_index = 0
    for country in ("China", "India"):
        for domain in DOMAINS:
            for local_index in range(5):
                claim_count = 5 if matter_index < 3 else 4
                if country == "India":
                    india_index = matter_index - 25
                    if india_index < 16:
                        quality = "research_grade"
                    elif india_index < 18:
                        quality = "longitudinal"
                    else:
                        quality = "minimal"
                else:
                    quality = "primary_source_reconstruction"
                candidate = f"{country.lower()}-{domain}-{local_index}"
                claims = []
                for claim_index in range(claim_count):
                    event_id = f"{candidate}:event:{claim_index}"
                    claims.append({
                        "claim": (
                            f"Documented event {claim_index} for {candidate}. "
                            "The record describes an institutional action, response, or outcome and preserves its source history."
                        ),
                        "matter_id": candidate,
                        "event_id": event_id,
                        "observed_at": f"202{claim_index % 6}-01-{claim_index + 1:02d}",
                        "status_stage": ["reported", "investigation_opened", "ruling", "implementation_followup", "resolved"][claim_index % 5],
                        "sources": [f"https://fixture.invalid/{candidate}/{claim_index}"],
                        "editorial_review_state": "accepted",
                        "trace_edges": [] if claim_index == 0 else [{
                            "source_event_id": f"{candidate}:event:{claim_index - 1}",
                            "target_event_id": event_id,
                            "relation_type": "superseded_by" if claim_index == 1 else "mitigated_by",
                            "epistemic_state": "observed",
                            "review_state": "accepted",
                        }],
                    })
                packets.append({
                    "schema": "nocturnal.trace5_empirical_case.v1",
                    "candidate_id": candidate,
                    "country": country,
                    "domain": domain,
                    "matter_id": candidate,
                    "chain_id": f"empirical-{candidate}",
                    "title": f"Scale fixture {candidate}",
                    "claims": claims,
                    "cohort": "development",
                    "selection_freeze": "fixture-selection-freeze.json",
                    "quality_state": quality,
                })
                matter_index += 1
    assert len(packets) == 50
    assert sum(len(packet["claims"]) for packet in packets) == 203
    return packets


class ScalePipelineTests(unittest.TestCase):
    def test_raw_trace_scale_builds_bounded_ten_cluster_agenda(self):
        with tempfile.TemporaryDirectory() as tmp:
            cite = RecordingCite()
            app = CiteRefinery(tmp, cite=cite, solution_refinery=LiteralRefinery())
            project = app.init_project("TRACE scale", "Map practical accountability problems into research and solution work")
            for packet in build_trace_packets():
                app.ingest_nocturnal_packet(project.id, packet)

            before = app.scale_report(project.id)
            self.assertEqual(before["empirical"]["observations"], 203)
            self.assertEqual(before["empirical"]["matters"], 50)
            self.assertEqual(before["empirical"]["explicit_literature_query_coverage"], 0.0)
            self.assertEqual(before["empirical"]["countries"], {"China": 103, "India": 100})
            self.assertEqual(before["empirical"]["quality_states"]["minimal"], 28)

            agenda = app.prepare_research_agenda(project.id, max_observations_per_brief=30, cohorts=["development"])
            self.assertEqual(len(agenda.brief_ids), 10)
            self.assertEqual(agenda.metrics["observations"], 203)
            self.assertEqual(agenda.metrics["matters"], 50)
            self.assertEqual(len(agenda.metrics["clusters"]), 10)

            state = app.store.load()
            self.assertEqual(len(state["research_agendas"]), 1)
            self.assertEqual(len(state["research_briefs"]), 10)
            for brief_id in agenda.brief_ids:
                brief = state["research_briefs"][brief_id]
                self.assertLessEqual(len(brief["observation_ids"]), 30)
                self.assertGreaterEqual(brief["metadata"]["fallback_question_count"], 2)
                self.assertEqual(brief["metadata"]["explicit_question_count"], 0)
                self.assertEqual(set(brief["metadata"]["cohort"]), {"development"})

    def test_scale_agenda_grounding_is_bounded_and_does_not_create_empirical_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            cite = RecordingCite()
            app = CiteRefinery(tmp, cite=cite, solution_refinery=LiteralRefinery())
            project = app.init_project("TRACE scale", "Bound research work without flattening epistemic layers")
            for packet in build_trace_packets():
                app.ingest_nocturnal_packet(project.id, packet)
            agenda = app.prepare_research_agenda(project.id, max_observations_per_brief=30)

            for brief_id in agenda.brief_ids:
                audit = app.ground_research_brief(project.id, brief_id, max_prompt_chars=12000, max_observation_chars=500)
                self.assertEqual(audit.status, "completed")
            self.assertEqual(len(cite.inputs), 10)
            self.assertTrue(all(len(prompt) <= 12000 for prompt in cite.inputs))
            self.assertTrue(all("structural_fallback" in prompt for prompt in cite.inputs))
            self.assertTrue(all("Treat the observations as empirical context, not as academic evidence." in prompt for prompt in cite.inputs))

            state = app.store.load()
            self.assertEqual(state["claims"], {})
            self.assertEqual(len(state["problem_observations"]), 203)
            self.assertEqual(sum(brief["status"] == "grounded" for brief in state["research_briefs"].values()), 10)

    def test_literal_refinery_falls_back_to_transparent_probe_without_semantic_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            refinery = LiteralRefinery()
            app = CiteRefinery(tmp, cite=RecordingCite(), solution_refinery=refinery)
            project = app.init_project("Solutions", "Map requirements against a literal registry")
            requirement = app.add_requirement(
                project.id,
                "Maintain verifiable evidence history across institutional revisions",
                tags=["provenance", "history"],
            )
            solution_map = app.map_requirements(project.id, [requirement.id], limit=10)
            mapped = solution_map.results[requirement.id]

            self.assertEqual(refinery.queries[0], (requirement.text, 10))
            self.assertIn(("provenance", 10), refinery.queries)
            self.assertEqual(mapped["canonical_candidate_count"], 1)
            self.assertEqual(mapped["canonical_candidates"][0]["subject_id"], "capability:provenance-history")
            self.assertEqual(mapped["canonical_candidates"][0]["matched_by_probe"], "provenance")
            self.assertGreaterEqual(len(mapped["canonical_search_probes"]), 2)

    def test_scale_report_surfaces_actual_bottlenecks(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp, cite=RecordingCite(), solution_refinery=LiteralRefinery())
            project = app.init_project("TRACE scale", "Measure integration bottlenecks")
            for packet in build_trace_packets():
                app.ingest_nocturnal_packet(project.id, packet)
            app.prepare_research_agenda(project.id, max_observations_per_brief=30)
            report = app.scale_report(project.id)

            self.assertEqual(report["research"]["briefs"], 10)
            self.assertEqual(report["research"]["briefs_using_structural_fallback"], 10)
            self.assertTrue(any("lack explicit literature-query hints" in warning for warning in report["warnings"]))
            self.assertTrue(any("quality is heterogeneous" in warning for warning in report["warnings"]))


if __name__ == "__main__":
    unittest.main()
