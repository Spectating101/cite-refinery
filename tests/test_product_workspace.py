import json
import tempfile
import threading
import unittest
from urllib.request import urlopen

from cite_refinery import CiteRefinery, ProductWorkspace, SemanticGraph
from cite_refinery.web import APP_HTML, make_server


def nocturnal_packet():
    return {
        "schema": "nocturnal.trace5_empirical_case.v1",
        "candidate_id": "taiwan-stray-dog-observability",
        "country": "Taiwan",
        "domain": "animal_management",
        "matter_id": "taiwan-stray-dog-observability",
        "chain_id": "empirical-taiwan-stray-dog-observability",
        "title": "Taiwan stray dog observability",
        "claims": [
            {
                "claim": "Local free-roaming dog population state is not continuously observed.",
                "matter_id": "taiwan-stray-dog-observability",
                "event_id": "survey-gap",
                "status_stage": "reported",
                "sources": ["https://example.invalid/taiwan-survey"],
                "trace_edges": [],
            }
        ],
    }


def semantic_packet():
    return {
        "schema": "cite_refinery.semantic_graph.v1",
        "source_system": "fixture",
        "clusters": [{"key": "observability", "title": "Population observability"}],
        "nodes": [
            {
                "key": "problem",
                "statement": "Current local free-roaming dog population is not continuously known.",
                "kind": "problem_claim",
                "layer": "neutral",
                "clusters": ["observability"],
            },
            {
                "key": "observation",
                "statement": "Periodic surveys leave intervals without current local estimates.",
                "kind": "observation",
                "layer": "practical",
                "clusters": ["observability"],
            },
            {
                "key": "method",
                "statement": "Repeated individual sightings can support capture-recapture estimation.",
                "kind": "method",
                "layer": "academic",
                "clusters": ["observability"],
            },
            {
                "key": "program",
                "statement": "A street survey program records geolocated sightings.",
                "kind": "program",
                "layer": "program",
                "clusters": ["observability"],
            },
        ],
        "edges": [
            {"source": "observation", "relation": "SUPPORTS", "target": "problem"},
            {"source": "problem", "relation": "MEASURED_BY", "target": "method"},
            {"source": "program", "relation": "PARTIALLY_ADDRESSES", "target": "problem"},
        ],
    }


class ProductWorkspaceTests(unittest.TestCase):
    def test_unified_project_view_preserves_engine_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project = app.init_project(
                "Free-roaming dog management",
                "Understand and reduce persistent free-roaming dog populations.",
            )
            app.ingest_nocturnal_packet(project.id, nocturnal_packet())
            app.prepare_research_brief(project.id, extra_questions=["How can hidden populations be estimated?"])
            app.add_requirement(project.id, "Continuously estimate local free-roaming dog population")
            capability = app.refinery.register_capability(
                project_id=project.id,
                name="street-observation",
                description="Collect structured geolocated street observations.",
                tags=["observability"],
            )
            app.refinery.register_implementation(
                capability_id=capability.id,
                provider="fixture",
                invocation={"command": "echo", "args": ["ok"]},
                project_id=project.id,
                validated=False,
            )
            SemanticGraph(app.store).ingest_packet(project.id, semantic_packet(), packet_ref="fixture.json")

            view = ProductWorkspace(app.store).project_view(project.id)
            self.assertEqual(view["schema"], "cite_refinery.product_workspace.v1")
            self.assertEqual(
                view["navigation"],
                ["overview", "reality", "research", "graph", "solutions", "build", "validate"],
            )
            self.assertEqual(view["sections"]["reality"]["engine"], "Nocturnal")
            self.assertEqual(view["sections"]["research"]["engine"], "Cite")
            self.assertEqual(view["sections"]["solutions"]["engine"], "Refinery")
            self.assertEqual(view["sections"]["graph"]["engine"], "Cite-Refinery Semantic Graph")
            self.assertEqual(view["sections"]["overview"]["reality_observations"], 1)
            self.assertEqual(view["sections"]["overview"]["research_briefs"], 1)
            self.assertEqual(view["sections"]["overview"]["open_requirements"], 1)
            self.assertGreaterEqual(view["sections"]["overview"]["semantic_nodes"], 4)
            self.assertEqual(view["sections"]["solutions"]["capabilities"][0]["name"], "street-observation")
            self.assertIn("graph_export", view)

            problem_node = next(
                node
                for node in view["graph_export"]["nodes"].values()
                if node["statement"].startswith("Current local free-roaming")
            )
            node_view = ProductWorkspace(app.store).node_view(project.id, problem_node["id"])
            self.assertEqual(
                node_view["coverage"]["intersection"],
                "practical_academic_program",
            )

    def test_project_list_is_product_summary_not_raw_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project = app.init_project("One workspace", "One problem")
            projects = ProductWorkspace(app.store).list_projects()
            self.assertEqual(len(projects), 1)
            self.assertEqual(projects[0]["id"], project.id)
            self.assertEqual(
                set(projects[0]["counts"]),
                {"reality", "research", "graph_nodes", "requirements", "experiments"},
            )


class ProductWebShellTests(unittest.TestCase):
    def test_html_exposes_integrated_product_navigation(self):
        for label in ("Reality", "Research", "Semantic map", "Solutions", "Build / Execute", "Validate / Feedback"):
            self.assertIn(label, APP_HTML)
        self.assertIn("Nocturnal", APP_HTML)
        self.assertIn("Refinery", APP_HTML)
        self.assertIn("Cite-Refinery", APP_HTML)
        self.assertIn("state.coverage=data.coverage;renderContent()", APP_HTML)

    def test_http_shell_and_project_api_run_without_external_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project = app.init_project("HTTP fixture", "Serve one integrated project")
            server = make_server(tmp, host="127.0.0.1", port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                port = server.server_address[1]
                with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=5) as response:
                    health = json.loads(response.read().decode("utf-8"))
                self.assertEqual(health["status"], "ok")

                with urlopen(f"http://127.0.0.1:{port}/api/projects", timeout=5) as response:
                    projects = json.loads(response.read().decode("utf-8"))
                self.assertEqual(projects[0]["id"], project.id)

                with urlopen(
                    f"http://127.0.0.1:{port}/api/projects/{project.id}?graph=1",
                    timeout=5,
                ) as response:
                    workspace = json.loads(response.read().decode("utf-8"))
                self.assertEqual(workspace["project"]["id"], project.id)
                self.assertIn("reality", workspace["sections"])
                self.assertIn("solutions", workspace["sections"])

                with urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
                    html = response.read().decode("utf-8")
                self.assertIn("problem intelligence workspace", html)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
