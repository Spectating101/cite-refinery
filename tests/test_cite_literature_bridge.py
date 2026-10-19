"""Synthetic Cite -> existing Nocturnal module regression tests."""
import copy
import tempfile
import unittest
from cite_refinery import CiteRefinery, SemanticGraph, ProductWorkspace
from cite_refinery.cite_literature_bridge import convert_search, resolve_target
from cite_refinery.hosted_store import WorkspaceDB


def source_case():
    return {
        "schema": "cite_refinery.semantic_graph.v1", "source_system": "nocturnal",
        "clusters": [{"key": "nocturnal-china-kangmei-2020",
                      "title": "Kangmei source case",
                      "provenance": {"candidate_id": "china-kangmei-2020",
                                     "frozen_empirical_commit": "a"*40}}],
        "nodes": [{"key": "nocturnal-china-kangmei-2020-scope",
                   "statement": "Kangmei empirical case scope", "layer": "neutral",
                   "clusters": ["nocturnal-china-kangmei-2020"]},
                  {"key": "event-1", "statement": "Administrative sanctions documented",
                   "layer": "practical", "kind": "observation",
                   "clusters": ["nocturnal-china-kangmei-2020"],
                   "source_refs": ["https://example.org/regulator"]}],
        "edges": [{"source": "event-1", "target": "nocturnal-china-kangmei-2020-scope",
                   "relation": "CONTEXT_FOR", "status": "qualified"}],
    }


def literature():
    return {
        "tool": "search", "status": "completed", "paper_count": 1,
        "topic": "Kangmei securities investor protection",
        "papers": [{"source": "semantic_scholar", "title": "Kangmei investor litigation study",
                    "abstract": "This paper investigates Kangmei.",
                    "doi": "10.1234/test.567", "authors": ["Researcher"],
                    "year": 2024, "venue": "Synthetic Journal"}],
    }


class AcademicBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = WorkspaceDB(self.tmp.name + "/research.sqlite3")
        keys = self.db.create_tenant("Research", "owner")
        self.user = keys["owner_user_id"]
        self.project = self.db.create_project(self.user, keys["tenant_id"], "Kangmei", "Case")
        prior = source_case()
        review = self.db.preview(self.user, self.project, prior)
        self.db.enqueue(self.user, self.project, prior, 0, review["packet_digest"])
        assert self.db.run_one_job()["status"] == "succeeded"

    def tearDown(self):
        self.tmp.cleanup()

    def _target(self):
        return resolve_target(self.db.project_state(self.user, self.project),
                              self.project, "china-kangmei-2020")

    def test_shared_cluster_and_candidate_no_false_support(self):
        target = self._target()
        packet = convert_search(literature(), target)
        self.assertEqual([n["layer"] for n in packet["nodes"]], ["academic"])
        self.assertEqual(packet["edges"][0]["status"], "candidate")
        self.assertEqual(packet["conversion_metadata"]["supported_claims"], 0)
        pre = self.db.preview(self.user, self.project, packet)
        self.assertEqual(pre["projected_new_records"]["semantic_clusters"], 0)
        self.assertEqual(pre["projected_new_records"]["semantic_nodes"], 1)
        self.assertEqual(pre["projected_new_records"]["semantic_edges"], 1)
        self.assertEqual(pre["authority_boundary_warnings"], [])
        self.db.enqueue(self.user, self.project, packet, pre["project_revision"], pre["packet_digest"])
        self.assertEqual(self.db.run_one_job()["status"], "succeeded")
        atlas = self.db.project_projection(self.user, self.project)["atlas"]
        self.assertEqual(atlas["summary"]["cluster_count"], 1)
        self.assertEqual(atlas["clusters"][0]["layer_counts"],
                         {"practical": 1, "academic": 1, "program": 0})
        self.assertEqual(atlas["clusters"][0]["missing_layers"], ["program"])
        state = self.db.project_state(self.user, self.project)
        candidates = [e for e in state["semantic_edges"].values()
                      if e["relation"] == "RELATED_TO"]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["status"], "candidate")
        # Candidate links do not enter represented evidence paths.
        p_node = next(n["id"] for n in state["semantic_nodes"].values()
                      if n["layer"] == "practical")
        from cite_refinery.hosted_store import _MemoryStore
        trace = ProductWorkspace(_MemoryStore(state)).trace_node(self.project, p_node)
        self.assertEqual(trace["paths"]["academic"], [])
        repeated = self.db.preview(self.user, self.project, packet)
        self.assertTrue(repeated["already_imported"])

    def test_reject_bad_or_off_topic_literature(self):
        target = self._target()
        source = literature()
        source["papers"][0]["doi"] = ""
        with self.assertRaises(ValueError):
            convert_search(source, target)
        source = literature()
        source["papers"][0]["abstract"] = "Unrelated audit topic"
        source["papers"][0]["title"] = "Unrelated paper"
        with self.assertRaisesRegex(ValueError, "Kangmei"):
            convert_search(source, target)
        source = literature()
        source["papers"][0]["source"] = "untrusted_feeder"
        with self.assertRaises(ValueError):
            convert_search(source, target)

    def test_cannot_create_target_from_unprovenanced_cluster(self):
        state = copy.deepcopy(self.db.project_state(self.user, self.project))
        for cluster in state["semantic_clusters"].values():
            cluster["provenance_receipts"] = []
        with self.assertRaisesRegex(ValueError, "provenance"):
            resolve_target(state, self.project, "china-kangmei-2020")
