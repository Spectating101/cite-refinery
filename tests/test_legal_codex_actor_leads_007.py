"""Actor identity leads: prosecutor initials cannot become signed procurement roles."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from cite_refinery.legal_codex_actors import build_actor_graph

DATA = Path(__file__).resolve().parents[1] / "examples/legal_codex_procurement_actor_leads_007.json"


def simulated_nocturnal(rows):
    groups = {
        "direct_reviewed_edges": [], "source_report_edges": [],
        "pending_review": [], "rejected_observations": [],
    }
    for i, row in enumerate(rows):
        category = (
            "rejected_observations" if row["review_state"] == "rejected" else
            "pending_review" if row["review_state"] == "pending" else
            "source_report_edges" if row["evidence_basis"] == "source_report"
            else "direct_reviewed_edges"
        )
        groups[category].append({**row, "observation_id": f"fixture-{i}"})
    return {
        "schema": "nocturnal_relationship_graph.v1", **groups,
        "boundaries": {
            "reported_edges_excluded_from_graph": True,
            "common_operator_attribution": "not_established",
            "payment_attribution": "not_established",
        },
    }


class ProcurementActorIdentityTests(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads(DATA.read_text(encoding="utf-8"))

    def project(self):
        return build_actor_graph(self.bundle, analyzer=simulated_nocturnal)

    def test_2020_prosecution_matter_not_falsely_called_a_court_case(self):
        projection = self.project()
        nodes = projection["graph_packet"]["nodes"]
        self.assertTrue(any(n["statement"].startswith("Investigation matter ")
                            for n in nodes))
        self.assertTrue(any(n["statement"].startswith("Court case ")
                            for n in nodes))

    def test_initials_only_remain_unresolved_nonmatched(self):
        projection = self.project()
        nodes = {n["key"]: n for n in projection["graph_packet"]["nodes"]}
        for ident in ("ppk_sd_bh", "ppk_sd_wh", "ppk_smp_hs"):
            self.assertEqual(
                nodes["actor-" + ident]["provenance"]["identity_status"],
                "source_initials_unresolved")
        self.assertFalse(any(
            "ppk_sd_wh" in (match["left_entity_id"], match["right_entity_id"])
            or "wahyu_haryadi_index" in (match["left_entity_id"], match["right_entity_id"])
            for match in projection["identity_candidates"]))
        self.assertEqual(projection["graph_packet"]["edges"], [])
        self.assertEqual(len(projection["pending_observations"]), 7)

    def test_unverified_wh_to_named_court_person_is_not_merged(self):
        proj = self.project()
        self.assertEqual(proj["reviewed_direct_relationship_count"], 0)
        self.assertEqual(len(proj["identity_candidates"]), 0)
        self.assertFalse(proj["personal_guilt_established"])
        self.assertFalse(proj["publication_authorized"])

    def test_accepting_initials_based_appointment_fails(self):
        row = next(x for x in self.bundle["relationships"]
                   if x["source_entity_id"] == "ppk_sd_wh")
        row["review_state"] = "accepted"
        row["reviewer"] = "Synthetic reviewer"
        row["reviewed_at"] = "2026-11-10"
        with self.assertRaisesRegex(ValueError, "unresolved initials"):
            self.project()

    def test_a_named_prosecution_report_still_does_not_become_direct_evidence(self):
        row = next(x for x in self.bundle["relationships"]
                   if x["source_entity_id"] == "sri_wahyuningsih")
        row["review_state"] = "accepted"
        row["reviewer"] = "Synthetic reviewer"
        row["reviewed_at"] = "2026-11-10"
        projection = self.project()
        self.assertEqual(len(projection["source_report_observations"]), 1)
        self.assertEqual(projection["graph_packet"]["edges"], [])

    def test_invented_identity_status_rejected(self):
        self.bundle["entities"][1]["identity_status"] = "definitely_Wahyu_Haryadi"
        with self.assertRaisesRegex(ValueError, "self-certify"):
            self.project()

    def test_wrong_report_source_rejected(self):
        self.bundle["relationships"][0]["source_url"] = "https://example.com/fiction"
        with self.assertRaisesRegex(ValueError, "source not listed"):
            self.project()


if __name__ == "__main__":
    unittest.main()
