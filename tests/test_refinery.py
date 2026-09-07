import tempfile
import unittest

from cite_refinery.orchestrator import CiteRefinery


class RefineryOverlayTests(unittest.TestCase):
    def test_project_overlay_is_private_until_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            one = app.init_project("One", "problem one")
            two = app.init_project("Two", "problem two")
            cap = app.refinery.register_capability(
                project_id=one.id,
                name="PDF claim extractor",
                description="Extract bounded claims from PDF evidence",
                tags=["pdf", "claims"],
            )
            self.assertEqual(app.refinery.search("PDF claim", project_id=two.id), [])
            self.assertEqual(app.refinery.search("PDF claim", project_id=one.id)[0]["id"], cap.id)

            promoted = app.promote_capability(one.id, cap.id)
            results = app.refinery.search("PDF claim", project_id=two.id)
            self.assertEqual(results[0]["id"], promoted.id)
            self.assertEqual(results[0]["scope"], "global")

    def test_local_capability_ranks_above_shared_equivalent(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project = app.init_project("Local", "problem")
            app.refinery.register_capability(name="Dataset profiler", description="Profile tabular datasets", tags=["dataset"])
            local = app.refinery.register_capability(project_id=project.id, name="Dataset profiler", description="Project-specific dataset profiler", tags=["dataset"])
            results = app.refinery.search("Dataset profiler", project_id=project.id)
            self.assertEqual(results[0]["id"], local.id)


if __name__ == "__main__":
    unittest.main()
