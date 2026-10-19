import json
import tempfile
import threading
import unittest
from urllib.parse import quote
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
        "clusters": [
            {"key": "observability", "title": "Population observability"},
            {"key": "replenishment", "title": "Population replenishment"},
        ],
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
            {
                "key": "replenishment-observation",
                "statement": "Incoming animals can replenish a managed local population.",
                "kind": "observation",
                "layer": "practical",
                "clusters": ["replenishment"],
            },
            {
                "key": "replenishment-mechanism",
                "statement": "Open populations can undermine local fertility control.",
                "kind": "mechanism",
                "layer": "academic",
                "clusters": ["replenishment"],
            },
        ],
        "edges": [
            {"source": "observation", "relation": "SUPPORTS", "target": "problem"},
            {"source": "problem", "relation": "MEASURED_BY", "target": "method"},
            {"source": "program", "relation": "PARTIALLY_ADDRESSES", "target": "problem"},
            {
                "source": "replenishment-observation",
                "relation": "SUPPORTS",
                "target": "replenishment-mechanism",
                "status": "qualified",
            },
        ],
    }


class ProductWorkspaceTests(unittest.TestCase):
    def _fixture(self, tmp):
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
        return app, project

    def test_product_core_is_clustered_three_layer_atlas(self):
        with tempfile.TemporaryDirectory() as tmp:
            app, project = self._fixture(tmp)
            view = ProductWorkspace(app.store).project_view(project.id)

            self.assertEqual(view["schema"], "cite_refinery.product_workspace.v2")
            self.assertEqual(view["primary_view"], "map")
            self.assertEqual(view["navigation"], ["map", "records", "project"])
            self.assertEqual(view["atlas"]["schema"], "cite_refinery.clustered_three_layer_map.v1")
            self.assertEqual(view["atlas"]["layers"], ["practical", "academic", "program"])

            by_title = {cluster["title"]: cluster for cluster in view["atlas"]["clusters"]}
            observability = by_title["Population observability"]
            self.assertEqual(
                observability["layer_presence"],
                {"practical": True, "academic": True, "program": True},
            )
            self.assertEqual(observability["intersection"], "practical_academic_program")
            self.assertEqual(observability["missing_layers"], [])
            self.assertEqual(len(observability["neutral_nodes"]), 1)
            self.assertEqual(len(observability["internal_edges"]), 3)

            replenishment = by_title["Population replenishment"]
            self.assertEqual(replenishment["layer_presence"]["practical"], True)
            self.assertEqual(replenishment["layer_presence"]["academic"], True)
            self.assertEqual(replenishment["layer_presence"]["program"], False)
            self.assertEqual(replenishment["missing_layers"], ["program"])
            self.assertEqual(replenishment["intersection"], "practical_academic_no_program")

            self.assertEqual(view["sections"]["practical"]["engine"], "Nocturnal")
            self.assertEqual(view["sections"]["academic"]["engine"], "Cite")
            self.assertEqual(view["sections"]["program"]["engine"], "Refinery")
            self.assertIn("without a chat interface", view["product_boundary"]["ai"])

    def test_cluster_view_and_node_view_are_directly_inspectable(self):
        with tempfile.TemporaryDirectory() as tmp:
            app, project = self._fixture(tmp)
            workspace = ProductWorkspace(app.store)
            atlas = workspace.cluster_atlas(project.id)
            observability = next(c for c in atlas["clusters"] if c["title"] == "Population observability")
            cluster_view = workspace.cluster_view(project.id, observability["id"])
            self.assertEqual(cluster_view["cluster"]["id"], observability["id"])
            self.assertIn("not proof", cluster_view["boundary"])

            problem_node = observability["neutral_nodes"][0]
            node_view = workspace.node_view(project.id, problem_node["id"])
            self.assertEqual(node_view["coverage"]["intersection"], "practical_academic_program")
            self.assertEqual(node_view["trace"]["schema"], "cite_refinery.node_layer_trace.v1")

    def test_project_list_summarizes_mapping_not_internal_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project = app.init_project("One workspace", "One problem")
            projects = ProductWorkspace(app.store).list_projects()
            self.assertEqual(len(projects), 1)
            self.assertEqual(projects[0]["id"], project.id)
            self.assertEqual(
                set(projects[0]["counts"]),
                {
                    "practical_records",
                    "academic_briefs",
                    "semantic_nodes",
                    "semantic_clusters",
                    "program_requirements",
                    "experiments",
                },
            )


class ProductWebShellTests(unittest.TestCase):
    def test_html_is_map_first_and_ai_optional(self):
        self.assertIn("clustered three-layer map", APP_HTML.lower())
        self.assertIn("Practical", APP_HTML)
        self.assertIn("Academic", APP_HTML)
        self.assertIn("Program", APP_HTML)
        self.assertIn("No AI call is required", APP_HTML)
        self.assertIn("data-cluster", APP_HTML)
        self.assertIn("data-node", APP_HTML)
        self.assertIn("setSelectionRange(start,end)", APP_HTML)
        self.assertIn("clusters.filter(c=>(", APP_HTML)
        self.assertIn("find(c=>c.node_count>0)", APP_HTML)
        self.assertNotIn("Ask the AI to begin", APP_HTML)

    def test_http_shell_exposes_atlas_cluster_and_node_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project = app.init_project("HTTP fixture", "Serve one clustered project")
            SemanticGraph(app.store).ingest_packet(project.id, semantic_packet(), packet_ref="fixture.json")
            server = make_server(tmp, host="127.0.0.1", port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                port = server.server_address[1]
                base = f"http://127.0.0.1:{port}"
                with urlopen(f"{base}/api/health", timeout=5) as response:
                    health = json.loads(response.read().decode("utf-8"))
                self.assertEqual(health["status"], "ok")
                self.assertEqual(health["primary_view"], "clustered_three_layer_map")

                with urlopen(f"{base}/api/projects", timeout=5) as response:
                    projects = json.loads(response.read().decode("utf-8"))
                self.assertEqual(projects[0]["id"], project.id)

                pid = quote(project.id, safe="")
                with urlopen(f"{base}/api/projects/{pid}?graph=1", timeout=5) as response:
                    workspace = json.loads(response.read().decode("utf-8"))
                self.assertEqual(workspace["primary_view"], "map")
                self.assertIn("atlas", workspace)

                with urlopen(f"{base}/api/projects/{pid}/atlas", timeout=5) as response:
                    atlas = json.loads(response.read().decode("utf-8"))
                self.assertEqual(atlas["layers"], ["practical", "academic", "program"])
                cluster = next(c for c in atlas["clusters"] if c["title"] == "Population observability")

                cid = quote(cluster["id"], safe="")
                with urlopen(f"{base}/api/projects/{pid}/clusters/{cid}", timeout=5) as response:
                    cluster_view = json.loads(response.read().decode("utf-8"))
                self.assertEqual(cluster_view["cluster"]["title"], "Population observability")

                node = cluster["neutral_nodes"][0]
                nid = quote(node["id"], safe="")
                with urlopen(f"{base}/api/projects/{pid}/nodes/{nid}/coverage?depth=1", timeout=5) as response:
                    node_view = json.loads(response.read().decode("utf-8"))
                self.assertEqual(node_view["coverage"]["intersection"], "practical_academic_program")

                with urlopen(f"{base}/", timeout=5) as response:
                    html = response.read().decode("utf-8")
                self.assertIn("clustered research map", html)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
