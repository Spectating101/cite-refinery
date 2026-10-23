import unittest
from cite_refinery.portfolio_cross_project import discover, DossierError


def graph():
    return {
        "atlas_actual_semantic_graph_ingested": True,
        "source_snapshots": [{"repo": "first"}, {"repo": "second"}],
        "packet": {"nodes": [
            {"key": "repo_first", "statement": "Provides reproducible provenance tracking for original sources and receipts.", "layer": "program"},
            {"key": "repo_second", "statement": "Creates reproducible datasets and evidence trails for researchers.", "layer": "program"},
        ], "edges": []}
    }


def result():
    return {"opportunities": [{
        "project_a": "first", "project_b": "second", "kind": "complementarity",
        "evidence_a": "repo_first", "evidence_b": "repo_second",
        "quote_a": "reproducible provenance tracking",
        "quote_b": "reproducible datasets and evidence",
        "hypothesis": "The dataset workflow may benefit from source-linked provenance receipts.",
        "validation_experiment": "Prototype a single evidence export and verify round-trip identity checks.",
        "alternative_explanation": "Both projects may already have incompatible evidence schemas."
    }]}


class CrossProjectTests(unittest.TestCase):
    def test_model_invocation_and_cross_source_receipts(self):
        calls = []
        def model(system, prompt):
            calls.append(prompt)
            return result()
        receipt = discover(graph(), model, model_identifier="unit-stub")
        self.assertEqual(receipt["candidate_count"], 1)
        self.assertTrue(receipt["all_candidates_unverified"])
        self.assertEqual(len(calls), 1)

    def test_swapped_provenance_rejected(self):
        x = result()
        x["opportunities"][0]["evidence_b"] = "repo_first"
        with self.assertRaisesRegex(DossierError, "scope"):
            discover(graph(), lambda *_: x, model_identifier="unit-stub")

    def test_fake_interoperability_quote_rejected(self):
        x = result()
        x["opportunities"][0]["quote_b"] = "successful production deployment"
        with self.assertRaisesRegex(DossierError, "quote B"):
            discover(graph(), lambda *_: x, model_identifier="unit-stub")

    def test_same_repo_cannot_count_as_cross_project(self):
        x = result()
        x["opportunities"][0]["project_b"] = "first"
        with self.assertRaisesRegex(DossierError, "pair"):
            discover(graph(), lambda *_: x, model_identifier="unit-stub")


if __name__ == "__main__":
    unittest.main()
