"""Meaning of graph traces, especially absent and candidate supply."""
import tempfile
import unittest
from cite_refinery import CiteRefinery, ProductWorkspace, SemanticGraph

def packet():
    return {
        "schema": "cite_refinery.semantic_graph.v1",
        "source_system": "trace-tests",
        "clusters": [{"key": "a", "title": "One module"}],
        "nodes": [
            {"key": "p", "statement": "Observed reality", "kind": "observation", "layer": "practical", "clusters": ["a"], "source_refs": ["https://example.org/practical"]},
            {"key": "k", "statement": "Research method", "kind": "method", "layer": "academic", "clusters": ["a"]},
            {"key": "s", "statement": "Candidate tool", "kind": "program", "layer": "program", "clusters": ["a"]},
            {"key": "u", "statement": "Unconnected tool", "kind": "program", "layer": "program", "clusters": ["a"]},
        ],
        "edges": [
            {"source": "p", "target": "k", "relation": "EXPLAINS", "status": "qualified", "provenance": {"note": "qualified mechanism"}},
            {"source": "k", "target": "s", "relation": "IMPLEMENTS", "status": "candidate"},
            {"source": "p", "target": "u", "relation": "MISSING_LINK", "status": "not_established"},
        ],
    }

class TracePathsTest(unittest.TestCase):
    def test_trace_does_not_upgrade_candidate_or_missing_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project = app.init_project("Trace", "Test provenance")
            SemanticGraph(app.store).ingest_packet(project.id, packet())
            workspace = ProductWorkspace(app.store)
            nodes = workspace.graph.export(project.id)["nodes"]
            p = next(n["id"] for n in nodes.values() if n["statement"] == "Observed reality")
            report = workspace.trace_node(project.id, p, max_depth=4)
            self.assertEqual(len(report["paths"]["practical"]), 1)
            self.assertEqual(len(report["paths"]["academic"]), 1)
            self.assertEqual(report["paths"]["program"], [])
            academic = report["paths"]["academic"][0]
            self.assertTrue(academic["has_qualification"])
            self.assertEqual(academic["steps"][0]["status"], "qualified")
            self.assertEqual(academic["steps"][0]["direction"], "forward")
            self.assertEqual(
                {e["relation"] for e in report["blocked_or_proposed_edges"]},
                {"IMPLEMENTS", "MISSING_LINK"},
            )
            self.assertIn("program", report["not_connected_within_depth"])
            self.assertEqual(workspace.node_view(project.id, p)["trace"], report)

    def test_reverse_traversal_direction_and_missing_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            project = app.init_project("Trace", "Test provenance")
            SemanticGraph(app.store).ingest_packet(project.id, packet())
            workspace = ProductWorkspace(app.store)
            nodes = workspace.graph.export(project.id)["nodes"]
            a = next(n["id"] for n in nodes.values() if n["statement"] == "Research method")
            report = workspace.trace_node(project.id, a)
            self.assertEqual(report["paths"]["practical"][0]["steps"][0]["direction"], "reverse")
            self.assertRaises(ValueError, workspace.trace_node, project.id, "not-a-real-node")
            self.assertRaises(ValueError, workspace.trace_node, project.id, a, max_depth=9)
