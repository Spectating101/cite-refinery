"""Actor graph: official court metadata as pending source claims, not proof.

These tests use a labelled Nocturnal contract-double; they do NOT claim
that real Nocturnal capture, identity verification or review took place.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.app import CiteRefinery
from cite_refinery.semantic import SemanticGraph
from cite_refinery.legal_codex_actors import build_actor_graph

REGISTER = Path(__file__).resolve().parents[1] / "examples/legal_codex_indonesia_actor_register_001.json"


def simulated_nocturnal(rows):
    groups = {
        "direct_reviewed_edges": [],
        "source_report_edges": [],
        "pending_review": [],
        "rejected_observations": [],
    }
    for i, row in enumerate(rows):
        record = dict(row, observation_id=f"simulated-{i}")
        group = ("rejected_observations" if row["review_state"] == "rejected" else
                 "pending_review" if row["review_state"] == "pending" else
                 "source_report_edges" if row["evidence_basis"] == "source_report" else
                 "direct_reviewed_edges")
        groups[group].append(record)
    return {
        "schema": "nocturnal_relationship_graph.v1", **groups,
        "boundaries": {
            "reported_edges_excluded_from_graph": True,
            "common_operator_attribution": "not_established",
            "payment_attribution": "not_established",
        },
    }


class ActorBridgeTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(REGISTER.read_text(encoding="utf-8"))

    def project(self, analyzer=simulated_nocturnal):
        return build_actor_graph(self.data, analyzer=analyzer)

    def test_real_court_register_has_no_prematurely_accepted_links(self):
        projection = self.project()
        self.assertEqual(len(self.data["cases"]), 2)
        self.assertEqual(len(self.data["entities"]), 12)
        self.assertEqual(len(self.data["relationships"]), 10)
        self.assertEqual(len(projection["pending_observations"]), 10)
        self.assertEqual(projection["graph_packet"]["edges"], [])
        self.assertEqual(projection["reviewed_direct_relationship_count"], 0)
        self.assertEqual(projection["simulated_relationship_count"], 0)
        self.assertEqual(projection["nocturnal_validator"], "test_double")
        self.assertFalse(projection["publication_authorized"])

    def test_possible_same_person_across_two_cases_never_auto_merges(self):
        projection = self.project()
        candidates = projection["identity_candidates"]
        self.assertEqual(len(candidates), 4)
        self.assertTrue(all(c["merged"] is False for c in candidates))
        actor_nodes = [n for n in projection["graph_packet"]["nodes"]
                       if n["key"].startswith("actor-")]
        self.assertEqual(len(actor_nodes), 12)
        self.assertTrue(all(n["provenance"]["same_name_is_not_same_identity"]
                            for n in actor_nodes))

    def test_source_report_excluded_and_direct_review_stays_candidate(self):
        first, second = self.data["relationships"][:2]
        first.update(review_state="accepted", reviewer="Synthetic reviewer",
                     reviewed_at="2026-11-10")
        second.update(review_state="accepted", reviewer="Synthetic reviewer",
                      reviewed_at="2026-11-10", evidence_basis="source_report")
        projection = self.project()
        self.assertEqual(len(projection["graph_packet"]["edges"]), 1)
        edge = projection["graph_packet"]["edges"][0]
        self.assertEqual(edge["status"], "candidate")
        self.assertEqual(edge["provenance"]["nocturnal_validation"], "simulated_contract_test")
        self.assertFalse(edge["provenance"]["source_integrity_verified"])
        self.assertEqual(projection["reviewed_direct_relationship_count"], 0)
        self.assertEqual(projection["simulated_relationship_count"], 1)
        self.assertEqual(len(projection["source_report_observations"]), 1)

    def test_staged_semantic_import_is_candidate_only(self):
        self.data["relationships"][0].update(review_state="accepted",
                                                reviewer="Synthetic reviewer",
                                                reviewed_at="2026-11-10")
        projection = self.project()
        with tempfile.TemporaryDirectory() as directory:
            app = CiteRefinery(directory)
            project = app.init_project("Test actor review", "Unreviewed case source observations")
            graph = SemanticGraph(app.store)
            preview = graph.preview_packet(project.id, projection["graph_packet"])
            self.assertFalse(preview["authority_boundary_warnings"])
            receipt = graph.ingest_packet(project.id, projection["graph_packet"],
                                          expected_state_digest=preview["state_digest"])
            state = app.store.load()
            self.assertEqual(len(receipt["edge_ids"]), 1)
            self.assertEqual(state["semantic_edges"][receipt["edge_ids"][0]]["status"],
                             "candidate")

    def test_collusion_label_is_not_allowed_as_a_graph_relation(self):
        self.data["relationships"][0]["relation"] = "COLLUDED_WITH"
        with self.assertRaisesRegex(ValueError, "unapproved relation"):
            self.project()

    def test_cross_case_reviewed_link_requires_explicit_identity_resolution(self):
        self.data["relationships"][0]["target_entity_id"] = self.data["entities"][-1]["id"]
        self.data["relationships"][0].update(
            source_url=self.data["cases"][0]["source_url"],
            review_state="accepted", reviewer="Synthetic reviewer", reviewed_at="2026-11-10")
        # Give the target a shared source reference to isolate cross-case rejection.
        target = next(e for e in self.data["entities"]
                      if e["id"] == self.data["relationships"][0]["target_entity_id"])
        target["source_refs"].append(self.data["relationships"][0]["source_url"])
        with self.assertRaisesRegex(ValueError, "cross-case"):
            self.project()

    def test_graph_does_not_accept_fake_nocturnal_promotion(self):
        def corrupt(rows):
            obj = simulated_nocturnal(rows)
            item = obj["pending_review"].pop(0)
            obj["direct_reviewed_edges"].append(item)
            return obj
        with self.assertRaisesRegex(ValueError, "review category"):
            self.project(corrupt)

    def test_graph_does_not_accept_missing_or_invented_links(self):
        def corrupt(rows):
            obj = simulated_nocturnal(rows)
            obj["direct_reviewed_edges"].append(
                dict(rows[0], source_entity_id="invented_actor"))
            return obj
        with self.assertRaisesRegex(ValueError, "lost or duplicated"):
            self.project(corrupt)

    def test_broken_source_reference_rejected(self):
        self.data["relationships"][0]["source_url"] = "https://example.com/fabricated"
        with self.assertRaisesRegex(ValueError, "source not listed"):
            self.project()

    def test_name_or_alias_cannot_claim_verified_identity(self):
        self.data["entities"][0]["identity_status"] = "definitely_same_person"
        with self.assertRaisesRegex(ValueError, "self-certify"):
            self.project()

    def test_review_without_human_reviewer_rejected(self):
        self.data["relationships"][0]["review_state"] = "accepted"
        with self.assertRaisesRegex(ValueError, "reviewer"):
            self.project()

    def test_duplicate_relationship_rejected(self):
        self.data["relationships"].append(copy.deepcopy(self.data["relationships"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate relationship"):
            self.project()


if __name__ == "__main__":
    unittest.main()
