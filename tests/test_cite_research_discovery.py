import tempfile
import unittest

from cite_refinery import CiteRefinery
from cite_refinery.cite_research import CiteResearchResult


DOMAINS = [
    "judicial_legal",
    "public_safety_infrastructure",
    "corporate_financial",
    "health_environment",
    "public_administration_rights",
]


class FakeDeepResearch:
    def __init__(self, *, status="completed"):
        self.status = status
        self.calls = []

    def deep(self, topic: str, *, target_count: int = 40, snowball_depth: int = 1) -> CiteResearchResult:
        self.calls.append((topic, target_count, snowball_depth))
        if self.status != "completed":
            return CiteResearchResult(
                engine="fake:deep_research",
                status=self.status,
                raw="not available",
                structured=None,
            )
        slug = str(abs(hash(topic)))
        payload = {
            "schema_version": 1,
            "tool": "deep_research",
            "status": "completed",
            "topic": topic,
            "paper_count": 2,
            "papers": [
                {
                    "title": f"Mechanisms for {topic[:40]}",
                    "doi": f"10.0000/{slug}-a",
                    "year": 2024,
                    "source": "fixture",
                },
                {
                    "title": f"Interventions for {topic[:40]}",
                    "doi": f"10.0000/{slug}-b",
                    "year": 2025,
                    "source": "fixture",
                },
            ],
        }
        return CiteResearchResult(
            engine="fake:deep_research",
            status="completed",
            raw="fixture deep research",
            structured=payload,
        )


def trace_packets():
    packets = []
    matter_index = 0
    for country in ("China", "India"):
        for domain in DOMAINS:
            for local_index in range(5):
                claim_count = 5 if matter_index < 3 else 4
                candidate = f"{country.lower()}-{domain}-{local_index}"
                claims = []
                for claim_index in range(claim_count):
                    event_id = f"{candidate}:event:{claim_index}"
                    claims.append({
                        "claim": f"Documented event {claim_index} for {candidate} with an institutional response or outcome.",
                        "matter_id": candidate,
                        "event_id": event_id,
                        "observed_at": f"202{claim_index % 6}-01-{claim_index + 1:02d}",
                        "status_stage": ["reported", "investigation_opened", "ruling", "implementation_followup", "resolved"][claim_index % 5],
                        "sources": [f"https://fixture.invalid/{candidate}/{claim_index}"],
                        "trace_edges": [] if claim_index == 0 else [{
                            "source_event_id": f"{candidate}:event:{claim_index - 1}",
                            "target_event_id": event_id,
                            "relation_type": "mitigated_by",
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
                    "title": candidate,
                    "claims": claims,
                    "cohort": "development",
                    "quality_state": "research_grade" if country == "India" and local_index < 3 else "development",
                })
                matter_index += 1
    assert len(packets) == 50
    assert sum(len(packet["claims"]) for packet in packets) == 203
    return packets


class CiteResearchDiscoveryTests(unittest.TestCase):
    def test_trace_scale_discovery_is_bounded_and_separate_from_grounding(self):
        with tempfile.TemporaryDirectory() as tmp:
            deep = FakeDeepResearch()
            app = CiteRefinery(tmp, cite_research=deep)
            project = app.init_project("TRACE discovery", "Acquire literature for practical accountability problems")
            for packet in trace_packets():
                app.ingest_nocturnal_packet(project.id, packet)
            agenda = app.prepare_research_agenda(project.id, max_observations_per_brief=30)
            self.assertEqual(len(agenda.brief_ids), 10)

            audits = [
                app.discover_research_brief(
                    project.id,
                    brief_id,
                    target_count=24,
                    snowball_depth=1,
                    max_questions=3,
                )
                for brief_id in agenda.brief_ids
            ]
            self.assertEqual(len(audits), 10)
            self.assertTrue(all(audit.purpose == "literature_discovery" for audit in audits))
            self.assertTrue(all(audit.status == "completed" for audit in audits))
            self.assertEqual(len(deep.calls), 30)
            self.assertTrue(all(target == 24 and depth == 1 for _, target, depth in deep.calls))
            self.assertTrue(all(audit.structured["questions_attempted"] == 3 for audit in audits))
            self.assertTrue(all(audit.structured["paper_count_total"] == 6 for audit in audits))

            state = app.store.load()
            self.assertEqual(len(state["problem_observations"]), 203)
            self.assertEqual(state["claims"], {})
            self.assertEqual(
                sum(audit["purpose"] == "literature_discovery" for audit in state["audits"].values()),
                10,
            )
            for brief_id in agenda.brief_ids:
                metadata = state["research_briefs"][brief_id]["metadata"]
                self.assertEqual(metadata["last_literature_discovery"]["paper_count_total"], 6)
                self.assertNotIn("last_grounding", metadata)

    def test_discovery_not_run_is_recorded_without_false_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            deep = FakeDeepResearch(status="not_run")
            app = CiteRefinery(tmp, cite_research=deep)
            project = app.init_project("Unavailable", "Record an unavailable literature backend honestly")
            packet = trace_packets()[0]
            app.ingest_nocturnal_packet(project.id, packet)
            brief = app.prepare_research_brief(project.id)
            audit = app.discover_research_brief(project.id, brief.id, max_questions=2)
            self.assertEqual(audit.status, "not_run")
            self.assertEqual(audit.structured["paper_count_total"], 0)
            self.assertEqual(app.store.load()["claims"], {})

    def test_discovery_bounds_are_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp, cite_research=FakeDeepResearch())
            project = app.init_project("Bounds", "Bound deep research work")
            app.ingest_nocturnal_packet(project.id, trace_packets()[0])
            brief = app.prepare_research_brief(project.id)
            with self.assertRaisesRegex(ValueError, "target_count"):
                app.discover_research_brief(project.id, brief.id, target_count=0)
            with self.assertRaisesRegex(ValueError, "snowball_depth"):
                app.discover_research_brief(project.id, brief.id, snowball_depth=9)
            with self.assertRaisesRegex(ValueError, "max_questions"):
                app.discover_research_brief(project.id, brief.id, max_questions=0)


if __name__ == "__main__":
    unittest.main()
