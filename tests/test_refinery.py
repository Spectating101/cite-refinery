import sys
import tempfile
import unittest

from cite_refinery.orchestrator import CiteRefinery


class RefineryOverlayTests(unittest.TestCase):
    def test_project_overlay_is_private_until_validated_promotion(self):
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

            experiment = app.add_experiment(one.id, name="validation", method="fixtures", result="passed", verdict="passed")
            promoted = app.promote_capability(one.id, cap.id, experiment.id)
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

    def test_local_implementation_cannot_run_from_other_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            one = app.init_project("One", "problem")
            two = app.init_project("Two", "problem")
            cap = app.refinery.register_capability(project_id=one.id, name="Private", description="Private tool")
            impl = app.refinery.register_implementation(
                capability_id=cap.id,
                project_id=one.id,
                provider="subprocess",
                invocation={"argv": [sys.executable, "-c", "print('ok')"], "input_mode": "none"},
            )
            with self.assertRaisesRegex(ValueError, "another project's local"):
                app.invoke(two.id, impl.id)

    def test_promoted_implementation_is_executable_by_later_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            one = app.init_project("Builder", "build reusable echo")
            cap = app.refinery.register_capability(project_id=one.id, name="Echo", description="Echo JSON")
            impl = app.refinery.register_implementation(
                capability_id=cap.id,
                project_id=one.id,
                provider="subprocess",
                invocation={"argv": [sys.executable, "-c", "import json,sys; print(json.dumps(json.load(sys.stdin)))"]},
            )
            run = app.invoke(one.id, impl.id, {"x": 1})
            experiment = app.add_experiment(one.id, name="echo validation", method="roundtrip", result="match", verdict="passed", run_ids=[run.id])
            promoted = app.promote_capability(one.id, cap.id, experiment.id)

            state = app.store.load()
            promoted_impl = next(i for i in state["implementations"].values() if i["capability_id"] == promoted.id)
            self.assertTrue(promoted_impl["validated"])

            two = app.init_project("Consumer", "reuse global echo")
            second_run = app.invoke(two.id, promoted_impl["id"], {"x": 2})
            self.assertEqual(second_run.status, "succeeded")
            self.assertEqual(second_run.output, {"x": 2})


if __name__ == "__main__":
    unittest.main()
