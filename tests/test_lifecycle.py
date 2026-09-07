import tempfile
import unittest

from cite_refinery.cite import CiteAuditResult
from cite_refinery.orchestrator import CiteRefinery


class FakeCite:
    def ground(self, text: str) -> CiteAuditResult:
        return CiteAuditResult(
            engine="fake:ground_claims",
            status="completed",
            raw="audited",
            structured={"received": text},
        )


class LifecycleTests(unittest.TestCase):
    def test_end_to_end_project_dossier(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp, cite=FakeCite())
            project = app.init_project("Wildlife routing", "Reduce avoidable food waste while respecting species constraints")
            claim = app.add_claim(project.id, "Routing donated food can reduce procurement waste.")
            audit = app.ground(project.id)
            evidence = app.add_evidence(
                project.id,
                source="doi:10.example/test",
                locator="p. 4",
                summary="Pilot evidence",
                claim_ids=[claim.id],
            )
            cap = app.refinery.register_capability(
                project_id=project.id,
                name="Constraint-aware routing",
                description="Route supplies under species and logistics constraints",
                tags=["routing", "constraints"],
            )
            impl = app.refinery.register_implementation(
                capability_id=cap.id,
                project_id=project.id,
                provider="python",
                invocation={"module": "routing.solve"},
            )
            artifact = app.add_artifact(project.id, name="routing-engine", kind="software", reusable=True, capability_id=cap.id)
            experiment = app.add_experiment(
                project.id,
                name="fixture validation",
                method="known-feasible routes",
                result="all fixtures satisfied",
                verdict="passed",
                metrics={"fixtures": 12, "passed": 12},
                claim_ids=[claim.id],
                artifact_ids=[artifact.id],
            )
            promoted = app.promote_capability(project.id, cap.id, experiment.id)
            dossier = app.dossier(project.id)

            self.assertEqual(audit.status, "completed")
            self.assertEqual(dossier["claims"][0]["status"], "audited")
            self.assertEqual(dossier["evidence"][0]["id"], evidence.id)
            self.assertEqual(dossier["implementations"][0]["id"], impl.id)
            self.assertEqual(dossier["experiments"][0]["verdict"], "passed")
            self.assertEqual(promoted.scope, "global")
            self.assertIn("promoted_from", promoted.provenance)
            markdown = app.dossier_markdown(project.id)
            self.assertIn("Routing donated food can reduce procurement waste.", markdown)
            self.assertNotIn("[audited] Routing donated food can reduce procurement waste.\n- None", markdown)

    def test_unavailable_cite_never_marks_claim_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            from cite_refinery.cite import CiteAgentCLIAdapter
            app.cite = CiteAgentCLIAdapter(command="definitely-not-a-real-cite-agent-binary")
            project = app.init_project("Test", "Test safe fallback")
            claim = app.add_claim(project.id, "An unsupported claim")
            audit = app.ground(project.id)
            state = app.store.load()
            self.assertEqual(audit.status, "not_run")
            self.assertEqual(state["claims"][claim.id]["status"], "unverified")


if __name__ == "__main__":
    unittest.main()
